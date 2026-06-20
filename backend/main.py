import asyncio
import base64
import json
import logging
import os
import re
import time
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from fastapi import FastAPI, File, Request, UploadFile, Form, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx

from analyzer import run_analysis, AnalysisError, SERVER_ANALYZE_DEADLINE_SECONDS
from tosspayments import (
    issue_billing_key,
    charge_billing,
    verify_webhook_signature,
    TossError,
    TossConfigError,
)
from pipeline.report_pdf import (
    REPORT_TYPES,
    ReportError,
    ReportUnavailableError,
    generate_report_pdf,
)

# ── 서비스 환경 ──────────────────────────────────────────────────────────────
SENTRY_DSN  = os.environ.get("SENTRY_DSN", "")
# BOHUMFIT-060 BF-01: 안전 기본 — SERVICE_ENV 미설정/오타 시 production 취급(디버그·문서 비활성).
#   로컬 개발은 SERVICE_ENV=development 를 명시해야 문서·디버그가 켜진다.
SERVICE_ENV = os.environ.get("SERVICE_ENV", "production")
IS_DEVELOPMENT = SERVICE_ENV.strip().lower() == "development"
IS_PRODUCTION  = not IS_DEVELOPMENT
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

_SENSITIVE_EVENT_EXACT_KEYS = {
    "_data",
    "active_files",
    "all_records",
    "apikey",
    "body",
    "birthdate_pw",
    "contents",
    "data",
    "disease_stats",
    "file_recs",
    "files",
    "gemini_payloads",
    "lines_by_file",
    "parsed_data",
    "parsed_records",
    "pdf_data",
    "raw_entries",
    "raw_response",
    "raw_text",
    "records",
    "result",
    "summary_reports",
    "system_prompt",
    "token",
    "vars",
}

_SENSITIVE_EVENT_KEYWORDS = (
    "authorization",
    "birthdate",
    "cookie",
    "password",
    "disease",
    "gemini",
    "hospital",
    "medical",
    "multipart",
    "patient",
    "pdf",
    "prescription",
    "raw_",
    "record",
    "진료",
    "상병",
    "병원",
    "처방",
)


def _is_sensitive_event_key(key) -> bool:
    key_l = str(key).lower()
    return key_l in _SENSITIVE_EVENT_EXACT_KEYS or any(token in key_l for token in _SENSITIVE_EVENT_KEYWORDS)


def _scrub_sensitive_event_values(value):
    """Sentry event 내부에 남은 PDF·진료기록·Gemini payload 계열 값을 제거."""
    if isinstance(value, dict):
        for key in list(value.keys()):
            if _is_sensitive_event_key(key):
                value[key] = "[Filtered]"
            else:
                value[key] = _scrub_sensitive_event_values(value[key])
        return value
    if isinstance(value, list):
        return [_scrub_sensitive_event_values(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_scrub_sensitive_event_values(item) for item in value)
    return value


def _sanitize_event(event, hint=None):
    """Sentry 전송 전 PDF 바이너리·진료 데이터·이메일 등 민감정보 제거"""
    try:
        req = event.get("request") or {}
        req.pop("data", None)
        req.pop("body", None)
        req.pop("cookies", None)
        req.pop("env", None)
        headers = req.get("headers") or {}
        for k in list(headers.keys()):
            if k.lower() in ("authorization", "cookie", "x-api-key", "apikey"):
                headers[k] = "[Filtered]"
        for ctx in (event.get("contexts") or {}).values():
            if isinstance(ctx, dict):
                for big in ("raw_response", "parsed_records", "summary_reports"):
                    ctx.pop(big, None)
        _scrub_sensitive_event_values(event.get("extra") or {})
        _scrub_sensitive_event_values(event.get("contexts") or {})
        _scrub_sensitive_event_values(event.get("breadcrumbs") or {})
        _scrub_sensitive_event_values(event.get("exception") or {})
    except Exception:
        pass
    return event


if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SERVICE_ENV,
        release=os.environ.get("RAILWAY_GIT_COMMIT_SHA", "dev"),
        traces_sample_rate=0.1,
        profiles_sample_rate=0.0,
        send_default_pii=False,
        include_local_variables=False,
        max_request_body_size="never",
        integrations=[
            FastApiIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        before_send=_sanitize_event,
    )

# ── FastAPI 앱 ───────────────────────────────────────────────────────────────
# BOHUMFIT-060 BF-01·BF-02: 운영(production)은 debug=False·API 문서(/docs·/redoc·/openapi) 비활성.
#   개발(SERVICE_ENV=development)에서만 문서·디버그 노출(로컬 편의).
app = FastAPI(
    title="BOHUMFIT AI Backend",
    version="1.0.0",
    debug=IS_DEVELOPMENT,
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)


# ── BOHUMFIT-060 BF-01: 전역 예외 핸들러 ──────────────────────────────────────
# 미처리 예외의 상세 트레이스백을 클라이언트에 노출하지 않는다(운영·개발 공통).
#   클라이언트엔 일반화 메시지, 상세는 서버 로그/Sentry 로만(052·047 로깅과 일관).
#   HTTPException·RateLimitExceeded 는 각자 핸들러가 처리하므로 여기 도달하지 않는다.
@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled error: %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."},
    )


