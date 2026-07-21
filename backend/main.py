import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
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
from pipeline.coverage_parser import parse_coverage_pdf  # BOHUMFIT-114
from coverage.service import (  # BOHUMFIT-179/193 (KB [전] 파서·신규제안 파서 격리 모듈)
    KBFormatError,
    ProposalParseError,
    analyze_kb_coverage,
    parse_newproposal_files,
)
from coverage.consulting import build_after_result  # BOHUMFIT-186 (컨설팅 후 설계 재계산)
from coverage.export_excel import build_workbook_bytes  # BOHUMFIT-181 (엑셀 내보내기)
from coverage.export_pdf import generate_coverage_pdf   # BOHUMFIT-181 (PDF 내보내기)
# BOHUMFIT-097: 번호 중복 hard-block 제거로 phone_guard 미사용(스펙 완화). 모듈은 보존.
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
from sms_nhn import SMSNotConfigured, SMSSendError, send_sms

# ── 서비스 환경 ──────────────────────────────────────────────────────────────
SENTRY_DSN  = os.environ.get("SENTRY_DSN", "")
# BOHUMFIT-060 BF-01: 안전 기본 — SERVICE_ENV 미설정/오타 시 production 취급(디버그·문서 비활성).
#   로컬 개발은 SERVICE_ENV=development 를 명시해야 문서·디버그가 켜진다.
SERVICE_ENV = os.environ.get("SERVICE_ENV", "production")
IS_DEVELOPMENT = SERVICE_ENV.strip().lower() == "development"
IS_PRODUCTION  = not IS_DEVELOPMENT
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
HCAPTCHA_SECRET = os.environ.get("HCAPTCHA_SECRET", "").strip()
HCAPTCHA_VERIFY_URL = "https://hcaptcha.com/siteverify"

# BOHUMFIT-204 F-02: 사용자별 한도와 별도로 IP 집계 한도를 둔다.
# 계정 다중 생성으로 분석/인증 요청을 분산하는 우회를 줄이되 기존 사용자별 throttle은 유지한다.
PHONE_VERIFY_IP_RATE_LIMIT = "5/minute,20/hour"
PASSWORD_RESET_IP_RATE_LIMIT = "5/minute,20/hour"
COVERAGE_ANALYZE_IP_RATE_LIMIT = "10/minute,60/hour"
ANALYZE_IP_RATE_LIMIT = "15/minute,90/hour"

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


# ── hCaptcha (BOHUMFIT-204 F-02) ─────────────────────────────────────────────
async def _verify_hcaptcha_token(request: Request) -> None:
    """HCAPTCHA_SECRET 설정 환경에서만 휴대폰 인증의 hCaptcha 토큰을 검증한다."""
    if not HCAPTCHA_SECRET:
        return

    token = (request.headers.get("x-hcaptcha-token") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="보안 확인을 완료해 주세요.")

    payload = {"secret": HCAPTCHA_SECRET, "response": token}
    remote_ip = get_remote_address(request)
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(HCAPTCHA_VERIFY_URL, data=payload)
        result = response.json() if response.is_success else {}
    except (httpx.HTTPError, ValueError):
        logger.warning("hCaptcha verification request failed")
        raise HTTPException(status_code=503, detail="보안 확인에 실패했습니다. 잠시 후 다시 시도해 주세요.")

    if not result.get("success"):
        logger.info("hCaptcha verification rejected")
        raise HTTPException(status_code=400, detail="보안 확인을 다시 완료해 주세요.")


# ── CORS ─────────────────────────────────────────────────────────────────────
_default_origins = "https://bohumfit.ai,https://www.bohumfit.ai,http://localhost:5173,http://localhost:3000"
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", _default_origins).split(",") if o.strip()]
if SERVICE_ENV == "production":
    # 운영 환경에서는 localhost 출처를 허용하지 않는다.
    ALLOWED_ORIGINS = [o for o in ALLOWED_ORIGINS if "localhost" not in o and "127.0.0.1" not in o]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    # BOHUMFIT-156a/171b: 히스토리 삭제(DELETE /history/{id})·최근→저장 승격(PATCH /history/{id}/save) 허용.
    allow_methods=["GET", "POST", "DELETE", "PATCH"],
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


