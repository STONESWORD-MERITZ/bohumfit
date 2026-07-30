# -*- coding: utf-8 -*-
"""BOHUMFIT-256 회귀 — overview(합계-only) 문서의 회사별 귀속 복원 + 상품명 폴백.

★계약: ①귀속 게이트(담보별 detail 합 == overview summary일 때만 채움) ②계약 특정은 유일할
때만(보험료 → 실패 시 상품명) ③summary·enrolled 불변 ④표준 문서 경로 무접촉.
익명 합성 픽스처(PII 0).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coverage.parser import (
    _detail_idx_with_product_fallback,
    _premium_index,
    _product_index,
    _resolve_overview_coverage,
    attribute_overview_by_company,
)

MAN = 10_000


def _contracts(premium_1=None, product_1="(무)합성손보실손의료비보장보험(19.01)"):
    return [
        {"idx": 1, "product": product_1, "monthly_premium": premium_1},
        {"idx": 2, "product": "(무)합성생명종합건강보험(2401)", "monthly_premium": 50_000},
    ]


def _page(header: list[str], body: list[str]) -> list[str]:
    return ["홍길동 님의 상품별 가입담보상세", *header, *body]


def _overview_matrix(**rows):
    """rows: kb_name=(summary, agg)"""
    return {
        name: {"kb_name": name, "kb_group": "실손", "group12": "가입특약(Y/N)",
               "agg": agg, "summary": summary, "by_company": {}, "overview": True}
        for name, (summary, agg) in rows.items()
    }


# ── 리졸버(overview 전용 — 실손 원문 표기) ──────────────────────────────────────
def test_resolver_maps_실손_원문_표기():
    assert _resolve_overview_coverage("1 실손 상해(일반상해,전체상해를 의미) 상해(일반상해)입원의료비 5,000만") == "상해입원의료비"
    assert _resolve_overview_coverage("4 실손 질병(전체질병을 의미) 질병(전체질병)입원의료비 5,000만") == "질병입원의료비"
    assert _resolve_overview_coverage("3 실손 상해(일반상해) 상해(일반상해)외래의료비 25만") == "상해통원의료비"
    assert _resolve_overview_coverage("2 실손 상해(일반상해) 상해(일반상해)처방조제료 5만") == "상해통원의료비"
    assert _resolve_overview_coverage("9 실손 비급여 MRI 검사 비급여 MRI 검사의료비(입원+통원) 300만") == "3대비급여실손"
    # 상해·질병이 동시에 등장하면 모호 → 귀속하지 않는다.
    assert _resolve_overview_coverage("1 실손 상해 및 질병 입원의료비 100만") is None


# ── 상품명 폴백(보험료 미제공 계약) ─────────────────────────────────────────────
def test_product_fallback_attributes_when_premium_missing():
    """★256 핵심: 보험료가 없어 253 역인덱스로 특정 불가한 계약 — 상품명 유일 매칭으로 귀속."""
    contracts = _contracts(premium_1=None)
    page = _page(["(무)합성손보실손의료비보장보험(19.01)"], ["1 실손 상해(일반상해)입원의료비 5,000만"])
    idx = _detail_idx_with_product_fallback(page, _premium_index(contracts), _product_index(contracts))
    assert idx == 1


def test_product_fallback_stays_unknown_when_multiple_match():
    """★오귀속 금지: 동일 상품명 계약 2건 → 유일하지 않으므로 미귀속(None)."""
    contracts = [
        {"idx": 1, "product": "(무)합성손보실손의료비보장보험(19.01)", "monthly_premium": None},
        {"idx": 2, "product": "(무)합성손보실손의료비보장보험(19.01)", "monthly_premium": None},
    ]
    page = _page(["(무)합성손보실손의료비보장보험(19.01)"], ["1 실손 상해(일반상해)입원의료비 5,000만"])
    assert _detail_idx_with_product_fallback(page, _premium_index(contracts), _product_index(contracts)) is None


def test_premium_path_takes_priority_over_product():
    """보험료 경로가 성립하면 그 결과를 쓴다(253 우선순위 유지)."""
    contracts = _contracts(premium_1=None)
    page = _page(
        ["(무)합성손보실손의료비보장보험(19.01)", "2024-01-01 ~ 2124-01-01 50,000원"],
        ["1 실손 상해(일반상해)입원의료비 5,000만"],
    )
    # 헤더 보험료 50,000원 = 계약2 → 상품명(계약1)보다 보험료 경로가 우선.
    assert _detail_idx_with_product_fallback(page, _premium_index(contracts), _product_index(contracts)) == 2


def test_short_product_name_not_indexed():
    """짧은 상품명은 오매칭 위험이 커 인덱스에서 제외한다."""
    assert _product_index([{"idx": 1, "product": "건강", "monthly_premium": None}]) == {}


# ── 귀속 게이트 ────────────────────────────────────────────────────────────────
def test_gate_fills_only_when_detail_sum_matches_summary():
    """★게이트: 합이 정확히 일치하는 담보만 채우고, 불일치 담보는 미충전 유지."""
    contracts = _contracts(premium_1=None)
    matrix = _overview_matrix(
        상해입원의료비=(5000 * MAN, "rep"),
        질병입원의료비=(9999 * MAN, "rep"),   # detail과 불일치 → 미충전
    )
    page = _page(
        ["(무)합성손보실손의료비보장보험(19.01)"],
        ["1 실손 상해(일반상해)입원의료비 5,000만", "4 실손 질병(전체질병)입원의료비 5,000만"],
    )
    filled = attribute_overview_by_company(matrix, [page], contracts)
    assert filled == {"상해입원의료비": 5000 * MAN}
    assert matrix["상해입원의료비"]["by_company"] == {"1": 5000 * MAN}
    assert matrix["질병입원의료비"]["by_company"] == {}     # ★불일치 → 비움 유지
    # summary·overview 플래그 불변.
    assert matrix["상해입원의료비"]["summary"] == 5000 * MAN
    assert matrix["질병입원의료비"]["summary"] == 9999 * MAN
    assert all(row["overview"] for row in matrix.values())


def test_components_sum_within_contract_for_통원():
    """통원의료비 = 외래 + 처방조제(계약 내부 구성 항목 합) — 실측 25만+5만=30만."""
    contracts = _contracts(premium_1=None)
    matrix = _overview_matrix(상해통원의료비=(300_000, "rep"))
    page = _page(
        ["(무)합성손보실손의료비보장보험(19.01)"],
        ["3 실손 상해(일반상해)외래의료비 25만", "2 실손 상해(일반상해)처방조제료 5만"],
    )
    filled = attribute_overview_by_company(matrix, [page], contracts)
    assert filled == {"상해통원의료비": 300_000}
    assert matrix["상해통원의료비"]["by_company"] == {"1": 300_000}


def test_ambiguous_contract_page_is_not_attributed():
    """계약 특정 실패 페이지의 담보는 귀속하지 않는다(오귀속 0 — '?'로 남김)."""
    contracts = [
        {"idx": 1, "product": "(무)합성손보실손의료비보장보험(19.01)", "monthly_premium": None},
        {"idx": 2, "product": "(무)합성손보실손의료비보장보험(19.01)", "monthly_premium": None},
    ]
    matrix = _overview_matrix(상해입원의료비=(5000 * MAN, "rep"))
    page = _page(["(무)합성손보실손의료비보장보험(19.01)"], ["1 실손 상해(일반상해)입원의료비 5,000만"])
    assert attribute_overview_by_company(matrix, [page], contracts) == {}
    assert matrix["상해입원의료비"]["by_company"] == {}


def test_noop_without_detail_or_contracts():
    matrix = _overview_matrix(상해입원의료비=(5000 * MAN, "rep"))
    assert attribute_overview_by_company(matrix, [], _contracts()) == {}
    assert attribute_overview_by_company(matrix, [["x"]], []) == {}
    assert attribute_overview_by_company({}, [["x"]], _contracts()) == {}
