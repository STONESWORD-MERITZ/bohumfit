# -*- coding: utf-8 -*-
"""BOHUMFIT-238 종수술비 5종→1~5종 표준 환산 회귀 — 익명 합성 픽스처만 사용."""
from __future__ import annotations

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coverage.aggregator import build_before  # noqa: E402
from coverage.jong_surgery import (  # noqa: E402
    DEFAULT_JONG_TABLE,
    MAN,
    OUT_OF_RANGE_LABEL,
    estimated_tier_label,
    has_explicit_tier,
    lookup_jong_tiers,
)
from coverage.parser import parse_detail_pages  # noqa: E402

SQL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "supabase", "manual",
                        "BOHUMFIT-238-01-jong-surgery-table.sql")


# ── 룩업 정확성: 확정표 10행 전부 ────────────────────────────────────────────
@pytest.mark.parametrize("base_man", sorted(DEFAULT_JONG_TABLE))
def test_lookup_exact_rows(base_man):
    tiers = lookup_jong_tiers(base_man * MAN)
    assert tiers == {i + 1: t * MAN for i, t in enumerate(DEFAULT_JONG_TABLE[base_man])}


def test_lookup_floor_rule():
    # 표에 없는 기준액은 이하 최대값 행(750만 → 700행, 1,500만 → 1,000행).
    assert lookup_jong_tiers(750 * MAN) == {i + 1: t * MAN for i, t in enumerate(DEFAULT_JONG_TABLE[700])}
    assert lookup_jong_tiers(1500 * MAN) == {i + 1: t * MAN for i, t in enumerate(DEFAULT_JONG_TABLE[1000])}


def test_lookup_out_of_range():
    assert lookup_jong_tiers(50 * MAN) is None      # 100만원 미만 — 표 외
    assert lookup_jong_tiers(None) is None
    assert lookup_jong_tiers(0) is None


def test_explicit_tier_markers():
    # 종별 분리형(원문 종별 금액 존재) — 환산 미적용 대상.
    assert has_explicit_tier("질병1~5종수술비Ⅱ(매회지급)(간편가입)(갱신형)_1종")
    assert has_explicit_tier("질병1-5종수술비Ⅲ(1종,동일질병당1회지급)(맞춤간편고지)")
    # 범위·기준 표기는 마커가 아니다(237-F 실측 — 단일 합산형).
    assert not has_explicit_tier("질병1~5종수술(수술당1회한)(5종수술)")


# ── fallback 내장표 = SQL 시딩표 값 일치(동기화 계약) ────────────────────────
def test_fallback_matches_sql_seed():
    sql = open(SQL_PATH, encoding="utf-8").read()
    rows = re.findall(r"\(\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)", sql)
    seeded = {int(r[0]): tuple(int(v) for v in r[1:]) for r in rows}
    assert seeded == DEFAULT_JONG_TABLE


# ── 파서 적용/미적용 ─────────────────────────────────────────────────────────
def _detail(lines_body: str):
    head = (
        "홍길동 님의 상품별 가입담보상세\n가나손보 | 가입일자 : 2024-01-01 |\n합성보험\n"
        "홍길동/홍길동 월납/20년/100세만기\n2024-01-01~2124-01-01 50,000원\n"
    )
    return (head + lines_body).splitlines()


CONTRACTS = [{"idx": 1, "monthly_premium": 50_000}]


def test_five_tier_base_converted_with_estimated_flag():
    page = _detail("2 정액 간편심사 질병1~5종수술(수술당1회한)(5종수술) 질병종수술 1,000만\n")
    _notes, extra = parse_detail_pages([page], CONTRACTS)
    assert "종수술비" not in extra  # 통합 버킷 대신 1~5종 세팅으로 대체
    for tier, man in ((1, 20), (2, 50), (3, 100), (4, 500), (5, 1000)):
        entry = extra[estimated_tier_label(tier)]
        assert entry["by_company"] == {"1": man * MAN}
        assert entry["estimated"] is True


def test_two_base_riders_sum_per_tier():
    page = _detail(
        "2 정액 질병1~5종수술(수술당1회한)(5종수술) 질병종수술 1,000만\n"
        "3 정액 상해1~5종수술(수술당1회한)(5종수술) 상해종수술 1,000만\n"
    )
    _notes, extra = parse_detail_pages([page], CONTRACTS)
    assert extra[estimated_tier_label(5)]["by_company"] == {"1": 2000 * MAN}
    assert extra[estimated_tier_label(1)]["by_company"] == {"1": 40 * MAN}


def test_explicit_tier_lines_not_converted():
    page = _detail(
        "16 정액 질병1~5종수술비Ⅱ(매회지급)(간편가입)(갱신형)_1종 질병종수술 10만\n"
        "17 정액 질병1~5종수술비Ⅱ(매회지급)(간편가입)(갱신형)_2종 질병종수술 20만\n"
    )
    _notes, extra = parse_detail_pages([page], CONTRACTS)
    # 원문 종별 존재 → 환산 미적용(원문 우선), 기존 통합 합산 유지·값 불변.
    assert extra["종수술비"]["by_company"] == {"1": 30 * MAN}
    assert not any("표준환산" in label for label in extra)


def test_below_table_kept_as_out_of_range():
    page = _detail("2 정액 질병1~5종수술(수술당1회한)(5종수술) 질병종수술 50만\n")
    _notes, extra = parse_detail_pages([page], CONTRACTS)
    assert extra[OUT_OF_RANGE_LABEL]["by_company"] == {"1": 50 * MAN}
    assert not any("표준환산" in label for label in extra)


def test_estimated_flag_survives_build_before():
    page = _detail("2 정액 질병1~5종수술(수술당1회한)(5종수술) 질병종수술 300만\n")
    _notes, extra = parse_detail_pages([page], CONTRACTS)
    raw = {
        "customer": {"name": "홍길동", "age": 40, "sex": "남자"},
        "contracts": [{"idx": 1, "insurer": "가나손보", "product": "합성", "contract_date": "2024-01-01",
                       "pay_cycle": "월납", "pay_years": 20, "pay_months": 240, "maturity": "100세",
                       "monthly_premium": 50_000}],
        "matrix": {}, "diagnosis": {}, "notes": {}, "extra": extra, "warnings": [],
    }
    before = build_before(raw, today="2026-07-21")
    rows = [c for c in before["coverages"] if "표준환산" in c["kb_name"]]
    assert len(rows) == 5
    assert all(row.get("estimated") is True for row in rows)
    tier3 = next(c for c in rows if c["kb_name"] == estimated_tier_label(3))
    assert tier3["summary"] == 50 * MAN  # 300만 행: 3종=50만


def test_custom_table_overrides_default():
    page = _detail("2 정액 질병1~5종수술(수술당1회한)(5종수술) 질병종수술 100만\n")
    custom = {100: (1, 2, 3, 4, 100)}
    _notes, extra = parse_detail_pages([page], CONTRACTS, jong_table=custom)
    assert extra[estimated_tier_label(1)]["by_company"] == {"1": 1 * MAN}
    assert extra[estimated_tier_label(5)]["by_company"] == {"1": 100 * MAN}