def _kakao_values(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        raw_values = value
    else:
        raw_values = [value]
    return [_s(v).strip() for v in raw_values if _s(v).strip()]


def _current_surgery_count(item: dict) -> int:
    if item.get("surgery_count") is not None:
        try:
            return max(0, int(item.get("surgery_count") or 0))
        except (TypeError, ValueError):
            return 0
    if isinstance(item.get("surgery_events"), list):
        return len(item.get("surgery_events") or [])
    if isinstance(item.get("surgery_dates"), list):
        return len(item.get("surgery_dates") or [])
    return len(_kakao_values(item.get("surgeries")))


def _visible_surgery_names(item: dict) -> list[str]:
    if _current_surgery_count(item) <= 0:
        return []
    return [s for s in _kakao_values(item.get("surgeries")) if s and s != "수술"]


def _kakao_has_surgery_signal(item: dict) -> bool:
    return bool(_current_surgery_count(item) > 0 or _kakao_values(item.get("surgery_suspected")))


def _disclosure_window_prefix(text: str) -> str:
    m = re.search(r"\d+\s*년\s*초과\s*\d+\s*년\s*이내|\d+\s*년\s*이내", text or "")
    return re.sub(r"\s+", " ", m.group(0)).strip() if m else ""


def _kakao_display_detail(item: dict) -> str:
    """복사문 판정라인: 입원 회차는 제거하고 현재 표시 범위의 수술/통원/투약만 남긴다."""
    detail = _s(item.get("detail")).strip()
    if not detail:
        return ""
    has_surgery = _current_surgery_count(item) > 0
    has_visit = (item.get("visit") or 0) > 0
    has_med = (item.get("med_days") or 0) > 0
    prefix = _disclosure_window_prefix(detail)
    normalized = re.sub(r"\s*(또는|및|과|와)\s*", "/", detail)
    parts = [p.strip() for p in re.split(r"\s*(?:/|,|·|\n)\s*", normalized) if p.strip()]
    kept = []
    had_inpatient = "입원" in detail
    for part in (parts or [detail]):
        if "입원" in part:
            continue
        if "수술" in part:
            if has_surgery:
                kept.append(part)
            continue
        if "통원" in part:
            if has_visit:
                kept.append(part)
            continue
        if "투약" in part or "처방" in part:
            if has_med:
                kept.append(part)
            continue
        if not had_inpatient:
            kept.append(part)
    if not kept and has_surgery:
        names = _visible_surgery_names(item)
        return f"{prefix + ' ' if prefix else ''}{'수술: ' + ', '.join(names) if names else '수술'}"
    text = " / ".join(kept)
    text = re.sub(r"\s{2,}", " ", text).strip()
    if prefix and not re.search(r"\d+\s*년", text) and re.search(r"수술|통원|투약|처방", text):
        return f"{prefix} {text}"
    return text


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
    # BOHUMFIT-205: 입원은 회차별(입원 개시일 ~ 종료일 / 일수)로 각각 표기한다.
    #   기존 한 줄(최초 진료일 ~ 최종 진료일 / 입원N일)은 여러 회 입원이 하나의 장기 입원처럼
    #   읽혀 입원 일수·기간 혼동을 유발했다(사용자 건의). periods 없으면 기존 형식 폴백.
    _periods = [
        p for p in (item.get("inpatient_periods") or [])
        if isinstance(p, dict) and _s(p.get("start"))
    ]
    if inpatient > 0 and _periods:
        _lines = []
        for p in sorted(_periods, key=lambda x: _s(x.get("start"))):
            st, en = _s(p.get("start")), _s(p.get("end"))
            try:
                dd = int(p.get("days") or 0)
            except (TypeError, ValueError):
                dd = 0
            p_date = f"{st} ~ {en}" if en and en != st else st
            p_days = f"입원{dd}일" if dd > 0 else "입원"
            # BOHUMFIT-213: 회차별 근거(어디서) — 병의원명이 있으면 덧붙인다(없으면 기존 형식 유지).
            p_hosp = _s(p.get("hospital")).strip()
            _tail = f" / {p_hosp}" if p_hosp else ""
            _lines.append(f"{p_date} / {p_days} / {code_clean} / {kind}{_s(item.get('name'))}{_tail}\n")
        line1 = "".join(_lines)
        if len(_periods) >= 2:
            line1 += f"→ 입원 총 {len(_periods)}회 · 합산 {inpatient}일\n"
    else:
        if inpatient > 0:
            visit_str = f"입원{inpatient}일"
        else:
            visit_str = f"통원{item.get('visit') or 1}회"
        # BOHUMFIT-213: 폴백 한 줄에도 근거(어디서) — 병의원 1곳 + 외 N곳 요약.
        _h_tail = ""
        if hosp_list:
            _h_tail = f" / {hosp_list[0]}" + (f" 외 {len(hosp_list) - 1}곳" if len(hosp_list) > 1 else "")
        line1 = f"{date_str} / {visit_str} / {code_clean} / {kind}{_s(item.get('name'))}{_h_tail}\n"

    surgery_count = _current_surgery_count(item)
    surgeries = _visible_surgery_names(item)
    suspected_names = _kakao_values(item.get("surgery_suspected"))
    suspected_grade = _s(item.get("surgery_suspected_grade")).strip()
    if surgery_count > 0:
        line2 = (", ".join(surgeries) if surgeries else "수술") + "\n"
    elif suspected_names:
        suspected_text = ", ".join(suspected_names)
        if suspected_grade:
            suspected_text += f" ({suspected_grade})"
        line2 = f"수술 의심: {suspected_text}\n"
    else:
        detail = _kakao_display_detail(item)
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
        # BOHUMFIT-128: Q2 추가검사·재검사 확인용(exam_check_only) 항목은 고지 복사 텍스트에서 제외
        #   (고지 대상이 아니라 설계사 확인용이므로 고객 안내 메시지에 넣지 않는다).
        items_q = [i for i in (summary_reports.get(q_title) or []) if not i.get("exam_check_only")]
        if not items_q:
            continue
        clean_title = re.sub(r"^\[.*?\]\s*", "", _s(q_title))
        msg += f"> {clean_title}\n"
        inpatient_items = [i for i in items_q if (i.get("inpatient") or 0) > 0]
        surgery_items   = [i for i in items_q if not (i.get("inpatient") or 0) > 0 and _kakao_has_surgery_signal(i)]
        other_items     = [i for i in items_q if not (i.get("inpatient") or 0) > 0 and not _kakao_has_surgery_signal(i)]

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


# ── 구독·사용량 게이트 (BOHUMFIT-069/212/231) ────────────────────────────────
# 분석 성공 시 사용량 체크·기록. admin은 무제한, internal은 월 100회,
# customer/기타 미구독자는 최초 누적 5회. 활성 구독 플랜은 기존 월 한도를 유지한다.
# BOHUMFIT-231: 등급 판정은 profiles.bohumfit_tier 단독 기준 — profiles.role은 FitHere
# 전용(advisor 신분)으로 분리되어 게이트가 읽지 않는다. tier 컬럼 부재·미지값은
# customer 취급(fail-closed) — 구DB에 코드가 먼저 배포돼도 한도만 보수적으로 적용된다.
# Supabase 서비스롤 키·supabase 패키지가 없으면 게이트 비활성(기존 무료 동작 유지) — graceful.
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
# BOHUMFIT-072/212: 플랜·무료 분석. 미구독자는 최초 누적 TRIAL_LIMIT(5)회까지 무료 분석.
PLANS = {
    "trial": {"price_krw": 0,     "limit": 5},     # 무료 분석(미구독·누적)
    "basic": {"price_krw": 14900, "limit": 30},    # 베이직
    "pro":   {"price_krw": 24900, "limit": 100},   # 프로
}
TRIAL_LIMIT = PLANS["trial"]["limit"]
MONTHLY_ANALYZE_LIMIT = PLANS["basic"]["limit"]   # 하위 호환(베이직 기본 한도)
# BOHUMFIT-231: 아래 두 상수는 profiles.bohumfit_tier 값이다(이름은 하위호환 유지).
ADMIN_ROLE = "admin"
INTERNAL_ROLE = "internal"
_supabase_admin_client = None
_supabase_admin_inited = False


def _month_bounds(now: datetime | None = None) -> tuple[str, str]:
    """이번 달(UTC) 시작·다음 달 시작 ISO. internal 월별 집계 창."""
    now = now or datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    nxt = start.replace(year=start.year + 1, month=1) if start.month == 12 else start.replace(month=start.month + 1)
    return start.isoformat(), nxt.isoformat()


def _normalize_bohumfit_tier(value) -> str:
    """profiles.bohumfit_tier 정규화 — null·미지값은 customer(fail-closed, BOHUMFIT-231)."""
    tier = str(value or "customer").strip().lower()
    if tier == ADMIN_ROLE:
        return ADMIN_ROLE
    if tier == INTERNAL_ROLE:
        return INTERNAL_ROLE
    return "customer"


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
        return {"is_admin": False, "is_internal": True, "enabled": False, "period_start": None, "period_end": None}

    def _count_usage(ps: str | None = None, pe: str | None = None) -> int:
        try:
            query = admin.table("usage_logs").select("id", count="exact").eq("user_id", user_id)
            if ps:
                query = query.gte("used_at", ps)
            if pe:
                query = query.lt("used_at", pe)
            u = query.execute()
            return getattr(u, "count", 0) or 0
        except Exception:
            return 0

    def _check() -> dict:
        # BOHUMFIT-231: bohumfit_tier 단독 판정. 컬럼 부재(구DB)·조회 실패 → customer(fail-closed).
        try:
            prof = admin.table("profiles").select("bohumfit_tier").eq("id", user_id).single().execute()
            role = _normalize_bohumfit_tier((getattr(prof, "data", None) or {}).get("bohumfit_tier"))
        except Exception:
            role = "customer"
        if role == ADMIN_ROLE:
            return {
                "is_admin": True,
                "is_internal": False,
                "enabled": True,
                "plan": ADMIN_ROLE,
                "quota_scope": "unlimited",
                "period_start": None,
                "period_end": None,
            }
        if role == INTERNAL_ROLE:
            # BOHUMFIT-110/212: internal = pro 동일 월 100회, 매월 used_at 기준 리셋.
            ips, ipe = _month_bounds()
            ilimit = PLANS["pro"]["limit"]
            if _count_usage(ips, ipe) >= ilimit:
                raise HTTPException(status_code=429, detail=f"이번 달 분석 횟수({ilimit}회)를 모두 사용했습니다.")
            return {
                "is_admin": False,
                "is_internal": True,
                "enabled": True,
                "plan": INTERNAL_ROLE,
                "quota_scope": "monthly",
                "period_start": ips,
                "period_end": ipe,
            }
        # 활성 구독 → 플랜별 한도.
        try:
            sub = admin.table("subscriptions").select("*").eq("user_id", user_id).eq("status", "active").single().execute()
            sub_data = getattr(sub, "data", None)
        except Exception:
            sub_data = None
        if sub_data:
            plan = sub_data.get("plan") or "basic"
            limit = PLANS.get(plan, PLANS["basic"])["limit"]
            ps, pe = sub_data.get("current_period_start"), sub_data.get("current_period_end")
            if _count_usage(ps, pe) >= limit:
                raise HTTPException(status_code=429, detail=f"이번 달 분석 횟수({limit}회)를 모두 사용했습니다.")
            return {
                "is_admin": False,
                "is_internal": False,
                "enabled": True,
                "plan": plan,
                "quota_scope": "subscription",
                "period_start": ps,
                "period_end": pe,
            }
        # BOHUMFIT-212: 미구독 customer/기타 → 최초 누적 무료 분석 TRIAL_LIMIT(5)회.
        if _count_usage() >= TRIAL_LIMIT:
            raise HTTPException(
                status_code=402,
                detail=f"무료 분석 최초 {TRIAL_LIMIT}회를 모두 사용했습니다. 구독 후 계속 이용하세요.",
            )
        return {
            "is_admin": False,
            "is_internal": False,
            "enabled": True,
            "plan": "trial",
            "quota_scope": "lifetime",
            "period_start": None,
            "period_end": None,
        }

    return await asyncio.to_thread(_check)


async def _log_usage(user_id: str, ctx: dict) -> None:
    """분석 성공 후 usage_logs 1건 적재. 게이트 비활성 시 skip. 실패는 분석을 막지 않음.
    BOHUMFIT-212: admin은 무제한이므로 차감하지 않고, internal/customer/구독자는 차감한다."""
    if not ctx.get("enabled"):
        return
    if ctx.get("is_admin") or ctx.get("quota_scope") == "unlimited":
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
@app.get("/health")
@app.get("/api/health")
def health():
    # BOHUMFIT-060 BF-05: 공개 헬스는 최소 정보만 노출(env·deps·커밋해시 제거).
    #   Railway 헬스체크용 200 status 는 유지. 상세 관측은 Sentry 로 일원화.
    return {"status": "ok"}


# ── 구독 결제 (BOHUMFIT-070 토스페이먼츠) ────────────────────────────────────
SUBSCRIPTION_PERIOD_DAYS = 30
# BOHUMFIT-072 오픈 이벤트: 베이직 첫 결제 9,900원(이후 정상가 14,900). 프로는 정상가.
OPEN_EVENT_BASIC_KRW = 9900


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
    plan = (payload.get("plan") or "basic").strip()
    if plan not in ("basic", "pro"):
        plan = "basic"
    if not auth_key or not customer_key:
        raise HTTPException(status_code=400, detail="authKey·customerKey가 필요합니다.")
    # BOHUMFIT-072: 베이직 첫 결제는 오픈 이벤트가(9,900), 프로는 정상가(24,900). 플랜 한도 basic 30·pro 100.
    amount = OPEN_EVENT_BASIC_KRW if plan == "basic" else PLANS[plan]["price_krw"]
    plan_limit = PLANS[plan]["limit"]
    try:
        issued = await issue_billing_key(auth_key, customer_key)
        billing_key = issued.get("billingKey")
        if not billing_key:
            raise TossError("빌링키 발급 응답에 billingKey가 없습니다.")
        order_id = f"sub-{user_id[:8]}-{int(time.time())}"
        payment = await charge_billing(
            billing_key, customer_key, amount, order_id, f"보험핏 {plan} 구독 (월 {plan_limit}회)",
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
            "plan": plan,
            "price_krw": PLANS[plan]["price_krw"],
            "current_period_start": period_start,
            "current_period_end": period_end,
            "toss_customer_key": customer_key,
            "toss_billing_key": billing_key,
        }, on_conflict="user_id").execute()

    await asyncio.to_thread(_upsert)
    logger.info("subscription activated: user=%s plan=%s order=%s", user_id[:8], plan, order_id)
    return {"status": "active", "plan": plan, "period_end": period_end}


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
    """구독 상태·등급별 사용량 조회 — BOHUMFIT-212 role/quota_scope 필드 포함.
    BOHUMFIT-231: 등급 원천은 profiles.bohumfit_tier. 응답 `role` 필드는 하위호환 키로
    유지하되 값은 보험핏 등급(tier)이다(프런트는 is_admin/is_internal/quota_scope만 소비 — 실측)."""
    admin = _get_supabase_admin()
    if admin is None:
        return {"status": "inactive", "plan": None, "period_end": None,
                "used": 0, "limit": TRIAL_LIMIT, "trial_used": 0, "trial_limit": TRIAL_LIMIT,
                "is_internal": False, "is_admin": False, "role": "customer", "quota_scope": "lifetime", "enabled": False}

    def _count(ps=None, pe=None) -> int:
        try:
            query = admin.table("usage_logs").select("id", count="exact").eq("user_id", user_id)
            if ps:
                query = query.gte("used_at", ps)
            if pe:
                query = query.lt("used_at", pe)
            u = query.execute()
            return getattr(u, "count", 0) or 0
        except Exception:
            return 0

    def _query() -> dict:
        # BOHUMFIT-231: bohumfit_tier 단독 판정(게이트와 동일 원천 — 표시·게이트 불일치 방지).
        try:
            prof = admin.table("profiles").select("bohumfit_tier").eq("id", user_id).single().execute()
            role = _normalize_bohumfit_tier((getattr(prof, "data", None) or {}).get("bohumfit_tier"))
        except Exception:
            role = "customer"
        is_admin = role == ADMIN_ROLE
        is_internal = role == INTERNAL_ROLE
        try:
            sub = admin.table("subscriptions").select("*").eq("user_id", user_id).single().execute()
            sub_data = getattr(sub, "data", None)
        except Exception:
            sub_data = None
        is_active = bool(sub_data) and sub_data.get("status") == "active"
        plan = (sub_data or {}).get("plan") if is_active else None
        tps, tpe = _month_bounds()
        quota_scope = "lifetime"
        if is_admin:
            used = 0
            limit = None
            quota_scope = "unlimited"
        elif is_internal:
            # BOHUMFIT-110/212: internal = pro 동일 월 100회.
            used = _count(tps, tpe)
            limit = PLANS["pro"]["limit"]
            quota_scope = "monthly"
        elif is_active:
            used = _count(sub_data.get("current_period_start"), sub_data.get("current_period_end"))
            limit = PLANS.get(plan, PLANS["basic"])["limit"]
            quota_scope = "subscription"
        else:
            used = _count()
            limit = TRIAL_LIMIT
        # BOHUMFIT-212: 무료 분석 사용량은 미구독 customer/기타의 누적 사용량.
        trial_used = used if (not is_active and not is_internal and not is_admin) else 0
        return {
            "status": ADMIN_ROLE if is_admin else "active" if is_active else "inactive",
            "plan": ADMIN_ROLE if is_admin else INTERNAL_ROLE if is_internal else plan,
            "period_end": (sub_data or {}).get("current_period_end") if is_active else None,
            "used": used,
            "limit": limit,
            "trial_used": trial_used,
            "trial_limit": TRIAL_LIMIT,
            "is_internal": is_internal,
            "is_admin": is_admin,
            "role": role,
            "quota_scope": quota_scope,
            "enabled": True,
        }

    return await asyncio.to_thread(_query)


