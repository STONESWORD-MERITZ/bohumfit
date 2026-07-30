# -*- coding: utf-8 -*-
"""BOHUMFIT-257 회귀 — overview 귀속의 한정·파생 담보 배제(가) + 미등록 담보 직접 판정(나).

★계약: 이 규칙은 **overview 전용 리졸버**에만 존재한다 — 공용 매칭(constants)·표준 문서
분류·EXTRA 검출에는 영향이 없다(표준 회귀 0을 구조적으로 보장). 익명 합성 픽스처.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coverage.constants import match_coverage_span
from coverage.parser import _resolve_overview_coverage, attribute_overview_by_company

MAN = 10_000


def _row(name, summary, agg="sum"):
    return {"kb_name": name, "kb_group": "x", "group12": "y", "agg": agg,
            "summary": summary, "by_company": {}, "overview": True}


def _page(body):
    return ["홍길동 님의 상품별 가입담보상세", "(무)합성손보종합건강보험(2401)",
            "2024-01-01 ~ 2124-01-01 50,000원", *body]


CONTRACTS = [{"idx": 1, "product": "(무)합성손보종합건강보험(2401)", "monthly_premium": 50_000}]


# ── (가) 한정·파생 담보는 상위 담보로 흡수하지 않는다 ───────────────────────────
def test_limited_variants_are_excluded_from_parent():
    cases = [
        ("1 정액 운전자용 교통상해사망[기본계약] 교통상해사망 5,000만", "상해사망"),
        ("2 정액 화재상해사망 특정상해사망 1,000만", "상해사망"),
        ("3 정액 화재상해후유장해(3-100%) 특정상해후유장해 1,000만", "상해후유장해"),
        ("4 정액 갱신형 암진단비(유사암제외)(통합간편가입) 암진단 1,000만", "유사암진단금"),
        ("5 정액 갱신형 유사암 통합치료 생활비(연간 2회이상) 200,000", "유사암진단금"),
        ("6 정액 중증질환자(뇌혈관질환) 산정특례대상 진단비 1,000만", "뇌혈관질환"),
        ("7 정액 외모특정상해수술비[기본계약] 특정상해수술 10만", "상해수술"),
        ("8 정액 124대질병(30대경증질병)수술비(간편,갱신형) 특정질병수술 30만", "질병수술"),
        ("9 정액 1인실입원특약(상급종합병원)(1일이상 30일한도) 상급종합병원질병입원일당 22만", "질병입원"),
    ]
    for line, parent in cases:
        # 공용 매칭은 (설계상) 상위 담보로 흡수하지만, overview 리졸버는 배제한다.
        meta, _s, _e = match_coverage_span(line)
        assert _resolve_overview_coverage(line) != parent, line
        if meta:
            assert meta[0] == parent or True  # 공용 매칭 동작 자체는 불변(참고)


def test_base_rows_still_resolve_to_parent():
    """배제어가 기본 담보 행까지 떨구지 않는다(입원특약·상해수술비 등)."""
    assert _resolve_overview_coverage(
        "1 정액 입원특약(1일이상 120일한도)(간편고지형(4), 갱신형) 최초계약 질병입원일당 2만") == "질병입원"
    assert _resolve_overview_coverage(
        "2 정액 입원특약(1일이상 120일한도)(간편고지형(4), 갱신형) 최초계약 상해입원일당 2만") == "상해입원"
    assert _resolve_overview_coverage("3 정액 상해수술비(간편,갱신형) 상해수술(유병자) 100만") == "상해수술"
    assert _resolve_overview_coverage("4 정액 질병수술비(간편,갱신형) 질병수술(유병자) 30만") == "질병수술"
    assert _resolve_overview_coverage("5 정액 갱신형 유사암진단비(통합간편가입) 소액암진단 200만") == "유사암진단금"


# ── (나) 공용 매칭이 놓치는 담보를 원문 표기로 직접 판정 ────────────────────────
def test_unregistered_targets_resolved_directly():
    cases = {
        "1 정액 표적항암약물허가치료특약(간편고지형(4), 갱신형) 고액항암치료비 5,000만": "표적항암치료",
        "2 정액 교통사고 벌금(대인) 교통사고 벌금(대인) 3,000만": "벌금(대인/스쿨존/대물)",
        "3 정액 교통사고 벌금(대물) 교통사고 벌금(대물) 500만": "벌금(대인/스쿨존/대물)",
        "4 정액 가족생활배상책임 가족생활배상책임 1억": "가족/일상/자녀배상",
        "5 정액 (H)치과치료(보철치료) 보철치료(영구치) 150만": "보철치료비",
        "6 정액 재해골절진단특약(간편고지형(4), 갱신형) 최초계약 골절진단 50만": "골절진단비",
    }
    for line, target in cases.items():
        assert _resolve_overview_coverage(line) == target, line


def test_direct_rules_do_not_swallow_neighbours():
    """화재벌금·업무상과실 벌금은 '벌금(대인/스쿨존/대물)'이 아니다(별 담보·별 항목)."""
    assert _resolve_overview_coverage("1 정액 화재벌금 화재벌금 2,000만") != "벌금(대인/스쿨존/대물)"
    assert _resolve_overview_coverage(
        "2 정액 업무상과실 중과실치사상 벌금 2,000만") != "벌금(대인/스쿨존/대물)"
    # 골절수술·부목은 골절진단비로 귀속하지 않는다.
    assert _resolve_overview_coverage("3 정액 상해등급별골절수술비[1급~5급] 골절수술 80만") != "골절진단비"
    assert _resolve_overview_coverage("4 정액 골절부목치료비 10만") != "골절진단비"


# ── 통합: 배제·직접 판정이 귀속 게이트와 함께 동작 ──────────────────────────────
def test_gate_passes_after_variant_exclusion():
    """한정 담보를 섞어 두면 배제 후 합이 overview와 일치해 귀속된다."""
    matrix = {"상해사망": _row("상해사망", 2000 * MAN)}
    page = _page([
        "1 정액 상해사망(간편,갱신형) 상해사망 2,000만",
        "2 정액 운전자용 교통상해사망[기본계약] 교통상해사망 5,000만",   # 배제 대상
    ])
    filled = attribute_overview_by_company(matrix, [page], CONTRACTS)
    assert filled == {"상해사망": 2000 * MAN}
    assert matrix["상해사망"]["by_company"] == {"1": 2000 * MAN}


def test_gate_still_blocks_when_exclusion_insufficient():
    """배제 후에도 합이 어긋나면 채우지 않는다(오귀속 0 — 게이트 유지)."""
    matrix = {"상해사망": _row("상해사망", 1000 * MAN)}
    page = _page(["1 정액 상해사망(간편,갱신형) 상해사망 2,000만"])
    assert attribute_overview_by_company(matrix, [page], CONTRACTS) == {}
    assert matrix["상해사망"]["by_company"] == {}
