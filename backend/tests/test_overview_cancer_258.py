# -*- coding: utf-8 -*-
"""BOHUMFIT-258 회귀 — overview 암 진단 계열 A안 분류(Human 결정).

A안: 일반암 → `암진단금` / 유사암(제자리암·상피내암·갑상샘암·소액암) → `유사암진단금` /
재진단암·특정암(경계성종양·기타피부암·대장점막내암)·치료비 계열은 ★상위 담보에 흡수 금지.
★"(…제외)" 괄호는 보장 한정 문구이므로 판정 전에 제거한다(실측: `암진단(기타피부암,
갑상선암및대장점막내암제외)`는 일반암 행). 익명 합성 픽스처.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coverage.parser import _cancer_core, _resolve_overview_coverage, attribute_overview_by_company

MAN = 10_000
CONTRACTS = [{"idx": 1, "product": "(무)합성손보종합건강보험(2401)", "monthly_premium": 50_000}]


def _row(name, summary, agg="sum"):
    return {"kb_name": name, "kb_group": "암 진단", "group12": "암", "agg": agg,
            "summary": summary, "by_company": {}, "overview": True}


def _page(body):
    return ["홍길동 님의 상품별 가입담보상세", "(무)합성손보종합건강보험(2401)",
            "2024-01-01 ~ 2124-01-01 50,000원", *body]


def test_exclusion_paren_is_stripped_before_judgement():
    """★'…제외' 괄호 제거 — 한정 문구를 담보 종류로 오인하지 않는다."""
    assert _cancer_core("암진단(기타피부암,갑상선암및대장점막내암제외)암진단(유병자)") == "암진단암진단(유병자)"
    assert _cancer_core("갱신형암진단비(유사암제외)(통합간편가입)") == "갱신형암진단비(통합간편가입)"


def test_general_cancer_rows_resolve_to_암진단금():
    cases = (
        "1 정액 간편심사[355(6대)] 암진단(기타피부암,갑상선암및대장점막내암제외) 암진단(유병자) 5,000만",
        "5 정액 갱신형 암진단비(유사암제외)(통합간편가입) 암진단(유병자) 1,000만",
        "2 정액 암(유사암제외)진단특약(간편고지형(4), 갱신형) 최초계약 암진단(유병자) 5,000만",
        # ★상품명에 '생활비'가 들어간 일반암 행도 귀속된다(실측 누락 원인이었던 케이스).
        "3 정액 더블보장보험료생활비환급특약P(무배당,저해약환급금형)[간편고지형]_2형 암진단(유병자) 900만",
    )
    for line in cases:
        assert _resolve_overview_coverage(line) == "암진단금", line


def test_non_general_cancer_rows_not_absorbed():
    """재진단암·특정암·치료비·유사암 계열은 `암진단금`으로 귀속하지 않는다."""
    for line in (
        "6 정액 간편심사[355(6대)] 신재진단암진단(4회한) 기타 인보험(정액)담보 5,000만",
        "2 정액 간편심사[355(6대)] 경계성종양진단 특정암진단 1,000만",
        "3 정액 간편심사[355(6대)] 기타피부암진단 특정암진단 1,000만",
        "4 정액 간편심사[355(6대)] 대장점막내암 특정암진단 1,000만",
        "5 정액 간편심사[355(6대)] 제자리암(상피내암)진단 특정암진단 1,000만",
        "7 정액 갱신형 26종 항암방사선및약물치료비(전이포함)(유사암제외) 1,000만",
        "8 정액 갱신형 암(유사암제외) 통합치료 생활비(연간 2회이상) 100만",
    ):
        assert _resolve_overview_coverage(line) != "암진단금", line


def test_유사암_rows_still_resolve_to_유사암진단금():
    """A안 ②: 유사암 계열은 계속 `유사암진단금`으로 귀속(공용 매칭 경로 유지)."""
    assert _resolve_overview_coverage(
        "5 정액 갱신형 유사암진단비(통합간편가입) 소액암진단(유사암진단) 200만") == "유사암진단금"
    assert _resolve_overview_coverage(
        "6 정액 간편심사[355(6대)] 갑상샘암진단 소액암진단(유사암진단) 1,000만") == "유사암진단금"


def test_gate_reconciles_general_cancer_only():
    """일반암만 합산해 overview 금액과 일치 → 귀속. 세부 담보 혼재에도 게이트 성립."""
    matrix = {"암진단금": _row("암진단금", 6000 * MAN),
              "유사암진단금": _row("유사암진단금", 200 * MAN)}
    page = _page([
        "1 정액 간편심사[355(6대)] 암진단(기타피부암,갑상선암및대장점막내암제외) 암진단(유병자) 5,000만",
        "3 정액 더블보장보험료생활비환급특약P[간편고지형]_2형 암진단(유병자) 1,000만",
        "6 정액 간편심사[355(6대)] 신재진단암진단(4회한) 5,000만",      # 흡수 금지
        "2 정액 간편심사[355(6대)] 경계성종양진단 특정암진단 1,000만",   # 흡수 금지
        "5 정액 갱신형 유사암진단비(통합간편가입) 소액암진단(유사암진단) 200만",
    ])
    filled = attribute_overview_by_company(matrix, [page], CONTRACTS)
    assert filled == {"암진단금": 6000 * MAN, "유사암진단금": 200 * MAN}
    assert matrix["암진단금"]["by_company"] == {"1": 6000 * MAN}
    assert matrix["유사암진단금"]["by_company"] == {"1": 200 * MAN}


def test_gate_blocks_when_general_sum_mismatches():
    """세부 담보를 섞어도 합이 어긋나면 채우지 않는다(오귀속 0)."""
    matrix = {"암진단금": _row("암진단금", 9999 * MAN)}
    page = _page(["1 정액 암진단(유사암제외) 암진단(유병자) 5,000만"])
    assert attribute_overview_by_company(matrix, [page], CONTRACTS) == {}
    assert matrix["암진단금"]["by_company"] == {}
