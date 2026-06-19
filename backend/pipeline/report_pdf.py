# -*- coding: utf-8 -*-
"""BOHUMFIT-030: 백엔드 리포트 PDF 생성 (고지/실손 분리).

HTML/CSS 템플릿(backend/templates/report_*.html)을 헤드리스 Chromium(playwright)으로
렌더링해 PDF 바이트를 반환한다.

설계 원칙
  - 금액·판정은 프런트(분석 화면·실손 계산기)가 보낸 payload 값을 **그대로 표시**한다.
    산식 재구현·재계산 금지 — 화면·계산기·서버 리포트가 동일 금액을 유지한다.
  - 건강정보 미저장: PDF·진료데이터를 디스크에 쓰지 않는다(메모리 내 휘발 처리).
  - 산출물에 구 브랜드명 문자열을 사용하지 않는다(문서번호 접두 BF-, 분석도구 BOHUMFIT).
  - 한글은 서버에 설치된 Noto CJK 폰트로 렌더링·임베딩한다(배포: fonts-noto-cjk).
    backend/fonts/ 에 폰트 파일을 두면 @font-face 로 우선 임베딩한다(선택).

payload 스키마 (프런트가 화면 표시값을 그대로 직렬화해 전달)
  disclosure:
    {
      "reference_date": "YYYY-MM-DD",
      "standard_reports": { "<질문 제목>": [SummaryItem, ...], ... },   # /api/analyze 응답 그대로
      "easy_reports":     { ... },                                      # 〃
      "all_disease_summary": [DiseaseSummary, ...],                     # 선택
      "total_med_sum": int,                                             # 선택
    }
  insurance:
    {
      "inputs": {
        "generation": 1~5 | null, "generation_period": str, "nc_option": 20|30|null,
        "bracket": 1~10 | null, "year": "YYYY",
        "covered_self_pay": int(원), "non_covered": int(원, 설계사 수기 입력),
      },
      "results": {                       # 모두 화면 계산값 그대로 (insuranceCalc 미러 출력)
        "claim":        {"possibility": str, "low": int, "high": int, "has": bool} | null,
        "self_pay_cap": {"eligible": int, "cap": int, "exceeded": bool, "excess": int,
                          "non_covered_excluded": bool} | null,
        "nhis_cap":     {"cap": int, "exceeded": bool, "refund": int} | null,
        "min_deductible": {
          "grade_label": str, "deductible": int,
          "cov_out":  {"charge": int, "reimbursement": int, "low_value": bool} | null,
          "nc_out":   {"charge": int, "reimbursement": int, "low_value": bool,
                        "visits": int, "total_mode": bool} | null,
          "inpatient":{"charge": int, "reimbursement": int, "low_value": bool} | null,
        } | null,
      },
    }
"""
from __future__ import annotations

import base64
import logging
import math
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# BOHUMFIT-051: 생성일시·문서번호를 서버 TZ(UTC)에 의존하지 않고 한국시간(KST)으로 명시 변환.
_KST = ZoneInfo("Asia/Seoul")


def _now_kst() -> datetime:
    return datetime.now(_KST)

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger("bohumfit.report_pdf")

REPORT_TYPES = ("disclosure", "insurance")

# ── 문서·사업자 상수 ─────────────────────────────────────────────────────────
DOC_PREFIX = "BF"  # 문서번호 접두 (구 접두 SR- 사용 금지 — BOHUMFIT-030 콘텐츠 수정 3)

BUSINESS_FOOTER = {
    "name":        "보험핏",
    "ceo":         "이민규",
    "biz_no":      "174-29-01975",
    # 소재지: 저장소·환경에 확정 값이 없어 env 로 주입(BIZ_ADDRESS). 미설정 시 "-" 표기.
    # ⚠ '통합 사업자' 확정 전까지 현재 값 유지 — 상호/대표/사업자번호/주소 확정 필요(handoff).
    "address":     os.environ.get("BIZ_ADDRESS", "-"),
    "tool":        "BOHUMFIT",
    "contact":     "contact@bohumfit.ai",
    "domain":      "BOHUMFIT.AI",  # BOHUMFIT-047 영업 자료 도메인 표기
}

