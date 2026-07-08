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


def test_screen_per_rider_table_uses_two_level_before_after_header() -> None:
    source = Path(__file__).resolve().parents[2] / "src" / "pages" / "CoverageRemodel.tsx"
    text = source.read_text(encoding="utf-8")
    head = text.split("comparisonGroups.map", 1)[1].split("<tbody>", 1)[0]

    assert re.search(r'<th\s+rowSpan=\{2\}[^>]*>\s*담보\s*</th>', head)
    assert re.search(r'<th\s+colSpan=\{2\}[^>]*>\s*전\s*</th>', head)
    assert re.search(r'<th\s+colSpan=\{2\}[^>]*>\s*후\s*</th>', head)
    assert re.search(r'<th\s+rowSpan=\{2\}[^>]*>\s*증감\s*</th>', head)
    assert re.search(r'<th\s+rowSpan=\{2\}[^>]*>\s*변화\s*</th>', head)
    assert head.count(">가입</th>") == 2
    assert head.count(">상태</th>") == 2


def test_pdf_per_rider_compare_table_groups_before_after_and_keeps_eight_cells() -> None:
    html = build_coverage_html(_report())
    section = html.split("특약별 보장 비교 · 개선 담보", 1)[1].split("</table>", 1)[0]

    assert '<th rowspan="2">대분류</th>' in section
    assert '<th rowspan="2">담보</th>' in section
    assert '<th colspan="2">전</th>' in section
    assert '<th colspan="2">후</th>' in section
    assert '<th rowspan="2" class="num">증감</th>' in section
    assert '<th rowspan="2">변화</th>' in section

    rows = re.findall(r"<tr><td.*?</tr>", section, re.S)
    row = next(item for item in rows if ">수술비</td>" in item)
    assert row.count("<td") == 8
    assert "부족" in row
    assert "충분" in row
    assert "+1,000만" in row
    assert "부족 -&gt; 충분" in row


def test_excel_compare_sheet_groups_before_after_columns_and_reorders_values() -> None:
    workbook = load_workbook(io.BytesIO(build_workbook_bytes(_report())))
    sheet = workbook["④ 전후 특약별"]
    header_row = next(
        row
        for row in range(1, sheet.max_row + 1)
        if sheet.cell(row=row, column=4).value == "전" and sheet.cell(row=row, column=6).value == "후"
    )
    merged = {str(cell_range) for cell_range in sheet.merged_cells.ranges}

    assert f"D{header_row}:E{header_row}" in merged
    assert f"F{header_row}:G{header_row}" in merged
    assert f"B{header_row}:B{header_row + 1}" in merged
    assert f"H{header_row}:H{header_row + 1}" in merged
    assert f"I{header_row}:I{header_row + 1}" in merged
    assert sheet.cell(header_row + 1, 4).value == "가입"
    assert sheet.cell(header_row + 1, 5).value == "상태"
    assert sheet.cell(header_row + 1, 6).value == "가입"
    assert sheet.cell(header_row + 1, 7).value == "상태"

    surgery = next(row for row in sheet.iter_rows(values_only=True) if row[1] == "수술비")
    assert surgery[:9] == (
        "수술",
        "수술비",
        20_000_000,
        10_000_000,
        "부족",
        20_000_000,
        "충분",
        10_000_000,
        "부족 -> 충분",
    )
