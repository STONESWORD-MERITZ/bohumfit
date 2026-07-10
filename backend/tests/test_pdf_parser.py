"""PDF 파서 — 빈/이미지 PDF 오류 메시지 회귀 테스트.

감사 지적: 정상 복호화됐으나 표가 없는 PDF(이미지 PDF 등)가 "비밀번호 확인"
안내로 잘못 떨어졌다. _empty_result_message 는 원인을 구분하되, 비밀번호
문제로 오인되지 않도록 "비밀번호"를 절대 언급하지 않는다.
"""
import os
import sys
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pipeline.pdf_parser as pdf_parser
from pipeline.pdf_parser import (
    _detect_ftype_by_page_text,
    _empty_result_message,
    _resolve_ftype,
    detect_file_type,
    parse_single_pdf,
)


def test_image_pdf_message_gives_original_download_guidance_not_password():
    """0문자 이미지 PDF는 원본 PDF 저장 경로를 안내하고 비밀번호로 오인시키지 않는다."""
    msg = _empty_result_message("진료내역.pdf", 3, "")
    assert "이미지로 저장된 PDF" in msg
    assert "텍스트가 포함된 원본 PDF" in msg
    assert "정부24 또는 The건강보험(건강보험공단)" in msg
    assert "[PDF 저장/다운로드]" in msg
    assert "인쇄 후 PDF 저장·화면 캡처·사진·스캔본" in msg
    assert "비밀번호" not in msg


def test_format_mismatch_message_not_password():
    """텍스트는 있으나 표 인식 실패 -> 형식 확인 안내, '비밀번호' 미언급."""
    msg = _empty_result_message("기타.pdf", 2, "이건 진료내역이 아닌 일반 문서입니다")
    assert "진료 표" in msg
    assert "비밀번호" not in msg


def test_text_present_does_not_use_image_pdf_guidance():
    """공백 제외 문자가 하나라도 있으면 이미지 PDF 안내로 폴백하지 않는다."""
    msg = _empty_result_message("텍스트.pdf", 2, "\n 건강보험 요양급여내역 \t")
    assert "이미지로 저장된 PDF" not in msg
    assert "인식 가능한 진료 표" in msg


def test_no_pages_message():
    """페이지가 없는 PDF -> 빈 PDF 안내."""
    msg = _empty_result_message("빈파일.pdf", 0, "")
    assert "빈 PDF" in msg
    assert "비밀번호" not in msg


def test_message_always_includes_filename():
    """어떤 파일이 문제인지 알 수 있도록 메시지에 파일명이 포함된다."""
    for n_pages, text in [(0, ""), (3, ""), (3, "텍스트있음")]:
        assert "내검사파일.pdf" in _empty_result_message("내검사파일.pdf", n_pages, text)


# ── BOHUMFIT-002: 처방 PDF 오분류 보정 회귀 테스트 ──────────────────────
#
# 헤더 OCR이 누락·왜곡되면 처방표 헤더가 detail 구조 휴리스틱에만 약하게
# 걸려 진료내역으로 오분류됐다. 보정 후에는 헤더 신호가 약할 때 페이지
# 본문 섹션 신호(_detect_ftype_by_page_text)를 우선하도록 한다.


def test_strong_header_detection_by_keyword():
    """헤더가 _FTYPE_KW 키워드와 명확히 일치하면 해당 타입으로 분류된다."""
    assert detect_file_type(("주상병명", "주상병코드", "내원일수")) == "basic"
    assert detect_file_type(("행위명칭", "수가코드", "급여비총액")) == "detail"
    assert detect_file_type(("약품명", "성분명", "조제일자")) == "pharma"


def test_weak_detail_header_yields_to_pharma_page_text():
    """헤더 OCR 누락으로 처방표 헤더가 detail 휴리스틱에만 걸린 경우,
    본문의 처방 섹션 신호로 'pharma'로 보정되어야 한다."""
    # 약품/처방 키워드가 모두 사라지고 일반 컬럼명만 남은 처방표 헤더
    headers = ("명칭", "코드", "일자", "수량", "금액")
    assert detect_file_type(headers) == "detail"          # 헤더만 보면 오분류
    assert _resolve_ftype(headers, "pharma") == "pharma"  # 본문 신호로 보정


def test_unknown_header_falls_back_to_page_text():
    """헤더가 전혀 인식되지 않으면(unknown) 본문 섹션 신호를 따른다."""
    headers = ("col_0", "col_1")
    assert detect_file_type(headers) == "unknown"
    assert _resolve_ftype(headers, "pharma") == "pharma"


def test_strong_header_wins_over_contradicting_page_text():
    """헤더 OCR이 성공(강신호)하면 본문 신호와 충돌해도 헤더를 신뢰한다."""
    headers = ("약품명", "성분명", "투약일수")
    assert _resolve_ftype(headers, "detail") == "pharma"
    assert _resolve_ftype(headers, "") == "pharma"


def test_pharma_page_text_overrides_strong_detail_header():
    """본문이 처방조제이면 OCR 오염된 detail 강신호보다 pharma를 우선한다."""
    headers = ("행위명칭", "수가코드", "급여비총액")
    assert detect_file_type(headers) == "detail"
    assert _resolve_ftype(headers, "pharma") == "pharma"


