# -*- coding: utf-8 -*-
"""실손/건보 청구 안내 계산 모듈 — 순수 함수 (SURIT-022 1단계).

기준 문서: .agent-harness/docs/BOHUMFIT_실비기능_설계_v3.md §3 (계산 로직).

원칙
  - 추정 안내형: 확정 금액 단정 금지. 출력은 "추정 범위 + 가능성".
  - 공제 미적용 → 동일 입력 = 동일 출력 (결정론적).
  - 알릴의무 로직과 독립. UI 없음(입력 → 출력만).

한계 (설계 §A 데이터 진단 반영 — 반환값/주석에 명시)
  - PDF "내가 낸 의료비"는 전부 급여 본인부담으로 간주(비급여 혼재 여부 PDF로 확정 불가).
  - 비급여는 PDF 미사용 — 사용자가 직접 입력(없으면 0).
  - 요양병원 120일 초과는 요양기관명 휴리스틱으로만 분기 시도(정확도 한계).
"""
from __future__ import annotations

import re
from typing import Any, Iterable

from .constants import (
    COPAY_RATE_DRAFT,
    GENERATION_COPAY_RATES,
    NHIS_CAP_BASE_YEAR,
    NHIS_OUT_OF_POCKET_CAP_2026,
    NHIS_PRE_PAYMENT_MAX_CAP_2026,
    NURSING_HOSPITAL_LONG_STAY_DAYS,
    SELF_PAY_ANNUAL_CAP,
)

DISCLAIMER = (
    "추정값입니다. 정확한 보험금·환급금 지급 여부와 금액은 보험사 약관·심사 및 "
    "국민건강보험공단 확인이 필요합니다."
)

# PDF 원시 레코드에서 '내가 낸 의료비'(급여 본인부담) 추출용 컬럼 후보
_SELF_PAY_COL_KEYS = ("내가낸의료비", "내가낸진료비", "본인부담금", "본인부담총액", "본인부담")
_DATE_COL_KEYS = ("진료개시일", "진료시작일", "진료일", "진료일자")
_HOSPITAL_COL_KEYS = ("요양기관명", "병·의원", "기관명", "병·의원&약국")
_INOUT_COL_KEYS = ("입내원구분", "입원외래구분", "구분")
_DAYS_COL_KEYS = ("입원일수", "요양일수", "내원일수")


# ── 내부 헬퍼 ──────────────────────────────────────────────────────────

def _norm(s: Any) -> str:
    return re.sub(r"[\s·ㆍ/\\&()\[\]_\-]+", "", str(s or ""))


def _get_field(rec: dict, keys: Iterable[str]) -> str:
    """레코드(dict)에서 정규화 키 일치로 값을 읽는다. 없으면 ''."""
    if not isinstance(rec, dict):
        return ""
    norm_items = [(_norm(k), v) for k, v in rec.items()]
    targets = [_norm(k) for k in keys]
    for t in targets:                       # 1) 정확 일치 우선
        for nk, v in norm_items:
            if nk == t and v not in (None, ""):
                return str(v).strip()
    for t in targets:                       # 2) 부분 일치 (헤더 OCR 변형 대비)
        for nk, v in norm_items:
            if t and t in nk and v not in (None, ""):
                return str(v).strip()
    return ""


def _to_won(raw: Any) -> int:
    """문자열/숫자에서 정수 원(整)을 추출. 숫자 없으면 0."""
    if raw is None or raw == "":
        return 0
    nums = re.findall(r"\d+", str(raw))
    if not nums:
        return 0
    try:
        return int("".join(nums))
    except ValueError:
        return 0


def _extract_year(date_str: Any) -> int | None:
    m = re.search(r"(\d{4})", str(date_str or ""))
    return int(m.group(1)) if m else None


def _won_to_man(won: int) -> str:
    """원 → '약 N만원' 표기 (만원 단위 반올림). 추정 톤."""
    if won <= 0:
        return "0원"
    return f"약 {round(won / 10_000):,}만원"


def _coerce_generation(generation: Any) -> int | None:
    try:
        g = int(generation)
    except (TypeError, ValueError):
        return None
    return g if g in GENERATION_COPAY_RATES else None


# ── 데이터 재집계 (설계 §5) ────────────────────────────────────────────

