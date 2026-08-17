# -*- coding: utf-8 -*-
"""BOHUMFIT-295 — ★불변식: **제안서가 없으면 [후] == [전]**.

290 Q6 대조표는 [전]·[후]를 각각 검증했을 뿐 이 불변식을 검증하지 않았고, 그 틈으로 실사용 회귀가 났다
(화면 [후] 종합비교가 0, Y/N이 N, 암에 비고행 값이 유입 — 원인은 프런트 재산출 경로, 295 문서 §1-2).

이 파일은 **서버 계층의 불변식**을 고정한다. 서버가 깨지면 어떤 표시 계층 수정으로도 못 고친다.
  ① 종합 판정 17행 · ② Y/N 5항목 · ③ 담보 49행 + 비고 · ④ 월납 — 제안서 0·해지 0이면 전부 동일
  ⑤ ★비고행(49행 밖 담보)은 `stage_totals` 체인에 **절대 유입되지 않는다**(row_id 기반)
  ⑥ 제안서가 있으면 정상적으로 달라진다(불변식이 "항상 같다"로 오해되지 않도록 반대 방향도 고정)

★PII(BOHUMFIT-295b/R2): 실 PDF·실명·실파일명을 쓰지 않는다. 290 `_raw` 선례대로 **익명 합성** 입력을
  `build_before`→`build_after_analysis`에 태워 서버 코드 경로를 그대로 실행한다(재현·robustness 모두 향상 —
  gitignore 폴더 존재에 의존하지 않는다).
"""
from __future__ import annotations

import pytest

from coverage.aggregator import build_before, build_final, compute_stage_totals, compute_yn_flags
from coverage.compare import build_after_analysis
from coverage.constants import PAYOUT_CASCADE_V2

MAN = 10_000


def _raw(matrix=None, extra=None, contracts=1):
    """290 선례 — 익명 합성 원본(고객 '테스트' · 보험사 '손보N')."""
    return {
        "customer": {"name": "테스트", "age": 40, "sex": "여자"},
        "contracts": [
            {"idx": i, "insurer": f"손보{i}", "product": f"상품{i}", "contract_date": "2024-01-01",
             "pay_cycle": "월납", "pay_years": 20, "pay_months": 240, "maturity": "100세",
             "monthly_premium": 10_000 * i}
            for i in range(1, contracts + 1)
        ],
        "matrix": matrix or {}, "diagnosis": {}, "notes": {}, "extra": extra or {}, "warnings": [],
    }


def _analysis(matrix=None, extra=None, contracts=1):
    before = build_before(_raw(matrix, extra, contracts), today="2026-08-18")
    final = build_final(before, {})
    return {"before": before, "final": final, "warnings": []}


# ── 두 형태 — 표준형(계약별 매트릭스)과 overview형(239 합계-only, Human 보고 케이스) ──────────
def _standard():
    return _analysis(
        matrix={
            "뇌혈관질환": {"by_company": {"1": 4000 * MAN}, "agg": "sum"},
            "허혈성심장질환": {"by_company": {"1": 2000 * MAN}, "agg": "sum"},
            "상해입원의료비": {"by_company": {"1": 5000 * MAN}, "agg": "rep"},
            "상해통원의료비": {"by_company": {"1": 5000 * MAN}, "agg": "rep"},
        },
        # 292 Phase E 결합 담보 — 비고행이라 구 이름 그대로 남는다(회귀 때 암 체인 오염의 통로).
        extra={"항암약물방사선": {"agg": "sum", "by_company": {"1": 1410 * MAN}}},
    )


def _overview():
    return _analysis(
        matrix={
            "뇌혈관질환": {"summary": 4000 * MAN, "agg": "sum", "overview": True, "by_company": {"1": None}},
            "상해입원의료비": {"summary": 5000 * MAN, "agg": "rep", "overview": True, "by_company": {"1": None}},
            "상해통원의료비": {"summary": 5000 * MAN, "agg": "rep", "overview": True, "by_company": {"1": None}},
        },
        extra={"항암약물방사선": {"agg": "sum", "by_company": {"1": 1410 * MAN}}},
    )


