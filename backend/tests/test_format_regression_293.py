# -*- coding: utf-8 -*-
"""BOHUMFIT-293(층위 2 정리) — ★산출물 **서식** 회귀 방지 스위트.

값 회귀는 290·291·292가 셀 단위로 막고 있다. 이 파일이 막는 것은 **값은 그대로인데 서식이 조용히
빠지는** 유형이다 — 291에서 실제로 일어났다(261 "20년 총납입 차액" 색상 단언이 양식 이식 중 누락됐고
Codex 2차 검증에서야 발견됐다). 그때 잃어버릴 뻔한 규칙을 한곳에 모아 **실문서 3건**으로 고정한다.

★고정 대상(291 Codex 회귀 유형 + 286~292 확정 서식)
  ① 차액 색상(261)   — `최종` 기대효과 열: 보장 증가=에메랄드 / 감소=앰버 · 월납·20년 총납입은 절감=에메랄드 / 증가=앰버
  ② 합계 강조        — 담보행 합계 2열은 bold
  ③ Q2 80% 메모      — `합계 미포함` 문구가 라벨 셀 메모에 남는다(243)
  ④ Q5 Y/N 메모      — yn_source 7행 라벨 메모에 `가입특약 Y/N`
  ⑤ L 접두(291)      — 케스케이드 하위 10행은 `최종` 시트에서만 `L ` 접두
  ⑥ 2열 안내(296)    — 별도 헤더 행 없이 행명·메모로 `질병 | 상해` 순서 유지
  ⑦ 브랜드 색(250)   — 에메랄드 헤더+흰 글자 · 그린 티 대분류 선두 · 라임 특수행 · **빨강 미사용**
  ⑧ 인쇄 설정        — 컨설팅 전/후·최종 landscape·fitToWidth=1·fitToHeight=0 · 표지 portrait · 눈금선 off · 틀고정
  ⑨ PDF 고령 가독성  — 본문 13.5pt·line-height 1.65 · 회사 5개씩 분할 · 섹션 page-break · 2열 병기 한 칸
  ⑩ 비고 블록        — 52행 밖 담보가 이름 그대로 보존된다

★이 파일은 서식만 본다. 값 단언은 291·292가 담당한다(중복 금지).
"""
from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")

from coverage.compare import build_after_analysis
from coverage.constants import (
    CASCADE_CHILD_PREFIX_V2,
    KB_COVERAGES_V2,
    SUM_EXCLUDED_NOTE_V2,
    YN_ITEMS_V2,
)
from coverage.excel_style import AMBER_TX, EMERALD, EMERALD_SOFT, GRAY_SOFT, GREENTEA, LIME, WHITE
from coverage.export_excel import (
    CASCADE_CHILD_ROWS,
    DATA_ROW0,
    DUAL_ORDER,
    SPECIAL_ROW_IDS,
    build_workbook_bytes,
    track_row_of,
)
from coverage.export_pdf import COMPANY_CHUNK, build_coverage_html
from coverage.service import analyze_kb_coverage
from coverage.v2_mapping import ROW_INDEX

REAL = Path(__file__).resolve().parents[2] / "보장분석" / "비교분석표"
DOCS = ("standard-1", "standard-2", "case-0805")
SHEET_COVER, SHEET_BEFORE, SHEET_AFTER, SHEET_FINAL = "표지(세로)", "컨설팅 전", "컨설팅 후", "최종"
FIXED = datetime(2026, 8, 18, 9, 0, 0)
COL_GROUP, COL_NAME, COL_SUM, COL_CO0 = 2, 3, 6, 8
FINAL_COL_BEFORE, FINAL_COL_AFTER, FINAL_COL_DELTA = 6, 8, 10
#: FIT 팔레트에 빨강은 없다(250 S0) — 수기표 원본의 빨간 합계는 의도적으로 미채택(291 충돌표).
FORBIDDEN_RED = {"FFFF0000", "FFC00000", "FFFF3B30"}


def _document_path(name: str) -> Path:
    inputs = sorted(REAL.glob("*INPUT.pdf"))
    dated = sorted(REAL.glob("20260805_*보장분석.pdf"))
    candidates = {"standard-1": inputs[:1], "standard-2": inputs[1:2], "case-0805": dated[:1]}
    if not candidates[name]:
        pytest.skip("실 PDF 없음(gitignore 폴더)")
    return candidates[name][0]


def _built(name: str):
    path = _document_path(name)
    result = build_after_analysis(analyze_kb_coverage(path.read_bytes()), {"existing": [], "proposals": []})
    return result, openpyxl.load_workbook(io.BytesIO(build_workbook_bytes(result, generated_at=FIXED)))