# ── Rate Limiter ─────────────────────────────────────────────────────────────
# BOHUMFIT-063: 레이트리밋 키 = 인증 사용자(Supabase user id) 우선, 실패 시 IP fallback.
#   문제(060 후속): get_remote_address(IP) 단독 → Railway 프록시 뒤에서 여러 사용자가 같은
#   프록시 IP로 보여 한 명이 한도를 쓰면 전체가 throttle(오작동) + X-Forwarded-For 위조 우회.
#   해결: Authorization Bearer JWT 의 sub 클레임으로 사용자별 한도 분리.
#   ※ key_func 는 매 요청 초기에 실행되고 인증 의존성(verify_jwt)보다 먼저이므로, 여기서는
#     서명 검증을 하지 않고 JWT payload 의 sub 만 가볍게 디코드한다(네트워크·DB 호출 없음).
#     실제 인증·권한은 기존 verify_jwt(Supabase Auth 서버 확인)가 담당 — 키는 식별자 용도뿐.
#     위조 토큰으로 남의 sub 키를 쓰면 그 사용자의 한도를 소모시키는 정도(권한 상승 아님).
def _ratelimit_key(request: Request) -> str:
    try:
        auth = request.headers.get("authorization") or ""
        if auth[:7].lower() == "bearer ":
            parts = auth[7:].strip().split(".")
            if len(parts) == 3 and parts[1]:
                seg = parts[1]
                seg += "=" * (-len(seg) % 4)  # base64url 패딩 보정
                claims = json.loads(base64.urlsafe_b64decode(seg.encode("ascii")))
                sub = claims.get("sub")
                if sub and isinstance(sub, str):
                    return f"user:{sub}"
    except Exception:
        # 토큰 없음·malformed·디코드 실패 등 모두 안전하게 IP fallback (크래시 금지).
        pass
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=_ratelimit_key, default_limits=["60/minute"])
app.state.limiter = limiter


# BOHUMFIT-060 BF-03: 레이트리밋 초과 시 한국어 안내(429). slowapi 기본 영문 응답 대체.
def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "요청이 너무 잦습니다. 잠시 후 다시 시도해 주세요."},
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

# ── CORS ─────────────────────────────────────────────────────────────────────
_default_origins = "https://bohumfit.ai,https://www.bohumfit.ai,https://surit-react.vercel.app,http://localhost:5173,http://localhost:3000"
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", _default_origins).split(",") if o.strip()]
if SERVICE_ENV == "production":
    # 운영 환경에서는 localhost 출처를 허용하지 않는다.
    ALLOWED_ORIGINS = [o for o in ALLOWED_ORIGINS if "localhost" not in o and "127.0.0.1" not in o]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── 로깅 설정 ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bohumfit")
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

# ── 상수 ─────────────────────────────────────────────────────────────────────
PRODUCT_TYPE_MAP = {
    "standard": "건강체/표준체 (일반심사)",
    "easy":     "간편심사 (유병자 3-10-5 기준)",
}

KAKAO_DISCLAIMER = (
    "\n※ BOHUMFIT은 보험 가입·인수·보험금 지급을 보장하지 않는 AI 보조 점검 도구입니다. "
    "최종 고지 범위와 심사 결과는 실제 청약서 문항, 약관, 보험회사 인수 기준에 따라 달라질 수 있습니다.\n"
)


# ── 내부 유틸 ────────────────────────────────────────────────────────────────
class _PDFFile:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def read(self) -> bytes:
        return self._data


def _s(v) -> str:
    """None-safe 문자열 변환: None이면 "" 반환, 그 외 str()."""
    return "" if v is None else str(v)


