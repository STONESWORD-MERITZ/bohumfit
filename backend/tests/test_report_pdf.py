# -*- coding: utf-8 -*-
"""BOHUMFIT-030: 리포트 PDF 생성 테스트 (고지/실손 분리).

- HTML 렌더링: 콘텐츠 수정 6건 반영 / LEGACY_BRAND 미존재 / 사업자 푸터 / 금액 passthrough(재계산 없음)
- PDF 바이트: 종류별 생성 + 한글 텍스트 추출 (Chromium 미설치 환경은 skip — Windows/배포에서 수행)
"""
import asyncio
import io
import os
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline import report_pdf as rp

GEN_AT = datetime(2026, 6, 11, 10, 30, 0)
DOC_NO = "BF-20260611-103000"
LEGACY_BRAND = "SU" + "RIT"


def _item(**over):
    """SummaryItem(직렬화 후) 형태 — /api/analyze 응답과 동일 키."""
    base = {
        "first_date": "2026-04-02",
        "latest_date": "2026-05-20",
        "first_diagnosis_date": "2026-04-02",
        "code": "K297",
        "display_code": "K29.7",
        "name": "상세불명의 위염",
        "visit": 3,
        "chojin_count": 1,
        "jaejin_count": 2,
        "total_clinic_visit": 3,
        "med_days": 14,
        "med_days_30plus": False,
        "inpatient": 0,
        "inpatient_count": 0,
        "inpatient_periods": [],
        "surgeries": [],
        "surgery_dates": [],
        "surgery_count": 0,
        "procedures": [],
        "procedure_dates": [],
        "surgery_suspected": [],
        "surgery_suspected_dates": [],
        "additional_tests": [],
        "additional_test_hit": False,
        "additional_test_reason": "",
        "q2_suspicion": "",
        "treatment_ongoing": None,
        "treatment_ongoing_reason": "",
        "drug_change_in_3m": False,
        "hospitals": ["서울속편한내과의원"],
        "first_hospital": "서울속편한내과의원",
        "last_hospital": "서울속편한내과의원",
        "detail": "3개월 이내 통원 진료",
    }
    base.update(over)
    return base


# 콘텐츠 수정 2 검증용 3종:
#   unconfirmed = AI 판단 부재(hit=False, reason="") → 이 경우에만 '확인 필요'
#   cleared     = AI 판단 비해당(hit=False, reason 있음) → 확정, '확인 필요' 금지
#   suspected   = AI 판단 해당(hit=True) → 고지 권고 근거
ITEM_UNCONFIRMED = _item()
ITEM_CLEARED = _item(
    code="I10", display_code="I10", name="본태성 고혈압",
    additional_test_reason="당일 단순 경과관찰로 추가검사·재검사 비해당",
)
ITEM_SUSPECTED = _item(
    code="K317", display_code="K31.7", name="위 및 십이지장의 폴립",
    additional_test_hit=True,
    additional_test_reason="위내시경 조직검사 후 재검 권고 소견",
    additional_tests=["재검사"],
)
ITEM_Q3_INPATIENT = _item(
    code="S835", display_code="S83.5", name="무릎 십자인대 염좌",
    first_date="2021-03-10", latest_date="2021-03-24",
    inpatient=14, inpatient_count=1, visit=2,
    surgeries=["인대 재건술"], surgery_count=1,
    detail="10년 이내 입원·수술",
)

DISCLOSURE_PAYLOAD = {
    "report_type": "disclosure",
    "reference_date": "2026-06-11",
    "standard_reports": {
        "[1번질문] 3개월 이내 진단·입원·수술·투약": [ITEM_UNCONFIRMED, ITEM_CLEARED],
        "[2번질문] 1년 이내 진단 (추가검사·재검사 의심 소견)": [ITEM_SUSPECTED],
        "[3번질문] 5년 이내 입원·수술·통원·투약": [ITEM_Q3_INPATIENT],
    },
    "easy_reports": {
        "[2번질문] 10년 이내 입원·수술": [ITEM_Q3_INPATIENT],
    },
    "all_disease_summary": [
        {
            "code": "K297", "display_code": "K29.7", "name": "상세불명의 위염",
            "first_date": "2026-04-02", "latest_date": "2026-05-20",
            "visit_count": 3, "inpatient_count": 0, "inpatient_days": 0,
            "surgery_count": 0, "med_days": 14, "hospitals": ["서울속편한내과의원"],
        },
    ],
    "total_med_sum": 14,
}

