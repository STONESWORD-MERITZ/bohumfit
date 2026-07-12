"""BOHUMFIT-205: 고지 복사문 입원 회차별 표시 회귀 테스트.

기존: 입원 항목이 `최초 진료일 ~ 최종 진료일 / 입원N일` 한 줄로 병합 표기되어
여러 회 입원이 하나의 장기 입원처럼 읽혔다(사용자 건의 — 전십자인대파열 3회 입원 사례).
변경: inpatient_periods 가 있으면 회차별 `개시일 ~ 종료일 / 입원N일` 줄로 각각 표기하고,
2회 이상이면 합산 줄을 덧붙인다. periods 없으면 기존 한 줄 형식 폴백(하위 호환).
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main


EASY_Q2_TITLE = "[2번질문] 10년 이내 입원·수술"


def _item(**overrides):
    base = {
        "first_date": "2022-12-19",
        "latest_date": "2025-08-03",
        "display_code": "S83",
        "code": "S83",
        "name": "전십자인대의 파열",
        "visit": 3,
        "med_days": 0,
        "inpatient": 23,
        "inpatient_periods": [],
        "surgeries": [],
        "surgery_suspected": [],
        "surgery_suspected_grade": "",
        "detail": "10년이내 입원 (23일)",
        "hospitals": ["테스트병원"],
    }
    base.update(overrides)
    return base


def test_kakao_inpatient_periods_listed_individually():
    """3회 입원 → 회차별 3줄(각 개시~종료/일수) + 합산 줄. 병합 한 줄 형식은 사라진다."""
    item = _item(inpatient_periods=[
        {"start": "2024-10-07", "end": "2024-10-15", "days": 9},
        {"start": "2022-12-19", "end": "2022-12-28", "days": 10},
        {"start": "2025-08-03", "end": "2025-08-06", "days": 4},
    ])
    msg = main._build_kakao_message("간편심사", date(2026, 7, 10), {EASY_Q2_TITLE: [item]})

    assert "[입원]" in msg
    # 회차별 줄 — 개시일 순 정렬
    assert "2022-12-19 ~ 2022-12-28 / 입원10일 / S83 / (양방)전십자인대의 파열" in msg
    assert "2024-10-07 ~ 2024-10-15 / 입원9일 / S83 / (양방)전십자인대의 파열" in msg
    assert "2025-08-03 ~ 2025-08-06 / 입원4일 / S83 / (양방)전십자인대의 파열" in msg
    i1 = msg.index("2022-12-19 ~ 2022-12-28")
    i2 = msg.index("2024-10-07 ~ 2024-10-15")
    i3 = msg.index("2025-08-03 ~ 2025-08-06")
    assert i1 < i2 < i3
    # 합산 줄
    assert "입원 총 3회 · 합산 23일" in msg
    # 기존 병합 한 줄(최초 진료일 ~ 최종 진료일 / 입원23일)은 더 이상 없어야 한다.
    assert "2022-12-19 ~ 2025-08-03 / 입원23일" not in msg


def test_kakao_inpatient_single_period_no_total_line():
    """1회 입원은 회차 줄 1개만 — 합산 줄 없음."""
    item = _item(
        inpatient=4,
        detail="10년이내 입원 (4일)",
        inpatient_periods=[{"start": "2023-06-16", "end": "2023-06-19", "days": 4}],
    )
    msg = main._build_kakao_message("간편심사", date(2026, 7, 10), {EASY_Q2_TITLE: [item]})
    assert "2023-06-16 ~ 2023-06-19 / 입원4일 / S83" in msg
    assert "입원 총" not in msg


def test_kakao_inpatient_without_periods_falls_back_to_legacy_line():
    """periods 정보가 없으면 기존 한 줄 형식 유지(하위 호환 — NHIS 등 일부 경로)."""
    item = _item(inpatient=10, inpatient_periods=[])
    msg = main._build_kakao_message("간편심사", date(2026, 7, 10), {EASY_Q2_TITLE: [item]})
    assert "2022-12-19 ~ 2025-08-03 / 입원10일 / S83 / (양방)전십자인대의 파열" in msg


def test_kakao_outpatient_line_unchanged():
    """통원 항목 형식은 불변."""
    item = _item(
        first_date="2025-01-01", latest_date="2025-02-01",
        inpatient=0, inpatient_periods=[], visit=5,
        code="K21", display_code="K21", name="위-식도역류병",
        detail="통원 5회",
    )
    msg = main._build_kakao_message("간편심사", date(2026, 7, 10), {EASY_Q2_TITLE: [item]})
    assert "2025-01-01 ~ 2025-02-01 / 통원5회 / K21 / (양방)위-식도역류병" in msg


def test_kakao_inpatient_same_day_period_shows_single_date():
    """당일 입퇴원(start==end)은 단일 날짜로 표기."""
    item = _item(
        inpatient=1, detail="10년이내 입원 (1일)",
        inpatient_periods=[{"start": "2024-01-30", "end": "2024-01-30", "days": 1}],
    )
    msg = main._build_kakao_message("간편심사", date(2026, 7, 10), {EASY_Q2_TITLE: [item]})
    assert "2024-01-30 / 입원1일 / S83" in msg
    assert "2024-01-30 ~ 2024-01-30" not in msg
