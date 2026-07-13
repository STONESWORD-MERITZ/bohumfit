"""BOHUMFIT-214/217: inpatient display is evidence/chips, judgment detail is surgery-only."""

import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main
from pipeline import report_pdf as rp


INPATIENT = "\uc785\uc6d0"
SURGERY = "\uc218\uc220"
HOSPITAL = "\ud14c\uc2a4\ud2b8\ubcd1\uc6d0"
DISEASE = "\ubb34\ub98e \uc778\ub300 \uc190\uc0c1"
EASY_Q2_TITLE = f"[2\ubc88\uc9c8\ubb38] 10\ub144\uc774\ub0b4 {INPATIENT}\u00b7{SURGERY}"


def _inpatient_item(**overrides):
    item = {
        "first_date": "2023-06-16",
        "latest_date": "2023-06-19",
        "display_code": "S83",
        "code": "S83",
        "name": DISEASE,
        "visit": 0,
        "med_days": 0,
        "inpatient": 4,
        "inpatient_count": 1,
        "inpatient_periods": [{"start": "2023-06-16", "end": "2023-06-19", "days": 4, "hospital": HOSPITAL}],
        "surgeries": [],
        "surgery_suspected": [],
        "surgery_suspected_grade": "",
        "detail": f"10\ub144\uc774\ub0b4 {INPATIENT} (4\uc77c)",
        "hospitals": [HOSPITAL],
    }
    item.update(overrides)
    return item


def test_kakao_keeps_inpatient_period_but_hides_duplicate_detail():
    item = _inpatient_item()
    msg = main._build_kakao_message("\uac04\ud3b8\uc2ec\uc0ac", date(2026, 7, 13), {EASY_Q2_TITLE: [item]})

    assert f"[{INPATIENT}]" in msg
    assert "2023-06-16 ~ 2023-06-19" in msg
    assert f"{INPATIENT}4" in msg
    assert item["detail"] not in msg


def test_pdf_metric_visibility_hides_inpatient_chips_only():
    metric = rp._metric_visibility(
        {"inpatient": 4, "inpatient_count": 1, "surgery_count": 1, "detail": f"10\ub144\uc774\ub0b4 {INPATIENT}\u00b7{SURGERY}"},
        "Q2",
        True,
    )

    assert metric["inpatient"] is False
    assert metric["inpatient_count"] is False
    assert metric["surgery"] is True


def test_pdf_keeps_inpatient_evidence_and_new_summary_chips():
    item = _inpatient_item()
    payload = {
        "reference_date": "2026-07-13",
        "standard_reports": {},
        "easy_reports": {EASY_Q2_TITLE: [item]},
        "all_disease_summary": [],
        "total_med_sum": 0,
    }

    html = rp.render_disclosure_html(payload, datetime(2026, 7, 13))

    assert "2023-06-16 ~ 2023-06-19" in html
    assert f"{INPATIENT} \ucd1d 1\ud68c" in html
    assert "\ud569\uc0b0 4\uc77c" in html
    assert f"{INPATIENT} 4\uc77c" not in html
    assert f"{INPATIENT} 1\ud68c" not in html
    assert item["detail"] not in html


def test_display_detail_is_surgery_only_after_217():
    surgery_name = "\uad00\uc808\uacbd\ud558\uc218\uc220\uc2dc\uc0ac\uc6a9\ud558\ub294\uce58\ub8cc\uc7ac\ub8cc\ube44\uc6a9"
    detail = f"10\ub144\uc774\ub0b4 {INPATIENT}(4\uc77c)/{SURGERY}: {surgery_name}/{INPATIENT}(9\uc77c)"
    item = _inpatient_item(
        surgery_count=1,
        surgeries=[surgery_name],
        surgery_events=[{"date": "2024-10-07", "hospital": HOSPITAL, "surgeries": [surgery_name]}],
        detail=detail,
    )

    assert rp._display_detail(item) == f"10\ub144\uc774\ub0b4 {SURGERY}: {surgery_name}"
    assert main._kakao_display_detail(item) == f"10\ub144\uc774\ub0b4 {SURGERY}: {surgery_name}"


def test_display_detail_drops_surgery_when_filtered_count_zero():
    surgery_name = "\uad00\uc808\uacbd\ud558\uc218\uc220"
    detail = f"10\ub144\uc774\ub0b4 {INPATIENT}(4\uc77c)/{SURGERY}: {surgery_name}"
    item = _inpatient_item(
        surgery_count=0,
        surgeries=[],
        surgery_events=[],
        detail=detail,
    )

    assert rp._display_detail(item) == ""
    assert main._kakao_display_detail(item) == ""
