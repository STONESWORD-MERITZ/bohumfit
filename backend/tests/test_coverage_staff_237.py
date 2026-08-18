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
# BOHUMFIT-290(S2): 집계 행이 V2 49행 — 구 이름 조회는 export와 같은 투영(legacy_form_view)으로.
from tests.v2names import legacy_form_view as _view  # noqa: E402
from coverage.v2_mapping import GROUP_APPENDIX_V2 as _APPENDIX  # noqa: E402


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


def test_n_surgery_lands_in_the_regular_row_with_max_amount():
    """★BOHUMFIT-296: N대수술비는 정규 행 `N대수술비 최대 보상금액`(수 술)으로 이관됐다.

    복수 N(131대 500만·121대 300만)은 **최대 보상금액**(max 500만)만 담는다(합산 아님·N 병기 없음).
    파서의 n_values 수집은 그대로 두되(정보), 표시명에는 N을 병기하지 않는다.
    """
    contracts = [{"idx": 1, "monthly_premium": 50_000}]
    _notes, extra = parse_detail_pages([DETAIL_N], contracts)
    assert sorted(extra["N대수술비"]["n_values"]) == [121, 131]
    assert extra["N대수술비"]["by_company"]["1"] == 5_000_000  # ★max(500만, 300만)
    before = build_before(_raw_with_extra(extra), today="2026-07-21")
    row = next(c for c in before["coverages"] if c.get("row_id") == "major_n_surgery")
    assert row["kb_name"] == "N대수술비 최대 보상금액"
    assert row["summary"] == 5_000_000 and row["group12"] == "수 술"
    # 구 N 병기 라벨은 더 이상 나오지 않는다.
    assert not any("N대수술비(" in c["kb_name"] for c in before["coverages"])


def test_single_n_value_lands_in_regular_row():
    before = build_before(
        _raw_with_extra({"N대수술비": {"agg": "sum", "by_company": {"1": 5_000_000}, "n_values": [131]}}),
        today="2026-07-21",
    )
    row = next(c for c in before["coverages"] if c.get("row_id") == "major_n_surgery")
    assert row["summary"] == 5_000_000 and row["kb_name"] == "N대수술비 최대 보상금액"


def test_no_n_values_lands_in_regular_row():
    before = build_before(
        _raw_with_extra({"N대수술비": {"agg": "sum", "by_company": {"1": 5_000_000}}}),
        today="2026-07-21",
    )
    assert any(c.get("row_id") == "major_n_surgery" for c in before["coverages"])