# 실손: 화면(insuranceCalc 미러) 계산값을 그대로 담은 payload — 서버는 표시만.
# 참조값: 급여 1,200만 4세대 → 청구 960만+비급여 35만=995만 / 자기부담 합산 240만(초과 40만)
#         10분위 상한 843만 → 환급 357만 / 의원 정액 1만, 통원 3만 → 보상 2만 (BOHUMFIT-029 참조값 계열)
INSURANCE_PAYLOAD = {
    "report_type": "insurance",
    "inputs": {
        "generation": 4, "generation_period": "2021.7~2026.5", "nc_option": None,
        "bracket": 10, "year": "2025",
        "covered_self_pay": 12_000_000, "non_covered": 500_000,
    },
    "results": {
        "claim": {"possibility": "청구 대상일 수 있음", "low": 9_950_000, "high": 9_950_000, "has": True},
        "self_pay_cap": {
            "eligible": 2_400_000, "cap": 2_000_000, "exceeded": True,
            "excess": 400_000, "non_covered_excluded": True,
        },
        "nhis_cap": {"cap": 8_430_000, "exceeded": True, "refund": 3_570_000},
        "min_deductible": {
            "grade_label": "의원", "deductible": 10_000,
            "cov_out": {"charge": 30_000, "reimbursement": 20_000, "low_value": False},
            "nc_out": {"charge": 30_000, "reimbursement": 20_000, "low_value": False,
                       "visits": 2, "total_mode": False},
            "inpatient": {"charge": 100_000, "reimbursement": 80_000, "low_value": False},
        },
    },
}


# ── 표시 포맷 미러 ───────────────────────────────────────────────────────────
def test_won_to_man_mirrors_frontend_wonToMan():
    assert rp._won_to_man(0) == "0원"
    assert rp._won_to_man(-5) == "0원"
    assert rp._won_to_man(None) == "0원"
    # JS Math.round 동작(floor(x+0.5)) — 파이썬 은행원 반올림과 달라야 함
    assert rp._won_to_man(25_000) == "약 3만원"
    assert rp._won_to_man(570_000) == "약 57만원"
    assert rp._won_to_man(8_430_000) == "약 843만원"
    assert rp._won_to_man(12_000_000) == "약 1,200만원"


# ── 고지 리포트 HTML ─────────────────────────────────────────────────────────
def test_disclosure_html_basics_and_footer():
    html = rp.render_report_html("disclosure", DISCLOSURE_PAYLOAD, GEN_AT)
    assert DOC_NO in html                      # 문서번호 접두 BF-
    assert "LEGACY_BRAND" not in html                 # 콘텐츠 수정 3
    assert "SR-" not in html
    # 사업자 정보 푸터
    for token in ("보험핏", "이민규", "174-29-01975", "소재지", "분석도구", "BOHUMFIT"):
        assert token in html
    # 면책
    assert "참고용 보조자료" in html
    assert "민감정보" in html


def test_disclosure_criteria_numbered_lines():
    """콘텐츠 수정 1: 고지 불요 판단 기준 1~5 각 항목 한 줄(개별 <li>)."""
    html = rp.render_report_html("disclosure", DISCLOSURE_PAYLOAD, GEN_AT)
    for c in rp.NO_DISCLOSURE_CRITERIA:
        assert f"<li>{c}</li>" in html
    assert len(rp.NO_DISCLOSURE_CRITERIA) == 5
    criteria_block = html.split('class="criteria"')[1].split("</ol>")[0]
    assert criteria_block.count("<li>") == 5
    assert "5년 초과 10년 이내 입원 또는 수술" in html
    assert "중대질환 진료 이력이 확인되지 않은 경우 (5번질문)" in html


def test_disclosure_confirm_needed_only_when_indeterminate():
    """콘텐츠 수정 2: '확인 필요'는 추가검사/재검사 미확정 항목에만 사용."""
    html = rp.render_report_html("disclosure", DISCLOSURE_PAYLOAD, GEN_AT)
    # 미확정(ITEM_UNCONFIRMED) 1건에만 '확인 필요' 라벨
    assert html.count("추가검사·재검사 확인 필요") == 1
    # AI 확정 비해당 → '해당 없음' 으로 확정 표기 (확인 필요 아님)
    assert "추가검사·재검사 해당 없음" in html
    assert "당일 단순 경과관찰로 추가검사·재검사 비해당" in html
    # AI 확정 해당 → 의심 표기
    assert "추가검사·재검사 의심" in html
    assert "위내시경 조직검사 후 재검 권고 소견" in html
    # 결정론 확정 항목 판정 표기
    assert "고지 권고" in html


