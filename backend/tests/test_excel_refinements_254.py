# -*- coding: utf-8 -*-
"""BOHUMFIT-254 회귀 → 291(S3) 49행 양식 이식.

254 개정 4건(구획선·보험료 상단·Y/N 회사별·가독) 중 **값 계약**은 그대로 지킨다:
  · Y/N은 담보 행에서 재파생(낡은 payload 무시) — 291에서는 별도 블록 없이 **행 안**(셀 메모)에 표시(Q5)
  · 회사별 월납·합계 월납 = payload 그대로(6행)
  · 계피관계·구분은 자리(메타 행)가 사라졌지만 **회사명 셀 메모**로 보존
  · 담보 금액 셀·회사합=합계 불변
★254 구획선(굵은 선) 규칙은 구 비분양식 전용이라 291 양식에서 폐기됐다(테스트도 삭제·기록).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coverage.aggregator import build_before, compute_yn_flags
from coverage.compare import build_after_analysis
from tests.excel_v2_layout import (
    COL_NAME,
    COL_SUM,
    ROW_COMPANY,
    ROW_PREMIUM,
    SHEET_AFTER,
    SHEET_BEFORE,
    company_cells,
    company_col,
    row_of,
    sum_cell,
    workbook,
)

MAN = 10_000


def _raw(with_yn: bool = True) -> dict:
    """계약 2개 — 계약1은 운전자 특약군, 계약2는 실손·자동차부상 보유(회사별 Y 표적)."""
    extra = {}
    if with_yn:
        extra = {
            "벌금(대인/스쿨존/대물)": {"agg": "sum", "by_company": {"1": 300 * MAN}},
            "교통사고처리지원금": {"agg": "sum", "by_company": {"1": 500 * MAN}},
            "자동차사고부상": {"agg": "sum", "by_company": {"2": 100 * MAN}},
            "상해입원의료비": {"agg": "rep", "by_company": {"2": 5000 * MAN}},
        }
    return {
        "customer": {"name": "홍길동", "age": 50, "sex": "남자"},
        "contracts": [
            {"idx": 1, "insurer": "합성손보1", "product": "합성상품1호", "contract_date": "2021-01-01",
             "pay_cycle": "월납", "pay_years": 20, "pay_months": 240, "maturity": "100세",
             "monthly_premium": 10_000, "remark": "계피상이(계약자 김*순·피보험자 홍길동)"},
            {"idx": 2, "insurer": "합성손보2", "product": "합성상품2호", "contract_date": "2022-01-01",
             "pay_cycle": "월납", "pay_years": 20, "pay_months": 240, "maturity": "100세",
             "monthly_premium": 20_000},
        ],
        "matrix": {
            "질병사망": {"by_company": {"1": 3000 * MAN, "2": 2000 * MAN}},
            "암진단금": {"by_company": {"1": 1000 * MAN}},
        },
        "diagnosis": {}, "notes": {}, "extra": extra, "warnings": [],
    }


def _analysis(with_yn: bool = True) -> dict:
    before = build_before(_raw(with_yn), today="2026-07-27")
    return {"before": before, "final": {"premium": before["premium"], "coverages": [], "rollup_by_group12": []}}


def _result(with_yn: bool = True):
    return build_after_analysis(_analysis(with_yn), {"existing": [], "proposals": []})


def _label_comment(ws, row_id: str) -> str:
    comment = ws.cell(row=row_of(row_id), column=COL_NAME).comment
    return comment.text if comment else ""


# ── 개정3: Y/N 회사별 (집계 파생 — 금액 불변) ────────────────────────────────────
def test_yn_flags_expose_per_company_without_changing_amounts():
    """yn_flags에 by_company(회사별 Y)가 실리고 원천 담보 금액은 그대로."""
    before = _analysis()["before"]
    flags = {f["item"]: f for f in compute_yn_flags(before["coverages"])}
    assert flags["운전자특약"]["value"] == "Y" and flags["운전자특약"]["by_company"] == {"1": "Y"}
    assert flags["자동차부상치료비"]["by_company"] == {"2": "Y"}
    assert flags["상해실손의료비"]["by_company"] == {"2": "Y"}
    assert flags["가족일상배상책임"]["value"] == "N" and flags["가족일상배상책임"]["by_company"] == {}
    rows = {c["row_id"]: c for c in before["coverages"] if c.get("row_id")}
    assert rows["driver_fine"]["by_company"] == {"1": 300 * MAN}
    assert rows["driver_injury_grade"]["by_company"] == {"2": 100 * MAN}


def test_yn_shown_inside_rows_not_in_a_separate_block():
    """291 Q5: Y/N 별도 블록 없음 — 운전자/배상/실비 행 라벨 메모에 `가입특약 Y/N: Y|N`, 금액은 회사 열에 그대로."""
    ws = workbook(_result())[SHEET_BEFORE]
    assert "가입특약 Y/N: Y" in _label_comment(ws, "driver_fine")
    assert "가입특약 Y/N: N" in _label_comment(ws, "liability_daily")
    assert ws.cell(row=row_of("driver_fine"), column=company_col(0)).value == 300
    assert ws.cell(row=row_of("driver_fine"), column=company_col(1)).value is None
    labels = [ws.cell(row=r, column=COL_NAME).value for r in range(1, ws.max_row + 1)]
    assert "운전자특약" not in labels and "가족일상배상책임" not in labels  # 구 Y/N 5행 없음


def test_yn_recomputed_from_coverages_not_stale_payload():
    """★실사용 동선 결함 고정: 클라이언트 [후] payload는 yn_flags가 [전] 값 그대로
    스프레드된다(coverages만 해지 반영). 시트는 담보 행에서 재파생해야 해지가 반영된다."""
    result = _result()
    stale = [dict(f) for f in result["before"]["yn_flags"]]      # [전] 스냅샷(운전자=계약1 Y)
    after_before = result["after"]["before"]
    for row in after_before["coverages"]:
        by_company = {k: v for k, v in (row.get("by_company") or {}).items() if k != "1"}
        row["by_company"] = by_company
        row["enrolled"] = any(v is not None for v in by_company.values())
        row["summary"] = sum(v for v in by_company.values() if v is not None) or None
        if row.get("sources"):
            row["sources"] = {n: {k: v for k, v in cells.items() if k != "1"} for n, cells in row["sources"].items()}
    after_before["yn_flags"] = stale                            # ★낡은 [전] 플래그
    after_before["contract_list"] = [c for c in after_before["contract_list"] if str(c["idx"]) != "1"]

    wb = workbook(result)
    assert "가입특약 Y/N: Y" in _label_comment(wb[SHEET_BEFORE], "driver_fine")   # [전]은 그대로 Y
    assert "가입특약 Y/N: N" in _label_comment(wb[SHEET_AFTER], "driver_fine")    # ★[후]는 해지 반영 N


# ── 개정2: 보험료(값 불변·위치는 291 양식 6행) ────────────────────────────────────
def test_premium_row_carries_company_and_total_monthly():
    result = _result()
    wb = workbook(result)
    ws = wb[SHEET_BEFORE]
    assert ws.cell(row=ROW_PREMIUM, column=company_col(0)).value == 10_000
    assert ws.cell(row=ROW_PREMIUM, column=company_col(1)).value == 20_000
    assert ws.cell(row=ROW_PREMIUM, column=COL_SUM).value == result["before"]["premium"]["monthly_total"]
    ws_a = wb[SHEET_AFTER]
    assert ws_a.cell(row=ROW_PREMIUM, column=COL_SUM).value == result["after"]["before"]["premium"]["monthly_total"]
    assert ws_a.cell(row=ROW_PREMIUM, column=company_col(0)).value == 10_000


def test_meta_block_keeps_kp_difference_inline():
    """계피관계·구분은 회사명 셀 메모로 보존(정보 손실 0 — 236·254 패턴, 291은 수기표에 메타 행이 없다)."""
    ws = workbook(_result())[SHEET_BEFORE]
    c1 = ws.cell(row=ROW_COMPANY, column=company_col(0)).comment
    c2 = ws.cell(row=ROW_COMPANY, column=company_col(1)).comment
    assert c1 and "계피상이" in c1.text and "2021-01-01" in c1.text
    assert c2 and "구분: 유지" in c2.text and "계피" not in c2.text


def test_amount_cells_unchanged_by_refinements():
    """★값 불변: 담보 금액 셀·회사합=합계가 개정 후에도 그대로."""
    result = _result()
    ws = workbook(result)[SHEET_BEFORE]
    rows = {c["row_id"]: c for c in result["before"]["coverages"] if c.get("row_id")}
    n = 2
    for row_id in ("death_disease", "cancer_general"):
        row = row_of(row_id)
        expected = rows[row_id].get("by_company") or {}
        for idx in range(n):
            got = ws.cell(row=row, column=company_col(idx)).value
            exp = expected.get(str(idx + 1))
            assert got == (None if exp is None else round(exp / MAN))
        assert sum(company_cells(ws, row, n)) == sum_cell(ws, row)
