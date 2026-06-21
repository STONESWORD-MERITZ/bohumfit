import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main


Q1_TITLE = "[1번질문] 3개월 이내 진단·입원·수술·투약"
Q2_TITLE = "[2번질문] 1년 이내 진단 (추가검사·재검사 의심 소견)"
Q3_TITLE = "[3번질문] 5년 이내 입원·수술·통원·투약"
Q4_TITLE = "[4번질문] 5년 초과 10년 이내 입원·수술"


def _item(**overrides):
    base = {
        "first_date": "2025-01-01",
        "latest_date": "2025-01-01",
        "display_code": "K21",
        "code": "K21",
        "name": "테스트질환",
        "visit": 1,
        "med_days": 0,
        "inpatient": 0,
        "surgeries": [],
        "surgery_suspected": [],
        "surgery_suspected_grade": "",
        "detail": "테스트 근거",
        "hospitals": ["테스트병원"],
    }
    base.update(overrides)
    return base


def test_kakao_message_includes_q4_5_to_10_inpatient_and_surgery_suspected():
    reports = {
        Q4_TITLE: [
            _item(
                first_date="2018-03-01",
                latest_date="2018-03-06",
                display_code="M51",
                code="M51",
                name="추간판장애",
                inpatient=6,
                detail="5년 초과 10년 이내 입원 확인",
            ),
            _item(
                first_date="2019-04-10",
                latest_date="2019-04-10",
                display_code="K60",
                code="K60",
                name="항문열구",
                surgery_suspected=["관혈적정복술"],
                surgery_suspected_grade="강",
                detail="5년 초과 10년 이내 수술 의심",
            ),
            _item(
                first_date="2020-02-02",
                latest_date="2020-02-02",
                display_code="S72",
                code="S72",
                name="대퇴골골절",
                surgeries=["골절정복술"],
            ),
        ]
    }

    msg = main._build_kakao_message("건강체", date(2026, 6, 21), reports)

    assert "5년 초과 10년 이내 입원·수술" in msg
    assert "M51" in msg and "추간판장애" in msg
    assert "K60" in msg and "항문열구" in msg
    assert "수술 의심: 관혈적정복술 (강)" in msg
    assert "S72" in msg and "골절정복술" in msg
    assert msg.index("[입원]") < msg.index("M51")
    assert msg.index("[수술]") < msg.index("K60")
    assert msg.index("[수술]") < msg.index("S72")
    assert "[통원]" not in msg


def test_kakao_message_keeps_q4_inpatient_item_surgery_suspicion_detail():
    reports = {
        Q4_TITLE: [
            _item(
                first_date="2019-03-10",
                latest_date="2019-03-15",
                display_code="M51",
                code="M51",
                name="추간판장애",
                inpatient=5,
                surgery_suspected=["척추수술"],
                surgery_suspected_grade="약",
            )
        ]
    }

    msg = main._build_kakao_message("건강체", date(2026, 6, 21), reports)

    assert "M51" in msg
    assert "수술 의심: 척추수술 (약)" in msg
    assert msg.index("[입원]") < msg.index("M51")


def test_kakao_message_keeps_existing_q1_q2_q3_window_sections():
    reports = {
        Q3_TITLE: [
            _item(
                first_date="2023-05-01",
                latest_date="2023-05-01",
                display_code="N76",
                code="N76",
                name="질염",
                visit=7,
                med_days=31,
                detail="5년 이내 통원·투약",
            )
        ],
        Q1_TITLE: [
            _item(
                first_date="2026-05-15",
                latest_date="2026-05-15",
                display_code="K21",
                code="K21",
                name="역류성식도염",
                detail="3개월 이내 진단",
            )
        ],
        Q2_TITLE: [
            _item(
                first_date="2026-01-20",
                latest_date="2026-01-20",
                display_code="R51",
                code="R51",
                name="두통",
                detail="1년 이내 추가검사 의심",
            )
        ],
    }

    msg = main._build_kakao_message("건강체", date(2026, 6, 21), reports)

    assert msg.index("3개월 이내 진단·입원·수술·투약") < msg.index("1년 이내 진단")
    assert msg.index("1년 이내 진단") < msg.index("5년 이내 입원·수술·통원·투약")
    assert "K21" in msg and "역류성식도염" in msg
    assert "R51" in msg and "두통" in msg
    assert "N76" in msg and "질염" in msg
