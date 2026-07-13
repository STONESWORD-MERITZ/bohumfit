"""BOHUMFIT-215: 조회기간 출력 정책 회귀.

PDF는 선택 N년 헤더만 표시하고, 실제 report payload 원본은 축소하지 않는다.
"""
from datetime import datetime

from pipeline import report_pdf as rp


Q3 = "[3번질문] 5년 이내 입원·수술·통원·투약"


def _item(date: str, code: str):
    return {
        "first_date": date,
        "latest_date": date,
        "display_code": code,
        "code": code,
        "name": f"테스트질환 {code}",
        "visit": 7,
        "med_days": 0,
        "inpatient": 0,
        "inpatient_count": 0,
        "inpatient_periods": [],
        "surgeries": [],
        "surgery_suspected": [],
        "detail": "5년 이내 통원",
        "hospitals": ["테스트병원"],
    }


def test_pdf_header_shows_selected_years_but_keeps_full_reports():
    payload = {
        "reference_date": "2026-07-13",
        "product_question_years": 10,
        "selected_query_years": 3,
        "standard_reports": {Q3: [_item("2022-07-12", "OLD"), _item("2024-01-01", "NEW")]},
        "easy_reports": {},
        "all_disease_summary": [],
        "total_med_sum": 0,
    }

    html = rp.render_disclosure_html(payload, datetime(2026, 7, 13))

    assert "가입예정상품 10년 고지형 · 선택 3년 고지" in html
    assert "PDF는 고지 누락 방지를 위해 10년 전체 병력을 보존합니다." in html
    assert "OLD" in html
    assert "NEW" in html
