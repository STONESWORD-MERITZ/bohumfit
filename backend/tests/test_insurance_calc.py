# -*- coding: utf-8 -*-
"""SURIT-022 실손/건보 계산 모듈 단위 테스트.

검증: 세대별 자기부담률 / 건보 분위 경계(초과·미달) / 동일입력=동일출력 /
      비급여 입력 유무 분기 / 연도별 집계 / 미확보 상한 판정불가 / 요양병원 휴리스틱.
기준 문서: .agent-harness/docs/BOHUMFIT_실비기능_설계_v3.md
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from insurance.constants import (  # noqa: E402
    NHIS_OUT_OF_POCKET_CAP_2026,
    NHIS_CAP_BASE_YEAR,
    SELF_PAY_ANNUAL_CAP,
    SELF_PAY_ANNUAL_CAP_WON,
    SELF_PAY_CAP_SCOPE,
)
from insurance.calculator import (  # noqa: E402
    aggregate_covered_self_pay_by_year,
    detect_nursing_long_stay,
    estimate_insurance_claim,
    check_self_pay_cap,
    check_nhis_out_of_pocket_cap,
    build_insurance_guidance,
)

_MAN = 10_000


# ── 세대별 자기부담률 적용 ────────────────────────────────
def test_claim_gen4_fixed_rate():
    """4세대 급여 자기부담 20% → 청구 추정 = 본인부담 × 0.8 (단일값)."""
    r = estimate_insurance_claim(1_000_000, 4)
    assert r["estimate_low"] == r["estimate_high"] == 800_000
    assert r["possibility"] == "청구 대상일 수 있음"


def test_claim_gen2_rate_range_produces_range():
    """2세대 급여 10~20% → 청구 추정이 범위(80만~90만)로 나온다."""
    r = estimate_insurance_claim(1_000_000, 2)
    assert r["estimate_low"] == 800_000   # 1 - 0.20
    assert r["estimate_high"] == 900_000  # 1 - 0.10


def test_claim_gen3_non_covered_option_30():
    """3세대 비급여 옵션 30% 지정 → 비급여 청구 = 입력 × 0.7."""
    r = estimate_insurance_claim(0, 3, non_covered=1_000_000, non_covered_option=30)
    assert r["non_covered"]["claim_low"] == r["non_covered"]["claim_high"] == 700_000


def test_claim_unknown_generation_is_indeterminate():
    r = estimate_insurance_claim(1_000_000, None)
    assert r["possibility"] == "판정 불가"
    assert r["estimate_low"] is None


# ── 비급여 입력 유무 분기 ─────────────────────────────────
def test_claim_non_covered_absent_vs_present():
    no_ncov = estimate_insurance_claim(1_000_000, 4)
    with_ncov = estimate_insurance_claim(1_000_000, 4, non_covered=500_000)
    assert any("비급여 미입력" in c for c in no_ncov["caveats"])
    # 비급여 30% → 35만 추가
    assert with_ncov["estimate_low"] == 800_000 + 350_000
    assert with_ncov["non_covered"]["input"] == 500_000


# ── 동일 입력 = 동일 출력 (결정론) ────────────────────────
def test_deterministic_same_input_same_output():
    a = estimate_insurance_claim(1_234_000, 4, non_covered=200_000)
    b = estimate_insurance_claim(1_234_000, 4, non_covered=200_000)
    assert a == b
    c = check_nhis_out_of_pocket_cap(3_000_000, 5)
    d = check_nhis_out_of_pocket_cap(3_000_000, 5)
    assert c == d


# ── 건보 본인부담상한제 분위 경계 ─────────────────────────
def test_nhis_cap_boundary_exceed_and_within():
    cap1 = NHIS_OUT_OF_POCKET_CAP_2026[1][0]  # 1분위 일반 = 90만
    assert cap1 == 90 * _MAN
    over = check_nhis_out_of_pocket_cap(cap1 + 1, 1)
    within = check_nhis_out_of_pocket_cap(cap1, 1)  # 경계 동일액 = 초과 아님(> 기준)
    assert over["possibility"] == "공단 환급 가능성 있음"
    assert over["refund_estimate"] == 1
    assert within["possibility"] == "환급 대상 아닐 수 있음"
    assert within["refund_estimate"] == 0
    assert over["base_year"] == NHIS_CAP_BASE_YEAR == 2026


def test_nhis_cap_nursing_uses_higher_cap():
    """요양병원 120일 초과 시 더 높은 상한(1분위 143만) 적용."""
    general = NHIS_OUT_OF_POCKET_CAP_2026[1][0]   # 90만
    nursing = NHIS_OUT_OF_POCKET_CAP_2026[1][1]   # 143만
    r = check_nhis_out_of_pocket_cap(general + 1, 1, nursing_long_stay=True)
    assert r["cap"] == nursing == 143 * _MAN
    assert r["possibility"] == "환급 대상 아닐 수 있음"  # 90만+1 < 143만


def test_nhis_cap_unknown_bracket_indeterminate():
    r = check_nhis_out_of_pocket_cap(9_999_999, None)
    assert r["possibility"] == "판정 불가"
    assert r["cap"] is None


# ── 실손 자기부담금 연 상한 (§4-2 v3-1 확정 — 세대별 합산범위) ──
def test_self_pay_cap_all_generations_200():
    assert SELF_PAY_ANNUAL_CAP_WON == 2_000_000
    assert all(SELF_PAY_ANNUAL_CAP[g] == 2_000_000 for g in range(1, 6))


def test_self_pay_cap_scope_constant():
    assert SELF_PAY_CAP_SCOPE[1] == "covered_plus_non_covered"
    assert SELF_PAY_CAP_SCOPE[3] == "covered_plus_non_covered"
    assert SELF_PAY_CAP_SCOPE[4] == "covered_only"
    assert SELF_PAY_CAP_SCOPE[5] == "covered_only"


def test_self_pay_cap_gen1_3_sums_covered_and_non_covered():
    """1~3세대: 급여+비급여 자기부담 합산, 200만 경계."""
    # 140만 + 60만 = 200만 == 상한 → 초과 아님(> 기준)
    r_eq = check_self_pay_cap(1_400_000, 2, non_covered_self_pay_share=600_000)
    assert r_eq["eligible_self_pay"] == 2_000_000
    assert r_eq["possibility"] == "상한 초과 아닐 수 있음"
    assert r_eq["non_covered_excluded"] is False
    # 140만 + 60만 + 1 → 초과
    r_over = check_self_pay_cap(1_400_001, 3, non_covered_self_pay_share=600_000)
    assert r_over["possibility"] == "초과분 추가 보장 가능성 있음"
    assert r_over["excess"] == 1


def test_self_pay_cap_gen4_5_covered_only_excludes_non_covered():
    """4~5세대: 급여 자기부담만. 비급여는 상한에서 제외(비급여 제외 증명)."""
    # 급여 190만 + 비급여 500만 → 급여만 190만 < 200만 → 초과 아님
    r = check_self_pay_cap(1_900_000, 4, non_covered_self_pay_share=5_000_000)
    assert r["non_covered_excluded"] is True
    assert r["eligible_self_pay"] == 1_900_000
    assert r["possibility"] == "상한 초과 아닐 수 있음"
    # 급여 200만 + 1 → 초과 (5세대도 동일 scope)
    r2 = check_self_pay_cap(2_000_001, 5, non_covered_self_pay_share=0)
    assert r2["possibility"] == "초과분 추가 보장 가능성 있음"
    assert r2["non_covered_excluded"] is True


def test_self_pay_cap_unknown_generation_indeterminate():
    r = check_self_pay_cap(3_000_000, None)
    assert r["possibility"] == "판정 불가"


# ── 연도별 급여 본인부담 집계 ─────────────────────────────
def _basic(date, self_pay=None, hosp="행복내과", in_out="외래", days=None, code="R05"):
    rec = {"_ftype": "basic", "진료개시일": date, "주상병코드": code,
           "병·의원": hosp, "입내원구분": in_out}
    if self_pay is not None:
        rec["내가 낸 의료비"] = self_pay
    if days is not None:
        rec["입원일수"] = days
    return rec


def test_aggregate_self_pay_by_year():
    recs = [
        _basic("2024-03-01", "10000"),
        _basic("2024-05-01", "5,000"),
        _basic("2025-01-10", "20000"),
    ]
    agg = aggregate_covered_self_pay_by_year(recs)
    assert agg["captured"] is True
    assert agg["by_year"] == {2024: 15000, 2025: 20000}
    assert agg["total"] == 35000


def test_aggregate_self_pay_column_missing():
    """'내가 낸 의료비' 컬럼이 없으면 captured=False + 한계 안내."""
    recs = [_basic("2024-03-01", self_pay=None)]
    agg = aggregate_covered_self_pay_by_year(recs)
    assert agg["captured"] is False
    assert agg["by_year"] == {}
    assert "찾지 못" in agg["limitation"]


# ── 요양병원 120일 초과 휴리스틱 ──────────────────────────
def test_detect_nursing_long_stay_over_120():
    recs = [
        _basic("2024-02-01", hosp="행복요양병원", in_out="입원", days="100"),
        _basic("2024-06-01", hosp="행복요양병원", in_out="입원", days="30"),
        _basic("2024-07-01", hosp="서울내과", in_out="입원", days="200"),  # 요양병원 아님 → 제외
    ]
    r = detect_nursing_long_stay(recs)
    assert r["by_year"] == {2024: 130}
    assert r["any_over_120"] is True
    assert r["heuristic"] is True


# ── 통합 안내 ────────────────────────────────────────────
def test_build_guidance_picks_latest_year_and_sections():
    recs = [_basic("2024-03-01", "100000"), _basic("2025-04-01", "300000")]
    g = build_insurance_guidance(recs, generation=4, income_bracket=10)
    assert g["target_year"] == 2025
    assert g["claim"]["kind"] == "insurance_claim"
    assert g["nhis_cap"]["kind"] == "nhis_out_of_pocket_cap"
    # gen4 급여 30만 × 0.2 = 6만 자기부담 < 200만 → 초과 아님, 비급여 제외
    assert g["self_pay_cap"]["possibility"] == "상한 초과 아닐 수 있음"
    assert g["self_pay_cap"]["non_covered_excluded"] is True
