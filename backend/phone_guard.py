"""BOHUMFIT-088: 휴대폰 번호 중복가입 임시 방어 — 순수 판정 헬퍼.

실본인확인(087·CI 기반) 연동 전 단계의 임시방편이다.
사용자가 번호를 직접 입력하는 스텁 구조라 "다른 번호 입력"으로는 우회 가능하며,
본 헬퍼는 오직 "동일 번호 재사용(같은 phone·phone_verified=true·다른 user)"만 차단한다.

main.py(FastAPI)와 분리해 둠으로써 무거운 의존성 없이 단위 테스트가 가능하다.
"""

from typing import Sequence, Any


def is_phone_duplicate_blocked(
    *,
    phone: str,
    is_internal: bool,
    other_verified_rows: Sequence[Any] | None,
) -> bool:
    """동일 휴대폰번호 중복가입을 막아야 하면 True.

    - phone 이 비어 있으면 검사 대상 아님 → False
    - internal 역할은 우회(정책 일관) → False
    - 같은 번호로 phone_verified=true 인 "다른 user" 행이 있으면 → True
    - 없으면 → False

    other_verified_rows: 동일 phone·phone_verified=true·현재 user 제외 조회 결과(list/None).
    """
    if not phone or is_internal:
        return False
    return bool(other_verified_rows)