# ── 고지 리포트 고정 문구 ────────────────────────────────────────────────────
# 콘텐츠 수정 1: '고지 불요 판단 기준' 1~5 번호 줄바꿈(각 항목 한 줄) 표시.
# 기준은 결정론 룰 엔진(filters.py R-H-Q1/Q3/Q4 + AI Q2)의 질문 창과 동일 — 표현만 정리.
NO_DISCLOSURE_CRITERIA = [
    "기준일로부터 3개월 이내 진단·의심소견·입원·수술·투약(상시복용 포함) 이력이 확인되지 않은 경우 (1번질문)",
    "기준일로부터 1년 이내 추가검사·재검사 필요 소견이 확인되지 않은 경우 (2번질문)",
    "기준일로부터 5년 이내 입원·수술, 7회 이상 통원 또는 30일 이상 투약 이력이 확인되지 않은 경우 (3번질문)",
    "기준일로부터 5년 초과 10년 이내 입원 또는 수술 이력이 확인되지 않은 경우 (4번질문)",
    "기준일로부터 5년 이내 중대질환 진료 이력이 확인되지 않은 경우 (5번질문)",
]
NO_DISCLOSURE_CRITERIA_NOTE = (
    "간편심사는 1번질문(3개월), 2번질문(10년 입원·수술), 3번질문(5년 6대질환) 기준으로 동일하게 판단합니다."
)

# BOHUMFIT-047 면책 강화(영업 자료 수준) — 모집 비주체·추정·비저장·고객 보유 명시.
DISCLOSURE_DISCLAIMER = (
    "본 자료는 보험 가입 권유·모집을 위한 것이 아니라, 고객이 보유하거나 제안받은 보험의 알릴의무(고지) "
    "사항을 점검·분석하기 위한 참고용 보조자료입니다. 점검 결과는 업로드한 진료자료를 바탕으로 AI가 산출한 "
    "추정이며, 의학적 진단이나 보험사 심사·인수·보험금 지급 여부를 확정하지 않습니다. 실제 알릴의무 대상과 "
    "범위는 보험사별 청약서 문항·약관·인수지침에 따라 달라질 수 있으므로, 청약 전 반드시 해당 청약서 문항과 "
    "대조해 주세요. 본 서비스는 분석 결과를 저장하지 않으며, 출력물은 고객 본인이 보유·관리합니다. 고지 누락에 "
    "대한 최종 책임은 청약자 본인에게 있습니다."
)

INSURANCE_DISCLAIMER = (
    "본 자료는 보험 가입 권유·모집을 위한 것이 아니라, 보유하거나 제안받은 보험의 보장을 점검·분석하기 위한 "
    "참고자료입니다. 표기된 금액은 추정값이며, 실제 보험금·환급금 지급 여부와 금액은 보험사 약관·심사 및 "
    "국민건강보험공단 확인이 필요합니다. 본 안내는 보험 모집·중개·상품추천·가입권유를 목적으로 하지 않으며, "
    "분석 결과를 저장하지 않고 출력물은 고객 본인이 보유합니다."
)

SENSITIVE_NOTICE = "본 문서는 진료기록 기반 민감정보를 포함합니다 — 보관·전달 시 취급에 주의하세요."

# 콘텐츠 수정 4: 비급여는 약관 자동 확인이 아니라 설계사 수기 입력 금액 기준임을 명시.
NON_COVERED_NOTE = (
    "비급여 항목은 약관 자동 확인이 아니라 설계사가 수기 입력한 비급여 금액 기준으로 산출되었습니다. "
    "실제 비급여 보장 범위는 가입 상품 약관에 따라 다를 수 있습니다."
)

# 콘텐츠 수정 5: 건보 본인부담상한제 환급은 급여 본인부담금 기준(비급여 제외).
NHIS_CAP_NOTE = (
    "본인부담상한제 환급은 급여 본인부담금 기준(비급여 제외)으로 산정·표기합니다. "
    "요양병원 120일 초과 입원 시 상한액이 달라질 수 있습니다."
)