def _with_kakao_disclaimer(message: str) -> str:
    """고객 안내 복사문 말미에 BOHUMFIT 면책 문구를 1회만 붙인다."""
    if KAKAO_DISCLAIMER.strip() in message:
        return message
    return message.rstrip() + KAKAO_DISCLAIMER


def _kakao_item(item: dict) -> str:
    fd = _s(item.get("first_date"))
    ld = _s(item.get("latest_date"))
    date_str = f"{fd} ~ {ld}" if fd and ld and fd != ld else (fd or ld or "")

    code_clean = _s(item.get("display_code") or item.get("code"))
    raw_hospitals = item.get("hospitals") or []
    hosp_list = [_s(h) for h in (raw_hospitals if isinstance(raw_hospitals, list) else list(raw_hospitals))]
    hosp_str = ", ".join(hosp_list)
    kind = "(한방)" if any(k in hosp_str for k in ["한의원", "한방", "한의"]) else "(양방)"

    inpatient = item.get("inpatient") or 0
    if inpatient > 0:
        visit_str = f"입원{inpatient}일"
    else:
        visit_str = f"통원{item.get('visit') or 1}회"

    line1 = f"{date_str} / {visit_str} / {code_clean} / {kind}{_s(item.get('name'))}\n"

    surgeries = item.get("surgeries") or []
    if surgeries:
        surg_names = [s for s in surgeries if s and s != "수술"]
        line2 = (", ".join(surg_names) if surg_names else "수술") + "\n"
    else:
        detail = _s(item.get("detail"))
        line2 = f"{detail[:60]}\n" if detail else ""

    return line1 + line2 + "\n"


def _build_kakao_message(product_type_kr: str, today, summary_reports: dict) -> str:
    msg = f"[{_s(product_type_kr)} 고지 사항]\n"
    msg += f"기준일: {today.strftime('%Y-%m-%d')}\n\n"

    if not summary_reports:
        msg += "고지 대상 없음\n"
        return msg

    def _q_sort_key(title):
        m = re.search(r'\d+', _s(title))
        return int(m.group()) if m else 999

    for q_title in sorted(summary_reports.keys(), key=_q_sort_key):
        clean_title = re.sub(r"^\[.*?\]\s*", "", _s(q_title))
        msg += f"> {clean_title}\n"
        items_q = summary_reports.get(q_title) or []
        inpatient_items = [i for i in items_q if (i.get("inpatient") or 0) > 0]
        surgery_items   = [i for i in items_q if not (i.get("inpatient") or 0) > 0 and i.get("surgeries")]
        other_items     = [i for i in items_q if not (i.get("inpatient") or 0) > 0 and not i.get("surgeries")]

        if inpatient_items:
            msg += "[입원]\n"
            for item in inpatient_items:
                msg += _kakao_item(item)
        if surgery_items:
            msg += "[수술]\n"
            for item in surgery_items:
                msg += _kakao_item(item)
        if other_items:
            msg += "[통원]\n"
            for item in other_items:
                msg += _kakao_item(item)
        msg += "\n"

    return msg


def _serialize_reports(summary_reports: dict) -> dict:
    def _q_sort_key(title):
        m = re.search(r'\d+', title)
        return int(m.group()) if m else 999

    def _to_list(v):
        if isinstance(v, set):
            return sorted(v)
        return v if v is not None else []

    out = {}
    for q_title in sorted(summary_reports.keys(), key=_q_sort_key):
        items = summary_reports[q_title]
        out[q_title] = [
            {
                **item,
                "surgeries":         _to_list(item.get("surgeries")),
                "procedures":        _to_list(item.get("procedures")),
                "surgery_suspected": _to_list(item.get("surgery_suspected")),
                "additional_tests":  _to_list(item.get("additional_tests")),
                "inpatient_periods": _to_list(item.get("inpatient_periods")),
            }
            for item in items
        ]
    return out