def _rgb(color) -> str | None:
    value = getattr(color, "rgb", None)
    return value if isinstance(value, str) else None


# ── ① 차액 색상(261) — 291에서 실제로 빠졌던 회귀 ────────────────────────────────
@pytest.mark.parametrize("name", DOCS)
def test_final_delta_colors_follow_direction(name):
    """★291 회귀 재발 방지: 기대효과 열의 방향 색이 사라지면 실패한다(값이 맞아도)."""
    _result, wb = _built(name)
    ws = wb[SHEET_FINAL]
    checked = 0
    for spec in KB_COVERAGES_V2:
        cell = ws.cell(row=DATA_ROW0 + ROW_INDEX[spec.row_id], column=FINAL_COL_DELTA)
        if not isinstance(cell.value, (int, float)) or cell.value == 0:
            continue
        want = EMERALD if cell.value > 0 else AMBER_TX      # 보장은 늘면 개선
        assert _rgb(cell.font.color) == want, (name, spec.display, cell.value)
        checked += 1
    for row in (4, 6):                                       # 월납 · 20년 총납입(261 P2 지표)
        cell = ws.cell(row=row, column=FINAL_COL_DELTA)
        if isinstance(cell.value, (int, float)):
            want = EMERALD if cell.value <= 0 else AMBER_TX  # 보험료는 줄면 개선 — 방향이 반대다
            assert _rgb(cell.font.color) == want, (name, "월납/총납입", row, cell.value)
            checked += 1
    assert checked >= 0  # 해지·제안 0이면 증감이 없을 수 있다 — 색이 "틀린" 경우만 실패시킨다


def test_final_delta_color_directions_are_opposite_for_premium_and_coverage():
    """해지 1건을 넣어 두 방향(보장 감소=앰버 / 보험료 절감=에메랄드)을 **실제 값으로** 확인한다."""
    path = _document_path(DOCS[0])
    analysis = analyze_kb_coverage(path.read_bytes())
    idx = analysis["before"]["contract_list"][0]["idx"]
    result = build_after_analysis(analysis, {"existing": [{"contract_idx": idx, "disposition": "cancel"}], "proposals": []})
    ws = openpyxl.load_workbook(io.BytesIO(build_workbook_bytes(result, generated_at=FIXED)))[SHEET_FINAL]
    drops = [ws.cell(row=DATA_ROW0 + ROW_INDEX[s.row_id], column=FINAL_COL_DELTA) for s in KB_COVERAGES_V2]
    drops = [c for c in drops if isinstance(c.value, (int, float)) and c.value < 0]
    assert drops, "해지했는데 감소한 담보가 하나도 없다"
    assert all(_rgb(c.font.color) == AMBER_TX for c in drops)
    prem = ws.cell(row=4, column=FINAL_COL_DELTA)
    assert prem.value is not None and prem.value <= 0 and _rgb(prem.font.color) == EMERALD
    assert _rgb(ws.cell(row=6, column=FINAL_COL_DELTA).font.color) == EMERALD   # 20년 총납입도 같은 색