def aggregate_covered_self_pay_by_year(records: list[dict]) -> dict:
    """PDF 원시 레코드의 '내가 낸 의료비'(=급여 본인부담)를 진료일 기준 연도별 합산.

    설계 §5-1: disease_aggregator 가 이 컬럼을 집계하지 않으므로 실손 모듈에서
    원시 레코드 기준으로 신규 재집계한다. 모든 금액을 급여로 간주한다.

    Returns:
      {
        "by_year":   {연도(int): 급여본인부담합(int 원)},
        "total":     전체 합(int 원),
        "captured":  bool,   # '내가 낸 의료비' 컬럼을 한 건이라도 찾았는지
        "limitation": str,   # 한계 안내 (컬럼 미발견 시 사유)
      }
    """
    by_year: dict[int, int] = {}
    captured = False
    for rec in records or []:
        amount_raw = _get_field(rec, _SELF_PAY_COL_KEYS)
        if amount_raw == "":
            continue
        captured = True
        year = _extract_year(_get_field(rec, _DATE_COL_KEYS))
        if year is None:
            continue
        by_year[year] = by_year.get(year, 0) + _to_won(amount_raw)

    if not captured:
        limitation = (
            "PDF 원시 레코드에서 '내가 낸 의료비'(본인부담금) 컬럼을 찾지 못했습니다. "
            "심평원 PDF 종류에 따라 해당 컬럼이 없을 수 있어 급여 본인부담 집계가 불가합니다."
        )
    else:
        limitation = (
            "PDF '내가 낸 의료비'는 전부 급여 본인부담으로 간주해 합산했습니다. "
            "비급여가 섞여 있을 경우 실제와 다를 수 있습니다(비급여는 사용자 입력으로 분리)."
        )
    return {
        "by_year": dict(sorted(by_year.items())),
        "total": sum(by_year.values()),
        "captured": captured,
        "limitation": limitation,
    }


def detect_nursing_long_stay(records: list[dict]) -> dict:
    """요양기관명 휴리스틱으로 요양병원 입원일수를 연도별 합산, 120일 초과 여부 판정.

    설계 §3-4/§5-3: 요양병원 구분 플래그가 없어 '요양병원' 문자열 휴리스틱으로만
    분기를 시도한다(정확도 한계 — 반환 limitation 에 명시).
    """
    by_year: dict[int, int] = {}
    for rec in records or []:
        hospital = _get_field(rec, _HOSPITAL_COL_KEYS)
        if "요양병원" not in _norm(hospital):
            continue
        in_out = _get_field(rec, _INOUT_COL_KEYS)
        if "입원" not in in_out:
            continue
        year = _extract_year(_get_field(rec, _DATE_COL_KEYS))
        if year is None:
            continue
        days = _to_won(_get_field(rec, _DAYS_COL_KEYS)) or 1
        by_year[year] = by_year.get(year, 0) + days

    over_years = [y for y, d in by_year.items() if d > NURSING_HOSPITAL_LONG_STAY_DAYS]
    return {
        "by_year": dict(sorted(by_year.items())),
        "over_120_years": sorted(over_years),
        "any_over_120": bool(over_years),
        "heuristic": True,
        "limitation": (
            "요양병원 여부를 기관명에 '요양병원'이 포함되는지로만 추정합니다. "
            "명칭에 드러나지 않으면 누락될 수 있어, 장기입원 시 상한이 다를 수 있습니다."
        ),
    }


# ── ① 실손 청구 추정 (설계 §3-2) ───────────────────────────────────────

