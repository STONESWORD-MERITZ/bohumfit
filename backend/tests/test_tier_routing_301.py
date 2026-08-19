# -*- coding: utf-8 -*-
"""BOHUMFIT-301 — [전] 종수술 tier 라우팅 · 이중 계상 정리 · 6종 이상 처분 회귀.

★고정하는 계약 (297 조사 → Human 확정 A·B·C·D)
  A. 종별 접두(질병/상해) + 종수 `(N종)`/`_N종`(N∈1~5) 개별행 → tier 질병/상해 열
     ([후] proposal_parser·286 B1과 동일 착지). 238 환산이 아니라 원문 값 그대로.
  B. 같은 (계약,종별)에 개별행이 있으면 요약행(기타인보험 정액담보)은 폐기(이중 계상).
     ★개별행이 없으면 요약행은 238 환산으로 살린다(요약행만 있는 문서 보존).
  C. 6종 이상(N≥6)은 1~5종 표에 넣지 않는다 — ignored 목록 + 경고.
  D. 위 결과로 bare "종수술비"는 비게 되어 비고에서 사라진다(종별 접두 없는 명시 tier는 예외적 bare 보존).
  ★291: 종별 접두가 없는 값은 질병/상해로 추측하지 않는다(미상 유지).

★PII: 익명 합성 픽스처만(실 PDF·실명 0).
★뮤테이션: 라우팅 제거 / 요약행 폐기 제거 / 종별 추측 삽입 각각을 심으면 아래 테스트가 실패한다.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coverage.aggregator import build_before  # noqa: E402
from coverage.constants import AGG_SUM  # noqa: E402
from coverage.jong_surgery import MAN, estimated_tier_label  # noqa: E402
from coverage.parser import (  # noqa: E402
    _jong_kind,
    _jong_tier_n,
    parse_detail_pages,
    route_jong_surgery,
)

CONTRACTS = [{"idx": 1, "monthly_premium": 50_000}]


def _rec(name, amount, key="1"):
    return (key, AGG_SUM, amount, name)


def _detail(lines_body: str):
    head = (
        "홍길동 님의 상품별 가입담보상세\n가나손보 | 가입일자 : 2024-01-01 |\n합성보험\n"
        "홍길동/홍길동 월납/20년/100세만기\n2024-01-01~2124-01-01 50,000원\n"
    )
    return (head + lines_body).splitlines()


# ── 종별·종수 추출 ───────────────────────────────────────────────────────────
def test_kind_extraction():
    assert _jong_kind("질병1-5종수술비Ⅳ(1종)") == "질병"
    assert _jong_kind("상해1-5종수술비Ⅲ(3종)") == "상해"
    assert _jong_kind("1~5종수술(5종수술)") is None  # 종별 접두 없음 → 미상(291)


def test_tier_n_extraction_both_forms():
    assert _jong_tier_n("상해1-5종수술비Ⅲ(3종)(간편)") == 3        # 괄호형
    assert _jong_tier_n("질병1~5종수술비Ⅱ(매회)_2종") == 2          # 밑줄형
    assert _jong_tier_n("질병1-8종수술비Ⅲ(8종)(간편)") == 8         # 6종 이상도 추출
    assert _jong_tier_n("질병1-5종수술(5종수술)") is None           # 기준 표기는 마커 아님
    assert _jong_tier_n("상해1-5종수술비Ⅲ(간편)기타인보험(정액)담보") is None  # 요약행


# ── A. 개별행 → tier 질병/상해 열 ────────────────────────────────────────────
def test_individual_routes_to_tier_columns():
    """★뮤테이션 ①(라우팅 제거→bare): 이 단언이 실패한다."""
    entries, ignored, suppressed = route_jong_surgery([
        _rec("질병1-5종수술비Ⅳ(1종)(간편)", 200_000),
        _rec("상해1-5종수술비Ⅲ(1종)(간편)", 500_000),
        _rec("질병1-5종수술비Ⅳ(3종)(간편)", 1_000_000),
    ])
    assert entries["N종수술비(질병 1종)"]["by_company"] == {"1": 200_000}
    assert entries["N종수술비(상해 1종)"]["by_company"] == {"1": 500_000}
    assert entries["N종수술비(질병 3종)"]["by_company"] == {"1": 1_000_000}
    assert "종수술비" not in entries  # bare로 새지 않는다
    assert ignored == [] and suppressed == []


def test_individual_lands_on_dual_columns_via_build_before():
    """A: build_before까지 태워 tier 질병/상해 열에 실리는지(착지 검증)."""
    page = _detail(
        "16 정액 질병1-5종수술비Ⅳ(간편)(갱신형)(4종) 질병종수술 1000만\n"
        "17 정액 상해1-5종수술비Ⅲ(간편)(갱신형)(4종) 상해종수술 500만\n"
    )
    _notes, extra = parse_detail_pages([page], CONTRACTS)
    raw = {
        "customer": {"name": "홍길동", "age": 40, "sex": "남자"},
        "contracts": [{"idx": 1, "insurer": "가나손보", "product": "합성", "contract_date": "2024-01-01",
                       "pay_cycle": "월납", "pay_years": 20, "pay_months": 240, "maturity": "100세",
                       "monthly_premium": 50_000}],
        "matrix": {}, "diagnosis": {}, "notes": {}, "extra": extra, "warnings": [],
    }
    before = build_before(raw, today="2026-07-21")
    row4 = next(c for c in before["coverages"] if c.get("row_id") == "tier_surgery_4")
    cols = row4["columns"]
    assert cols["disease"]["summary"] == 1000 * MAN
    assert cols["injury"]["summary"] == 500 * MAN
    assert (cols.get("unspecified") or {}).get("summary") in (None, 0)


# ── 종별 접두 없음 → bare 보존(추측 금지) ────────────────────────────────────
def test_no_kind_stays_bare_not_guessed():
    """★뮤테이션 ③(종별 추측 삽입): 종별 없는 명시 tier를 질병/상해로 넣으면 실패한다."""
    entries, _ig, _sp = route_jong_surgery([_rec("1~5종수술비(2종)(무종별)", 300_000)])
    assert entries["종수술비"]["by_company"] == {"1": 300_000}
    assert not any(lbl.startswith("N종수술비(") for lbl in entries)


# ── B. 이중 계상 정리 ────────────────────────────────────────────────────────
def test_summary_suppressed_when_individual_present():
    """★뮤테이션 ②(요약행 폐기 제거): 요약행이 238 환산으로 살아나 미상 열이 생기면 실패한다."""
    entries, _ig, suppressed = route_jong_surgery([
        _rec("상해1-5종수술비Ⅲ(1종)(간편)", 500_000),
        _rec("상해1-5종수술비Ⅲ(5종)(간편)", 5_000_000),
        _rec("상해1-5종수술비Ⅲ(간편)기타인보험(정액)담보", 5_500_000),  # 요약행=개별합
    ])
    assert entries["N종수술비(상해 1종)"]["by_company"] == {"1": 500_000}
    assert entries["N종수술비(상해 5종)"]["by_company"] == {"1": 5_000_000}
    assert not any("표준환산" in lbl for lbl in entries)  # 요약행 238 환산 안 생김
    assert len(suppressed) == 1 and suppressed[0]["amount"] == 5_500_000


def test_summary_only_survives_as_conversion():
    """B 단서: 개별행이 없으면 요약행은 238 환산으로 살린다(요약행만 있는 문서)."""
    entries, _ig, suppressed = route_jong_surgery([
        _rec("상해1-5종수술비Ⅲ(간편)기타인보험(정액)담보", 5_000_000),
    ])
    assert suppressed == []
    assert entries[estimated_tier_label(5)]["by_company"] == {"1": 500 * MAN}
    assert entries[estimated_tier_label(1)].get("estimated") is True


def test_pure_five_base_line_still_converted():
    """순수 5종기준액(종별·종수 미상)은 종전대로 238 환산(미상 열)."""
    entries, _ig, _sp = route_jong_surgery([_rec("1~5종수술(5종수술)", 300 * MAN)])
    assert entries[estimated_tier_label(3)]["by_company"] == {"1": 50 * MAN}


# ── C. 6종 이상 무시 ─────────────────────────────────────────────────────────
def test_six_plus_ignored_with_warning():
    entries, ignored, _sp = route_jong_surgery([
        _rec("질병1-8종수술비Ⅲ(3종)(간편)", 500_000),   # 1~5종: 라우팅
        _rec("질병1-8종수술비Ⅲ(6종)(간편)", 1_000_000),  # 6종: 무시
        _rec("질병1-8종수술비Ⅲ(8종)(간편)", 1_000_000),  # 8종: 무시
    ])
    assert entries["N종수술비(질병 3종)"]["by_company"] == {"1": 500_000}
    assert sorted(r["n"] for r in ignored) == [6, 8]
    assert not any("6종" in lbl or "8종" in lbl for lbl in entries)


def test_six_plus_surfaces_document_warning():
    """C: 6종 이상 무시는 parse_document 경고로 추적 가능해야 한다(sink)."""
    page = _detail("16 정액 질병1-8종수술비Ⅲ(간편)(갱신형)(7종) 질병종수술 100만\n")
    sink = {}
    parse_detail_pages([page], CONTRACTS, sink=sink)
    assert [r["n"] for r in sink["jong_ignored"]] == [7]


# ── D. 값 보존 검산 ──────────────────────────────────────────────────────────
def test_value_conservation_individual_sum():
    """개별행 1~5종 합이 tier 합계로 정확히 보존된다(정본C류 · 손실 0)."""
    lines = [
        _rec("질병1-5종수술비Ⅱ(1종,)", 200_000),
        _rec("질병1-5종수술비Ⅱ(2종,)", 300_000),
        _rec("질병1-5종수술비Ⅱ(3종,)", 1_000_000),
        _rec("질병1-5종수술비Ⅱ(4종,)", 10_000_000),
        _rec("질병1-5종수술비Ⅱ(5종,)", 10_000_000),
    ]
    entries, _ig, _sp = route_jong_surgery(lines)
    tier_total = sum(e["by_company"]["1"] for lbl, e in entries.items() if lbl.startswith("N종수술비("))
    assert tier_total == 21_500_000  # bare 이전값과 정확히 일치
    assert "종수술비" not in entries  # bare 완전 소거(D)
