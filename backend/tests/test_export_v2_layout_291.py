# -*- coding: utf-8 -*-
"""BOHUMFIT-291(S3) — 산출물 49행 양식(엑셀·PDF) 계약.

★S2 값 계층은 동결이다. 이 파일이 고정하는 것은 **모양**과 **값 무변경 증명**이다.
  ①시트 4개(표지·컨설팅 전·컨설팅 후·최종) · 행명 49개 = V2 스키마 문자열 · 회사당 2열
  ②2열 병기: 종수술 = 질병|상해, 간병인 = 상해|질병 · 종별 미확인은 병합 1값
  ③Q2 80% 행: 값 표시 + "합계 미포함" 메모 · Q5 Y/N은 행 메모(별도 블록 없음)
  ④`최종`: L 접두(케스케이드 하위 10행 · 이 시트만) · 종합 판정 블록 17행 = compute_stage_totals 1:1 · 비고 블록
  ⑤★값 무변경: 시트 셀(만원) == S2 집계(summary/by_company/columns) 전 셀
  ⑥PDF: 2열 병기 한 칸 `질병/상해` · 종합 17행 · L 접두(특약별 비교) · Y/N 블록 없음 · 회사 5개 분할 유지
  ⑦신판 수기표 행명 46개 문자열 일치(파일이 있을 때)
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from coverage.aggregator import build_before, compute_stage_totals
from coverage.compare import build_after_analysis
from coverage.constants import CASCADE_CHILD_PREFIX_V2, KB_COVERAGES_V2, PAYOUT_CASCADE_V2, SUM_EXCLUDED_NOTE_V2
from coverage.export_excel import CASCADE_CHILD_ROWS, DUAL_ORDER
from coverage.export_pdf import build_coverage_html
from tests.excel_v2_layout import (
    COL_GROUP,
    COL_NAME,
    COL_SUM,
    ROW_COMPANY,
    SHEET_AFTER,
    SHEET_BEFORE,
    SHEET_FINAL,
    company_col,
    row_of,
    workbook,
    final_row_of,
)

MAN = 10_000


def _raw(matrix=None, extra=None, contracts=2):
    return {
        "customer": {"name": "홍길동", "age": 50, "sex": "남자"},
        "contracts": [
            {"idx": i, "insurer": f"합성손보{i}", "product": f"합성상품{i}", "contract_date": "2024-01-01",
             "pay_cycle": "월납", "pay_years": 20, "pay_months": 240, "maturity": "100세",
             "monthly_premium": 10_000 * i}
            for i in range(1, contracts + 1)
        ],
        "matrix": matrix or {}, "diagnosis": {}, "notes": {}, "extra": extra or {}, "warnings": [],
    }


def _result(matrix=None, extra=None, plan=None):
    before = build_before(_raw(matrix, extra), today="2026-08-17")
    analysis = {"before": before, "final": {"premium": before["premium"], "coverages": [], "rollup_by_group12": []}}
    return build_after_analysis(analysis, plan or {"existing": [], "proposals": []})


RICH = {
    "질병사망": {"by_company": {"1": 3000 * MAN, "2": 2000 * MAN}},
    "상해후유장해": {"by_company": {"1": 5000 * MAN}},
    "뇌혈관질환": {"by_company": {"1": 1000 * MAN}},
    "뇌졸중": {"by_company": {"2": 2000 * MAN}},
    "간병인/간호간병상해일당": {"by_company": {"2": 10 * MAN}},
    "간병인/간호간병질병일당": {"by_company": {"2": 20 * MAN}},
    "벌금(대인/스쿨존/대물)": {"by_company": {"1": 300 * MAN}},
}
RICH_EXTRA = {
    "80%이상 후유장해": {"agg": "sum", "by_company": {"1": 2000 * MAN}},
    "화상진단비": {"agg": "sum", "by_company": {"1": 300 * MAN}},
}


# ── ① 골격 ────────────────────────────────────────────────────────────────
def test_four_sheets_and_49_row_labels():
    wb = workbook(_result(RICH, RICH_EXTRA))
    assert wb.sheetnames == ["표지(세로)", SHEET_BEFORE, SHEET_AFTER, SHEET_FINAL]
    for sheet in (SHEET_BEFORE, SHEET_AFTER):
        ws = wb[sheet]
        labels = [ws.cell(row=row_of(r.row_id), column=COL_NAME).value for r in KB_COVERAGES_V2]
        assert labels == [r.display for r in KB_COVERAGES_V2]   # 수기표 문자열 그대로(띄어쓰기 포함)
        groups = [ws.cell(row=row_of(r.row_id), column=COL_GROUP).value for r in KB_COVERAGES_V2 if ws.cell(row=row_of(r.row_id), column=COL_GROUP).value]
        assert groups == list(dict.fromkeys(r.group for r in KB_COVERAGES_V2))  # 대분류 11 병합 선두
        assert ws.cell(row=ROW_COMPANY, column=company_col(0)).value == "합성손보1"
        assert ws.cell(row=ROW_COMPANY, column=company_col(1)).value == "합성손보2"
        assert ws.page_setup.fitToWidth == 1


# ── ② 2열 병기 ────────────────────────────────────────────────────────────
def test_dual_columns_split_disease_and_injury():
    plan = {"existing": [], "proposals": [{
        "proposal_id": "P1", "insurer": "메리츠", "product": "알파", "monthly_premium": 77_470, "pay_months": 240,
        "coverages": [
            {"kb_name": "N종수술비(질병 5종)", "amount": 400 * MAN, "group12": "수술", "agg": "sum"},
            {"kb_name": "N종수술비(상해 5종)", "amount": 1000 * MAN, "group12": "수술", "agg": "sum"},
        ],
    }]}
    result = _result(RICH, plan=plan)
    ws = workbook(result)[SHEET_AFTER]
    r5 = row_of("tier_surgery_5")
    p_col = company_col(2)  # P1은 세 번째 계약 열
    assert ws.cell(row=ROW_COMPANY, column=p_col).value == "메리츠"
    assert (ws.cell(row=r5, column=p_col).value, ws.cell(row=r5, column=p_col + 1).value) == (400, 1000)  # 질병|상해
    assert (ws.cell(row=r5, column=COL_SUM).value, ws.cell(row=r5, column=COL_SUM + 1).value) == (400, 1000)
    # 간병인 = 질병|상해 (★292 Phase F: 종수술과 통일 — 291의 상해|질병에서 수정. 값 무변경, 열 순서만)
    rc = row_of("caregiver")
    assert (ws.cell(row=rc, column=company_col(1)).value, ws.cell(row=rc, column=company_col(1) + 1).value) == (20, 10)
    assert DUAL_ORDER["caregiver"] == ("disease", "injury")


def test_unspecified_tier_value_is_merged_not_guessed():
    extra = {"일반종수술 3종(표준환산)": {"agg": "sum", "by_company": {"1": 50 * MAN}, "estimated": True}}
    ws = workbook(_result(extra=extra))[SHEET_BEFORE]
    r3 = row_of("tier_surgery_3")
    assert ws.cell(row=r3, column=COL_SUM).value == 50 and ws.cell(row=r3, column=COL_SUM + 1).value is None
    assert ws.cell(row=r3, column=company_col(0)).value == 50 and ws.cell(row=r3, column=company_col(0) + 1).value is None


# ── ③ Q2·Q5 표기 ─────────────────────────────────────────────────────────
def test_80_percent_row_shows_value_with_sum_excluded_note():
    ws = workbook(_result(RICH, RICH_EXTRA))[SHEET_BEFORE]
    r80 = row_of("disability_80")
    assert ws.cell(row=r80, column=COL_SUM).value == 2000
    assert ws.cell(row=r80, column=COL_NAME).value == "상해 질병 후 유 장 해 80%"
    assert SUM_EXCLUDED_NOTE_V2 in ws.cell(row=r80, column=COL_NAME).comment.text
    labels = [ws.cell(row=r, column=COL_NAME).value for r in range(1, ws.max_row + 1)]
    assert "운전자특약" not in labels  # 별도 Y/N 블록 없음(Q5)
    assert "가입특약 Y/N: Y" in ws.cell(row=row_of("driver_fine"), column=COL_NAME).comment.text


# ── ④ 최종 ────────────────────────────────────────────────────────────────
def test_final_sheet_l_prefix_stage_block_and_appendix():
    result = _result(RICH, RICH_EXTRA)
    wb = workbook(result)
    ws = wb[SHEET_FINAL]
    labels = {r.row_id: ws.cell(row=final_row_of(r.row_id), column=COL_NAME).value for r in KB_COVERAGES_V2}  # 292: 최종은 헤더 없음
    for rid in CASCADE_CHILD_ROWS:
        assert labels[rid].startswith(CASCADE_CHILD_PREFIX_V2), rid
    assert labels["stroke"] == "L 뇌 졸 중" and labels["cancer_drug_targeted"] == "L 표적 약물 치료"
    for rid in ("cerebral_disease", "cardiac_disease", "ischemic_heart", "cancer_general", "cancer_surgery"):
        assert not labels[rid].startswith("L ")
    assert len(CASCADE_CHILD_ROWS) == 10
    # L 접두는 최종 시트에만
    assert wb[SHEET_BEFORE].cell(row=row_of("stroke"), column=COL_NAME).value == "뇌 졸 중"
    # 종합 판정 블록 17행 = 케스케이드 1:1
    stages = compute_stage_totals(result["before"]["coverages"])
    found = {}
    for r in range(56, ws.max_row + 1):
        v = ws.cell(row=r, column=COL_GROUP).value
        if v in stages:
            found[v] = ws.cell(row=r, column=6).value
    assert list(found) == list(stages) and len(found) == len(PAYOUT_CASCADE_V2) == 17
    for key, value in stages.items():
        assert found[key] == round(value / MAN)
    assert stages["뇌초기"] <= stages["뇌중기"] <= stages["뇌말기"]
    # 비고 블록: 화상진단비
    all_text = [ws.cell(row=r, column=COL_NAME).value for r in range(56, ws.max_row + 1)]
    assert "화상진단비" in all_text
    # 기대효과 = 후 − 전 (해지 0 → 0)
    assert ws.cell(row=row_of("death_disease"), column=10).value == 0


# ── ⑤ ★값 무변경 증명 ────────────────────────────────────────────────────
def _expect_cells(row: dict, key):
    order = DUAL_ORDER.get(row.get("row_id") or "")
    if order and row.get("columns"):
        cols = row["columns"]

        def _v(col):
            cell = cols.get(col) or {}
            return cell.get("summary") if key is None else (cell.get("by_company") or {}).get(key)

        if _v("unspecified") is not None:
            return [row.get("summary") if key is None else (row.get("by_company") or {}).get(key)]
        return [_v(order[0]), _v(order[1])]
    return [row.get("summary") if key is None else (row.get("by_company") or {}).get(key)]


def _man(v):
    return None if v is None else round(v / MAN)


def test_every_sheet_cell_equals_s2_aggregation():
    result = _result(RICH, RICH_EXTRA)
    wb = workbook(result)
    checked = 0
    for sheet, payload in ((SHEET_BEFORE, result["before"]), (SHEET_AFTER, result["after"]["before"])):
        ws = wb[sheet]
        rows = {c["row_id"]: c for c in payload["coverages"] if c.get("row_id")}
        for spec in KB_COVERAGES_V2:
            row = row_of(spec.row_id)
            data = rows[spec.row_id]
            exp = [_man(v) for v in _expect_cells(data, None)]
            got = [ws.cell(row=row, column=COL_SUM + i).value for i in range(len(exp))]
            assert got == exp, (sheet, spec.display, "합계")
            checked += 1
            for i, co in enumerate(payload["contract_list"]):
                key = str(co["idx"])
                exp = [_man(v) for v in _expect_cells(data, key)]
                got = [ws.cell(row=row, column=company_col(i) + j).value for j in range(len(exp))]
                got = [None if (g == "Y" and e is None) else g for g, e in zip(got, exp)]  # Q5 표기
                assert got == exp, (sheet, spec.display, key)
                checked += 1
        assert ws.cell(row=6, column=COL_SUM).value == payload["premium"]["monthly_total"]
    assert checked >= 49 * 3 * 2


REAL = Path(__file__).resolve().parents[2] / "보장분석" / "비교분석표"


@pytest.mark.parametrize("name", ["이인숙-INPUT.pdf", "라금실INPUT.pdf", "20260805_오현지님_보장분석.pdf"])
def test_real_documents_render_and_match_s2(name):
    path = REAL / name
    if not path.exists():
        pytest.skip("실 PDF 없음(gitignore 폴더)")
    from coverage.service import analyze_kb_coverage

    r = analyze_kb_coverage(path.read_bytes())
    result = build_after_analysis(r, {"existing": [], "proposals": []})
    wb = workbook(result)
    ws = wb[SHEET_BEFORE]
    rows = {c["row_id"]: c for c in result["before"]["coverages"] if c.get("row_id")}
    for spec in KB_COVERAGES_V2:
        exp = [_man(v) for v in _expect_cells(rows[spec.row_id], None)]
        got = [ws.cell(row=row_of(spec.row_id), column=COL_SUM + i).value for i in range(len(exp))]
        assert got == exp, spec.display
    stages = compute_stage_totals(result["before"]["coverages"])
    assert stages["뇌초기"] <= stages["뇌중기"] <= stages["뇌말기"]


# ── ⑥ PDF ─────────────────────────────────────────────────────────────────
def test_pdf_dual_cell_stage_rows_l_prefix_and_no_yn_block():
    plan = {"existing": [], "proposals": [{
        "proposal_id": "P1", "insurer": "메리츠", "product": "알파", "monthly_premium": 77_470, "pay_months": 240,
        "coverages": [
            {"kb_name": "N종수술비(질병 5종)", "amount": 400 * MAN, "group12": "수술", "agg": "sum"},
            {"kb_name": "N종수술비(상해 5종)", "amount": 1000 * MAN, "group12": "수술", "agg": "sum"},
        ],
    }]}
    html = build_coverage_html(_result(RICH, RICH_EXTRA, plan))
    assert "400만원/1,000만원" in html                                   # 2열 병기 한 칸(질병/상해)
    assert html.count('<td class="nm">L 뇌 졸 중') >= 1                   # 특약별 비교(최종 대응) L 접두
    for key in ("뇌초기", "뇌중기", "뇌말기", "심장초기", "심장중기", "다빈치(일반암)", "중 입 자 치료"):
        assert f'<td class="grp">{key}</td>' in html                        # 종합 17행
    assert "심장말기" not in html                                          # 구 3단 폐기
    assert "가입특약 Y/N</h3>" not in html                                # 별도 Y/N 블록 없음
    assert "[가입 Y]" in html and f"[{SUM_EXCLUDED_NOTE_V2}]" in html      # 행 안 태그
    assert "49행 밖 담보 — 정보 보존" in html                              # 비고 블록
    assert 'class="chunk-caption"' not in html or html.count('<th rowspan="2">담보</th>') >= 1


# ── ⑦ 신판 수기표 대조 ────────────────────────────────────────────────────
def test_new_workbook_row_names_match(tmp_path=None):
    matches = sorted(REAL.glob("* - 민규.xlsx"))
    if not matches:
        pytest.skip("수기 엑셀 없음(gitignore 폴더)")
    openpyxl = pytest.importorskip("openpyxl")
    manual = openpyxl.load_workbook(matches[0], data_only=True)
    ours = workbook(_result(RICH, RICH_EXTRA))
    assert manual.sheetnames[1:3] == [SHEET_BEFORE, SHEET_AFTER]
    manual_rows = [str(manual[SHEET_BEFORE].cell(row=r, column=3).value).strip() for r in range(7, 53)]
    added = {"유사암 수술", "다빈치 특정암", "순환계 치료비"}
    ours_rows = [ours[SHEET_BEFORE].cell(row=row_of(r.row_id), column=COL_NAME).value for r in KB_COVERAGES_V2]
    assert [x for x in ours_rows if x not in added] == manual_rows
