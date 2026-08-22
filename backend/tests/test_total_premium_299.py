# -*- coding: utf-8 -*-
"""BOHUMFIT-299 — 총납입 산식 [전] 기준 통일(일시납 미곱) 계약.

★고정하는 계약 (Human 확정)
  ① [전](`aggregator._paid`)과 [후](`compare._paid_total`)는 **같은 산식**을 쓴다.
  ② 234 결정 — **일시납은 표기 금액이 1회 납입 총액**이므로 개월 수를 곱하지 않는다.
     곱하면 이미 납입 완료된 금액이 부풀려져 [전]과 상시 어긋난다(295 §1-6 ② 발견).
  ③ ★일시납이 없는 계약은 **값이 변하지 않는다**(월납 × 개월 그대로).
  ④ 수정은 `compare._paid_total` **한 지점**에서만 한다(방어 분산 금지 — 295 선례).
  ★276c 월납 절삭 규칙과 무관하다(총납입은 이미 절삭된 월납을 받아 쓴다).

★PII: 익명 합성 픽스처만.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coverage.aggregator import _paid  # noqa: E402
from coverage.compare import _paid_total  # noqa: E402


def _contract(cycle, premium, months, idx=1):
    return {"idx": idx, "insurer": "가나손보", "product": "합성", "contract_date": "2024-01-01",
            "pay_cycle": cycle, "pay_years": months // 12 if months else None, "pay_months": months,
            "maturity": "100세", "monthly_premium": premium}


# ── ①② [전]·[후] 동일 산식 ─────────────────────────────────────────────────
def test_before_and_after_use_the_same_formula():
    """★뮤테이션(산식 통일 되돌림) 검출점 — 두 함수가 모든 케이스에서 같은 값을 낸다."""
    cases = [
        _contract("월납", 100_000, 240),
        _contract("일시납", 555_960, 12),
        _contract("일시납", 1_131_720, 12),
        _contract("연납", 1_200_000, 240),
        _contract("월납", 0, 240),
    ]
    for c in cases:
        assert _paid(c) == _paid_total(c), c["pay_cycle"]


def test_lump_sum_is_not_multiplied():
    """★뮤테이션(일시납 판정 제거) 검출점 — 일시납은 표기 금액 그대로."""
    c = _contract("일시납", 555_960, 12)
    assert _paid_total(c) == 555_960          # 6,671,520(순진곱)이 아니다
    assert _paid_total(c) != 555_960 * 12


def test_monthly_contract_value_is_unchanged():
    """★값 보존 — 일시납이 아니면 종전과 같다(월납 × 개월)."""
    c = _contract("월납", 100_000, 240)
    assert _paid_total(c) == 24_000_000 == _paid(c)
    y = _contract("연납", 50_000, 120)
    assert _paid_total(y) == 6_000_000 == _paid(y)


def test_missing_values_stay_none():
    assert _paid_total(_contract("월납", None, 240)) is None
    assert _paid_total(_contract("월납", 100_000, None)) is None
    # 일시납은 개월 수가 없어도 표기 금액을 그대로 쓴다(개월을 안 보므로).
    assert _paid_total(_contract("일시납", 555_960, None)) == 555_960


# ── ③ 문서 단위 값 보존 ────────────────────────────────────────────────────
def test_document_total_matches_before_side():
    """일시납 2건 + 월납 12건 혼합에서 [전] 합계와 [후] 합계가 일치한다.

    ★295가 기록한 실측 불일치(126,083,040 vs 144,647,520)의 차이 18,564,480은
      정확히 일시납 2건의 (순진곱 − 표기금액) 합이다 — 통일 후 0이 된다.
    """
    contracts = [_contract("월납", 500_000, 240, idx=i) for i in range(1, 13)]
    contracts.append(_contract("일시납", 555_960, 12, idx=13))
    contracts.append(_contract("일시납", 1_131_720, 12, idx=14))
    before_total = sum((_paid(c) or 0) for c in contracts)
    after_total = sum((_paid_total(c) or 0) for c in contracts)
    assert before_total == after_total
    naive = sum(((c["monthly_premium"] or 0) * (c["pay_months"] or 0)) for c in contracts)
    assert naive - after_total == (555_960 * 12 - 555_960) + (1_131_720 * 12 - 1_131_720) == 18_564_480


def test_no_lump_sum_document_is_untouched():
    """★일시납이 없는 문서는 통일 전후로 값이 같다(회귀 0)."""
    contracts = [_contract("월납", 300_000, 240, idx=i) for i in range(1, 15)]
    naive = sum(c["monthly_premium"] * c["pay_months"] for c in contracts)
    assert sum((_paid_total(c) or 0) for c in contracts) == naive