# ── 종수술 환산표 로딩 (BOHUMFIT-238) ───────────────────────────────────────
# Supabase jong_surgery_conversion(Human 수정 가능)을 우선 사용하고, 테이블 미존재·
# 조회 실패·게이트 비활성 시 coverage.jong_surgery.DEFAULT_JONG_TABLE로 fallback
# (배포↔SQL 실행 순서 안전망 — 237-A식). 값은 프로세스 수명 동안 캐시한다.
_jong_table_cache: dict | None = None
_jong_table_loaded = False


def _get_jong_conversion_table() -> dict | None:
    global _jong_table_cache, _jong_table_loaded
    if _jong_table_loaded:
        return _jong_table_cache
    _jong_table_loaded = True
    admin = _get_supabase_admin()
    if admin is None:
        return None
    try:
        res = admin.table("jong_surgery_conversion").select(
            "base_man, tier1_man, tier2_man, tier3_man, tier4_man, tier5_man"
        ).execute()
        rows = getattr(res, "data", None) or []
        table = {
            int(row["base_man"]): (
                int(row["tier1_man"]), int(row["tier2_man"]), int(row["tier3_man"]),
                int(row["tier4_man"]), int(row["tier5_man"]),
            )
            for row in rows
        }
        _jong_table_cache = table or None
    except Exception as e:
        logger.warning("종수술 환산표 조회 실패 — 내장 기본표 fallback: %s", e)
        _jong_table_cache = None
    return _jong_table_cache


# ── 관리자 tier 관리 (BOHUMFIT-233) ─────────────────────────────────────────
# 231/232 이후 tier 변경은 service role 경유만 가능 — admin 전용 API로 SQL 운영을 졸업한다.
# ★'admin' 지정은 API로 불가(422): 권한 상승 오남용 방지를 위해 admin 추가만은 SQL 절차 유지.
# 212 게이트 판정 로직은 무변경 — tier를 "쓰는" API만 신설한다.
ADMIN_TIER_ALLOWED = ("internal", "customer")
ADMIN_TIER_PAGE_SIZE = 200
ADMIN_TIER_MAX_PAGES = 25  # ≤5,000 계정 탐색 상한 — 초과 시 미발견 처리(안전 상한)


def _fetch_bohumfit_tier(admin, user_id: str) -> str:
    """요청자/대상의 현재 tier — 231 게이트와 동일 원천·동일 fail-closed(customer)."""
    try:
        prof = admin.table("profiles").select("bohumfit_tier").eq("id", user_id).single().execute()
        return _normalize_bohumfit_tier((getattr(prof, "data", None) or {}).get("bohumfit_tier"))
    except Exception:
        return "customer"


def _require_tier_admin(user_id: str):
    """admin 클라이언트 확보 + 요청자 bohumfit_tier='admin' 검증. 아니면 403."""
    admin = _get_supabase_admin()
    if admin is None:
        raise HTTPException(status_code=503, detail="관리 기능을 사용할 수 없습니다. 잠시 후 다시 시도해 주세요.")
    if _fetch_bohumfit_tier(admin, user_id) != ADMIN_ROLE:
        raise HTTPException(status_code=403, detail="관리자만 사용할 수 있는 기능입니다.")
    return admin


def _auth_users_page(admin, page: int) -> list:
    """auth.users 페이지 조회 — supabase-py 버전에 따라 list 또는 .users 래핑 응답을 흡수."""
    res = admin.auth.admin.list_users(page=page, per_page=ADMIN_TIER_PAGE_SIZE)
    users = getattr(res, "users", res)
    return list(users or [])


def _auth_email_of(admin, target_id: str) -> str | None:
    try:
        res = admin.auth.admin.get_user_by_id(target_id)
        user = getattr(res, "user", res)
        return getattr(user, "email", None)
    except Exception:
        return None


def _find_auth_user_by_email(admin, email: str):
    """auth.users에서 이메일(lower) 일치 사용자 탐색 — profiles.email NULL 계정 안전.
    SQL JOIN은 PostgREST로 불가하므로 admin API 페이지네이션으로 대체(서비스 롤 전용)."""
    target = email.strip().lower()
    for page in range(1, ADMIN_TIER_MAX_PAGES + 1):
        try:
            users = _auth_users_page(admin, page)
        except Exception:
            return None
        for user in users:
            if (getattr(user, "email", "") or "").strip().lower() == target:
                return user
        if len(users) < ADMIN_TIER_PAGE_SIZE:
            return None
    return None