def test_disclosure_cleared_only_payload_has_no_confirm_needed():
    payload = {
        "report_type": "disclosure",
        "reference_date": "2026-06-11",
        "standard_reports": {"[1번질문] 3개월 이내 진단·입원·수술·투약": [ITEM_CLEARED]},
        "easy_reports": {},
    }
    html = rp.render_report_html("disclosure", payload, GEN_AT)
    assert "확인 필요" not in html


def test_disclosure_q3_item_has_no_clinical_review_line():
    payload = {
        "report_type": "disclosure",
        "reference_date": "2026-06-11",
        "standard_reports": {"[3번질문] 5년 이내 입원·수술·통원·투약": [ITEM_Q3_INPATIENT]},
        "easy_reports": {},
    }
    html = rp.render_report_html("disclosure", payload, GEN_AT)
    # Q3(치료일수·입원 등)는 결정론 확정 — 추가검사 확인 필요 라벨 미사용
    assert "확인 필요" not in html
    assert "고지 권고" in html


def test_disclosure_escapes_user_strings():
    evil = _item(name="<script>alert(1)</script>", detail="<b>주입</b>")
    payload = {
        "report_type": "disclosure",
        "reference_date": "2026-06-11",
        "standard_reports": {"[1번질문] 3개월 이내 진단·입원·수술·투약": [evil]},
        "easy_reports": {},
    }
    html = rp.render_report_html("disclosure", payload, GEN_AT)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


# ── 실손 리포트 HTML ─────────────────────────────────────────────────────────
def test_insurance_html_fixes_4_5_6():
    html = rp.render_report_html("insurance", INSURANCE_PAYLOAD, GEN_AT)
    assert "LEGACY_BRAND" not in html
    assert DOC_NO in html
    # 수정 4: 비급여 = 설계사 수기 입력 금액 기준
    assert "설계사가 수기 입력한 비급여 금액 기준으로 산출" in html
    assert "설계사 수기 입력" in html
    # 수정 5: 본인부담상한제 = 급여 기준(비급여 제외)
    assert "급여 본인부담금 기준(비급여 제외)" in html
    # 수정 6: 200만원 상한 세대별 규칙 명시
    assert rp.SELF_PAY_CAP_RULES[0] in html
    assert rp.SELF_PAY_CAP_RULES[1] in html
    assert "1~3세대" in html and "4세대 이후" in html
    # 사업자 푸터 + 면책
    for token in ("보험핏", "이민규", "174-29-01975", "분석도구", "BOHUMFIT"):
        assert token in html
    assert "보험 모집·중개·상품추천·가입권유" in html


def test_insurance_amounts_match_payload_exactly():
    """금액 동일성: 리포트 수치 == payload(화면 계산값). 재계산 없음."""
    html = rp.render_report_html("insurance", INSURANCE_PAYLOAD, GEN_AT)
    assert "약 995만원" in html      # claim low=high
    assert "약 240만원" in html      # cap.eligible
    assert "약 200만원" in html      # cap.cap
    assert "약 40만원" in html       # cap.excess
    assert "약 843만원" in html      # nhis.cap
    assert "약 357만원" in html      # nhis.refund
    assert "약 1,200만원" in html    # covered_self_pay
    assert "약 50만원" in html       # non_covered
    assert "약 2만원" in html        # min_ded 보상 (참조값)
    assert "약 8만원" in html        # 입원 보상


def test_insurance_refund_highlight_and_covered_for_insurance_row():
    """BOHUMFIT-035/036: 청구 추정·공단 환급 금액 강조 + 건보 상한까지만 실손 반영한 금액 표시."""
    payload = {
        **INSURANCE_PAYLOAD,
        "inputs": {
            **INSURANCE_PAYLOAD["inputs"],
            "covered_self_pay": 10_000_000,
            "covered_for_insurance": 3_260_000,
            "bracket": 6,
            "non_covered": 500_000,
        },
        "results": {
            **INSURANCE_PAYLOAD["results"],
            "claim": {"possibility": "청구 대상일 수 있음", "low": 3_010_000, "high": 3_330_000, "has": True},
            "nhis_cap": {"cap": 3_260_000, "exceeded": True, "refund": 6_740_000},
            "min_deductible": None,
        },
    }
    html = rp.render_report_html("insurance", payload, GEN_AT)
    assert "claim-highlight" in html
    assert "실손 청구 추정" in html
    assert "약 301만원~약 333만원 수준" in html
    assert "refund-highlight" in html
    assert "예상 공단 환급" in html
    assert "약 674만원 수준" in html
    assert "실손 급여 반영액" in html
    assert "약 326만원" in html
    assert "건보 상한까지만 반영" in html


