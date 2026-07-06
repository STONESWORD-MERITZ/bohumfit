# BOHUMFIT-051 고지 리포트 PDF 표현 개선 회귀 — KST·페이지구분·로고·소재지·브랜딩 토큰.
#   분석 로직 무관 — HTML 렌더 산출물 문자열만 검증(Chromium PDF 변환은 Codex/Windows).
from datetime import datetime
from zoneinfo import ZoneInfo

import pipeline.report_pdf as R

GEN = datetime(2026, 6, 17, 11, 15, 0, tzinfo=ZoneInfo("Asia/Seoul"))


def _payload():
    return {
        "reference_date": "2026-06-17",
        "standard_reports": {"[3번질문] 5년 이내 입원·수술·통원·투약": [
            {"code": "J32", "display_code": "J32", "name": "만성부비동염", "visit": 10,
             "med_days": 47, "inpatient": 0, "inpatient_count": 0, "surgery_dates": [],
             "surgeries": [], "first_diagnosis_date": "2021-07-28", "detail": "통원 10회"}]},
        "easy_reports": {"[2번질문] 10년 이내 입원·수술": [
            {"code": "B44", "display_code": "B44", "name": "아스페르길루스증", "visit": 6,
             "med_days": 49, "inpatient": 3, "inpatient_count": 1, "surgery_dates": ["2024-01-01"],
             "surgeries": ["비용적출술"], "first_diagnosis_date": "2024-01-01", "detail": "입원·수술"}]},
        "all_disease_summary": [], "total_med_sum": 240,
    }


# ── A-2: 생성일시·문서번호 KST 표기 ──────────────────────────────────────
def test_generated_at_and_doc_no_kst_format():
    html = R.render_report_html("disclosure", _payload(), GEN)
    assert "2026-06-17 11:15" in html                       # 생성일시 KST
    assert "BF-20260617-111500" in html.replace(" ", "")    # 문서번호 = BF-YYYYMMDD-HHMMSS(KST)


def test_now_kst_is_seoul():
    # 서버 TZ 무관하게 KST 시간대 반환
    assert R._now_kst().tzinfo is not None
    assert R._now_kst().utcoffset().total_seconds() == 9 * 3600


# ── B-1: 점검 기준일 값 렌더(payload 에 있을 때) ──────────────────────────
def test_reference_date_rendered_when_present():
    html = R.render_report_html("disclosure", _payload(), GEN)
    assert "점검 기준일 <b>2026-06-17</b>" in html


# ── A-3: 간편심사 섹션 새 페이지 ─────────────────────────────────────────
def test_easy_section_page_break():
    html = R.render_report_html("disclosure", _payload(), GEN)
    assert 'class="product-sec page-break"' in html
    assert "page-break-before: always" in html


# ── A-1 / C: 워드마크·브랜드 토큰·뱃지 ────────────────────────────────────
def test_brand_tokens_and_wordmark():
    html = R.render_report_html("disclosure", _payload(), GEN)
    assert "--brand-green: #084734" in html
    assert "#15663D" not in html
    assert "#2E6B3E" not in html
    assert "#145C2A" not in html
    assert "--accent: #B45309" in html           # 종전 미정의 var 보정
    assert "wordmark-sub" in html                # 깔끔한 보조 라인(깨진 SVG 보조텍스트 대체)
    assert "background: var(--brand-green); color: #fff" in html  # 고지 권고 뱃지 그린


# ── A-4: 소재지 도로명/상세 분리 ─────────────────────────────────────────
def test_split_address():
    assert R._split_address("충북 청주시 어딘가로 17, 3층 301호(분평동)") == \
        ["충북 청주시 어딘가로 17", "3층 301호(분평동)"]
    assert R._split_address("-") == ["-"]
    assert R._split_address("") == ["-"]


# ── 분석 로직·한글 폰트·브랜드명 불변 ─────────────────────────────────────
def test_font_stack_and_brand_preserved():
    html = R.render_report_html("disclosure", _payload(), GEN)
    assert "Noto Sans" in html
    assert "BOHUMFIT" in html