@app.get("/admin/tier/list")
async def admin_tier_list(user_id: str = Depends(verify_jwt)):
    """admin/internal 계정 목록 — PII 최소화: 이메일·tier만 반환(이름·전화 등 미반환)."""
    def _q() -> dict:
        admin = _require_tier_admin(user_id)
        try:
            rows = (
                admin.table("profiles")
                .select("id, bohumfit_tier")
                .in_("bohumfit_tier", ["admin", "internal"])
                .execute()
            )
            data = getattr(rows, "data", None) or []
        except Exception:
            raise HTTPException(status_code=502, detail="목록 조회에 실패했습니다. 잠시 후 다시 시도해 주세요.")
        members = []
        for row in data:
            members.append({
                "email": _auth_email_of(admin, row.get("id")) or "(이메일 확인 불가)",
                "tier": row.get("bohumfit_tier"),
            })
        members.sort(key=lambda m: (m["tier"] != ADMIN_ROLE, m["email"]))
        return {"members": members}

    return await asyncio.to_thread(_q)


@app.post("/admin/tier/set")
async def admin_tier_set(payload: dict = Body(...), user_id: str = Depends(verify_jwt)):
    """이메일로 대상 지정 → bohumfit_tier 'internal'(지정)/'customer'(해제)."""
    def _q() -> dict:
        admin = _require_tier_admin(user_id)
        email = str(payload.get("email") or "").strip()
        tier = str(payload.get("tier") or "").strip().lower()
        if not email or "@" not in email:
            raise HTTPException(status_code=422, detail="올바른 이메일을 입력해 주세요.")
        if tier not in ADMIN_TIER_ALLOWED:
            # 'admin' 포함 그 외 값 전부 거부 — admin 추가는 SQL 절차 유지(파일 상단 주석).
            raise HTTPException(status_code=422, detail="지정 가능한 등급은 internal 또는 customer뿐입니다.")
        target = _find_auth_user_by_email(admin, email)
        if target is None:
            raise HTTPException(status_code=404, detail="해당 이메일로 가입된 계정이 없습니다. 가입 후 다시 시도해 주세요.")
        target_id = str(getattr(target, "id", "") or "")
        if not target_id:
            raise HTTPException(status_code=502, detail="대상 계정 정보를 확인하지 못했습니다.")
        if target_id == user_id:
            raise HTTPException(status_code=400, detail="자기 자신의 등급은 변경할 수 없습니다.")
        if _fetch_bohumfit_tier(admin, target_id) == ADMIN_ROLE:
            # admin 강등도 API로 불가 — 마지막 admin 잠금·상호 강등 사고 방지(SQL 절차 유지).
            raise HTTPException(status_code=400, detail="admin 계정의 등급은 API로 변경할 수 없습니다.")
        try:
            # 1004 phone_verified와 동일 패턴 — 행 없어도 생성되도록 upsert. tier 외 컬럼 무접촉.
            admin.table("profiles").upsert(
                {"id": target_id, "bohumfit_tier": tier}, on_conflict="id"
            ).execute()
        except Exception:
            raise HTTPException(status_code=502, detail="등급 반영에 실패했습니다. 잠시 후 다시 시도해 주세요.")
        return {"ok": True, "email": email, "tier": tier}

    return await asyncio.to_thread(_q)


# ── 휴대폰 본인인증 (BOHUMFIT-074 — 현재 스텁, 추후 토스 본인인증 라이브 키 후 실연동) ──
@app.post("/auth/verify-phone")
@limiter.limit("10/minute")
@limiter.limit(PHONE_VERIFY_IP_RATE_LIMIT, key_func=get_remote_address)
async def verify_phone(
    request: Request,
    payload: dict = Body(...),
    user_id: str = Depends(verify_jwt),
):
    """휴대폰 본인인증 결과 수신 → profiles.phone_verified=true 마킹.
    TODO: 통신사 본인인증(PASS/OTP) 라이브 연동 후 실제 검증(토큰/CI 대조) 추가. 현재는 스텁.
    BOHUMFIT-097: 번호 소유 확인 수준으로 완화 — 동일 번호 중복 hard-block(088 409) 제거.
      (어뷰징 방지 1인 1계정은 087 CI 기반 실연동에서 완성. ★중복 허용엔 088 DB unique index
       profiles_phone_verified_unique drop 필요 — 미적용 시 upsert가 unique 위반으로 실패함.)"""
    await _verify_hcaptcha_token(request)
    phone = (payload.get("phone") or "").strip()
    admin = _get_supabase_admin()
    if admin is not None:
        def _update() -> None:
            try:
                # BOHUMFIT-085: UPDATE→UPSERT. profiles 행이 없는 계정(소셜·기존 가입)도
                # 인증 즉시 행이 생성·반영되어 게이트를 통과(행 없음 → UPDATE no-op 잠금 방지).
                patch: dict = {"id": user_id, "phone_verified": True}
                if phone:
                    patch["phone"] = phone
                admin.table("profiles").upsert(patch, on_conflict="id").execute()
            except Exception as e:
                logger.warning("phone_verified 갱신 실패: %s", e)
        await asyncio.to_thread(_update)
    return {"verified": True, "message": "본인인증이 완료되었습니다."}


# ── 비밀번호 찾기: SMS 코드 → 서버 검증 → Supabase Admin 비밀번호 변경 (BOHUMFIT-216) ──
PASSWORD_RESET_CODE_TTL_SECONDS = 5 * 60
PASSWORD_RESET_TOKEN_TTL_SECONDS = 10 * 60
PASSWORD_RESET_MAX_ATTEMPTS = 5
_password_reset_codes: dict[str, dict] = {}
_password_reset_tokens: dict[str, dict] = {}


def _normalize_phone_digits(phone: str) -> str:
    return re.sub(r"[^0-9]", "", phone or "")


def _password_reset_secret() -> str:
    return os.environ.get("PASSWORD_RESET_OTP_SECRET", "").strip() or SUPABASE_SERVICE_KEY or "bohumfit-local-reset-secret"


def _hash_reset_code(phone: str, code: str) -> str:
    msg = f"{phone}:{code}".encode("utf-8")
    return hmac.new(_password_reset_secret().encode("utf-8"), msg, hashlib.sha256).hexdigest()


def _cleanup_password_reset_store(now: float | None = None) -> None:
    now = now or time.time()
    for key in [k for k, v in _password_reset_codes.items() if float(v.get("expires_at", 0)) < now]:
        _password_reset_codes.pop(key, None)
    for key in [k for k, v in _password_reset_tokens.items() if float(v.get("expires_at", 0)) < now]:
        _password_reset_tokens.pop(key, None)


async def _find_verified_profile_by_phone(phone: str) -> str | None:
    admin = _get_supabase_admin()
    if admin is None:
        raise HTTPException(status_code=503, detail="비밀번호 재설정 서버 설정이 아직 완료되지 않았습니다.")

    def _query():
        res = (
            admin.table("profiles")
            .select("id, phone, phone_verified")
            .eq("phone", phone)
            .eq("phone_verified", True)
            .execute()
        )
        data = getattr(res, "data", None) or []
        return data[0].get("id") if data else None

    return await asyncio.to_thread(_query)


async def _get_auth_user_record(user_id: str) -> dict:
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
        raise HTTPException(status_code=503, detail="비밀번호 재설정 서버 설정이 아직 완료되지 않았습니다.")
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(
                f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
                headers={"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"},
            )
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="회원 정보를 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.")
    if res.status_code == 404:
        raise HTTPException(status_code=404, detail="등록된 휴대폰 번호를 확인해 주세요.")
    if res.status_code >= 400:
        raise HTTPException(status_code=503, detail="회원 정보를 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.")
    try:
        return res.json()
    except ValueError:
        raise HTTPException(status_code=503, detail="회원 정보를 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.")


def _auth_user_provider_label(user: dict) -> str:
    providers = list((user.get("app_metadata") or {}).get("providers") or [])
    for identity in user.get("identities") or []:
        provider = (identity or {}).get("provider")
        if provider and provider not in providers:
            providers.append(provider)
    labels = {"kakao": "카카오", "google": "Google"}
    social = [labels[p] for p in providers if p in labels]
    return "/".join(social)


def _auth_user_has_password(user: dict) -> bool:
    providers = list((user.get("app_metadata") or {}).get("providers") or [])
    providers.extend((identity or {}).get("provider") for identity in (user.get("identities") or []))
    providers = [p for p in providers if p]
    if "email" in providers:
        return True
    return bool(user.get("email")) and not providers


async def _update_supabase_user_password(user_id: str, password: str) -> None:
    if not (SUPABASE_URL and SUPABASE_SERVICE_KEY):
        raise HTTPException(status_code=503, detail="비밀번호 재설정 서버 설정이 아직 완료되지 않았습니다.")
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.put(
                f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
                headers={
                    "apikey": SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                    "Content-Type": "application/json",
                },
                json={"password": password},
            )
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="비밀번호 변경 요청에 실패했습니다. 잠시 후 다시 시도해 주세요.")
    if res.status_code >= 400:
        raise HTTPException(status_code=503, detail="비밀번호 변경 요청에 실패했습니다. 잠시 후 다시 시도해 주세요.")


