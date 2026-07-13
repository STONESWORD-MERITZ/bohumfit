"""BOHUMFIT-214: 입원 판정 라인 중복 제거 표시 회귀.

판정 결과 payload의 inpatient 값은 그대로 보존하되, 하단 판정 칩/detail에서만 입원 중복을 숨긴다.
"""
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main
from pipeline import report_pdf as rp


EASY_Q2_TITLE = "[2번질문] 10년 이내 입원·수술"


def _inpatient_item(**overrides):
    item = {
        "first_date": "2023-06-16",
        "latest_date": "2023-06-19",
        "display_code": "S83",
        "code": "S83",
        "name": "무릎 인대 손상",
        "visit": 0,
        "med_days": 0,
        "inpatient": 4,
        "inpatient_count": 1,
        "inpatient_periods": [{"start": "2023-06-16", "end": "2023-06-19", "days": 4, "hospital": "테스트병원"}],
        "surgeries": [],
        "surgery_suspected": [],
        "surgery_suspected_grade": "",
        "detail": "10년이내 입원 (4일)",
        "hospitals": ["테스트병원"],
    }
    item.update(overrides)
    return item


def test_kakao_keeps_inpatient_period_but_hides_duplicate_detail():
    msg = main._build_kakao_message("간편심사", date(2026, 7, 13), {EASY_Q2_TITLE: [_inpatient_item()]})

    assert "[입원]" in msg
    assert "2023-06-16 ~ 2023-06-19 / 입원4일 / S83 / (양방)무릎 인대 손상 / 테스트병원" in msg
    assert "10년이내 입원 (4일)" not in msg


def test_pdf_metric_visibility_hides_inpatient_chips_only():
    metric = rp._metric_visibility(
        {"inpatient": 4, "inpatient_count": 1, "surgery_count": 1, "detail": "10년 이내 입원·수술"},
        "Q2",
        True,
    )

    assert metric["inpatient"] is False
    assert metric["inpatient_count"] is False
    assert metric["surgery"] is True


def test_pdf_keeps_inpatient_evidence_without_inpatient_chip():
    payload = {
        "reference_date": "2026-07-13",
        "standard_reports": {},
        "easy_reports": {EASY_Q2_TITLE: [_inpatient_item()]},
        "all_disease_summary": [],
        "total_med_sum": 0,
    }

    html = rp.render_disclosure_html(payload, datetime(2026, 7, 13))

    assert "입원 근거" in html
    assert "2023-06-16 ~ 2023-06-19" in html
    assert "입원 4일" not in html
    assert "입원 1회" not in html
    assert "10년이내 입원 (4일)" not in html
