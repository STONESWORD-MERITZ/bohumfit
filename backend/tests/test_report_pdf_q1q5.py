# BOHUMFIT-036 고지내역 PDF — 034 Q1~Q5 재편 반영 회귀(Chromium 불요·HTML 렌더 단계만).
#  익명 합성 데이터(PII 없음). PDF 변환(Playwright)은 Codex/Windows 권위.
from datetime import datetime
from pipeline.report_pdf import _metric_visibility, _prepare_section, render_disclosure_html


def test_metric_visibility_q4_inpatient_surgery():
    m = _metric_visibility({"inpatient": 5, "inpatient_count": 1, "surgery_count": 1}, "Q4", False)
    assert not m["inpatient"] and not m["inpatient_count"]  # BOHUMFIT-214: 입원은 상단 입원근거로만 표시
    assert m["surgery"]
    assert not m["visit"] and not m["med"]          # Q4 통원·투약 없음


def test_metric_visibility_q5_no_chips():
    m = _metric_visibility({"inpatient": 5, "surgery_count": 1}, "Q5", False)
    assert m == {"visit": False, "inpatient": False, "inpatient_count": False, "surgery": False, "med": False}


def test_prepare_section_exposes_suspected_grade():
    reports = {"[4번질문] 5년 초과 10년 이내 입원·수술": [
        {"code": "M51", "name": "추간판", "surgery_suspected": ["관혈적정복술"], "surgery_suspected_grade": "강"}]}
    secs = _prepare_section(reports, is_easy=False)
    assert secs[0]["q_num"] == "Q4"
    assert secs[0]["rows"][0]["suspected_grade"] == "강"


def _full_payload():
    return {
        "reference_date": "2026-06-15",
        "standard_reports": {
            "[1번질문] 3개월 이내 진단·입원·수술·투약": [{"code": "K21", "name": "역류성식도염", "visit": 2, "first_date": "2026-04-01", "latest_date": "2026-04-10"}],
            "[3번질문] 5년 이내 입원·수술·통원·투약": [{"code": "N76", "name": "질염", "visit": 14, "med_days": 31, "first_date": "2024-01-01", "latest_date": "2024-06-01"}],
            "[4번질문] 5년 초과 10년 이내 입원·수술": [{"code": "M51", "name": "추간판", "inpatient": 5, "inpatient_count": 1, "surgery_suspected": ["관혈적정복술"], "surgery_suspected_grade": "강", "first_date": "2019-03-10", "latest_date": "2019-03-15"}],
            "[5번질문] 5년 이내 10대질환": [{"code": "C50", "name": "유방암", "first_date": "2023-09-01", "latest_date": "2023-09-01"}],
        },
        "easy_reports": {}, "all_disease_summary": [], "total_med_sum": 31,
    }


def test_render_disclosure_html_q1_to_q5_and_grade():
    html = render_disclosure_html(_full_payload(), datetime(2026, 6, 16))
    assert "3개월" in html
    assert "5년 이내 입원·수술·통원·투약" in html          # Q3 5년
    assert "5년 초과 10년 이내 입원·수술" in html           # Q4 5~10년
    assert "5년 이내 10대질환" in html                      # Q5 중대질환
    assert "5년 초과 10년 이내 입원 또는 수술" in html       # PDF 기준 문구도 Q4 재편 반영
    assert "중대질환 진료 이력이 확인되지 않은 경우 (5번질문)" in html
    assert "10년 이내 입원·수술, 7회 이상 통원" not in html
    assert "수술 의심—확인 필요 (강)" in html               # Q4 공단 의심 강
    assert "통원 14회" in html and "투약 31일" in html


def test_render_empty_section_shows_no_disclosure():
    html = render_disclosure_html({"standard_reports": {}, "easy_reports": {}}, datetime(2026, 6, 16))
    assert "고지 검토 항목이 없습니다" in html               # 빈 섹션 "해당없음"


def test_render_deterministic():
    a = render_disclosure_html(_full_payload(), datetime(2026, 6, 16))
    b = render_disclosure_html(_full_payload(), datetime(2026, 6, 16))
    assert a == b
