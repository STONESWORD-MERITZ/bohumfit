"""BOHUMFIT-128: Q2 추가검사·재검사 확인용(exam_check_only) 항목은 고지 복사(카카오) 텍스트에서 제외."""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import _build_kakao_message

Q2 = "[2번질문] 1년 이내 진단 (추가검사·재검사 의심 소견)"


def _item(code, name, exam=False):
    return {
        "code": code, "name": name, "exam_check_only": exam,
        "visit": 2, "inpatient": 0, "surgeries": [], "surgery_suspected": [],
        "first_date": "2025-05-01", "latest_date": "2025-06-01",
    }


def test_exam_check_only_excluded_general_included():
    """(a)(b) exam_check_only 항목은 복사 텍스트 미포함, 일반 항목은 포함."""
    reports = {Q2: [_item("J30", "알레르기비염", exam=True),
                    _item("K05", "치주염", exam=False)]}
    msg = _build_kakao_message("건강체/표준체 (일반심사)", datetime(2026, 6, 25), reports)
    assert "치주염" in msg, "일반 항목은 복사 텍스트에 포함돼야 함"
    assert "알레르기비염" not in msg, "exam_check_only 항목은 복사 텍스트에서 제외돼야 함"


def test_section_dropped_when_all_exam_only():
    """섹션 전체가 exam_check_only면 해당 질문 헤더도 출력하지 않음."""
    reports = {Q2: [_item("J30", "알레르기비염", exam=True)]}
    msg = _build_kakao_message("건강체/표준체 (일반심사)", datetime(2026, 6, 25), reports)
    assert "알레르기비염" not in msg
    assert "1년 이내 진단" not in msg