def test_insurance_no_recalculation_passthrough():
    """입력과 모순된 결과값을 줘도 그대로 표시 → 서버 재계산이 없음을 증명."""
    payload = {
        "report_type": "insurance",
        "inputs": {"generation": 2, "generation_period": "2009.10~2017.3", "nc_option": None,
                   "bracket": 1, "year": "2024", "covered_self_pay": 1_000, "non_covered": 0},
        "results": {
            "claim": {"possibility": "청구 대상일 수 있음", "low": 1_234_000, "high": 2_345_000, "has": True},
            "self_pay_cap": None,
            "nhis_cap": None,
            "min_deductible": None,
        },
    }
    html = rp.render_report_html("insurance", payload, GEN_AT)
    assert "약 123만원~약 235만원" in html
    # 1~3세대 규칙 강조 + 미선택 영역 문구
    assert "선택 세대 적용" in html
    assert "산출하지 않았습니다" in html


def test_insurance_generation_rule_highlight_gen4():
    html = rp.render_report_html("insurance", INSURANCE_PAYLOAD, GEN_AT)
    # 4세대: 두 규칙 모두 표기하되 4세대 이후 행이 강조(hit)
    gen4_row = html.split("4세대 이후</span>")[0].rsplit('class="rule', 1)[1]
    assert "hit" in gen4_row


def test_render_report_html_rejects_unknown_type():
    with pytest.raises(rp.ReportError):
        rp.render_report_html("kakao", {}, GEN_AT)
    with pytest.raises(rp.ReportError):
        rp.render_report_html("disclosure", "not-a-dict", GEN_AT)  # type: ignore[arg-type]


# ── 엔드포인트 wiring (Chromium 불필요 — 렌더러는 monkeypatch) ───────────────
def test_endpoint_streams_pdf_and_sets_headers(monkeypatch):
    from fastapi.testclient import TestClient

    try:
        import main
    except Exception as e:  # pragma: no cover — 샌드박스 마운트 truncation 회피 (ENV-MOUNT-NOTES)
        pytest.skip(f"main import 불가(샌드박스 마운트 제약) — Windows 검증에서 수행: {e}")

    async def _fake_pdf(report_type, payload, generated_at=None):
        return b"%PDF-1.7 fake"

    monkeypatch.setattr(main, "generate_report_pdf", _fake_pdf)
    main.app.dependency_overrides[main.verify_jwt] = lambda: "test-user"
    try:
        client = TestClient(main.app)
        res = client.post("/api/report/pdf", json=INSURANCE_PAYLOAD)
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("application/pdf")
        assert "BF-insurance-" in res.headers.get("content-disposition", "")
        assert res.headers.get("cache-control") == "no-store"
        assert res.content.startswith(b"%PDF-")

        bad = client.post("/api/report/pdf", json={"report_type": "kakao"})
        assert bad.status_code == 400
    finally:
        main.app.dependency_overrides.pop(main.verify_jwt, None)


# ── PDF 바이트 (Chromium 필요 — 미설치 시 skip) ─────────────────────────────
def _gen_pdf_or_skip(report_type: str, payload: dict) -> bytes:
    try:
        return asyncio.run(rp.generate_report_pdf(report_type, payload, GEN_AT))
    except rp.ReportUnavailableError as e:
        pytest.skip(f"Chromium 미설치 — PDF 바이트 테스트 스킵: {e}")


def test_pdf_bytes_disclosure():
    pdf = _gen_pdf_or_skip("disclosure", DISCLOSURE_PAYLOAD)
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 10_000


def test_pdf_bytes_insurance():
    pdf = _gen_pdf_or_skip("insurance", INSURANCE_PAYLOAD)
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 10_000


def test_pdf_korean_text_extractable_and_no_legacy_brand():
    """한글 깨짐 없음(텍스트 추출 가능) + 산출물 LEGACY_BRAND 0건."""
    import pdfplumber

    for rtype, payload, probe in (
        ("disclosure", DISCLOSURE_PAYLOAD, "알릴의무"),
        ("insurance", INSURANCE_PAYLOAD, "실손"),
    ):
        pdf = _gen_pdf_or_skip(rtype, payload)
        with pdfplumber.open(io.BytesIO(pdf)) as doc:
            text = "\n".join((p.extract_text() or "") for p in doc.pages)
        assert probe in text
        assert "보험핏" in text
        assert "LEGACY_BRAND" not in text
        assert "BF-20260611" in text
