from __future__ import annotations

import io
import os
import re
import sys
from pathlib import Path

from openpyxl import load_workbook

from coverage.compare import build_after_analysis
from coverage.export_excel import build_workbook_bytes
from coverage.export_pdf import build_coverage_html

sys.path.insert(0, os.path.dirname(__file__))
from test_coverage_compare_188 import _analysis, _plan  # noqa: E402


def _report() -> dict:
    return build_after_analysis(_analysis(), _plan())


def test_screen_per_rider_table_focuses_on_coverage_amounts() -> None:
    source = Path(__file__).resolve().parents[2] / "src" / "pages" / "CoverageRemodel.tsx"
    text = source.read_text(encoding="utf-8")
    head = text.split("comparisonGroups.map", 1)[1].split("<tbody>", 1)[0]

    assert "전 보장금액" in head
    assert "후 보장금액" in head
    assert re.search(r">\s*증감\s*</th>", head)
    assert ">상태</th>" not in head
    assert ">변화</th>" not in head


def test_pdf_per_rider_compare_table_focuses_on_coverage_amounts() -> None:
    html = build_coverage_html(_report())
    section = html.split("특약별 보장금액 비교", 1)[1].split("</table>", 1)[0]

    assert "<th>대분류</th>" in section
    assert "<th>담보</th>" in section
    assert '<th class="num">전 보장금액</th>' in section
    assert '<th class="num">후 보장금액</th>' in section
    assert '<th class="num">증감</th>' in section

    rows = re.findall(r"<tr><td.*?</tr>", section, re.S)
    row = next(item for item in rows if ">수술비</td>" in item)
    assert row.count("<td") == 5
    assert "+1,000만" in row
    assert "부족" not in row
    assert "충분" not in row


def test_excel_compare_sheet_uses_amount_columns_only() -> None:
    workbook = load_workbook(io.BytesIO(build_workbook_bytes(_report())))
    sheet = workbook["④ 전후 특약별"]
    header_row = next(
        row
        for row in range(1, sheet.max_row + 1)
        if sheet.cell(row=row, column=3).value == "전 보장금액" and sheet.cell(row=row, column=4).value == "후 보장금액"
    )

    surgery = next(row for row in sheet.iter_rows(values_only=True) if row[1] == "수술비")
    assert surgery[:5] == (
        "수술",
        "수술비",
        10_000_000,
        20_000_000,
        10_000_000,
    )
    assert "부족" not in surgery
    assert "충분" not in surgery
