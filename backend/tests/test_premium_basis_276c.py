# -*- coding: utf-8 -*-
"""BOHUMFIT-276c — 가입제안서 월납 기준 확정(보장보험료 합계 · 원 단위 절삭).

★Human 확정(2026-08-08): 월납은 `보장보험료 합계`를 읽고 **원 단위 절삭**(버림)한다.
  276b가 항목을 `1회차보험료(할인후)` → `보장보험료 합계`로 교정했고(105,802),
  여기에 절삭을 적용해 **105,800**이 된다.
  ★값은 276b 이전(105,800)과 같아지지만 **경로가 다르다** — 잘못된 항목 → 맞는 항목 + 절삭.
"""
from __future__ import annotations

import pytest

from coverage.proposal_parser import (
    PREMIUM_TRUNCATE_UNIT,
    _extract_premium,
    parse_proposal_text,
    truncate_premium,
)

DOC = """
(무) 메리츠 The좋은 알파Plus보장보험2607(2.0)
계약사항 : 20년납 20년만기 | 월납
보장보험료 합계 105,802 원
1회차보험료(할인후) 105,800 원
기본계약 1 갱신형 일반상해사망[기본계약] 1백만원 16
"""


@pytest.mark.parametrize(
    "raw,expected",
    [(105_802, 105_800), (105_800, 105_800), (105_809, 105_800), (99, 90), (5, 0), (0, 0), (None, None)],
)
def test_truncate_is_floor_not_round(raw, expected):
    """★반올림이 아니라 **버림**이다(105,809 → 105,800)."""
    assert truncate_premium(raw) == expected
    assert PREMIUM_TRUNCATE_UNIT == 10


def test_premium_uses_total_then_truncates():
    """★항목은 `보장보험료 합계`(276b), 절삭은 원 단위(276c)."""
    assert _extract_premium(DOC, None) == 105_800
    assert parse_proposal_text(DOC, "p.pdf")["monthly_premium"] == 105_800


def test_truncation_happens_once():
    """★절삭은 한 지점에서만 — 멱등이라 이중 적용돼도 값이 더 깎이지 않는다."""
    once = truncate_premium(105_802)
    assert truncate_premium(once) == once
    # 소스 계약: 절삭 호출은 `_extract_premium` 한 곳뿐이다.
    import pathlib

    src = (pathlib.Path(__file__).resolve().parents[1] / "coverage" / "proposal_parser.py").read_text(
        encoding="utf-8"
    )
    assert src.count("truncate_premium(") == 2  # 정의 1 + 호출 1


def test_totals_use_truncated_values():
    """합계는 **이미 절삭된** 값을 더한다(합계 단계에서 다시 깎지 않는다)."""
    from coverage.proposal_parser import parse_proposal_texts

    result = parse_proposal_texts([("a.pdf", DOC), ("b.pdf", DOC)])
    assert result["premium"]["monthly_total"] == 105_800 * 2


# ── ★기준 일관성 — 기존 계약(KB)과 다르다는 사실을 고정한다 ────────────────
def test_existing_contract_premium_is_not_truncated():
    """★KB 보장분석(기존 계약) 월납은 `parse_won`이 **절삭하지 않는다**(원문 그대로).

    즉 [후] 합계는 **절삭된 제안서 월납 + 절삭 안 된 기존 계약 월납**이 섞인다.
    ★이 사실을 임의로 통일하지 않고 **기록만** 한다(Human 결정 사안 — 276c 태스크 문서 참조).
    """
    from coverage.amount import parse_won

    assert parse_won("681,312") == 681_312   # 정본 이*숙 월납 — 끝자리 2가 살아 있다
    assert parse_won("4,675,189") == 4_675_189
    import pathlib

    src = (pathlib.Path(__file__).resolve().parents[1] / "coverage" / "amount.py").read_text(encoding="utf-8")
    assert "truncate" not in src.lower()


def test_276a_276b_results_unchanged():
    """276a 폴백 제거·276b 파싱 교정이 그대로다."""
    result = parse_proposal_text(DOC, "p.pdf")
    amounts = {c["kb_name"]: c["amount"] for c in result["coverages"]}
    assert amounts["상해사망"] == 1_000_000                     # 276b T1
    assert "2607(2.0)" in result["product"]                     # 276b T3
    assert all("registry" not in str(c.get("source")) for c in result["coverages"])  # 276a