FORMS = [("표준형", _standard), ("overview형", _overview)]


def _rows(payload):
    return {c.get("row_id") or ("비고:" + c["kb_name"]): c.get("summary") for c in payload["coverages"]}


def _yn(payload):
    return {f["item"]: f.get("value") for f in compute_yn_flags(payload["coverages"])}


@pytest.mark.parametrize("kind, make", FORMS)
def test_no_proposal_means_after_equals_before(kind, make):
    """★★핵심 불변식 — 제안서 0건·해지 0이면 [후]의 모든 표시 축이 [전]과 같다."""
    result = build_after_analysis(make(), {"existing": [], "proposals": []})
    before, after = result["before"], result["after"]["before"]

    assert compute_stage_totals(after["coverages"]) == compute_stage_totals(before["coverages"]), f"{kind} 종합 17행"
    assert _yn(after) == _yn(before), f"{kind} Y/N"
    assert _rows(after) == _rows(before), f"{kind} 담보 49행+비고"
    assert after["premium"]["monthly_total"] == before["premium"]["monthly_total"], f"{kind} 월납"
    # payload가 실제로 내려주는 파생값도 동일해야 한다(프런트가 이 값을 그대로 쓴다 — 배선 회귀는 295b R1이 별도 고정).
    assert after.get("stage_totals") == before.get("stage_totals"), f"{kind} stage_totals payload"
    assert after.get("yn_flags") == before.get("yn_flags"), f"{kind} yn_flags payload"


@pytest.mark.parametrize("kind, make", FORMS)
def test_appendix_rows_never_enter_the_cascade(kind, make):
    """⑤ ★비고행은 종합 체인에 유입되지 않는다 — 회귀 때 암에 들어온 값이 이 경로였다(프런트 미러).

    서버는 `row_id` 기반이라 구조적으로 불가능하다. 그 사실을 값으로 고정한다.
    """
    before = build_after_analysis(make(), {"existing": [], "proposals": []})["before"]
    stages = compute_stage_totals(before["coverages"])
    row_values = {c["row_id"]: (c.get("summary") or 0) for c in before["coverages"] if c.get("row_id")}
    for label, chain in zip(stages, PAYOUT_CASCADE_V2.values()):
        assert stages[label] == sum(row_values.get(rid, 0) for rid in chain), label


def test_cascade_never_contains_the_combined_anticancer_appendix_value():
    """★재현: 결합 담보 `항암약물방사선`(292 Phase E 보존분)이 비고행인데 암 체인에 들어가면 실패."""
    before = build_after_analysis(_standard(), {"existing": [], "proposals": []})["before"]
    combined = next((c for c in before["coverages"] if c["kb_name"] == "항암약물방사선"), None)
    assert combined is not None and combined.get("summary") == 1410 * MAN
    assert combined.get("row_id") is None                       # 비고행이 맞다
    stages = compute_stage_totals(before["coverages"])
    for label, value in stages.items():
        assert value != combined["summary"], f"{label}에 비고행 값이 그대로 들어갔다"


def test_proposals_do_change_the_after_side():
    """⑥ 반대 방향 — 제안서가 있으면 [후]는 정상적으로 달라진다(불변식이 '항상 같다'가 아님)."""
    proposal = {
        "proposal_id": "P1", "insurer": "신규손보", "product": "신규상품",
        "monthly_premium": 30_000, "pay_months": 240,
        "coverages": [{"kb_name": "암수술", "amount": 2000 * MAN, "group12": "암", "agg": "sum"}],
    }
    result = build_after_analysis(_standard(), {"existing": [], "proposals": [proposal]})
    before, after = result["before"], result["after"]["before"]
    sb, sa = compute_stage_totals(before["coverages"]), compute_stage_totals(after["coverages"])
    assert sb != sa                                             # 종합비교가 달라진다
    assert sb["암 수 술 (레보아이 포함)"] == 0 and sa["암 수 술 (레보아이 포함)"] == 2000 * MAN
    row = next(c for c in after["coverages"] if c.get("row_id") == "cancer_surgery")
    assert row["by_company"].get("P1") == 2000 * MAN            # 신규 제안 열에 실린다