def estimate_insurance_claim(
    covered_self_pay: int,
    generation: Any,
    *,
    non_covered: int = 0,
    non_covered_option: int | None = None,
) -> dict:
    """세대별 자기부담률로 실손 청구 추정액(범위)을 산출한다.

    청구 추정 = 금액 × (1 - 자기부담률).  자기부담률이 범위면 추정도 범위가 된다.
    급여 = PDF '내가 낸 의료비', 비급여 = 사용자 입력(없으면 0).
    공제 미적용 → 동일 입력 = 동일 출력.
    """
    gen = _coerce_generation(generation)
    if gen is None:
        return {
            "kind": "insurance_claim",
            "possibility": "판정 불가",
            "estimate_low": None,
            "estimate_high": None,
            "message": "실손 세대(1~5)를 선택하면 청구 추정 범위를 안내할 수 있습니다.",
            "caveats": ["세대 미선택"],
            "disclaimer": DISCLAIMER,
        }

    rates = GENERATION_COPAY_RATES[gen]
    cov_lo, cov_hi = rates["covered"]

    # 비급여 자기부담률 — 3세대 등 옵션(20/30) 우선, 없으면 범위 사용
    options = rates.get("non_covered_options")
    if non_covered_option is not None and options and non_covered_option in options:
        ncov_lo = ncov_hi = options[non_covered_option]
    else:
        ncov_lo, ncov_hi = rates["non_covered"]

    covered_self_pay = max(0, int(covered_self_pay or 0))
    non_covered = max(0, int(non_covered or 0))

    # 청구 추정 범위: 높은 자기부담률 → 낮은 청구액
    cov_claim_low = int(round(covered_self_pay * (1 - cov_hi)))
    cov_claim_high = int(round(covered_self_pay * (1 - cov_lo)))
    ncov_claim_low = int(round(non_covered * (1 - ncov_hi)))
    ncov_claim_high = int(round(non_covered * (1 - ncov_lo)))

    total_low = cov_claim_low + ncov_claim_low
    total_high = cov_claim_high + ncov_claim_high

    has_amount = (covered_self_pay + non_covered) > 0
    possibility = "청구 대상일 수 있음" if has_amount else "청구 대상 아닐 수 있음"

    caveats: list[str] = []
    if COPAY_RATE_DRAFT:
        caveats.append("세대별 자기부담률은 약관 검증 전 초안값 — 실제와 다를 수 있음")
    if non_covered == 0:
        caveats.append("비급여 미입력 — 비급여 청구분은 추정에 포함되지 않음")
    if gen == 5:
        caveats.append("5세대 급여 외래는 건보 연동(최대 60%)이라 추정 범위가 넓음")

    if total_low == total_high:
        est_msg = f"청구 추정 {_won_to_man(total_low)} 수준일 수 있습니다"
    else:
        est_msg = f"청구 추정 {_won_to_man(total_low)}~{_won_to_man(total_high)} 수준일 수 있습니다"

    return {
        "kind": "insurance_claim",
        "generation": gen,
        "possibility": possibility,
        "estimate_low": total_low,
        "estimate_high": total_high,
        "covered": {"self_pay": covered_self_pay, "claim_low": cov_claim_low, "claim_high": cov_claim_high},
        "non_covered": {"input": non_covered, "claim_low": ncov_claim_low, "claim_high": ncov_claim_high},
        "message": f"{possibility} — {est_msg}." if has_amount else f"{possibility}.",
        "caveats": caveats,
        "disclaimer": DISCLAIMER,
    }


# ── ② 실손 자기부담금 연 상한 초과 (설계 §3-3) ─────────────────────────

def check_self_pay_cap(annual_self_pay: int, generation: Any) -> dict:
    """연간 실손 자기부담금이 세대별 연 상한을 초과하는지.

    설계 §4-2 상한값 미확보(None) → '판정 불가'로 반환(추측 금지).
    """
    gen = _coerce_generation(generation)
    base = {
        "kind": "self_pay_cap",
        "generation": gen,
        "disclaimer": DISCLAIMER,
    }
    if gen is None:
        return {**base, "possibility": "판정 불가",
                "message": "실손 세대(1~5)를 선택해 주세요.",
                "limitation": "세대 미선택"}

    cap = SELF_PAY_ANNUAL_CAP.get(gen)
    if cap is None:
        return {
            **base,
            "possibility": "판정 불가",
            "cap": None,
            "message": "세대별 실손 자기부담금 연 상한값이 아직 확보되지 않아 초과 여부를 판정할 수 없습니다.",
            "limitation": "설계문서 §4-2 미확보 — 약관 확인 후 상한값 입력 시 판정 가능",
        }

    annual_self_pay = max(0, int(annual_self_pay or 0))
    exceeded = annual_self_pay > cap
    excess = max(0, annual_self_pay - cap)
    return {
        **base,
        "possibility": "초과분 추가 보장 가능성 있음" if exceeded else "상한 초과 아닐 수 있음",
        "cap": cap,
        "annual_self_pay": annual_self_pay,
        "excess": excess,
        "message": (
            f"연 자기부담금이 세대 상한({_won_to_man(cap)})을 초과해 초과분 {_won_to_man(excess)} "
            f"수준의 추가 보장 가능성이 있습니다."
            if exceeded else
            f"연 자기부담금이 세대 상한({_won_to_man(cap)}) 이내로 보입니다."
        ),
    }