# 콘텐츠 수정 6: 실손 자기부담금 연 200만원 상한 — 세대별 합산 범위 명시.
# (세대 라벨은 템플릿의 행 태그로 표시 — 본문 중복 방지)
SELF_PAY_CAP_RULES = [
    "급여+비급여 자기부담금 합계가 연 200만원을 초과하면 초과분을 보험사가 환급합니다.",
    "급여 자기부담금이 연 200만원을 초과하면 초과분을 보험사가 환급합니다(비급여 제외).",
]

# ── 템플릿 환경 ──────────────────────────────────────────────────────────────
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"
_BRAND_DIR = Path(__file__).resolve().parent.parent / "assets" / "brand"

# 헤더 워드마크 로고 (BOHUMFIT-051).
#   - 헤더 배경이 라이트(흰색)라 컬러 버전을 사용한다. 어두운 헤더가 생기면 white 버전으로 교체.
#   - 프런트의 @/assets import 방식은 백엔드에서 쓸 수 없으므로 파일을 읽어 base64 data-URI 로 임베드한다.
#   - SVG 머리의 <?xml ?>/<!DOCTYPE> 선언은 외부 DTD 참조로 data-URI 로드를 막을 수 있어 제거본을 써야 한다.
#     정식 에셋(src/assets/brand)에는 이미 제거돼 있고 복사본도 동일함을 확인했다(안전을 위해 런타임에서도 제거).
_LOGO_FILES = {
    "color": "bohumfit_logo.svg",
    "white": "bohumfit_logo_white.svg",
}

# <?xml ...?> 선언과 <!DOCTYPE ...> 선언 제거용 (data-URI 로드 차단 방지)
_SVG_PROLOG_RE = re.compile(r"<\?xml.*?\?>\s*|<!DOCTYPE[^>]*>\s*", re.IGNORECASE | re.DOTALL)


def _logo_data_uri(variant: str = "color") -> str:
    """브랜드 워드마크 SVG → base64 data-URI. 파일이 없으면 빈 문자열(텍스트 폴백)."""
    fname = _LOGO_FILES.get(variant, _LOGO_FILES["color"])
    path = _BRAND_DIR / fname
    try:
        svg = path.read_text(encoding="utf-8")
    except OSError:
        logger.warning("brand logo not found: %s", path)
        return ""
    svg = _SVG_PROLOG_RE.sub("", svg).strip()
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(("html",)),
)


def _won_to_man(won) -> str:
    """src/lib/insuranceCalc.ts wonToMan 미러 — 표시 포맷만, 계산 아님.

    JS Math.round(= floor(x+0.5)) 와 동일하게 처리한다(파이썬 round 는 은행원 반올림).
    """
    try:
        w = int(won)
    except (TypeError, ValueError):
        return "0원"
    if w <= 0:
        return "0원"
    return f"약 {math.floor(w / 10000 + 0.5):,}만원"


def _won_range(low, high) -> str:
    if low == high:
        return _won_to_man(low)
    return f"{_won_to_man(low)}~{_won_to_man(high)}"


_env.filters["won_man"] = _won_to_man


# ── 고지 리포트: 화면(DiseaseCard) 표시 규칙 미러 (표시 전용, 판정 로직 아님) ──
def _extract_q_number(q_title: str) -> str:
    m = re.search(r"(\d+)\s*번\s*질문", q_title or "")
    if m:
        return f"Q{m.group(1)}"
    m = re.search(r"\d+", q_title or "")
    return f"Q{m.group()}" if m else "Q"


def _clean_q_title(q_title: str) -> str:
    return re.sub(r"^\[.*?\]\s*", "", q_title or "")


