import asyncio
import logging
import os
import re
import time
from datetime import date
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
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
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


# ── 엔드포인트 ───────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    # BOHUMFIT-060 BF-05: 공개 헬스는 최소 정보만 노출(env·deps·커밋해시 제거).
    #   Railway 헬스체크용 200 status 는 유지. 상세 관측은 Sentry 로 일원화.
    return {"status": "ok"}


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

    filename = f"BF-{report_type}-{date.today().strftime('%Y%m%d')}.pdf"
    logger.info("report pdf done: type=%s bytes=%d", report_type, len(pdf))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # 민감정보 — 중간 캐시 금지
            "Cache-Control": "no-store",
        },
    )