def test_pharma_page_text_overrides_strong_basic_header():
    """본문이 처방조제이면 OCR 오염된 basic 강신호보다 pharma를 우선한다."""
    headers = ("주상병명", "주상병코드", "내원일수")
    assert detect_file_type(headers) == "basic"
    assert _resolve_ftype(headers, "pharma") == "pharma"


def test_non_pharma_page_text_does_not_override_headers_or_weak_rules():
    """B안 보정은 pharma 본문 한정이며 detail/basic 일반 우선화는 하지 않는다."""
    assert _resolve_ftype(("약품명", "성분명", "투약일수"), "detail") == "pharma"
    weak_headers = ("명칭", "코드", "일자", "수량", "금액")
    assert _resolve_ftype(weak_headers, "detail") == "detail"
    assert _resolve_ftype(weak_headers, "basic") == "basic"


def test_weak_header_used_when_no_page_signal():
    """본문 신호가 없으면 약한 헤더 추정값이라도 그대로 사용한다."""
    headers = ("명칭", "코드", "일자", "수량", "금액")
    assert _resolve_ftype(headers, "") == "detail"


def test_page_text_detection_tolerates_whitespace():
    """섹션 표제어가 공백·줄바꿈으로 끊겨도 인식된다."""
    assert _detect_ftype_by_page_text("처방 조제 내역서") == "pharma"
    assert _detect_ftype_by_page_text("세부 진료\n정보") == "detail"
    assert _detect_ftype_by_page_text("기본진료정보") == "basic"
    assert _detect_ftype_by_page_text("일반 안내문") == ""


def test_page_text_pharma_signal_by_med_days_when_title_lost():
    """BOHUMFIT-094: 섹션 표제어까지 OCR 누락돼도 처방 전용 컬럼어 '투약일수'면 pharma."""
    # 표제어 없이 표 컬럼어만 남은 처방 페이지 본문
    assert _detect_ftype_by_page_text("약품명 성분명 투약일수 30 조제일자") == "pharma"
    assert _detect_ftype_by_page_text("투약 일수") == "pharma"  # 공백 끊김 허용


def test_section_title_takes_precedence_over_med_days_signal():
    """표제어가 있으면 표제어가 우선 — '투약일수'가 같이 있어도 기본/세부로 유지."""
    assert _detect_ftype_by_page_text("세부진료정보 ... 투약일수") == "detail"
    assert _detect_ftype_by_page_text("기본진료정보 투약일수") == "basic"


def test_unknown_header_with_med_days_page_resolves_pharma():
    """헤더+표제어 모두 누락(unknown)이라도 본문 '투약일수' 신호로 pharma 보정."""
    headers = ("col_0", "col_1", "col_2")
    assert detect_file_type(headers) == "unknown"
    page_ftype = _detect_ftype_by_page_text("약품명 투약일수")
    assert _resolve_ftype(headers, page_ftype) == "pharma"


class _FakePage:
    def __init__(self, text, tables):
        self._text = text
        self._tables = tables
        self.flushed = False

    def extract_text(self):
        return self._text

    def extract_tables(self):
        return self._tables

    def flush_cache(self):
        self.flushed = True


class _FakePdf:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_parse_single_pdf_whitespace_only_uses_image_download_guidance(monkeypatch):
    """공백뿐인 추출 결과만 이미지 PDF 안내 대상이다."""
    pages = [_FakePage(" \n\t ", [])]
    monkeypatch.setattr(pdf_parser, "_open_pdf", lambda data, password: _FakePdf(pages))

    result = parse_single_pdf(BytesIO(b"%PDF-fake"), "")

    assert result["records"] == []
    assert len(result["parse_errors"]) == 1
    assert "이미지로 저장된 PDF" in result["parse_errors"][0]
    assert "[PDF 저장/다운로드]" in result["parse_errors"][0]


def test_parse_single_pdf_text_nhis_keeps_existing_parser_path(monkeypatch):
    """텍스트가 있는 익명 요양급여내역은 기존 NHIS 파서로 정상 분석한다."""
    nhis_text = (
        "건강보험 요양급여내역\n"
        "2020.01.02 1 새봄의원 02-111-2222 100,000\n"
        "1\n"
        "외래 1 익명질환 A00 20,000\n"
    )
    pages = [_FakePage(nhis_text, [])]
    monkeypatch.setattr(pdf_parser, "_open_pdf", lambda data, password: _FakePdf(pages))

    result = parse_single_pdf(BytesIO(b"%PDF-fake"), "")

    assert result["parse_errors"] == []
    assert len(result["records"]) == 1
    assert result["records"][0]["_ftype"] == "nhis"
    assert result["records"][0]["상병코드"] == "A00"


def test_parse_single_pdf_uses_page_local_ftype_for_later_pharma_page(monkeypatch):
    """합본 PDF에서 뒤쪽 처방 페이지는 첫 페이지 basic 신호에 끌리지 않는다."""
    pages = [
        _FakePage("기본진료정보", []),
        _FakePage("처방조제", [
            [
                ["col_0", "col_1"],
                ["2026.05.01", "베포리진정"],
            ]
        ]),
    ]
    monkeypatch.setattr(pdf_parser, "_open_pdf", lambda data, password: _FakePdf(pages))

    result = parse_single_pdf(BytesIO(b"%PDF-fake"), "")

    assert result["parse_errors"] == []
    assert len(result["records"]) == 1
    assert result["records"][0]["_ftype"] == "pharma"
    assert all(page.flushed for page in pages)
