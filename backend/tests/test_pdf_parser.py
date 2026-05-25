"""PDF 파서 — 빈/이미지 PDF 오류 메시지 회귀 테스트.

감사 지적: 정상 복호화됐으나 표가 없는 PDF(이미지 PDF 등)가 "비밀번호 확인"
안내로 잘못 떨어졌다. _empty_result_message 는 원인을 구분하되, 비밀번호
문제로 오인되지 않도록 "비밀번호"를 절대 언급하지 않는다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.pdf_parser import (
    _detect_ftype_by_page_text,
    _empty_result_message,
    _resolve_ftype,
    detect_file_type,
)


def test_image_pdf_message_mentions_image_not_password():
    """텍스트가 없는 PDF -> 이미지 PDF 안내, '비밀번호' 미언급."""
    msg = _empty_result_message("진료내역.pdf", 3, "")
    assert "이미지" in msg
    assert "비밀번호" not in msg


def test_format_mismatch_message_not_password():
    """텍스트는 있으나 표 인식 실패 -> 형식 확인 안내, '비밀번호' 미언급."""
    msg = _empty_result_message("기타.pdf", 2, "이건 진료내역이 아닌 일반 문서입니다")
    assert "진료 표" in msg
    assert "비밀번호" not in msg


def test_no_pages_message():
    """페이지가 없는 PDF -> 빈 PDF 안내."""
    msg = _empty_result_message("빈파일.pdf", 0, "")
    assert "빈 PDF" in msg
    assert "비밀번호" not in msg


def test_message_always_includes_filename():
    """어떤 파일이 문제인지 알 수 있도록 메시지에 파일명이 포함된다."""
    for n_pages, text in [(0, ""), (3, ""), (3, "텍스트있음")]:
        assert "내검사파일.pdf" in _empty_result_message("내검사파일.pdf", n_pages, text)


# ── SURIT-002: 처방 PDF 오분류 보정 회귀 테스트 ──────────────────────
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