def _metric_visibility(item: dict, q_num: str, is_easy: bool) -> dict:
    """Disclosure.tsx getMetricVisibility 미러."""
    detail = item.get("detail") or ""
    surg_n = item.get("surgery_count")
    if surg_n is None:
        surg_n = len(item.get("surgeries") or [])
    has_inpatient = (item.get("inpatient") or 0) > 0 or (item.get("inpatient_count") or 0) > 0
    has_surgery = surg_n > 0
    has_visit_trigger = (item.get("visit") or 0) >= 7 or ("통원" in detail)
    has_med_trigger = (item.get("med_days") or 0) >= 30 or ("투약" in detail) or ("처방" in detail)

    if is_easy:
        return {
            "visit": False,
            "inpatient": q_num == "Q2" and has_inpatient,
            "inpatient_count": q_num == "Q2" and (item.get("inpatient_count") or 0) > 0,
            "surgery": q_num == "Q2" and has_surgery,
            "med": False,
        }
    if q_num == "Q1":
        return {
            "visit": False,
            "inpatient": has_inpatient,
            "inpatient_count": (item.get("inpatient_count") or 0) > 0,
            "surgery": has_surgery,
            "med": has_med_trigger,
        }
    if q_num == "Q3":
        return {
            "visit": has_visit_trigger,
            "inpatient": has_inpatient,
            "inpatient_count": (item.get("inpatient_count") or 0) > 0,
            "surgery": has_surgery,
            "med": has_med_trigger,
        }
    if q_num == "Q4":  # BOHUMFIT-034/036: 5년 초과 10년 이내 입원·수술(통원·투약 없음)
        return {
            "visit": False,
            "inpatient": has_inpatient,
            "inpatient_count": (item.get("inpatient_count") or 0) > 0,
            "surgery": has_surgery,
            "med": False,
        }
    # Q5(중대질환) 및 기타 = 메트릭 칩 없음(기존 Q4 중대질환과 동일)
    return {"visit": False, "inpatient": False, "inpatient_count": False, "surgery": False, "med": False}


def _show_clinical_review(q_num: str, is_easy: bool) -> bool:
    """Disclosure.tsx shouldShowClinicalReview 미러."""
    if is_easy:
        return q_num == "Q1"
    return q_num in ("Q1", "Q2")


def _clinical_review(item: dict) -> dict:
    """추가검사·재검사 표시 상태 결정 (BOHUMFIT-030 콘텐츠 수정 2 — 표시 전용).

    '확인 필요'는 **추가검사/재검사(1년 질문) 해당 여부 미확정**일 때만 사용한다.
      - suspected  : AI 판단 해당(additional_test_hit) 또는 q2_suspicion 존재 → 고지 권고 근거
      - cleared    : AI 판단 결과가 있고 비해당(reason 존재, hit=False) → 확정. '확인 필요' 아님
      - unconfirmed: AI 판단 결과 자체가 없음(hit=False, reason 빈값) → 이 경우에만 '확인 필요'
    전용 플래그가 없어 additional_test_hit / additional_test_reason / q2_suspicion 조합으로
    식별한다(result_builder.py: _at_res 부재 시 reason="" 보장). 판정 룰 자체는 불변.
    """
    suspicion = (item.get("q2_suspicion") or "").strip()
    reason = (item.get("additional_test_reason") or "").strip()
    if bool(item.get("additional_test_hit")) or suspicion:
        return {
            "state": "suspected",
            "label": "추가검사·재검사 의심",
            "text": suspicion or reason or "AI 판단: 1년 내 추가검사·재검사 해당 가능성",
        }
    if reason:
        return {
            "state": "cleared",
            "label": "추가검사·재검사 해당 없음",
            "text": reason,
        }
    return {
        "state": "unconfirmed",
        "label": "추가검사·재검사 확인 필요",
        "text": "AI 판단 결과가 없어 1년 내 추가검사·재검사 해당 여부가 미확정입니다. 원자료(검사 기록)와 대조해 주세요.",
    }


def _format_period(item: dict) -> str:
    fd = item.get("first_date") or ""
    ld = item.get("latest_date") or ""
    if fd and ld and fd != ld:
        return f"{fd} ~ {ld}"
    return fd or ld or ""


