# -*- coding: utf-8 -*-
"""BOHUMFIT-237 직원 피드백 1차 회귀 — 익명 합성 픽스처만 사용.

A 금액 한글 단위 포맷터 / B 운전자 6주미만 별도 담보 / C N대수술비 N 병기.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coverage.aggregator import build_before  # noqa: E402
from coverage.amount import format_krw, format_krw_delta  # noqa: E402
from coverage.constants import classify_extra, extract_n_surgery  # noqa: E402
from coverage.parser import parse_detail_pages  # noqa: E402


# ── A: 공용 포맷터 ────────────────────────────────────────────────────────────
def test_format_krw_units():
    assert format_krw(20_000_000) == "2,000만원"
    assert format_krw(120_000_000) == "1억 2,000만원"
    assert format_krw(100_000_000) == "1억원"
    assert format_krw(5_000) == "5,000원"
    assert format_krw(20_005_000) == "2,000만 5,000원"
    assert format_krw(0) == "0원"
    assert format_krw(None) == "-"
    assert format_krw_delta(-20_000_000) == "−2,000만원"
    assert format_krw_delta(20_000_000) == "+2,000만원"
    assert format_krw_delta(0) == "0"


# ── B: 운전자 6주미만 — 실측 원문 "교통사고 처리지원금(6주미만 진단)" ────────
def test_six_week_rider_classified_as_driver():
    got = classify_extra("18 실손 교통사고 처리지원금(6주미만 진단) 교통사고 처리지원금(6주미만 진단) 1,000만")
    assert got is not None and got[0] == "교통사고처리지원금(6주미만)"


# ── C: N대수술비 N 추출·병기 ─────────────────────────────────────────────────
def test_extract_n_surgery():
    assert extract_n_surgery("16 정액 131대질병수술비(1) 특정질병수술 500만") == 131
    # 괄호 수식어의 숫자는 N이 아니다(234 ② 계열 — 괄호 제거 후 매칭)
    assert extract_n_surgery("18 정액 119대질병수술비(20대질병)(맞춤간편고지) 특정질병수술 100만") == 119
    assert extract_n_surgery("화상진단비 화상진단 20만") is None


DETAIL_N = """홍길동 님의 상품별 가입담보상세
가나손보 | 가입일자 : 2024-01-01 |
합성 건강보험
홍길동/홍길동 월납/20년/100세만기
2024-01-01~2124-01-01 50,000원
1 정액 131대질병수술비(간편가입) 특정질병수술 500만
2 정액 121대질병수술비(갱신형) 특정질병수술 300만
""".splitlines()


def _raw_with_extra(extra):
    return {
        "customer": {"name": "홍길동", "age": 40, "sex": "남자"},
        "contracts": [{"idx": 1, "insurer": "가나손보", "product": "합성", "contract_date": "2024-01-01",
                       "pay_cycle": "월납", "pay_years": 20, "pay_months": 240, "maturity": "100세",
                       "monthly_premium": 50_000}],
        "matrix": {},
        "diagnosis": {},
        "notes": {},
        "extra": extra,
        "warnings": [],
    }


def test_n_values_collected_and_displayed():
    contracts = [{"idx": 1, "monthly_premium": 50_000}]
    _notes, extra = parse_detail_pages([DETAIL_N], contracts)
    assert sorted(extra["N대수술비"]["n_values"]) == [121, 131]
    before = build_before(_raw_with_extra(extra), today="2026-07-21")
    names = [c["kb_name"] for c in before["coverages"]]
    # 복수 N은 나열 병기(정보 무손실 — 최대값 단일 표기 대신 채택, 근거는 태스크 문서)
    assert "N대수술비(121·131대)" in names
    row = next(c for c in before["coverages"] if c["kb_name"] == "N대수술비(121·131대)")
    assert row["summary"] == 8_000_000
    assert row["group12"] == "기타"


def test_single_n_value_displayed():
    before = build_before(
        _raw_with_extra({"N대수술비": {"agg": "sum", "by_company": {"1": 5_000_000}, "n_values": [131]}}),
        today="2026-07-21",
    )
    assert any(c["kb_name"] == "N대수술비(131대)" for c in before["coverages"])


def test_no_n_values_keeps_plain_label():
    before = build_before(
        _raw_with_extra({"N대수술비": {"agg": "sum", "by_company": {"1": 5_000_000}}}),
        today="2026-07-21",
    )
    assert any(c["kb_name"] == "N대수술비" for c in before["coverages"])