# ── 업로드 제한 ──────────────────────────────────────────────────────────────
# BOHUMFIT-053: 10년 고지형 전체 분석 = 발급기간별 분할 파일 최대 10개(기본/세부/처방 + 연도별 + 자동차).
#   순차 파싱(OOM 핫픽스)으로 메모리 피크는 파일 1개분으로 유지되나, 대용량 PDF 다수 시 총
#   파싱 시간이 ANALYZE_TIMEOUT_SECONDS(300s)에 근접할 수 있음 — handoff 경고 참조.
MAX_FILE_COUNT = 10
MAX_FILE_SIZE  = 15 * 1024 * 1024   # 파일당 15MB
MAX_TOTAL_SIZE = 40 * 1024 * 1024   # 총합 40MB (10개×소형 PDF 충분)
# BOHUMFIT-BUG-006: 318p 대용량 PDF Gemini 응답 + 후처리 합산 ~170s 초과로 타임아웃 연장.
# 기존: 170 (프런트 180초보다 짧게) → 300 으로 상향. 프런트 타임아웃도 함께 검토 필요.
# BOHUMFIT-058: 값(300)은 analyzer.SERVER_ANALYZE_DEADLINE_SECONDS 단일 소스에서 공유한다.
#   analyzer 의 동적 AI 예산이 이 상한을 기준으로 남은 시간을 계산하므로 두 곳이 어긋나면 안 된다.
ANALYZE_TIMEOUT_SECONDS = SERVER_ANALYZE_DEADLINE_SECONDS   # 서버측 분석 상한 (318p 대용량 PDF 대응)

# ── 인증 (Supabase 토큰 검증) ────────────────────────────────────────────────
# JWT 비밀키/서명 알고리즘에 의존하지 않고 Supabase Auth 서버에 토큰을 직접
# 확인한다. Legacy·신형(비대칭 키) 프로젝트 모두에서 동작한다.
_bearer = HTTPBearer(auto_error=True)