def _prepare_section(reports: dict, is_easy: bool) -> list[dict]:
    """summary_reports(dict) → 템플릿용 질문 섹션 리스트. 값은 가공 없이 전달."""
    if not isinstance(reports, dict):
        return []

    def _q_sort_key(title: str):
        m = re.search(r"\d+", title or "")
        return int(m.group()) if m else 999

    sections = []
    for q_title in sorted(reports.keys(), key=_q_sort_key):
        items = reports.get(q_title) or []
        q_num = _extract_q_number(q_title)
        prepared = []
        # 화면(Disclosure.tsx)과 동일: 최근 진료일 내림차순 정렬 (표시 순서만)
        def _item_sort_key(it: dict):
            return (it.get("latest_date") or it.get("first_date") or "", it.get("first_date") or "")
        for item in sorted(items, key=_item_sort_key, reverse=True):
            if not isinstance(item, dict):
                continue
            surg_n = item.get("surgery_count")
            if surg_n is None:
                surg_n = len(item.get("surgeries") or [])
            show_review = _show_clinical_review(q_num, is_easy)
            prepared.append({
                "item": item,
                "period": _format_period(item),
                "metric": _metric_visibility(item, q_num, is_easy),
                "surgery_n": surg_n,
                "procedures_n": len(item.get("procedures") or []),
                "suspected_n": len(item.get("surgery_suspected") or []),
                "suspected_grade": item.get("surgery_suspected_grade") or "",  # BOHUMFIT-036: 공단 수술의심 강/약(Q4)
                "review": _clinical_review(item) if show_review else None,
            })
        sections.append({
            "q_num": q_num,
            "title": _clean_q_title(q_title),
            # 키 이름 주의: "items" 는 Jinja 에서 dict.items 메서드와 충돌 → "rows" 사용
            "rows": prepared,
            "count": len(prepared),
        })
    return sections


def _count_items(reports) -> int:
    if not isinstance(reports, dict):
        return 0
    return sum(len(v or []) for v in reports.values())


def _has_surgery_suspected(sections: list[dict]) -> bool:
    for section in sections:
        for row in section.get("rows") or []:
            if row.get("suspected_grade") or row.get("suspected_n"):
                return True
    return False


# ── 폰트 임베딩 ──────────────────────────────────────────────────────────────
def _font_face_css() -> str:
    """backend/fonts/ 에 폰트 파일이 있으면 @font-face 로 임베딩(선택 사항).

    기본 경로는 서버 설치 폰트(fonts-noto-cjk)를 font-family 로 사용한다.
    """
    if not _FONTS_DIR.is_dir():
        return ""
    faces = []
    for f in sorted(_FONTS_DIR.iterdir()):
        if f.suffix.lower() not in (".ttf", ".otf", ".ttc"):
            continue
        fmt = "collection" if f.suffix.lower() == ".ttc" else ("opentype" if f.suffix.lower() == ".otf" else "truetype")
        faces.append(
            "@font-face { font-family: 'BohumfitCJK'; src: url('file://%s') format('%s'); }"
            % (f.as_posix(), fmt)
        )
    return "\n".join(faces)


# ── 렌더링 ───────────────────────────────────────────────────────────────────
class ReportError(ValueError):
    """payload 형식 오류 등 사용자 입력 문제."""


class ReportUnavailableError(RuntimeError):
    """Chromium 미설치 등 렌더러 사용 불가."""


def build_doc_no(generated_at: datetime) -> str:
    return f"{DOC_PREFIX}-{generated_at.strftime('%Y%m%d-%H%M%S')}"


def _common_context(generated_at: datetime) -> dict:
    return {
        "doc_no": build_doc_no(generated_at),
        "generated_at": generated_at.strftime("%Y-%m-%d %H:%M"),
        "biz": BUSINESS_FOOTER,
        "font_face_css": _font_face_css(),
        "sensitive_notice": SENSITIVE_NOTICE,
        # 헤더 워드마크 로고(라이트 헤더 → 컬러). 비어 있으면 템플릿이 텍스트 워드마크로 폴백.
        "logo_data_uri": _logo_data_uri("color"),
    }


