# BOHUMFIT-114: 보장 비교분석 파서 회귀 — 합성(mock) 텍스트만 사용(실 PDF·PII 없음).
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pipeline.coverage_parser as cp
from pipeline.coverage_parser import (
    parse_hanwha_current,
    parse_kb_current,
    parse_proposal_generic,
    parse_coverage_pdf,
    _detect_insurer,
    _extract_premium,
    _extract_coverages,
)

# ── 합성 페이지(가짜 이름 '홍길동' — PII 누수 검증용) ─────────────────────────
CUR_HANWHA = [
    "한화손해보험 보장분석 (담당설계사 : 홍길동 / 2026.06.22 기준)\n월납보험료 합계 105,030 원",
    "한화손해보험 (무)종합보장보험 홍길동 2025/12 20년납 100세만기 월납 55,640 38 1,296",
    "보장내역\n정액 일반암진단비 5,000 일반암\n실손 질병입원 5000 만원\n정액 뇌혈관질환진단비 3,000 뇌혈관질환",
]
CUR_KB = [
    "KB손해보험 보장분석\n월납보험료 합계 72,000 원",
    "KB손해보험 (무)KB건강보험 홍길동 2024/03 30년납 90세만기 월납 72,000 10 500",
    "보장내역\n정액 유사암진단비 1,000 유사암\n정액 상해사망 10,000 상해사망",
]
PROPOSAL_SS = [
    "삼성화재 가입제안서\n월납보험료 89,000 원",
    "정액 일반암진단비 3,000 일반암\n실손 상해입원 5000 만원\n정액 뇌졸중진단비 2,000 뇌졸중",
]


def test_detect_insurer():
    assert _detect_insurer("한화손해보험 보장분석") == "한화손해보험"
    assert _detect_insurer("KB손보 안내") == "KB손해보험"
    assert _detect_insurer("삼성화재 제안서") == "삼성화재"
    assert _detect_insurer("동양생명 ...") == "동양생명"
    assert _detect_insurer("알 수 없는 문서") == "알 수 없음"


def test_extract_premium():
    assert _extract_premium("월납보험료 합계 105,030 원") == 105030
    assert _extract_premium("월 보험료 89,000") == 89000
    assert _extract_premium("보험료 정보 없음") == 0


def test_extract_coverages_clean_and_no_noise():
    text = "\n".join([
        "메리츠화재 홍길동 2025/12 100세만기 월납 55,640",  # 회사+날짜 → 제외
        "정액 일반암진단비 5,000 일반암",                    # 담보 → 포함
        "실손 질병입원 5000 만원",                            # 담보 → 포함
        "보험계약정보 회사명 상품명 계약자",                  # 헤더 → 제외
    ])
    covs = _extract_coverages(text)
    names = [c["name"] for c in covs]
    assert "일반암진단비" in names and "질병입원" in names
    # 연도형 금액·회사명·이름 라인은 담보로 잡히지 않는다.
    blob = str(covs)
    assert "홍길동" not in blob and "2025" not in str([c["amount"] for c in covs])


def test_hanwha_current_no_pii_leak():
    r = parse_hanwha_current(CUR_HANWHA)
    assert r["insurer"] == "한화손해보험" and r["doc_type"] == "current"
    assert len(r["contracts"]) >= 1
    c = r["contracts"][0]
    assert c["monthly_premium"] == 55640 and c["coverage_end"] == "100세만기"
    # ★ 계약자 성명(PII)이 어떤 필드에도 들어가면 안 된다.
    import json
    assert "홍길동" not in json.dumps(r, ensure_ascii=False)
    assert any(cov["name"] == "일반암진단비" for cov in c["coverages"])


def test_kb_current_basic():
    r = parse_kb_current(CUR_KB)
    assert r["insurer"] == "KB손해보험"
    assert r["contracts"] and r["contracts"][0]["monthly_premium"] == 72000
    import json
    assert "홍길동" not in json.dumps(r, ensure_ascii=False)


def test_proposal_generic():
    r = parse_proposal_generic(PROPOSAL_SS)
    assert r["insurer"] == "삼성화재" and r["doc_type"] == "proposal"
    assert r["summary"]["total_monthly_premium"] == 89000
    names = [c["name"] for c in r["contracts"][0]["coverages"]]
    assert "일반암진단비" in names and "상해입원" in names


def test_parse_coverage_pdf_routes_current(monkeypatch):
    monkeypatch.setattr(cp, "_pages_text", lambda b: CUR_HANWHA)
    r = parse_coverage_pdf(b"%PDF-fake", "current")
    assert r["doc_type"] == "current" and r["insurer"] == "한화손해보험"


def test_parse_coverage_pdf_routes_proposal(monkeypatch):
    monkeypatch.setattr(cp, "_pages_text", lambda b: PROPOSAL_SS)
    r = parse_coverage_pdf(b"%PDF-fake", "proposal")
    assert r["doc_type"] == "proposal" and r["summary"]["total_monthly_premium"] == 89000


def test_parse_coverage_pdf_empty_or_image(monkeypatch):
    monkeypatch.setattr(cp, "_pages_text", lambda b: ["", ""])  # 텍스트 없음(이미지 PDF)
    r = parse_coverage_pdf(b"%PDF-img", "current")
    assert r["contracts"] == [] and r["parse_warnings"]
    assert any("이미지" in w for w in r["parse_warnings"])


def test_parse_warnings_recorded_for_unknown_proposal(monkeypatch):
    monkeypatch.setattr(cp, "_pages_text", lambda b: ["내용 없는 문서"])
    r = parse_coverage_pdf(b"%PDF", "proposal")
    assert r["insurer"] == "알 수 없음"
    assert any("감지 실패" in w or "추출하지 못" in w for w in r["parse_warnings"])
