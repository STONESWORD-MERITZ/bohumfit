# -*- coding: utf-8 -*-
"""BOHUMFIT-179b coverage parser regressions.

Fixtures are synthetic text snippets derived from the public parsing spec shape.
No real PDF, name, phone number, or contract file is stored in this test.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
from test_coverage_parser_179 import P5_LINES, P6_LINES, P7_LINES, P20_LINES  # noqa: E402

from coverage.aggregator import build_before, build_final  # noqa: E402
from coverage.constants import GROUP13, GROUP_ETC, classify_extra  # noqa: E402
from coverage.parser import parse_contract_list, parse_detail_pages, parse_diagnosis, parse_matrix  # noqa: E402

MAN = 10_000
EOK = 100_000_000

DETAIL_IDX2 = """홍길동 님의 상품별 가입담보상세
KB손보 | 가입일자 : 2023-11-15 |
KB Yes!365 건강보험(세만기)(무배당)(23.11) (1/2)
홍길동/홍길동 월납/25년/90세만기
2023-11-15~2082-11-15 101,463원
1 정액 일반상해사망(기본) 상해사망 1억
9 정액 모든 양성종양 및 폴립진단비(연간1회한) 특정질병진단 20만
10 정액 다빈도 양성종양 및 폴립진단비(연간1회한) 특정질병진단 10만
16 정액 112대질병수술비(1) 특정질병수술 500만
17 정액 112대질병수술비(2) 특정질병수술 300만
18 정액 112대질병수술비(3) 특정질병수술 100만
19 정액 112대질병수술비(4) 특정질병수술 50만
20 정액 112대질병수술비(5) 특정질병수술 50만
21 정액 5대장기이식수술비 특정질병수술 2,000만
23 정액 112대질병수술비(6) 기타수술 40만
""".splitlines()

DETAIL_IDX4 = """홍길동 님의 상품별 가입담보상세
삼성화재 | 가입일자 : 2012-05-25 |
무배당 삼성화재 건강보험 새시대건강파트너 (1204.5)
김*수/홍길동 월납/81년/100세만기
2012-05-25~2093-05-25 82,249원
16 정액 중대화상·부식진단비 중대화상진단 1,000만
17 정액 [갱신형]5대골절수술비 특정상해수술 50만
20 정액 [갱신형]5대장기이식수술비 기타수술 1,000만
""".splitlines()

DETAIL_IDX5 = """홍길동 님의 상품별 가입담보상세
삼성화재 | 가입일자 : 2024-02-07 |
무배당 삼성화재 건강보험 마이헬스 파트너(2402.9) 4종(일반형)
김*수/홍길동 월납/5년/100세만기
2024-02-07~2093-02-07 10,380원
2 정액 상급종합병원 1인실 입원일당(1일이상, 30일한도) 상급종합병원 질병입원일당 40만
3 정액 종합병원 1인실 입원일당(1일이상, 30일한도) 종합병원이하 질병입원일당 20만
4 정액 상급종합병원 1인실 입원일당(1일이상, 30일한도) 상급종합병원 상해입원일당 40만
5 정액 종합병원 1인실 입원일당(1일이상, 30일한도) 종합병원이하 상해입원일당 20만
""".splitlines()

DETAIL_IDX6 = """홍길동 님의 상품별 가입담보상세
삼성생명 | 가입일자 : 2013-12-29 |
퍼펙트통합보험Ⅰ3.0(無)_표준체
김*수/홍길동 월납/15년/9999세만기
2013-12-29~9999-12-31 333,600원
15 정액 퍼펙트통합보험Ⅰ3.0無_표준체 중대화상진단 5,000만
19 정액 리빙케어80세無(주피/갱신) 기타수술 2,000만
20 정액 특정질병수술無(주피/갱신) 기타수술 500만
""".splitlines()

DETAILS = [DETAIL_IDX2, DETAIL_IDX4, DETAIL_IDX5, DETAIL_IDX6]


def _build():
    contracts = parse_contract_list(P5_LINES)
    notes, extra = parse_detail_pages(DETAILS, contracts)
    raw = {
        "customer": {"name": "홍길동", "age": 33, "sex": "남자"},
        "contracts": contracts,
        "matrix": parse_matrix([P6_LINES, P7_LINES]),
        "diagnosis": parse_diagnosis(P20_LINES),
        "notes": notes,
        "extra": extra,
        "warnings": [],
    }
    before = build_before(raw)
    final = build_final(before, raw["diagnosis"])
    return raw, before, final


def _cov(table: dict, name: str):
    return next(c for c in table["coverages"] if c["kb_name"] == name)


def test_group13_added():
    assert len(GROUP13) == 13
    assert GROUP13[-1] == GROUP_ETC


def test_179_regression_totals_unchanged():
    _, before, _ = _build()
    assert before["premium"]["monthly_total"] == 573_227
    assert before["premium"]["paid_total"] == 181_984_128


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("상해사망", 5 * EOK + 5000 * MAN),
        ("일반암", 1 * EOK),
        ("상해입원일당", 6 * MAN),
    ],
)
def test_179_regression_core_coverages_unchanged(name, expected):
    _, before, _ = _build()
    assert _cov(before, name)["summary"] == expected


def test_179_base_coverage_count_unchanged():
    _, before, _ = _build()
    base = [c for c in before["coverages"] if c["group12"] != GROUP_ETC]
    assert len(base) == 37


@pytest.mark.parametrize(
    ("text", "label"),
    [
        ("112대질병수술비 특정질병수술 500만", "N대수술비"),
        ("중대화상·부식진단비 중대화상진단 1,000만", "화상"),
        ("양성종양 및 폴립진단비 특정질병진단 20만", "양성종양·폴립"),
        ("상급종합병원 1인실 입원일당 상급종합병원 질병입원일당 40만", "상급/종합병원 일당"),
    ],
)
def test_classify_extra_patterns(text, label):
    assert classify_extra(text)[0] == label


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("N대수술비", 4090 * MAN),
        ("화상", 6000 * MAN),
        ("양성종양·폴립", 30 * MAN),
        ("상급/종합병원 일당", 120 * MAN),
    ],
)
def test_extra_coverages_summary(name, expected):
    _, before, _ = _build()
    assert _cov(before, name)["summary"] == expected
    assert _cov(before, name)["group12"] == GROUP_ETC
    assert _cov(before, name)["agg"] == "sum"


def test_extra_not_pollute_base_rows():
    _, before, _ = _build()
    etc_names = {c["kb_name"] for c in before["coverages"] if c["group12"] == GROUP_ETC}
    assert "상해사망" not in etc_names
    assert "일반암" not in etc_names


def test_detail_premium_maps_to_contract_idx():
    _, before, _ = _build()
    by_company = _cov(before, "상급/종합병원 일당")["by_company"]
    assert by_company == {"5": 120 * MAN}


def test_kp_same_and_diff_remarks():
    raw, before, _ = _build()
    assert raw["notes"][2]["kp_differs"] is False
    assert raw["notes"][4]["kp_differs"] is True
    c2 = next(c for c in before["companies"] if c["idx"] == 2)
    c4 = next(c for c in before["companies"] if c["idx"] == 4)
    assert c2["remark"] == "계피동일"
    assert c4["remark"].startswith("계피상이")


def test_final_includes_etc_rollup():
    _, _, final = _build()
    groups = {r["group12"] for r in final["rollup_by_group12"]}
    assert GROUP_ETC in groups
    etc = [c for c in final["coverages"] if c["group12"] == GROUP_ETC]
    assert etc and all(c["recommended"] is None for c in etc)
