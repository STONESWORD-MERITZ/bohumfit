# BOHUMFIT-067 리포트 본문 고객명 표시 회귀 — render_report_html(disclosure).
#
# 고객명은 payload.customer_name(프런트: 사용자 입력 > 공단 자동추출(065) > "")이며, 있으면 헤더에
#   "고객명 ○○○" 표시, 없으면 그 줄 생략(폴백). PII — 화면·PDF 표시만, 서버 영구 저장 안 함.
from datetime import datetime

from pipeline import report_pdf as rp

GEN = datetime(2026, 6, 11, 10, 30, 0)
BASE = {
    "report_type": "disclosure",
    "reference_date": "2026-06-11",
    "standard_reports": {},
    "easy_reports": {},
    "all_disease_summary": [],
    "total_med_sum": 0,
}


# ── ④ 고객명 있으면 본문(헤더)에 표시 ─────────────────────────────────────────
def test_report_body_shows_customer_name():
    html = rp.render_report_html("disclosure", {**BASE, "customer_name": "홍길동"}, GEN)
    assert "고객명" in html
    assert "홍길동" in html


# ── ④ 고객명 없으면 그 줄 생략(폴백) ─────────────────────────────────────────
def test_report_body_omits_when_no_name():
    html = rp.render_report_html("disclosure", BASE, GEN)
    assert "고객명" not in html


def test_report_body_omits_when_blank_name():
    html = rp.render_report_html("disclosure", {**BASE, "customer_name": "   "}, GEN)
    assert "고객명" not in html   # 공백만이면 strip 후 "" → 생략


# ── 문서번호·생성일시·점검 기준일은 고객명 유무와 무관하게 유지 ────────────────
def test_header_meta_preserved():
    html = rp.render_report_html("disclosure", {**BASE, "customer_name": "홍길동"}, GEN)
    assert "문서번호" in html and "생성일시" in html and "점검 기준일" in html