@app.post("/auth/password-reset/request")
@limiter.limit(PASSWORD_RESET_IP_RATE_LIMIT, key_func=get_remote_address)
async def password_reset_request(request: Request, payload: dict = Body(...)):
    await _verify_hcaptcha_token(request)
    phone = _normalize_phone_digits(payload.get("phone") or "")
    if len(phone) < 10:
        raise HTTPException(status_code=400, detail="등록 휴대폰 번호를 정확히 입력해 주세요.")

    user_id = await _find_verified_profile_by_phone(phone)
    if not user_id:
        raise HTTPException(status_code=404, detail="등록된 휴대폰 번호를 확인해 주세요.")

    user = await _get_auth_user_record(user_id)
    if not _auth_user_has_password(user):
        provider = _auth_user_provider_label(user) or "소셜"
        raise HTTPException(status_code=400, detail=f"{provider} 로그인 계정은 비밀번호가 없습니다. 해당 소셜 버튼으로 로그인해 주세요.")

    code = f"{secrets.randbelow(1_000_000):06d}"
    try:
        await send_sms(phone, f"[보험핏] 비밀번호 재설정 인증번호는 {code} 입니다. 5분 안에 입력해 주세요.")
    except SMSNotConfigured:
        raise HTTPException(status_code=503, detail="NHN SMS 모듈 또는 발신번호 승인이 아직 준비되지 않아 실발송할 수 없습니다.")
    except SMSSendError:
        raise HTTPException(status_code=503, detail="SMS 발송에 실패했습니다. 잠시 후 다시 시도해 주세요.")

    _cleanup_password_reset_store()
    _password_reset_codes[phone] = {
        "user_id": user_id,
        "code_hash": _hash_reset_code(phone, code),
        "expires_at": time.time() + PASSWORD_RESET_CODE_TTL_SECONDS,
        "attempts": 0,
    }
    return {"sent": True, "message": "등록된 휴대폰으로 인증번호를 보냈습니다."}


@app.post("/auth/password-reset/verify")
@limiter.limit(PASSWORD_RESET_IP_RATE_LIMIT, key_func=get_remote_address)
async def password_reset_verify(request: Request, payload: dict = Body(...)):
    phone = _normalize_phone_digits(payload.get("phone") or "")
    code = re.sub(r"[^0-9]", "", payload.get("code") or "")
    _cleanup_password_reset_store()
    row = _password_reset_codes.get(phone)
    if not row:
        raise HTTPException(status_code=400, detail="인증번호가 만료되었거나 요청 이력이 없습니다.")
    row["attempts"] = int(row.get("attempts") or 0) + 1
    if row["attempts"] > PASSWORD_RESET_MAX_ATTEMPTS:
        _password_reset_codes.pop(phone, None)
        raise HTTPException(status_code=400, detail="인증번호 입력 횟수를 초과했습니다. 다시 요청해 주세요.")
    if not code or not hmac.compare_digest(row.get("code_hash") or "", _hash_reset_code(phone, code)):
        raise HTTPException(status_code=400, detail="인증번호가 일치하지 않습니다.")

    token = secrets.token_urlsafe(32)
    _password_reset_tokens[token] = {
        "user_id": row["user_id"],
        "phone": phone,
        "expires_at": time.time() + PASSWORD_RESET_TOKEN_TTL_SECONDS,
    }
    _password_reset_codes.pop(phone, None)
    return {"verified": True, "reset_token": token, "message": "휴대폰 인증이 완료되었습니다."}


@app.post("/auth/password-reset/confirm")
@limiter.limit(PASSWORD_RESET_IP_RATE_LIMIT, key_func=get_remote_address)
async def password_reset_confirm(request: Request, payload: dict = Body(...)):
    token = (payload.get("reset_token") or "").strip()
    password = payload.get("password") or ""
    if len(password) < 10:
        raise HTTPException(status_code=400, detail="새 비밀번호는 10자 이상으로 입력해 주세요.")

    _cleanup_password_reset_store()
    row = _password_reset_tokens.pop(token, None)
    if not row:
        raise HTTPException(status_code=400, detail="재설정 인증이 만료되었습니다. 다시 인증해 주세요.")

    await _update_supabase_user_password(row["user_id"], password)
    return {"updated": True, "message": "비밀번호가 변경되었습니다. 새 비밀번호로 로그인해 주세요."}


# ── 분석 히스토리 (BOHUMFIT-156a) ────────────────────────────────────────────
# 설계사가 분석 결과를 별칭(label)으로 저장해 두고 재열람하는 기능.
# - 테이블 bohumfit_analysis_history + RLS는 Human이 Supabase에 생성 완료(가정 스키마:
#   id uuid PK, user_id uuid, label text, mode text, result jsonb, created_at timestamptz).
# - 접근은 service role(_get_supabase_admin) → RLS 우회이므로 모든 쿼리에
#   .eq("user_id", user_id) 소유권 필터를 강제한다(usage_logs·billing 패턴 동일).
# - 무료 저장 한도 10건 / profiles.role='internal' 무제한 (Human 확정 정책).
# - 보관 90일: 조회에서 제외(gte cutoff) + 본인 접근 시 만료분 lazy 삭제.
#   (Railway 단일 프로세스에 스케줄러가 없어 cron 대신 접근 시점 정리 —
#    조회 필터가 노출 0을 보장하므로 삭제 지연은 보관 비용 문제일 뿐 노출 위험 아님.)
# - ★실명 저장 금지: result.customer_name(심평원 PDF 추출 실명)은 저장 전 서버에서 제거.
HISTORY_TABLE = "bohumfit_analysis_history"
HISTORY_FREE_LIMIT = 10            # 무료 저장 한도(internal 외 전 사용자) — saved 트랙
HISTORY_RETENTION_DAYS = 90        # saved 트랙 보관 기간(일)
HISTORY_MAX_RESULT_BYTES = 1_000_000   # result jsonb 상한(실측 극단 ~350KB의 여유 2.8배)
HISTORY_MAX_LABEL_LEN = 40
HISTORY_LIST_MAX = 50              # 페이지네이션 limit 상한
# BOHUMFIT-171b: 2트랙 — recent(분석 시 자동 기록·10개 롤링·7일 보관) / saved(수동 저장·기존 156 정책).
#   track 컬럼('recent'|'saved', 기본 'saved')은 Human이 SQL로 추가 완료.
HISTORY_TRACKS = ("recent", "saved")
HISTORY_RECENT_LIMIT = 10          # recent 롤링 개수(전 사용자 공통, 한도 검사 아님)
HISTORY_RECENT_RETENTION_DAYS = 7  # recent 보관 기간(일)


def _history_retention_days(track: str) -> int:
    return HISTORY_RECENT_RETENTION_DAYS if track == "recent" else HISTORY_RETENTION_DAYS


def _history_cutoff_dt(track: str = "saved") -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=_history_retention_days(track))


def _history_parse_dt(value):
    """Supabase timestamptz 문자열 → aware datetime. 실패 시 None(만료 판정 보수적 skip)."""
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _require_history_admin():
    admin = _get_supabase_admin()
    if admin is None:
        raise HTTPException(status_code=503, detail="히스토리 기능을 준비 중입니다. 잠시 후 다시 시도해 주세요.")
    return admin


def _history_is_internal(admin, user_id: str) -> bool:
    try:
        prof = admin.table("profiles").select("role").eq("id", user_id).single().execute()
        return ((getattr(prof, "data", None) or {}).get("role")) == "internal"
    except Exception:
        return False


def _history_count(admin, user_id: str, cutoff_iso: str) -> int:
    """saved 트랙 저장 개수 — 무료 한도 검사용(recent는 한도 소모 안 함 — BOHUMFIT-171b)."""
    try:
        r = (
            admin.table(HISTORY_TABLE).select("id", count="exact")
            .eq("user_id", user_id).eq("track", "saved").gte("created_at", cutoff_iso).execute()
        )
        return getattr(r, "count", 0) or 0
    except Exception:
        # 게이트 계열과 동일한 가용성 우선(graceful) — 집계 실패가 저장을 막지 않는다.
        return 0


def _history_lazy_purge(admin, user_id: str) -> None:
    """만료분 lazy 삭제(본인 레코드만) — saved 90일·recent 7일(BOHUMFIT-171b).
    실패해도 요청은 진행(조회 필터가 노출 차단)."""
    for track in HISTORY_TRACKS:
        try:
            cutoff = _history_cutoff_dt(track).isoformat()
            (
                admin.table(HISTORY_TABLE).delete()
                .eq("user_id", user_id).eq("track", track).lt("created_at", cutoff).execute()
            )
        except Exception as e:
            logger.warning("history lazy purge 실패(요청은 진행, track=%s): %s", track, e)