# ── ②③④⑤⑥⑦⑩ 엑셀 서식 ────────────────────────────────────────────────────
@pytest.mark.parametrize("name", DOCS)
def test_excel_format_contract(name):
    _result, wb = _built(name)
    assert wb.sheetnames == [SHEET_COVER, SHEET_BEFORE, SHEET_AFTER, SHEET_FINAL]
    yn_sources = {row.row_id for row in KB_COVERAGES_V2 if row.yn_source}
    assert len(yn_sources) == 7 and len(YN_ITEMS_V2) == 5

    for sheet in (SHEET_BEFORE, SHEET_AFTER):
        ws = wb[sheet]
        # ⑥ 2열 라벨(★296: 292 F 헤더 행 제거 · 간병인 순서만 유지)
        assert DUAL_ORDER["caregiver"] == ("disease", "injury")
        for r in range(DATA_ROW0, DATA_ROW0 + len(KB_COVERAGES_V2)):
            assert ws.cell(row=r, column=COL_NAME).value != "2열 병기 (좌 | 우)"
        for spec in KB_COVERAGES_V2:
            row = track_row_of(spec.row_id)
            label = ws.cell(row=row, column=COL_NAME)
            assert label.value == spec.display                      # ⑤ 전/후 시트엔 L 접두가 없다
            assert not str(label.value).startswith(CASCADE_CHILD_PREFIX_V2)
            assert ws.cell(row=row, column=COL_SUM).font.b, (sheet, spec.display)   # ② 합계 강조
            note = label.comment.text if label.comment else ""
            if spec.sum_excluded:
                assert SUM_EXCLUDED_NOTE_V2 in note, (sheet, spec.display)          # ③ Q2
            if spec.row_id in yn_sources:
                assert "가입특약 Y/N" in note, (sheet, spec.display)                 # ④ Q5
            # ⑦ 브랜드: 회색 헤더는 그레이, 특수행은 라임, 대분류 선두는 그린 티, 빨강은 어디에도 없다
            # ★BOHUMFIT-302b: `sum_excluded` 회색이 특수 강조(LIME)보다 우선한다 —
            #   순환계 치료비는 SPECIAL_ROW_IDS이면서 회색 헤더가 됐다.
            if spec.sum_excluded:
                assert _rgb(ws.cell(row=row, column=COL_SUM).fill.fgColor) == GRAY_SOFT
            elif spec.row_id in SPECIAL_ROW_IDS:
                assert _rgb(ws.cell(row=row, column=COL_SUM).fill.fgColor) == LIME
        header = ws.cell(row=2, column=COL_CO0)
        if header.value:
            assert _rgb(header.fill.fgColor) == EMERALD and _rgb(header.font.color) == WHITE
        assert _rgb(ws.cell(row=2, column=COL_SUM).fill.fgColor) == EMERALD_SOFT
        leads = {_rgb(ws.cell(row=track_row_of(KB_COVERAGES_V2[0].row_id), column=COL_GROUP).fill.fgColor)}
        assert leads == {GREENTEA}
        # ⑧ 인쇄
        assert ws.page_setup.orientation == "landscape"
        assert ws.page_setup.fitToWidth == 1 and ws.page_setup.fitToHeight == 0
        assert ws.sheet_view.showGridLines is False and ws.freeze_panes

    # ⑤ 최종 시트에서만 L 접두
    wsf = wb[SHEET_FINAL]
    for spec in KB_COVERAGES_V2:
        value = wsf.cell(row=DATA_ROW0 + ROW_INDEX[spec.row_id], column=COL_NAME).value
        assert value.startswith(CASCADE_CHILD_PREFIX_V2) == (spec.row_id in CASCADE_CHILD_ROWS), spec.display
    # 표지는 세로
    assert wb[SHEET_COVER].page_setup.orientation == "portrait"

    # ⑦ 빨강 0 — 전 시트 전 셀(글자·면)
    for sheet in wb.sheetnames:
        for row in wb[sheet].iter_rows():
            for cell in row:
                assert _rgb(cell.font.color) not in FORBIDDEN_RED, (sheet, cell.coordinate)
                assert _rgb(cell.fill.fgColor) not in FORBIDDEN_RED, (sheet, cell.coordinate)


@pytest.mark.parametrize("name", DOCS)
def test_appendix_block_keeps_out_of_schema_names(name):
    """⑩ 52행 밖 담보는 비고 블록에 **이름 그대로** 남는다(정보 보존 — 276a)."""
    result, wb = _built(name)
    extras = [c["kb_name"] for c in result["before"]["coverages"] if not c.get("row_id")]
    if not extras:
        pytest.skip("비고행 없음")
    ws = wb[SHEET_BEFORE]
    shown = {ws.cell(row=r, column=COL_NAME).value for r in range(DATA_ROW0, ws.max_row + 1)}
    assert set(extras) <= shown, sorted(set(extras) - shown)


# ── ⑨ PDF 고령 가독성 ──────────────────────────────────────────────────────
@pytest.mark.parametrize("name", DOCS)
def test_pdf_readability_contract(name):
    path = _document_path(name)
    result = build_after_analysis(analyze_kb_coverage(path.read_bytes()), {"existing": [], "proposals": []})
    html = build_coverage_html(result, generated_at=FIXED)
    assert "font-size: 13.5pt" in html and "line-height: 1.65" in html   # 고령 가독성(261)
    assert "page-break" in html                                          # 섹션 분리
    assert COMPANY_CHUNK == 5
    companies = len(result["before"]["contract_list"])
    assert html.count('<th rowspan="2">담보</th>') >= max(1, -(-companies // COMPANY_CHUNK))
    assert f"[{SUM_EXCLUDED_NOTE_V2}]" in html                           # Q2 태그
    assert "52행 밖 담보 — 정보 보존" in html                             # 비고 헤딩
    assert "가입특약 Y/N</h3>" not in html                                # 구 Y/N 블록 부활 금지
    assert "#FF0000" not in html.upper()                                 # 브랜드: 빨강 미사용
