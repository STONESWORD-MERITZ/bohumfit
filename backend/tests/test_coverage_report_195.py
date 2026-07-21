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

    assert "table-fixed" in head
    assert "<colgroup>" in head
    assert "전 보장금액" in head
    assert "후 보장금액" in head
    assert re.search(r">\s*증감\s*</th>", head)
    assert ">상태</th>" not in head
    assert ">변화</th>" not in head


def test_screen_proposal_amount_editor_is_collapsed_by_default() -> None:
    source = Path(__file__).resolve().parents[2] / "src" / "pages" / "CoverageRemodel.tsx"
    text = source.read_text(encoding="utf-8")
    section = text.split('h3 className="ko-heading text-base font-bold text-ink-900">핵심 보장금액', 1)[1].split(
        "{afterResult &&", 1
    )[0]

    assert "expandedProposalIds" in section
    assert "toggleProposalExpanded" in section
    assert 'aria-expanded={expanded}' in section
    assert '{expanded ? "접기" : "펼치기"}' in section
    assert "{expanded && (" in section
    assert "핵심 보장금액을 입력해 주세요." in section


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
    # BOHUMFIT-237 A: 보장금액 셀 한글 단위 문자열 전환(증감은 부호 병기).
    assert surgery[:5] == (
        "수술",
        "수술비",
        "1,000만원",
        "2,000만원",
        "+1,000만원",
    )
    assert "부족" not in surgery
    assert "충분" not in surgery