def _history_trim_recent(admin, user_id: str) -> None:
    """BOHUMFIT-171b: recent 롤링 — 최신 HISTORY_RECENT_LIMIT개 초과분(오래된 순)을 삭제."""
    try:
        res = (
            admin.table(HISTORY_TABLE).select("id")
            .eq("user_id", user_id).eq("track", "recent")
            .order("created_at", desc=True)
            .range(HISTORY_RECENT_LIMIT, HISTORY_RECENT_LIMIT + HISTORY_LIST_MAX - 1)
            .execute()
        )
        extra_ids = [r.get("id") for r in (getattr(res, "data", None) or []) if r.get("id")]
        if extra_ids:
            admin.table(HISTORY_TABLE).delete().eq("user_id", user_id).in_("id", extra_ids).execute()
    except Exception as e:
        logger.warning("recent 롤링 삭제 실패(요청은 진행): %s", e)


async def _history_record_recent(user_id: str, result: dict, reference_date: str) -> None:
    """BOHUMFIT-171b: 분석 완료 시 recent 자동 기록 — 어떤 실패도 분석 응답을 막지 않는다(격리).
    실명(customer_name)은 156a 정책 그대로 저장 전 제거. label은 기준일 기반 자동 생성."""
    try:
        admin = _get_supabase_admin()
        if admin is None:
            return

        payload = dict(result)
        payload.pop("customer_name", None)
        payload["reference_date"] = reference_date
        if len(json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")) > HISTORY_MAX_RESULT_BYTES:
            logger.warning("recent 자동 기록 skip: 결과 크기 상한 초과")
            return

        def _rec() -> None:
            admin.table(HISTORY_TABLE).insert({
                "user_id": user_id,
                "label": f"{reference_date} 분석",
                "mode": "standard",
                "result": payload,
                "track": "recent",
            }).execute()
            _history_trim_recent(admin, user_id)

        await asyncio.to_thread(_rec)
    except Exception as e:
        logger.warning("recent 자동 기록 실패(분석 응답은 정상 반환): %s", e)


@app.post("/history")
@limiter.limit("20/minute")
async def history_create(
    request: Request,
    payload: dict = Body(...),
    user_id: str = Depends(verify_jwt),
):
    """분석 결과 저장 — {label(별칭·실명 금지), mode(standard|easy), result(분석 응답 JSON), track?}.
    BOHUMFIT-171b: track='recent'(자동 기록 트랙·한도 없음·10개 롤링)|'saved'(기본·기존 156 정책)."""
    label = str(payload.get("label") or "").strip()
    mode = str(payload.get("mode") or "").strip()
    track = str(payload.get("track") or "saved").strip()
    result = payload.get("result")
    if not label:
        raise HTTPException(status_code=400, detail="저장할 별칭을 입력해 주세요.")
    if len(label) > HISTORY_MAX_LABEL_LEN:
        raise HTTPException(status_code=400, detail=f"별칭은 {HISTORY_MAX_LABEL_LEN}자 이내로 입력해 주세요.")
    if mode not in PRODUCT_TYPE_MAP:
        raise HTTPException(status_code=400, detail="mode는 standard 또는 easy여야 합니다.")
    if track not in HISTORY_TRACKS:
        raise HTTPException(status_code=400, detail="track은 recent 또는 saved여야 합니다.")
    if not isinstance(result, dict) or not result:
        raise HTTPException(status_code=400, detail="저장할 분석 결과가 없습니다. 분석을 먼저 실행해 주세요.")

    # ★실명 저장 금지(Human 정책): PDF에서 추출된 고객 실명 필드는 저장하지 않는다.
    result = dict(result)
    result.pop("customer_name", None)

    try:
        result_bytes = len(json.dumps(result, ensure_ascii=False, default=str).encode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="분석 결과 형식이 올바르지 않습니다.")
    if result_bytes > HISTORY_MAX_RESULT_BYTES:
        raise HTTPException(status_code=413, detail="분석 결과가 너무 커서 저장할 수 없어요.")

    admin = _require_history_admin()

    def _create() -> dict:
        _history_lazy_purge(admin, user_id)
        is_internal = _history_is_internal(admin, user_id)
        used = None
        # BOHUMFIT-171b: 한도 검사는 saved 트랙만(recent는 롤링으로 자체 상한).
        if track == "saved" and not is_internal:
            used = _history_count(admin, user_id, _history_cutoff_dt("saved").isoformat())
            if used >= HISTORY_FREE_LIMIT:
                raise HTTPException(
                    status_code=409,
                    detail=f"히스토리 저장 한도({HISTORY_FREE_LIMIT}건)에 도달했어요. "
                           "기존 항목을 삭제하거나 Pro 플랜을 확인해 주세요.",
                )
        try:
            ins = admin.table(HISTORY_TABLE).insert({
                "user_id": user_id,
                "label": label,
                "mode": mode,
                "result": result,
                "track": track,
            }).execute()
            row = (getattr(ins, "data", None) or [{}])[0]
        except Exception as e:
            logger.warning("history insert 실패: %s", e)
            raise HTTPException(status_code=500, detail="히스토리 저장에 실패했어요. 잠시 후 다시 시도해 주세요.")
        if track == "recent":
            _history_trim_recent(admin, user_id)
        return {
            "id": row.get("id"),
            "label": label,
            "mode": mode,
            "track": track,
            "created_at": row.get("created_at"),
            "quota": {"used": (used + 1) if used is not None else None,
                      "max": None if (is_internal or track == "recent") else HISTORY_FREE_LIMIT},
        }

    return await asyncio.to_thread(_create)


@app.get("/history")
@limiter.limit("60/minute")
async def history_list(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    track: str = "saved",
    user_id: str = Depends(verify_jwt),
):
    """본인 히스토리 목록 — result 제외, 최신순 페이지네이션.
    BOHUMFIT-171b: track 필터('recent'|'saved', 기본 saved — 156 호환)."""
    limit = max(1, min(HISTORY_LIST_MAX, limit))
    offset = max(0, offset)
    if track not in HISTORY_TRACKS:
        raise HTTPException(status_code=400, detail="track은 recent 또는 saved여야 합니다.")
    admin = _require_history_admin()

    def _list() -> dict:
        _history_lazy_purge(admin, user_id)
        cutoff = _history_cutoff_dt(track).isoformat()
        try:
            res = (
                admin.table(HISTORY_TABLE)
                .select("id,label,mode,track,created_at", count="exact")
                .eq("user_id", user_id).eq("track", track).gte("created_at", cutoff)
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
        except Exception as e:
            logger.warning("history list 실패: %s", e)
            raise HTTPException(status_code=500, detail="히스토리 목록을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.")
        items = getattr(res, "data", None) or []
        total = getattr(res, "count", None) or 0
        if track == "recent":
            quota = {"used": total, "max": HISTORY_RECENT_LIMIT}
        else:
            quota = {"used": total,
                     "max": None if _history_is_internal(admin, user_id) else HISTORY_FREE_LIMIT}
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "track": track,
            "retention_days": _history_retention_days(track),
            "quota": quota,
        }

    return await asyncio.to_thread(_list)


@app.get("/history/{history_id}")
@limiter.limit("60/minute")
async def history_get(
    request: Request,
    history_id: str,
    user_id: str = Depends(verify_jwt),
):
    """본인 소유 단건 result 조회 — 타인/부재/만료 모두 404(존재 여부 비노출).
    BOHUMFIT-171b: 만료 판정은 행의 track 기준(recent 7일 / saved 90일)."""
    admin = _require_history_admin()

    def _get() -> dict:
        try:
            res = (
                admin.table(HISTORY_TABLE)
                .select("id,label,mode,track,result,created_at")
                .eq("id", history_id).eq("user_id", user_id)
                .single().execute()
            )
            row = getattr(res, "data", None)
        except Exception:
            row = None
        if not row:
            raise HTTPException(status_code=404, detail="히스토리를 찾을 수 없어요. 삭제됐거나 보관 기간이 지났을 수 있어요.")
        row_track = row.get("track") if row.get("track") in HISTORY_TRACKS else "saved"
        cutoff_dt = _history_cutoff_dt(row_track)
        created = _history_parse_dt(row.get("created_at"))
        if created is not None and created < cutoff_dt:
            _history_lazy_purge(admin, user_id)
            raise HTTPException(
                status_code=404,
                detail=f"보관 기간({_history_retention_days(row_track)}일)이 지나 삭제된 히스토리예요.",
            )
        return row

    return await asyncio.to_thread(_get)


@app.delete("/history/{history_id}")
@limiter.limit("30/minute")
async def history_delete(
    request: Request,
    history_id: str,
    user_id: str = Depends(verify_jwt),
):
    """본인 소유 단건 삭제 — 타인/부재 404."""
    admin = _require_history_admin()

    def _delete() -> dict:
        try:
            res = (
                admin.table(HISTORY_TABLE).delete()
                .eq("id", history_id).eq("user_id", user_id).execute()
            )
            deleted = getattr(res, "data", None) or []
        except Exception as e:
            logger.warning("history delete 실패: %s", e)
            raise HTTPException(status_code=500, detail="히스토리 삭제에 실패했어요. 잠시 후 다시 시도해 주세요.")
        if not deleted:
            raise HTTPException(status_code=404, detail="히스토리를 찾을 수 없어요.")
        return {"ok": True, "id": history_id}

    return await asyncio.to_thread(_delete)


@app.patch("/history/{history_id}/save")
@limiter.limit("20/minute")
async def history_promote(
    request: Request,
    history_id: str,
    payload: dict = Body(...),
    user_id: str = Depends(verify_jwt),
):
    """BOHUMFIT-171b: recent → saved 승격 — 별칭(실명 금지) 필수, saved 무료 한도(10건) 검사 적용.
    승격 후 보관 기간은 saved 기준(90일, created_at 기준 유지)."""
    label = str(payload.get("label") or "").strip()
    if not label:
        raise HTTPException(status_code=400, detail="저장할 별칭을 입력해 주세요.")
    if len(label) > HISTORY_MAX_LABEL_LEN:
        raise HTTPException(status_code=400, detail=f"별칭은 {HISTORY_MAX_LABEL_LEN}자 이내로 입력해 주세요.")
    admin = _require_history_admin()

    def _promote() -> dict:
        _history_lazy_purge(admin, user_id)
        is_internal = _history_is_internal(admin, user_id)
        used = None
        if not is_internal:
            used = _history_count(admin, user_id, _history_cutoff_dt("saved").isoformat())
            if used >= HISTORY_FREE_LIMIT:
                raise HTTPException(
                    status_code=409,
                    detail=f"히스토리 저장 한도({HISTORY_FREE_LIMIT}건)에 도달했어요. "
                           "기존 항목을 삭제하거나 Pro 플랜을 확인해 주세요.",
                )
        try:
            res = (
                admin.table(HISTORY_TABLE)
                .update({"track": "saved", "label": label})
                .eq("id", history_id).eq("user_id", user_id).eq("track", "recent")
                .execute()
            )
            updated = getattr(res, "data", None) or []
        except Exception as e:
            logger.warning("history promote 실패: %s", e)
            raise HTTPException(status_code=500, detail="저장으로 전환하지 못했어요. 잠시 후 다시 시도해 주세요.")
        if not updated:
            raise HTTPException(status_code=404, detail="히스토리를 찾을 수 없어요. 이미 저장됐거나 삭제됐을 수 있어요.")
        return {
            "ok": True,
            "id": history_id,
            "label": label,
            "track": "saved",
            "quota": {"used": (used + 1) if used is not None else None,
                      "max": None if is_internal else HISTORY_FREE_LIMIT},
        }

    return await asyncio.to_thread(_promote)


@app.post("/history/{history_id}/report-pdf")
@limiter.limit("10/minute,60/hour")
async def history_report_pdf(
    request: Request,
    history_id: str,
    user_id: str = Depends(verify_jwt),
):
    """BOHUMFIT-157: 저장(saved) 히스토리를 고객 전달용 고지 리포트 PDF 파일로 다운로드.
    - 공유 URL 금지(Human 확정) — 파일 응답만. 소유권(.eq user_id) 강제, 타인/부재/만료 404.
    - recent(자동 기록) 항목은 409 + "먼저 저장" 안내 — 별칭이 확인된 항목만 파일화.
    - 분석 파이프라인 무접촉: 저장된 result를 기존 generate_report_pdf로 렌더만 한다.
    - 파일명: BohumFit_고지의무리포트_{별칭}_{YYYYMMDD}.pdf (금지 문자 제거 — 실명 아닌 별칭)."""
    admin = _require_history_admin()

    def _load():
        try:
            res = (
                admin.table(HISTORY_TABLE)
                .select("id,label,mode,track,result,created_at")
                .eq("id", history_id).eq("user_id", user_id)
                .single().execute()
            )
            return getattr(res, "data", None)
        except Exception:
            return None

    row = await asyncio.to_thread(_load)
    if not row:
        raise HTTPException(status_code=404, detail="히스토리를 찾을 수 없어요.")
    row_track = row.get("track") if row.get("track") in HISTORY_TRACKS else "saved"
    created = _history_parse_dt(row.get("created_at"))
    if created is not None and created < _history_cutoff_dt(row_track):
        raise HTTPException(status_code=404, detail="보관 기간이 지나 삭제된 히스토리예요.")
    if row_track != "saved":
        raise HTTPException(status_code=409, detail="최근 자동 기록 항목은 먼저 저장한 뒤 PDF로 내려받을 수 있어요.")
    result = row.get("result")
    if not isinstance(result, dict) or not result:
        raise HTTPException(status_code=404, detail="리포트로 만들 분석 결과가 없어요.")

    report_payload = {
        "report_type": "disclosure",
        "reference_date": result.get("reference_date") or "",
        "customer_name": "",  # 실명 미저장(156a) — 헤더 고객명 줄 생략, 별칭은 파일명에만
        "standard_reports": result.get("standard_reports") or {},
        "easy_reports": result.get("easy_reports") or {},
        "all_disease_summary": result.get("all_disease_summary") or [],
        "total_med_sum": result.get("total_med_sum") or 0,
    }
    try:
        pdf = await asyncio.wait_for(
            generate_report_pdf("disclosure", report_payload),
            timeout=REPORT_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("history report pdf 시간 초과 (%ss)", REPORT_TIMEOUT_SECONDS)
        raise HTTPException(status_code=504, detail="리포트 생성이 시간 내에 끝나지 않았어요. 잠시 후 다시 시도해 주세요.")
    except ReportError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ReportUnavailableError as e:
        logger.error("history report pdf 렌더러 사용 불가: %s", e)
        raise HTTPException(status_code=503, detail="리포트 생성 기능을 준비 중입니다. 잠시 후 다시 시도해 주세요.")
    except Exception as e:
        logger.exception("history report pdf failed: %s", e)
        raise HTTPException(status_code=500, detail="리포트를 생성하지 못했어요. 잠시 후 다시 시도해 주세요.")

    safe_label = re.sub(r"[^가-힣A-Za-z0-9]", "", str(row.get("label") or ""))[:20]
    ref = str(report_payload.get("reference_date") or "").strip()
    ref_match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", ref)
    date_part = "".join(ref_match.groups()) if ref_match else date.today().strftime("%Y%m%d")
    base = f"BohumFit_고지의무리포트_{safe_label}_{date_part}" if safe_label else f"BohumFit_고지의무리포트_{date_part}"
    ascii_fallback = f"BohumFit_report_{date_part}.pdf"
    disposition = (
        f'attachment; filename="{ascii_fallback}"; '
        f"filename*=UTF-8''{urllib.parse.quote(base + '.pdf')}"
    )
    logger.info("history report pdf done: bytes=%d", len(pdf))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": disposition,
            "Access-Control-Expose-Headers": "Content-Disposition",
            "Cache-Control": "no-store",
        },
    )


