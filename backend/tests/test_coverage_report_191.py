from __future__ import annotations

import io
import os
import sys
from datetime import datetime

from openpyxl import load_workbook

from coverage.compare import build_after_analysis
from coverage.export_excel import build_workbook_bytes
from coverage.export_pdf import build_coverage_html

sys.path.insert(0, os.path.dirname(__file__))
from test_coverage_compare_188 import _analysis, _plan  # noqa: E402


def _report() -> dict:
    report = build_after_analysis(_analysis(), _plan())
    report["report_cover"] = {
        "customer_name": "홍길동",
        "insurance_age": "45세",
        "age_change_date": "2026-08-01",
        "ga_name": "리뷰온에셋",
        "planner_name": "김설계",
        "written_date": "2026-07-08",
    }
    return report


def test_pdf_cover_renders_fit_original_cover_fields_and_masks_customer() -> None:
    html = build_coverage_html(_report(), datetime(2026, 7, 8))

    assert "보장분석 리포트" in html
    assert "FIT 보장분석" in html
    assert "GA LOGO" in html
    assert "홍*동" in html
    assert "홍길동" not in html
    for value in ("45세", "2026-08-01", "리뷰온에셋", "김설계", "2026-07-08"):
        assert value in html
    assert "#084734" in html
    assert "보험 모집·중개·상품추천·가입권유" in html


def test_pdf_comparison_has_three_axes_and_group_expansion() -> None:
    html = build_coverage_html(_report(), datetime(2026, 7, 8))

    assert "월납입보험료" in html
    assert "150,000원 → 130,000원" in html
    assert "20,000원 절감" in html
    assert "총납입보험료" in html
    assert "2,400,000원 절감" in html
    assert "대분류별 보장 변화" in html
    assert "개선 담보" in html
    assert "암진단" in html and "수술비" in html


def test_excel_compare_sheet_includes_before_after_premium_and_group_summary() -> None:
    workbook = load_workbook(io.BytesIO(build_workbook_bytes(_report())))
    compare = workbook["④ 전후 특약별"]
    values = [cell.value for row in compare.iter_rows() for cell in row if cell.value is not None]

    for label in ("전 월납", "후 월납", "월납 증감", "전 총납입", "후 총납입", "총납입 증감"):
        assert label in values
    assert 150_000 in values
    assert 130_000 in values
    assert -20_000 in values
    assert "대분류별 보장 변화" in values
    assert "암" in values and "수술" in values
    assert 50_000_000 in values
    assert 10_000_000 in values