def _split_address(addr: str) -> list[str]:
    """BOHUMFIT-051 A-4: 긴 소재지를 도로명/상세로 자연 분리(첫 쉼표 기준). 값 없으면 단일."""
    if not addr or addr.strip() in ("", "-"):
        return [addr or "-"]
    head, sep, tail = addr.partition(",")
    return [head.strip(), tail.strip()] if sep and tail.strip() else [addr.strip()]


def render_disclosure_html(payload: dict, generated_at: datetime) -> str:
    std_reports = payload.get("standard_reports") or {}
    easy_reports = payload.get("easy_reports") or {}
    std_sections = _prepare_section(std_reports, is_easy=False)
    easy_sections = _prepare_section(easy_reports, is_easy=True)
    ctx = {
        **_common_context(generated_at),
        # BOHUMFIT-051 A-1: 깨진 SVG 보조 텍스트 대신 깔끔한 CSS 텍스트 워드마크(브랜드 그린) 사용.
        "logo_data_uri": "",
        # BOHUMFIT-051 A-4: 소재지 도로명/상세 2줄 분리.
        "biz_address_lines": _split_address(BUSINESS_FOOTER.get("address", "-")),
        "reference_date": payload.get("reference_date") or "-",
        # BOHUMFIT-067: 리포트 본문(헤더)에 고객명 표시. payload 값(사용자 입력>자동추출)이며 없으면 ""(줄 생략).
        #   PII — 화면·PDF 표시만, 서버 영구 저장 안 함(기존 휘발 설계 유지).
        "customer_name": (payload.get("customer_name") or "").strip(),
        "std_sections": std_sections,
        "easy_sections": easy_sections,
        "has_surgery_suspected": _has_surgery_suspected(std_sections) or _has_surgery_suspected(easy_sections),
        "std_count": _count_items(std_reports),
        "easy_count": _count_items(easy_reports),
        "all_diseases": payload.get("all_disease_summary") or [],
        "total_med_sum": payload.get("total_med_sum"),
        "criteria": NO_DISCLOSURE_CRITERIA,
        "criteria_note": NO_DISCLOSURE_CRITERIA_NOTE,
        "disclaimer": DISCLOSURE_DISCLAIMER,
    }
    return _env.get_template("report_disclosure.html").render(**ctx)


def render_insurance_html(payload: dict, generated_at: datetime) -> str:
    inputs = payload.get("inputs") or {}
    results = payload.get("results") or {}
    claim = results.get("claim")
    cap = results.get("self_pay_cap")
    nhis = results.get("nhis_cap")
    min_ded = results.get("min_deductible")

    gen = inputs.get("generation")
    gen_label = f"{gen}세대" if gen else "모름"
    period = inputs.get("generation_period") or ""
    if gen and period:
        gen_label += f" ({period})"
    nc_option = inputs.get("nc_option")
    if gen == 3:
        gen_label += f" · 비급여 {str(nc_option) + '%' if nc_option is not None else '미선택'}"
    bracket = inputs.get("bracket")

    ctx = {
        **_common_context(generated_at),
        "inputs": inputs,
        "gen_label": gen_label,
        "bracket_label": f"{bracket}분위" if bracket else "모름",
        "year_label": inputs.get("year") or "-",
        "covered_self_pay": inputs.get("covered_self_pay") or 0,
        "non_covered": inputs.get("non_covered") or 0,
        "claim": claim,
        "claim_range": _won_range(claim.get("low", 0), claim.get("high", 0)) if claim else "",
        "cap": cap,
        "nhis": nhis,
        "min_ded": min_ded,
        "non_covered_note": NON_COVERED_NOTE,
        "nhis_cap_note": NHIS_CAP_NOTE,
        "cap_rules": SELF_PAY_CAP_RULES,
        "disclaimer": INSURANCE_DISCLAIMER,
    }
    return _env.get_template("report_insurance.html").render(**ctx)