# ── 보장 비교분석 PDF 파싱 (BOHUMFIT-114) ──────────────────────────────────────
@app.post("/coverage/parse")
@limiter.limit("20/minute")
async def coverage_parse(
    request: Request,
    file: UploadFile = File(..., description="보장분석서(current) 또는 가입제안서(proposal) PDF"),
    doc_type: str = Form(..., description="current | proposal"),
    user_id: str = Depends(verify_jwt),
):
    """BOHUMFIT-114: 보장 비교분석 PDF 파싱.
    - current = 보장분석서(한화/KB/공통), proposal = 가입제안서(범용).
    - PDF 열기 실패 400, 그 외 파싱 이상은 결과의 parse_warnings에 기록 후 200.
    - ★ PII(성명·주민번호 등)는 파서가 저장하지 않으며 서버에도 보관하지 않는다(분석 후 즉시 폐기)."""
    dt = doc_type if doc_type in ("current", "proposal") else "proposal"
    fname = file.filename or "upload.pdf"
    if not fname.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드할 수 있어요.")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"개별 PDF 크기는 {MAX_FILE_SIZE // (1024 * 1024)}MB를 넘을 수 없습니다.",
        )
    try:
        result = await asyncio.to_thread(parse_coverage_pdf, data, dt)
    except ValueError as e:  # PDF 열기 실패(손상·암호 등)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("coverage_parse failed: %s", e)
        raise HTTPException(status_code=500, detail="보장분석 파싱에 실패했어요. 잠시 후 다시 시도해 주세요.")
    finally:
        del data
    return result