async def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    """Supabase Auth 서버에 토큰을 확인해 로그인 진위를 검증하고 사용자 ID를 반환한다."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        logger.error("SUPABASE_URL / SUPABASE_ANON_KEY 미설정 — 인증 검증 불가. 환경변수를 설정하세요.")
        raise HTTPException(status_code=503, detail="서비스 점검 중입니다. 잠시 후 다시 시도해 주세요.")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {credentials.credentials}",
                },
            )
    except httpx.HTTPError as e:
        logger.warning("Supabase 인증 서버 호출 실패: %s", e)
        raise HTTPException(status_code=503, detail="로그인 확인에 실패했습니다. 잠시 후 다시 시도해 주세요.")
    if resp.status_code != 200:
        logger.warning("토큰 검증 실패: status=%s", resp.status_code)
        raise HTTPException(status_code=401, detail="로그인이 필요합니다. 다시 로그인한 뒤 시도해 주세요.")
    try:
        user_id = (resp.json() or {}).get("id")
    except ValueError:
        user_id = None
    if not user_id:
        raise HTTPException(status_code=401, detail="유효하지 않은 인증 토큰입니다.")
    return user_id


# ── 구독·사용량 게이트 (BOHUMFIT-069) ────────────────────────────────────────
# /api/analyze 성공 시 월 30회 한도 체크·차감. internal(profiles.role) 무제한.
# Supabase 서비스롤 키·supabase 패키지가 없으면 게이트 비활성(기존 무료 동작 유지) — graceful.
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
MONTHLY_ANALYZE_LIMIT = 30
_supabase_admin_client = None
_supabase_admin_inited = False


def _get_supabase_admin():
    """서비스롤 Supabase 클라이언트(지연 초기화·캐시). 키/패키지 없으면 None → 게이트 비활성."""
    global _supabase_admin_client, _supabase_admin_inited
    if _supabase_admin_inited:
        return _supabase_admin_client
    _supabase_admin_inited = True
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
        logger.warning("구독 게이트 비활성: SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY 미설정")
        return None
    try:
        from supabase import create_client
        _supabase_admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    except Exception as e:  # 패키지 미설치·초기화 실패 → 비활성(서비스 중단 방지)
        logger.warning("구독 게이트 비활성: supabase 클라이언트 초기화 실패 — %s", e)
        _supabase_admin_client = None
    return _supabase_admin_client


async def _enforce_subscription(user_id: str) -> dict:
    """월 한도·구독 체크. 위반 시 HTTPException(402 구독없음 / 429 한도초과).
    반환 dict: {is_internal, enabled, period_start, period_end}. 동기 SDK는 to_thread로 감싼다."""
    admin = _get_supabase_admin()
    if admin is None:
        return {"is_internal": True, "enabled": False, "period_start": None, "period_end": None}

    def _check() -> dict:
        try:
            prof = admin.table("profiles").select("role").eq("id", user_id).single().execute()
            role = (getattr(prof, "data", None) or {}).get("role")
        except Exception:
            role = None
        if role == "internal":
            return {"is_internal": True, "enabled": True, "period_start": None, "period_end": None}
        try:
            sub = admin.table("subscriptions").select("*").eq("user_id", user_id).eq("status", "active").single().execute()
            sub_data = getattr(sub, "data", None)
        except Exception:
            sub_data = None
        if not sub_data:
            raise HTTPException(status_code=402, detail="구독이 필요합니다.")
        ps, pe = sub_data.get("current_period_start"), sub_data.get("current_period_end")
        usage = (
            admin.table("usage_logs").select("id", count="exact")
            .eq("user_id", user_id).gte("used_at", ps).lte("used_at", pe).execute()
        )
        if (getattr(usage, "count", 0) or 0) >= MONTHLY_ANALYZE_LIMIT:
            raise HTTPException(
                status_code=429,
                detail=f"이번 달 분석 횟수({MONTHLY_ANALYZE_LIMIT}회)를 모두 사용했습니다.",
            )
        return {"is_internal": False, "enabled": True, "period_start": ps, "period_end": pe}

    return await asyncio.to_thread(_check)


async def _log_usage(user_id: str, ctx: dict) -> None:
    """분석 성공 후 usage_logs 1건 적재. internal·게이트 비활성 시 skip. 실패는 분석을 막지 않음."""
    if not ctx.get("enabled") or ctx.get("is_internal"):
        return
    admin = _get_supabase_admin()
    if admin is None:
        return

    def _ins() -> None:
        try:
            admin.table("usage_logs").insert({
                "user_id": user_id,
                "period_start": ctx.get("period_start"),
                "period_end": ctx.get("period_end"),
            }).execute()
        except Exception as e:
            logger.warning("usage_logs insert 실패(분석은 정상 반환): %s", e)

    await asyncio.to_thread(_ins)


# ── 엔드포인트 ───────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    # BOHUMFIT-060 BF-05: 공개 헬스는 최소 정보만 노출(env·deps·커밋해시 제거).
    #   Railway 헬스체크용 200 status 는 유지. 상세 관측은 Sentry 로 일원화.
    return {"status": "ok"}


# ── 구독 결제 (BOHUMFIT-070 토스페이먼츠) ────────────────────────────────────
SUBSCRIPTION_PRICE_KRW = 9900
SUBSCRIPTION_PERIOD_DAYS = 30


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


@app.post("/billing/issue-key")
@limiter.limit("10/minute")
async def billing_issue_key(
    request: Request,
    payload: dict = Body(...),
    user_id: str = Depends(verify_jwt),
):
    """토스 SDK 인증(authKey) → 빌링키 발급 → 최초 9,900원 결제 → subscriptions upsert."""
    admin = _get_supabase_admin()
    if admin is None:
        raise HTTPException(status_code=503, detail="구독 기능을 준비 중입니다. 잠시 후 다시 시도해 주세요.")
    auth_key = (payload.get("authKey") or "").strip()
    customer_key = (payload.get("customerKey") or user_id or "").strip()
    if not auth_key or not customer_key:
        raise HTTPException(status_code=400, detail="authKey·customerKey가 필요합니다.")
    try:
        issued = await issue_billing_key(auth_key, customer_key)
        billing_key = issued.get("billingKey")
        if not billing_key:
            raise TossError("빌링키 발급 응답에 billingKey가 없습니다.")
        order_id = f"sub-{user_id[:8]}-{int(time.time())}"
        payment = await charge_billing(
            billing_key, customer_key, SUBSCRIPTION_PRICE_KRW, order_id, "보험핏 구독 (월 30회)",
        )
    except TossConfigError:
        raise HTTPException(status_code=503, detail="결제 설정이 준비되지 않았습니다. 관리자에게 문의해 주세요.")
    except TossError as e:
        logger.warning("토스 빌링/결제 실패: %s", e)
        raise HTTPException(status_code=502, detail="결제 처리에 실패했어요. 카드 정보를 확인하고 다시 시도해 주세요.")
    if str(payment.get("status")) != "DONE":
        raise HTTPException(status_code=402, detail="결제가 승인되지 않았습니다. 다시 시도해 주세요.")

    start = datetime.now(timezone.utc)
    end = start + timedelta(days=SUBSCRIPTION_PERIOD_DAYS)
    period_start, period_end = _iso(start), _iso(end)

    def _upsert() -> None:
        admin.table("subscriptions").upsert({
            "user_id": user_id,
            "status": "active",
            "plan": "basic",
            "price_krw": SUBSCRIPTION_PRICE_KRW,
            "current_period_start": period_start,
            "current_period_end": period_end,
            "toss_customer_key": customer_key,
            "toss_billing_key": billing_key,
        }, on_conflict="user_id").execute()

    await asyncio.to_thread(_upsert)
    logger.info("subscription activated: user=%s order=%s", user_id[:8], order_id)
    return {"status": "active", "plan": "basic", "period_end": period_end}


@app.post("/billing/webhook")
async def billing_webhook(request: Request):
    """토스 웹훅 — HMAC 서명 검증 후 결제상태 반영(DONE→active / CANCELED·FAIL→inactive)."""
    raw = await request.body()
    secret = os.environ.get("TOSS_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(status_code=503, detail="웹훅 설정이 준비되지 않았습니다.")
    signature = (
        request.headers.get("TossPayments-Signature")
        or request.headers.get("toss-signature")
        or request.headers.get("x-toss-signature")
        or ""
    )
    if not verify_webhook_signature(secret, raw, signature):
        raise HTTPException(status_code=401, detail="유효하지 않은 웹훅 서명입니다.")
    try:
        body = json.loads(raw or b"{}")
    except ValueError:
        raise HTTPException(status_code=400, detail="잘못된 웹훅 본문입니다.")
    data = body.get("data") if isinstance(body.get("data"), dict) else body
    status = str(data.get("status") or "")
    customer_key = data.get("customerKey") or ""
    admin = _get_supabase_admin()
    if admin is None:
        return {"ok": True, "ignored": "subscription backend disabled"}

    new_status = None
    if status == "DONE":
        new_status = "active"
    elif status in ("CANCELED", "CANCELLED", "FAILED", "ABORTED", "EXPIRED"):
        new_status = "inactive"
    if new_status and customer_key:
        def _update() -> None:
            patch = {"status": new_status}
            if new_status == "active":
                start = datetime.now(timezone.utc)
                patch["current_period_start"] = _iso(start)
                patch["current_period_end"] = _iso(start + timedelta(days=SUBSCRIPTION_PERIOD_DAYS))
            try:
                admin.table("subscriptions").update(patch).eq("toss_customer_key", customer_key).execute()
            except Exception as e:
                logger.warning("웹훅 구독 갱신 실패: %s", e)
        await asyncio.to_thread(_update)
    return {"ok": True}


@app.get("/billing/status")
async def billing_status(user_id: str = Depends(verify_jwt)):
    """구독 상태·이번 달 사용량 조회 — { status, plan, period_end, used, limit, is_internal }."""
    admin = _get_supabase_admin()
    if admin is None:
        return {"status": "inactive", "plan": None, "period_end": None,
                "used": 0, "limit": MONTHLY_ANALYZE_LIMIT, "is_internal": False, "enabled": False}

    def _query() -> dict:
        try:
            prof = admin.table("profiles").select("role").eq("id", user_id).single().execute()
            role = (getattr(prof, "data", None) or {}).get("role")
        except Exception:
            role = None
        is_internal = role == "internal"
        try:
            sub = admin.table("subscriptions").select("*").eq("user_id", user_id).single().execute()
            sub_data = getattr(sub, "data", None)
        except Exception:
            sub_data = None
        used = 0
        if sub_data and sub_data.get("status") == "active":
            try:
                u = (
                    admin.table("usage_logs").select("id", count="exact")
                    .eq("user_id", user_id)
                    .gte("used_at", sub_data.get("current_period_start"))
                    .lte("used_at", sub_data.get("current_period_end")).execute()
                )
                used = getattr(u, "count", 0) or 0
            except Exception:
                used = 0
        return {
            "status": (sub_data or {}).get("status", "inactive"),
            "plan": (sub_data or {}).get("plan"),
            "period_end": (sub_data or {}).get("current_period_end"),
            "used": used,
            "limit": MONTHLY_ANALYZE_LIMIT,
            "is_internal": is_internal,
            "enabled": True,
        }

    return await asyncio.to_thread(_query)


@app.post("/api/analyze")
@limiter.limit("5/minute,30/hour")
async def analyze(
    request: Request,
    files: list[UploadFile] = File(..., description="심평원 진료 PDF"),
    reference_date: str = Form(..., description="YYYY-MM-DD"),
    birthdate_pw: str = Form(default="", description="PDF 비밀번호용 생년월일"),
    user_id: str = Depends(verify_jwt),
):
    try:
        ref_date = date.fromisoformat(reference_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="reference_date는 YYYY-MM-DD 형식이어야 합니다.")

    if not files:
        raise HTTPException(status_code=400, detail="PDF 파일을 1개 이상 업로드해 주세요.")

    if len(files) > MAX_FILE_COUNT:
        raise HTTPException(
            status_code=413,
            detail=f"PDF는 최대 {MAX_FILE_COUNT}개까지 업로드할 수 있습니다.",
        )
    for f in files:
        if getattr(f, "size", None) and f.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"개별 PDF 크기는 {MAX_FILE_SIZE // (1024 * 1024)}MB를 넘을 수 없습니다.",
            )

    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="서비스 점검 중입니다. 잠시 후 다시 시도해 주세요.",
        )

    # BOHUMFIT-069: 구독·월 한도 체크(internal 무제한·미설정 시 비활성). 위반 시 402/429.
    _sub_ctx = await _enforce_subscription(user_id)

    logger.info(
        "analyze start: ref_date=%s files=%d",
        reference_date, len(files),
    )

    async def _read(f):
        data = await f.read()
        if len(data) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"개별 PDF 크기는 {MAX_FILE_SIZE // (1024 * 1024)}MB를 넘을 수 없습니다.",
            )
        if b"%PDF-" not in data[:1024]:
            raise HTTPException(
                status_code=400,
                detail="PDF 형식이 아닌 파일이 포함돼 있습니다. 심평원 진료 PDF만 업로드해 주세요.",
            )
        return _PDFFile(name=f.filename or "unknown.pdf", data=data)

    active_files = await asyncio.gather(*[_read(f) for f in files])

    total_size = sum(len(af.read()) for af in active_files)
    if total_size > MAX_TOTAL_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"전체 PDF 합계 크기는 {MAX_TOTAL_SIZE // (1024 * 1024)}MB를 넘을 수 없습니다.",
        )

    # 표준 컨텍스트로 AI 분석 (Q1-Q4 전체 수집) — 간편 결과는 파생
    product_type_kr = PRODUCT_TYPE_MAP["standard"]

    try:
        result = await asyncio.wait_for(
            run_analysis(
                active_files=active_files,
                product_type=product_type_kr,
                reference_date=ref_date,
                birthdate_pw=birthdate_pw,
                api_key=api_key,
            ),
            timeout=ANALYZE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("analyze 시간 초과 (%ss)", ANALYZE_TIMEOUT_SECONDS)
        raise HTTPException(
            status_code=504,
            detail="분석이 시간 내에 끝나지 않았어요. PDF 페이지 수를 줄이거나 잠시 후 다시 시도해 주세요.",
        )
    except AnalysisError as e:
        # 사용자 친화 메시지 그대로 전달 (parse_single_pdf 에서 이미 정제됨)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # 내부 오류는 사용자에게 디테일 노출 금지. 서버 로그·Sentry 에는 남김.
        logger.exception("analyze endpoint failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="서버에서 분석을 완료하지 못했어요. 잠시 후 다시 시도해 주세요.",
        )

    # BOHUMFIT-069: 분석 성공 → 사용량 1건 차감(internal·비활성 시 skip, 실패는 응답 막지 않음).
    await _log_usage(user_id, _sub_ctx)

    std_reports   = result["standard_reports"]
    easy_reports  = result["easy_reports"]
    flagged_codes = result["flagged_codes"]
    today         = result["analysis_today"]
    ai_res        = result["ai_result"]
    meritz        = result.get("meritz_easy", {})
    record_counts = result.get("record_counts", {})
    parse_errors  = result.get("parse_errors", [])

    logger.info(
        "analyze done: flagged=%d total_q=%d records(basic=%d,pharma=%d,detail=%d) parse_errors=%d",
        len(flagged_codes), len(std_reports),
        record_counts.get("basic", 0),
        record_counts.get("pharma", 0),
        record_counts.get("detail", 0),
        len(parse_errors),
    )

    std_kakao  = _build_kakao_message(PRODUCT_TYPE_MAP["standard"], today, std_reports)
    easy_kakao = _build_kakao_message(PRODUCT_TYPE_MAP["easy"],     today, easy_reports)
    if meritz.get("detail_message"):
        std_kakao  += "\n" + meritz["detail_message"]
        easy_kakao += "\n" + meritz["detail_message"]
    std_kakao = _with_kakao_disclaimer(std_kakao)
    easy_kakao = _with_kakao_disclaimer(easy_kakao)

    return {
        "flagged_count":        len(flagged_codes),
        "total_q_count":        len(std_reports),
        "total_visit_sum":      sum(item["visit"] for items in std_reports.values() for item in items),
        "total_med_sum":        sum(item["med_days"] for items in std_reports.values() for item in items),
        "standard_reports":     _serialize_reports(std_reports),
        "easy_reports":         _serialize_reports(easy_reports),
        "all_disease_summary":  result["all_disease_summary"],
        "standard_kakao":       std_kakao,
        "easy_kakao":           easy_kakao,
        "kakao_message":        std_kakao,   # 하위 호환
        "customer_name":        result.get("customer_name", ""),   # BOHUMFIT-065: 출력 파일명용(판정 무관)
        "record_counts":        record_counts,
        "parse_errors":         parse_errors,
        "warnings":             result["retry_warnings"],
        # BOHUMFIT-023: 실손 안내용 급여 본인부담 연도별 (additive — 고지 응답 불변).
        "covered_self_pay_by_year": result.get("covered_self_pay_by_year", {}),
        "covered_self_pay_captured": result.get("covered_self_pay_captured", False),
        "verdict":              ai_res.get("health_verdict") or ai_res.get("simple_verdict", ""),
        "verdict_reason":       ai_res.get("health_reason") or ai_res.get("simple_reason", ""),
        "recommend":            ai_res.get("recommend", ""),
        "meritz_easy_eligible":         meritz.get("meritz_easy_eligible", False),
        "meritz_easy_exception_count":  meritz.get("exception_diseases_count", 0),
        "meritz_easy_recommended_year": meritz.get("recommended_disclosure_year"),
        "meritz_easy_details":          meritz.get("exception_diseases", []) + meritz.get("rejected_diseases", []),
        "meritz_easy_message":          meritz.get("detail_message", ""),
    }


# ── 리포트 PDF (BOHUMFIT-030) ────────────────────────────────────────────────
REPORT_TIMEOUT_SECONDS = 60  # Chromium 렌더 포함 서버측 상한


@app.post("/api/report/pdf")
@limiter.limit("10/minute,60/hour")
async def report_pdf(
    request: Request,
    payload: dict = Body(...),
    user_id: str = Depends(verify_jwt),
):
    """고지/실손 리포트 PDF 생성 — report_type ∈ {disclosure, insurance}.

    금액·판정은 프런트가 보낸 분석 결과(payload)를 그대로 표시한다(재계산 없음).
    응답은 스트림 다운로드(application/pdf)이며, PDF·진료데이터는 서버에
    영구 저장하지 않는다(메모리 내 휘발 처리).
    """
    report_type = str(payload.get("report_type") or "")
    if report_type not in REPORT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="report_type 은 disclosure 또는 insurance 여야 합니다.",
        )

    try:
        pdf = await asyncio.wait_for(
            generate_report_pdf(report_type, payload),
            timeout=REPORT_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("report pdf 시간 초과 (%ss)", REPORT_TIMEOUT_SECONDS)
        raise HTTPException(
            status_code=504,
            detail="리포트 생성이 시간 내에 끝나지 않았어요. 잠시 후 다시 시도해 주세요.",
        )
    except ReportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ReportUnavailableError as e:
        logger.error("report pdf 렌더러 사용 불가: %s", e)
        raise HTTPException(
            status_code=503,
            detail="리포트 생성 기능을 준비 중입니다. 잠시 후 다시 시도해 주세요.",
        )
    except Exception as e:
        logger.exception("report pdf endpoint failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="리포트를 생성하지 못했어요. 잠시 후 다시 시도해 주세요.",
        )

    # BOHUMFIT-065: 파일명 = 보험핏-고지내역-{고객이름}-{기준일}. 고객명은 payload 성명(없으면 폴백),
    #   기준일은 분석 reference_date(없으면 오늘). 비ASCII 호환 위해 RFC 5987 filename* + ASCII filename 병기.
    ref = str(payload.get("reference_date") or date.today().strftime("%Y-%m-%d"))
    safe_name = re.sub(r"[^가-힣A-Za-z0-9]", "", str(payload.get("customer_name") or ""))[:20]
    label = "고지내역" if report_type == "disclosure" else "실손분석"
    base = f"보험핏-{label}-{safe_name}-{ref}" if safe_name else f"보험핏-{label}-{ref}"
    ascii_fallback = f"BF-{report_type}-{ref}.pdf"
    disposition = (
        f'attachment; filename="{ascii_fallback}"; '
        f"filename*=UTF-8''{urllib.parse.quote(base + '.pdf')}"
    )
    logger.info("report pdf done: type=%s bytes=%d", report_type, len(pdf))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": disposition,
            # 민감정보 — 중간 캐시 금지
            "Cache-Control": "no-store",
        },
    )