def render_report_html(report_type: str, payload: dict, generated_at: datetime | None = None) -> str:
    """report_type 별 HTML 렌더링. 산출물은 BOHUMFIT 표기만 사용(구 브랜드명 금지)."""
    if report_type not in REPORT_TYPES:
        raise ReportError(f"report_type 은 {REPORT_TYPES} 중 하나여야 합니다.")
    if not isinstance(payload, dict):
        raise ReportError("payload 는 JSON 객체여야 합니다.")
    generated_at = generated_at or _now_kst()   # BOHUMFIT-051: KST 기준
    if report_type == "disclosure":
        html = render_disclosure_html(payload, generated_at)
    else:
        html = render_insurance_html(payload, generated_at)
    # 콘텐츠 수정 3: 템플릿·고정 문구는 BOHUMFIT 표기만 사용(구 브랜드명 금지) —
    # 준수 여부는 tests/test_report_pdf.py 에서 산출물 문자열 검사로 강제한다.
    return html


# ── PDF 변환 (헤드리스 Chromium) ────────────────────────────────────────────
_FOOTER_TEMPLATE = (
    '<div style="width:100%; font-size:8px; color:#8a8f98; padding:0 12mm; '
    'display:flex; justify-content:space-between;">'
    "<span>분석도구 BOHUMFIT · {doc_no}</span>"
    '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span>'
    "</div>"
)

PDF_RENDER_TIMEOUT_MS = 30_000


async def html_to_pdf_bytes(html: str, doc_no: str) -> bytes:
    """HTML → PDF 바이트. 디스크 미사용(메모리 내 처리), 외부 네트워크 차단."""
    try:
        from playwright.async_api import async_playwright
    except ImportError as e:
        raise ReportUnavailableError("playwright 미설치 — PDF 렌더러를 사용할 수 없습니다.") from e

    try:
        async with async_playwright() as p:
            # Playwright가 설치한 Chromium을 사용한다.
            # Railway/Nixpacks 빌드에서 `python -m playwright install --with-deps chromium`을
            # 실행하면 이 경로로 렌더링된다. channel 지정은 시스템 Chromium 의존을
            # 만들 수 있어 배포 환경에서 더 취약하다.
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            try:
                page = await browser.new_page()
                # 외부 리소스 차단 — 템플릿은 자체 완결(로컬 폰트 file:// 만 허용)
                await page.route(
                    re.compile(r"^https?://"),
                    lambda route: route.abort(),
                )
                await page.set_content(html, wait_until="load", timeout=PDF_RENDER_TIMEOUT_MS)
                # 이미지(헤더 로고 data-URI 등) 디코드 완료 보장 — 디코드 전 캡처 시 로고가 누락된다.
                await page.evaluate(
                    "async () => { await Promise.all("
                    "Array.from(document.images).map("
                    "img => (img.decode ? img.decode() : Promise.resolve()).catch(() => {})"
                    ")); }"
                )
                await page.wait_for_timeout(60)
                pdf = await page.pdf(
                    format="A4",
                    print_background=True,
                    margin={"top": "14mm", "bottom": "16mm", "left": "12mm", "right": "12mm"},
                    display_header_footer=True,
                    header_template="<span></span>",
                    footer_template=_FOOTER_TEMPLATE.format(doc_no=doc_no),
                )
            finally:
                await browser.close()
    except ReportUnavailableError:
        raise
    except Exception as e:
        # Chromium 실행 파일 미설치(playwright install 누락) 등
        msg = str(e)
        if "Executable doesn't exist" in msg or "playwright install" in msg:
            raise ReportUnavailableError(
                "Chromium 미설치 — 배포 환경에서 `playwright install chromium` 실행이 필요합니다."
            ) from e
        raise
    return pdf


async def generate_report_pdf(report_type: str, payload: dict, generated_at: datetime | None = None) -> bytes:
    """리포트 종류별 PDF 생성 오케스트레이터 (휘발 처리 — 저장 없음)."""
    generated_at = generated_at or _now_kst()   # BOHUMFIT-051: KST 기준
    html = render_report_html(report_type, payload, generated_at)
    pdf = await html_to_pdf_bytes(html, build_doc_no(generated_at))
    logger.info("report pdf generated: type=%s bytes=%d", report_type, len(pdf))
    return pdf