# ── ③ 건보 본인부담상한제 초과 (설계 §3-4) ─────────────────────────────

def check_nhis_out_of_pocket_cap(
    annual_covered_self_pay: int,
    income_bracket: Any,
    *,
    nursing_long_stay: bool = False,
) -> dict:
    """연간 급여 본인부담금이 소득분위별 본인부담상한(2026)을 초과하는지.

    설계 §3-4: 대상은 급여 본인부담금만(비급여 입력분 제외). 요양병원 120일 초과 시
    별도(높은) 상한을 적용한다. 분위 미선택('모름') → 판정 불가.
    """
    base = {
        "kind": "nhis_out_of_pocket_cap",
        "base_year": NHIS_CAP_BASE_YEAR,
        "scope": "급여 본인부담금만 (비급여·선별급여·전액본인부담·상급병실 등 제외)",
        "disclaimer": DISCLAIMER,
    }
    try:
        bracket = int(income_bracket)
    except (TypeError, ValueError):
        bracket = None
    if bracket not in NHIS_OUT_OF_POCKET_CAP_2026:
        return {
            **base,
            "possibility": "판정 불가",
            "cap": None,
            "message": "소득분위(1~10)를 선택하면 본인부담상한제 환급 가능성을 안내할 수 있습니다.",
            "limitation": "소득분위 미선택",
        }

    general_cap, nursing_cap = NHIS_OUT_OF_POCKET_CAP_2026[bracket]
    cap = nursing_cap if nursing_long_stay else general_cap
    annual = max(0, int(annual_covered_self_pay or 0))
    exceeded = annual > cap
    refund = max(0, annual - cap)
    return {
        **base,
        "income_bracket": bracket,
        "nursing_long_stay": nursing_long_stay,
        "cap": cap,
        "annual_covered_self_pay": annual,
        "possibility": "공단 환급 가능성 있음" if exceeded else "환급 대상 아닐 수 있음",
        "refund_estimate": refund,
        "message": (
            f"{bracket}분위 상한({_won_to_man(cap)})을 초과해 공단 환급 {_won_to_man(refund)} "
            f"수준의 가능성이 있습니다(진료일 기준 연도별, 급여만)."
            if exceeded else
            f"연 급여 본인부담금이 {bracket}분위 상한({_won_to_man(cap)}) 이내로 보입니다."
        ),
    }


# ── 통합 안내 (선택 — 세 안내를 한 번에 구성) ──────────────────────────

def build_insurance_guidance(
    records: list[dict],
    *,
    generation: Any,
    income_bracket: Any = None,
    non_covered: int = 0,
    non_covered_option: int | None = None,
    year: int | None = None,
) -> dict:
    """PDF 레코드 + 사용자 입력으로 3대 안내를 한 번에 구성한다(순수).

    year 미지정 시 가장 최근 연도를 사용. 단정 금지 — 각 항목은 가능성/범위.
    """
    agg = aggregate_covered_self_pay_by_year(records)
    by_year = agg["by_year"]
    target_year = year if year is not None else (max(by_year) if by_year else None)
    covered_self_pay = by_year.get(target_year, 0) if target_year is not None else 0

    nursing = detect_nursing_long_stay(records)
    nursing_over = (target_year in nursing["over_120_years"]) if target_year is not None else nursing["any_over_120"]

    annual_self_pay_total = covered_self_pay + max(0, int(non_covered or 0))

    return {
        "target_year": target_year,
        "covered_self_pay_by_year": by_year,
        "covered_capture_limitation": None if agg["captured"] else agg["limitation"],
        "claim": estimate_insurance_claim(
            covered_self_pay, generation,
            non_covered=non_covered, non_covered_option=non_covered_option,
        ),
        "self_pay_cap": check_self_pay_cap(annual_self_pay_total, generation),
        "nhis_cap": check_nhis_out_of_pocket_cap(
            covered_self_pay, income_bracket, nursing_long_stay=nursing_over,
        ),
        "nursing_long_stay": nursing,
        "disclaimer": DISCLAIMER,
    }
