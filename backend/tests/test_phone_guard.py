"""BOHUMFIT-088: 휴대폰 번호 중복가입 임시 방어 — 순수 판정 단위 테스트."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phone_guard import is_phone_duplicate_blocked


def test_no_phone_not_blocked():
    # 번호 없음 → 검사 대상 아님
    assert is_phone_duplicate_blocked(phone="", is_internal=False, other_verified_rows=[{"id": "x"}]) is False


def test_internal_bypasses_even_if_duplicate():
    # internal 역할은 중복이어도 우회
    assert (
        is_phone_duplicate_blocked(phone="01012345678", is_internal=True, other_verified_rows=[{"id": "x"}])
        is False
    )


def test_no_duplicate_rows_not_blocked():
    # 동일 번호의 다른 인증 계정 없음 → 통과
    assert is_phone_duplicate_blocked(phone="01012345678", is_internal=False, other_verified_rows=[]) is False
    assert is_phone_duplicate_blocked(phone="01012345678", is_internal=False, other_verified_rows=None) is False


def test_duplicate_rows_blocked():
    # 동일 번호로 이미 인증된 다른 계정 존재 → 차단
    assert (
        is_phone_duplicate_blocked(
            phone="01012345678", is_internal=False, other_verified_rows=[{"id": "other-user"}]
        )
        is True
    )