# ── KB 신정원 보장분석 제안서 → 리모델링 [전]/[최종] (BOHUMFIT-179) ─────────────
@app.post("/coverage/analyze")
@limiter.limit("20/minute")
@limiter.limit(COVERAGE_ANALYZE_IP_RATE_LIMIT, key_func=get_remote_address)
async def coverage_analyze(
    request: Request,
    file: UploadFile = File(..., description="KB 신정원 보장분석 제안서 PDF"),
    user_id: str = Depends(verify_jwt),
):
    """BOHUMFIT-179: KB 신정원 보장분석 제안서 PDF → 리모델링 보장분석표 데이터.
    - 응답 = {before(회사별 세부·월납 내림차순), final(담보 합산+진단), warnings}. KB 표준양식 전용.
    - KB 양식 아님/PDF 손상 → 400. 그 외 실패 500.
    - ★ PII(성명·계약)는 서버에 저장하지 않으며 요청-응답 내에서만 처리 후 즉시 폐기."""
    fname = file.filename or "upload.pdf"
    if not fname.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드할 수 있어요.")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"개별 PDF 크기는 {MAX_FILE_SIZE // (1024 * 1024)}MB를 넘을 수 없습니다.",
        )
    if b"%PDF-" not in data[:1024]:
        raise HTTPException(status_code=400, detail="올바른 PDF 파일이 아니에요.")
    _sub_ctx = await _enforce_subscription(user_id)
    try:
        jong_table = await asyncio.to_thread(_get_jong_conversion_table)
        result = await asyncio.to_thread(analyze_kb_coverage, data, jong_table)
    except KBFormatError as e:  # 비-KB 양식·PDF 열기 실패
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("coverage_analyze failed: %s", e)
        raise HTTPException(status_code=500, detail="보장분석 생성에 실패했어요. 잠시 후 다시 시도해 주세요.")
    finally:
        del data
    await _log_usage(user_id, _sub_ctx)
    return result


# ── 회사별 신규 가입제안서 → 컨설팅 [후] 신규제안 (BOHUMFIT-193) ───────────────
@app.post("/coverage/proposals/parse")
@limiter.limit("20/minute")
async def coverage_proposals_parse(
    request: Request,
    files: list[UploadFile] = File(..., description="회사별 신규 가입제안서 PDF 목록"),
    user_id: str = Depends(verify_jwt),
):
    """BOHUMFIT-193: 회사별 가입제안서 PDF → [후] 재계산용 신규제안 목록.

    - 응답 = {proposals, premium.monthly_total, warnings, metadata}.
    - 실제 PDF/추출 텍스트는 서버에 저장하지 않고 요청 처리 후 폐기한다.
    - 기존 BOHUMFIT-114/179 파서와 ``backend/pipeline``에는 연결하지 않는다.
    """
    if not files:
        raise HTTPException(status_code=400, detail="신규 가입제안서 PDF를 1개 이상 업로드해 주세요.")
    if len(files) > MAX_FILE_COUNT:
        raise HTTPException(status_code=413, detail=f"PDF는 최대 {MAX_FILE_COUNT}개까지 업로드할 수 있습니다.")

    payload: list[tuple[str, bytes]] = []
    total_size = 0
    try:
        for file in files:
            fname = file.filename or "proposal.pdf"
            if not fname.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail="PDF 파일만 업로드할 수 있어요.")
            data = await file.read()
            if not data:
                raise HTTPException(status_code=400, detail="빈 파일입니다.")
            if len(data) > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=400,
                    detail=f"개별 PDF 크기는 {MAX_FILE_SIZE // (1024 * 1024)}MB를 넘을 수 없습니다.",
                )
            if b"%PDF-" not in data[:1024]:
                raise HTTPException(status_code=400, detail="올바른 PDF 파일이 아니에요.")
            total_size += len(data)
            payload.append((fname, data))
        if total_size > MAX_TOTAL_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"전체 PDF 합계 크기는 {MAX_TOTAL_SIZE // (1024 * 1024)}MB를 넘을 수 없습니다.",
            )
        return await asyncio.to_thread(parse_newproposal_files, payload)
    except HTTPException:
        raise
    except ProposalParseError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("coverage proposal parse failed: %s", e)
        raise HTTPException(status_code=500, detail="신규 가입제안서 파싱에 실패했습니다. 수기로 보완해 주세요.")
    finally:
        del payload


# ── 보장분석 리모델링표 내보내기 (BOHUMFIT-181) ────────────────────────────────
#   프런트가 분석 결과 JSON(before/final)을 전달 → 서버는 렌더만(재파싱 X). PII 미저장.
def _coverage_export_names(payload: dict, ext: str) -> tuple[str, str]:
    label = ((payload.get("before") or {}).get("customer") or {}).get("name") or ""
    safe = re.sub(r"[^가-힣A-Za-z0-9]", "", str(label))[:20] or "고객"
    date_part = date.today().strftime("%Y%m%d")
    return f"BohumFit_보장분석_{safe}_{date_part}.{ext}", f"BohumFit_coverage_{date_part}.{ext}"


def _coverage_disposition(payload: dict, ext: str) -> str:
    base, ascii_fb = _coverage_export_names(payload, ext)
    return f'attachment; filename="{ascii_fb}"; filename*=UTF-8\'\'{urllib.parse.quote(base)}'


def _require_analysis(payload: dict) -> None:
    if not isinstance(payload, dict) or "before" not in payload or "final" not in payload:
        raise HTTPException(status_code=400, detail="분석 결과(before/final)가 필요해요.")


@app.post("/coverage/export/excel")
@limiter.limit("20/minute")
async def coverage_export_excel(
    request: Request,
    payload: dict = Body(..., description="/coverage/analyze 응답(before/final)"),
    user_id: str = Depends(verify_jwt),
):
    """BOHUMFIT-181: [전]/[최종] JSON → 엑셀(.xlsx) 스트림. ★서버 미저장."""
    _require_analysis(payload)
    try:
        data = await asyncio.to_thread(build_workbook_bytes, payload)
    except Exception as e:
        logger.exception("coverage excel export failed: %s", e)
        raise HTTPException(status_code=500, detail="엑셀 생성에 실패했어요. 잠시 후 다시 시도해 주세요.")
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": _coverage_disposition(payload, "xlsx"),
            "Access-Control-Expose-Headers": "Content-Disposition",
            "Cache-Control": "no-store",
        },
    )


@app.post("/coverage/export/pdf")
@limiter.limit("10/minute,60/hour")
async def coverage_export_pdf(
    request: Request,
    payload: dict = Body(..., description="/coverage/analyze 응답(before/final)"),
    user_id: str = Depends(verify_jwt),
):
    """BOHUMFIT-181: [전]/[최종] JSON → FIT v1.1 PDF 스트림(헤드리스 Chromium). ★서버 미저장."""
    _require_analysis(payload)
    try:
        pdf = await asyncio.wait_for(generate_coverage_pdf(payload), timeout=REPORT_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="PDF 생성이 시간 내에 끝나지 않았어요. 잠시 후 다시 시도해 주세요.")
    except ReportUnavailableError as e:
        logger.error("coverage pdf 렌더러 사용 불가: %s", e)
        raise HTTPException(status_code=503, detail="PDF 생성 기능을 준비 중입니다. 잠시 후 다시 시도해 주세요.")
    except Exception as e:
        logger.exception("coverage pdf export failed: %s", e)
        raise HTTPException(status_code=500, detail="PDF 생성에 실패했어요. 잠시 후 다시 시도해 주세요.")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": _coverage_disposition(payload, "pdf"),
            "Access-Control-Expose-Headers": "Content-Disposition",
            "Cache-Control": "no-store",
        },
    )


@app.post("/coverage/consulting/after")
@limiter.limit("20/minute")
async def coverage_consulting_after(
    request: Request,
    payload: dict = Body(..., description="analysis + consulting_plan"),
    user_id: str = Depends(verify_jwt),
):
    """BOHUMFIT-186: [전] 분석 결과와 컨설팅 플랜으로 [후] 설계를 재계산한다."""
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else payload
    plan = payload.get("consulting_plan") or payload.get("plan") or {}
    if not isinstance(analysis, dict) or "before" not in analysis or "final" not in analysis:
        raise HTTPException(status_code=400, detail="분석 결과(before/final)가 필요합니다.")
    try:
        return await asyncio.to_thread(build_after_result, analysis, plan)
    except Exception as e:
        logger.exception("coverage consulting after failed: %s", e)
        raise HTTPException(status_code=500, detail="후 설계 재계산에 실패했습니다.")


@app.post("/api/analyze")
@limiter.limit("5/minute,30/hour")
@limiter.limit(ANALYZE_IP_RATE_LIMIT, key_func=get_remote_address)
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

    # BOHUMFIT-069/212/231: bohumfit_tier별 분석 횟수 체크(admin 무제한·internal 월100·미구독 customer 누적5).
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

    # BOHUMFIT-069/212: 분석 성공 → 사용량 1건 기록(admin·비활성은 skip, 실패는 응답 막지 않음).
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

    response_payload = {
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

    # BOHUMFIT-171b: 최근 분석 자동 기록(recent 트랙·10개 롤링·7일) — 응답 조립 이후 부수 저장.
    #   내부 try/except로 완전 격리: 어떤 실패도 분석 응답을 막지 않는다. 실명(customer_name)은 제거 저장.
    await _history_record_recent(user_id, response_payload, reference_date)

    return response_payload


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
