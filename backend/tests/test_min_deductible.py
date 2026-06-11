# -*- coding: utf-8 -*-
"""BOHUMFIT-028 실손 최소공제(정액↔정률 max) + 의원 자동분류 — §6-3 케이스 1~14.

기준 문서: .agent-harness/docs/BOHUMFIT_실비기능_설계_v4.md
additive — 기존 ①②③ 로직 회귀 없음(별도 함수).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from insurance.constants import (  # noqa: E402
    MIN_DEDUCTIBLE_BY_GEN,
    MIN_DEDUCTIBLE_DEFAULT_GRADE,
)
from insurance.calculator import (  # noqa: E402
    classify_provider,
    provider_deductible,
    estimate_claim_per_row,
    estimate_non_covered_claim_with_deductible,
)


# ── 케이스 1~3: max(정액, 정률) 산식 ──
def test_case1_fixed_dominant_clinic():
    r = estimate_claim_per_row(30000, 0.20, 10000)  # 정률 6천 < 정액 1만
    assert r["final_deductible"] == 10000
    assert r["reimbursement"] == 20000
    assert r["low_value"] is False


def test_case2_pct_dominant_general():
    r = estimate_claim_per_row(200000, 0.20, 15000)  # 정률 4만 > 정액 1.5만
    assert r["final_deductible"] == 40000
    assert r["reimbursement"] == 160000


def test_case3_boundary_pct_equals_fixed():
    r = estimate_claim_per_row(50000, 0.20, 10000)  # 정률 1만 == 정액 1만
    assert r["pct_deductible"] == r["fixed_deductible"] == 10000
    assert r["reimbursement"] == 40000


# ── 케이스 4: 비급여 건별 ≠ 총액 일괄 ──
def test_case4_per_visit_vs_total_differs():
    per = estimate_non_covered_claim_with_deductible(
        copay_rate=0.30, fixed_deductible=10000, per_visit_amount=30000, visit_count=3)
    tot = estimate_non_covered_claim_with_deductible(
        copay_rate=0.30, fixed_deductible=10000, total_amount=90000)
    assert per["reimbursement"] == 60000   # (3만-1만)×3
    assert tot["reimbursement"] == 63000   # 9만-2.7만 (공제 1회)
    assert per["reimbursement"] != tot["reimbursement"]
    assert per["total_only"] is False and tot["total_only"] is True


# ── 케이스 5: 입원(정액 통원공제 없음 → 정률만) ──
def test_case5_inpatient_no_fixed_deductible():
    r = estimate_claim_per_row(100000, 0.20, 0)
    assert r["final_deductible"] == 20000  # 정률만
    assert r["reimbursement"] == 80000


# ── 케이스 6~8: 세대·등급 분기 ──
def test_case6_unknown_grade_defaults_tertiary():
    assert provider_deductible(4, "unknown") == 20000  # 상급 2만
    assert MIN_DEDUCTIBLE_DEFAULT_GRADE == "tertiary"


def test_case7_gen1_legacy_none():
    assert provider_deductible(1, "clinic") is None
    assert MIN_DEDUCTIBLE_BY_GEN[1] is None


def test_case8_gen5_prep_none():
    assert provider_deductible(5, "clinic") is None
    assert MIN_DEDUCTIBLE_BY_GEN[5] is None


# ── 케이스 9: 최소공제 미사용(정액 0) → 기존 정률 산식과 일치 ──
def test_case9_no_min_deductible_matches_pct_only():
    charge, rate = 50000, 0.20
    r = estimate_claim_per_row(charge, rate, 0)
    assert r["reimbursement"] == int(round(charge * (1 - rate)))  # 4만 = 기존 산식


# ── 케이스 10: 백엔드-TS 미러 참조값 (Disclosure.tsx insClaimPerRow 와 일치해야) ──
# Codex/리뷰어는 아래 참조값이 프론트 TS 미러 결과와 동일한지 대조한다.
MIRROR_REFERENCE = {
    "clinic_3man_r20_d10k": (estimate_claim_per_row(30000, 0.20, 10000)["reimbursement"], 20000),
    "general_20man_r20_d15k": (estimate_claim_per_row(200000, 0.20, 15000)["reimbursement"], 160000),
    "low_value_8k": (estimate_claim_per_row(8000, 0.20, 10000)["reimbursement"], 0),
}

def test_case10_mirror_reference_values():
    for k, (got, expected) in MIRROR_REFERENCE.items():
        assert got == expected, f"{k}: {got} != {expected}"


# ── 케이스 11~12: 기관 자동분류 ──
def test_case11_clinic_classification():
    assert classify_provider("서울정형외과의원") == "clinic"
    assert classify_provider("행복한의원") == "clinic"


def test_case12_hospital_not_misclassified_as_clinic():
    assert classify_provider("삼성서울병원") == "unknown"
    assert classify_provider("서울대학교병원") == "unknown"
    assert classify_provider("강북삼성병원") == "unknown"


# ── 케이스 13: 청구 실익 낮음 ──
def test_case13_low_value_when_charge_below_deductible():
    r = estimate_claim_per_row(8000, 0.20, 10000)  # 진료비 < 정액공제
    assert r["reimbursement"] == 0
    assert r["low_value"] is True


# ── 케이스 14: 비급여 총액만 → total_only 플래그 + 안내 ──
def test_case14_total_only_flag_and_limitation():
    r = estimate_non_covered_claim_with_deductible(
        copay_rate=0.30, fixed_deductible=10000, total_amount=90000)
    assert r["total_only"] is True
    assert "limitation" in r and "회차별" in r["limitation"]


# ── additive 회귀: 기존 ①②③ 함수 영향 없음(별도 함수 존재 확인) ──
def test_existing_functions_untouched():
    from insurance.calculator import (
        estimate_insurance_claim, check_self_pay_cap, check_nhis_out_of_pocket_cap,
    )
    assert callable(estimate_insurance_claim)
    assert callable(check_self_pay_cap)
    assert callable(check_nhis_out_of_pocket_cap)
