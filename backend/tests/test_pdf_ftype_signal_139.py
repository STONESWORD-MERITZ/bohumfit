"""BOHUMFIT-139: 헤더·표제어 OCR 누락 시 본문 신호 다수결 타입 판별 회귀."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.pdf_parser import _detect_ftype_by_page_text


def test_headerless_pharma_by_signals():
    """(a) 표제어·'투약일수' 없는 처방조제 본문 → 처방(pharma)."""
    txt = "순번 약품명 성분명 1일 투여횟수 1회투약량\n타이레놀 아세트아미노펜 3 1정"
    assert _detect_ftype_by_page_text(txt) == "pharma"


def test_headerless_basic_by_signals():
    """(b) 표제어 없는 기본진료 본문 → 기본(basic)."""
    txt = "순번 주상병코드 주상병명 입원/외래 진료일수 진료개시일\nM544 요통 외래 1 2024-01-10"
    assert _detect_ftype_by_page_text(txt) == "basic"


def test_headerless_detail_by_signals():
    txt = "순번 진료내역 코드명 초진 재진 처치및수술"
    assert _detect_ftype_by_page_text(txt) == "detail"


def test_section_title_still_takes_precedence():
    """(c) 정상 표제어/전용 컬럼어는 기존 우선 판별 유지."""
    assert _detect_ftype_by_page_text("기본진료정보 표") == "basic"
    assert _detect_ftype_by_page_text("처방조제정보 표") == "pharma"
    assert _detect_ftype_by_page_text("세부진료정보 표") == "detail"
    assert _detect_ftype_by_page_text("...투약일수...") == "pharma"


def test_no_signal_returns_empty():
    assert _detect_ftype_by_page_text("의미 없는 일반 텍스트") == ""
    assert _detect_ftype_by_page_text("") == ""
