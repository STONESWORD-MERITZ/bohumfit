# -*- coding: utf-8 -*-
"""BOHUMFIT-250 회귀 — 엑셀 시각 디벨롭(값 불변·스타일 존재·면 전용 색 계약). 익명 합성."""
from __future__ import annotations

import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import openpyxl

from coverage.aggregator import build_before
from coverage.excel_style import EMERALD, FILL_ONLY_COLORS, GREENTEA, LIME, WHITE
from coverage.export_excel import build_workbook_bytes

MAN = 10_000


def _analysis() -> dict:
    raw = {
        "customer": {"name": "홍길동", "age": 50, "sex": "남자"},
        "contracts": [{
            "idx": 1, "insurer": "가나손보", "product": "합성", "contract_date": "2024-01-01",
            "pay_cycle": "월납", "pay_years": 20, "pay_months": 240, "maturity": "100세",
            "monthly_premium": 50_000,
        }],
        "matrix": {
            "일반사망" if False else "질병사망": {"by_company": {"1": 5000 * MAN}},
            "암진단금": {"by_company": {"1": 3000 * MAN}},
        },
        "diagnosis": {}, "notes": {},
        "extra": {
            "순환계 치료비": {"agg": "sum", "by_company": {"1": 1000 * MAN}},
            "일반종수술 5종(표준환산)": {"agg": "sum", "by_company": {"1": 500 * MAN}, "estimated": True},
        },
        "warnings": [],
    }
    before = build_before(raw, today="2026-07-27")
    return {"before": before, "final": {"premium": before["premium"], "coverages": [], "rollup_by_group12": []}}


def _label_cells(ws) -> dict:
    cells = {}
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str):
                cells.setdefault(cell.value, cell)
    return cells


def test_style_presence_and_values_unchanged():
    """헤더=에메랄드+흰 글자·강조 행=그린 티·특수 행=라임·패널 라벨 — 값은 249와 동일 규칙."""
    wb = openpyxl.load_workbook(io.BytesIO(build_workbook_bytes(_analysis())))
    ws = wb["비교분석표"]
    labels = _label_cells(ws)
    header = labels["담보내용"]
    assert header.fill.fgColor.rgb == EMERALD and header.font.color.rgb == WHITE
    assert ws.cell(row=5, column=2).fill.fgColor.rgb == EMERALD
    assert ws.cell(row=5, column=2).font.color.rgb == WHITE
    # 강조 행(암진단금 — 원본 실측 위치 세트): 값 셀에 그린 티 면.
    cancer = labels["암진단금"]
    assert any(ws.cell(row=cancer.row, column=col).fill.fgColor.rgb == GREENTEA
               for col in range(2, ws.max_column))
    # 특수 행(순환계 치료비): 라임 면.
    circ = labels["순환계 치료비"]
    assert any(ws.cell(row=circ.row, column=col).fill.fgColor.rgb == LIME
               for col in range(2, ws.max_column))
    # 우측 고객정보 패널(라벨+공란 — PII 미기입).
    assert "1.성명 : " in labels and "[양식]" in labels and "고등전산" in labels
    # 값 검증(스타일 계층이 값을 바꾸지 않음): 질병사망=양식 12행 합계 5,000만 → 5000(만원).
    assert ws.cell(row=12, column=3).value == 5000
    assert ws.cell(row=16, column=3).value == 3000
    # 인쇄 폭 맞춤(15계약 대응 — 사양 결정 3 잠정).
    assert ws.page_setup.fitToWidth == 1


def test_fill_only_colors_never_used_as_font_color():
    """★면 전용 색(라임·그린 티)은 폰트 색으로 사용 금지 — 전 시트 전 셀 검사."""
    wb = openpyxl.load_workbook(io.BytesIO(build_workbook_bytes(_analysis())))
    for sheet_name in wb.sheetnames:
        for row in wb[sheet_name].iter_rows():
            for cell in row:
                color = getattr(cell.font.color, "rgb", None)
                assert color not in FILL_ONLY_COLORS, (sheet_name, cell.coordinate)
