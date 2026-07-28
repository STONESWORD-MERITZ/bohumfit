# -*- coding: utf-8 -*-
"""BOHUMFIT-253 회귀 — by_company 귀속 복원(합계-회사별 불일치 해소).

배경(Codex 252 반려): layout=True 추출이 표 행을 줄바꿈해 월보험료가 기간 라인이 아닌
아래 줄에 놓이는 detail 페이지에서 `_detail_contract_idx`가 None → EXTRA 담보가 '?'
키로 귀속돼 실계약 회사합 ≠ 합계(A 항암약물방사선 등 실측). 익명 합성 픽스처.

원칙: ①헤더 16줄 폴백은 ★유일 계약 매칭일 때만 귀속 ②모호(복수/0 매칭)는 '?' 유지
(오귀속 금지 — 251 원칙) ③'?' 버킷 포함 회사합 = 합계(대사) ④'?'는 [후] 이월 보존(246).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coverage.aggregator import build_before, build_final
from coverage.compare import build_after_analysis
from coverage.parser import parse_detail_pages

MAN = 10_000

CONTRACTS = [
    {"idx": 1, "monthly_premium": 50_000},
    {"idx": 2, "monthly_premium": 33_300},
]


def _page(head_lines: list[str], body: str) -> list[str]:
    return ["홍길동 님의 상품별 가입담보상세", *head_lines, *body.splitlines()]


def test_fallback_attributes_when_premium_below_period_line():
    """★결함 재현: 기간 라인에 보험료 없음 + 2줄 아래 보험료 — 폴백으로 계약 귀속."""
    page = _page(
        ["가나손보 | 가입일자 : 2024-01-01 |", "합성보험",
         "2024-01-01 ~ 2124-01-01",          # 기간 라인(보험료 없음 — 랩된 표 행)
         "홍길동/홍길동 월납/20년/100세만기",
         "50,000원"],                          # 보험료가 별도 줄(실측 레이아웃)
        "2 정액 항암약물방사선치료비 항암치료 200만\n",
    )
    _notes, extra = parse_detail_pages([page], CONTRACTS)
    assert extra["항암약물방사선"]["by_company"] == {"1": 200 * MAN}  # '?' 아님


def test_ambiguous_multiple_premium_matches_stay_unknown():
    """★오귀속 금지: 헤더에 두 계약의 보험료가 모두 등장(모호) — '?' 유지."""
    page = _page(
        ["가나손보 | 가입일자 : 2024-01-01 |", "합성보험",
         "2024-01-01 ~ 2124-01-01",
         "50,000원 갱신 후 33,300원"],         # 두 계약 보험료 동시 등장 — 유일 결정 불가
        "2 정액 항암약물방사선치료비 항암치료 200만\n",
    )
    _notes, extra = parse_detail_pages([page], CONTRACTS)
    assert extra["항암약물방사선"]["by_company"] == {"?": 200 * MAN}


def test_no_premium_evidence_stays_unknown():
    """원천 부재(보험료·기간 어디에도 없음) — '?' 유지(계약 미확인 명시)."""
    page = _page(
        ["가나손보", "합성보험"],
        "2 정액 화상치료비 화상 110만\n",
    )
    _notes, extra = parse_detail_pages([page], CONTRACTS)
    assert extra["화상"]["by_company"] == {"?": 110 * MAN}


# ── 253 회송 보정(Codex 반려 재현 — 동일 보험료 계약 축약 오귀속) ────────────────
CONTRACTS_DUP = [
    {"idx": 1, "monthly_premium": 50_000},
    {"idx": 2, "monthly_premium": 50_000},   # ★동일 보험료 — dict last-wins가 계약1을 덮던 결함
]
CONTRACTS_TRIPLE = CONTRACTS_DUP + [{"idx": 3, "monthly_premium": 50_000}]

_BODY = "2 정액 항암약물방사선치료비 항암치료 200만\n"


def _fallback_page() -> list[str]:
    """헤더 폴백 경로 — 기간 라인에 보험료 없음, 별도 줄에 50,000원 하나."""
    return _page(
        ["가나손보 | 가입일자 : 2024-01-01 |", "합성보험",
         "2024-01-01 ~ 2124-01-01",
         "홍길동/홍길동 월납/20년/100세만기",
         "50,000원"],
        _BODY,
    )


def _period_line_page() -> list[str]:
    """기간 라인 경로 — 기간 라인 위에 보험료 50,000원."""
    return _page(
        ["가나손보 | 가입일자 : 2024-01-01 |", "합성보험",
         "홍길동/홍길동 월납/20년/100세만기",
         "2024-01-01 ~ 2124-01-01 50,000원"],
        _BODY,
    )


def test_same_premium_two_contracts_stay_unknown_fallback():
    """★반려 재현(헤더 폴백): 동일 보험료 2계약 — 특정 불가 → '?'(계약2 오귀속 0)."""
    _notes, extra = parse_detail_pages([_fallback_page()], CONTRACTS_DUP)
    assert extra["항암약물방사선"]["by_company"] == {"?": 200 * MAN}


def test_same_premium_two_contracts_stay_unknown_period_line():
    """★반려 재현(기간 라인 경로): 동일 보험료 2계약 — 양 경로 동일 유일성 판정."""
    _notes, extra = parse_detail_pages([_period_line_page()], CONTRACTS_DUP)
    assert extra["항암약물방사선"]["by_company"] == {"?": 200 * MAN}


def test_same_premium_three_contracts_stay_unknown_both_paths():
    """동일 보험료 3계약 이상 — 양 경로 모두 '?' 유지."""
    for page in (_fallback_page(), _period_line_page()):
        _notes, extra = parse_detail_pages([page], CONTRACTS_TRIPLE)
        assert extra["항암약물방사선"]["by_company"] == {"?": 200 * MAN}


def test_unique_premium_attributes_both_paths():
    """서로 다른 보험료 유일 매칭 — 양 경로 모두 귀속(기존 통과 유지)."""
    for page in (_fallback_page(), _period_line_page()):
        _notes, extra = parse_detail_pages([page], CONTRACTS)
        assert extra["항암약물방사선"]["by_company"] == {"1": 200 * MAN}


def test_period_line_two_different_matching_premiums_stay_unknown():
    """기간 라인에 두 계약의 상이 보험료가 동시 등장(구 last-match 승자 지점) — 모호 → '?'."""
    page = _page(
        ["가나손보 | 가입일자 : 2024-01-01 |", "합성보험",
         "2024-01-01 ~ 2124-01-01 50,000원 갱신 후 33,300원"],
        _BODY,
    )
    _notes, extra = parse_detail_pages([page], CONTRACTS)
    assert extra["항암약물방사선"]["by_company"] == {"?": 200 * MAN}


def _analysis_with_unknown() -> dict:
    """'?' 버킷이 남는 합성 케이스 — 대사·이월 검증용."""
    raw = {
        "customer": {"name": "홍길동", "age": 50, "sex": "남자"},
        "contracts": [{
            "idx": 1, "insurer": "가나손보", "product": "합성", "contract_date": "2024-01-01",
            "pay_cycle": "월납", "pay_years": 20, "pay_months": 240, "maturity": "100세",
            "monthly_premium": 50_000,
        }],
        "matrix": {"질병사망": {"by_company": {"1": 5000 * MAN}}},
        "diagnosis": {}, "notes": {},
        "extra": {"화상": {"agg": "sum", "by_company": {"?": 110 * MAN}}},
        "warnings": [],
    }
    before = build_before(raw, today="2026-07-27")
    return {"before": before, "final": {"premium": before["premium"], "coverages": [], "rollup_by_group12": []}}


def test_unknown_bucket_sum_reconciles_and_carries_to_after():
    """'?' 포함 회사합=합계 대사 성립 + [후] 이월 보존(246 계약 미상 키 이월 규칙)."""
    analysis = _analysis_with_unknown()
    ids = {"1"}
    for row in analysis["before"]["coverages"]:
        if not row.get("enrolled") or row.get("summary") is None:
            continue
        vals = [v for v in (row.get("by_company") or {}).values() if isinstance(v, (int, float))]
        total = max(vals) if row.get("agg") == "max" else sum(vals)
        assert total == row["summary"], row["kb_name"]  # ★'?' 버킷 포함 대사 0

    result = build_after_analysis(analysis, {"existing": [], "proposals": []})
    after_rows = {c["kb_name"]: c for c in result["after"]["before"]["coverages"]}
    fire = after_rows["화상"]
    assert fire.get("by_company", {}).get("?") == 110 * MAN  # 이월 보존
    assert fire.get("summary") == 110 * MAN                  # 합계 불변
