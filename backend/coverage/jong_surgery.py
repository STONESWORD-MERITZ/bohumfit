"""BOHUMFIT-238: 종수술비 5종 기준 → 1~5종 표준 환산 룩업.

원문에 종별 금액 없이 "5종 기준 최대금액"만 있는 종수술비 담보에 적용한다.
표는 상품별로 정확하지 않은 "표준 환산 기준"이므로 산출값에는 항상 구분 표시와
문구("표준 환산 기준 — 상품별 실제와 상이할 수 있음")를 병기한다.

룩업표 원천: Supabase `jong_surgery_conversion` 테이블(Human이 수정 가능 —
supabase/manual/BOHUMFIT-238-01-jong-surgery-table.sql로 시딩). DB 미존재·조회 실패
시 아래 내장 기본표로 fallback(배포↔SQL 실행 순서 안전망 — 237-A식).
★내장표는 시딩 SQL의 값과 동일해야 한다(테스트 test_fallback_matches_sql_seed가 고정).
"""
from __future__ import annotations

import re

MAN = 10_000

# Human 판독 검증 완료 확정표(2026-07-21) — {5종 기준(만원): (1종, 2종, 3종, 4종, 5종)(만원)}
DEFAULT_JONG_TABLE: dict[int, tuple[int, int, int, int, int]] = {
    100: (5, 10, 15, 50, 100),
    200: (5, 10, 15, 50, 200),
    300: (10, 30, 50, 100, 300),
    400: (10, 30, 50, 100, 400),
    500: (10, 30, 50, 100, 500),
    600: (20, 30, 40, 150, 600),
    700: (20, 30, 40, 150, 700),
    800: (20, 50, 100, 500, 800),
    900: (20, 50, 100, 500, 900),
    1000: (20, 50, 100, 500, 1000),
}

# 종별 명시 마커 — "…_1종", "(1종," / "(3종)" 형태(원문 종별 금액이 이미 있는 분리형).
# "질병1~5종수술"의 범위 표기나 "(5종수술)" 기준 표기는 마커가 아니다(237-F 실측).
_TIER_MARKER_RE = re.compile(r"_[1-5]종|\([1-5]종[,)]")


def has_explicit_tier(compact_name: str) -> bool:
    """담보명(공백 제거)에 종별 마커가 있으면 True — 환산 미적용(원문 우선)."""
    return bool(_TIER_MARKER_RE.search(compact_name or ""))


def lookup_jong_tiers(base_won, table: dict | None = None):
    """5종 기준액(원) → {1: 원, …, 5: 원}. 표 외(100만원 미만)·무효 입력은 None.

    표에 없는 기준액은 "이하 최대값" 행으로 룩업(예: 750만 → 700행, 1,500만 → 1,000행).
    """
    tbl = table or DEFAULT_JONG_TABLE
    if not base_won or base_won < 100 * MAN:
        return None
    base_man = int(base_won) // MAN
    floors = [k for k in tbl if k <= base_man]
    if not floors:
        return None
    tiers = tbl[max(floors)]
    return {index + 1: tier * MAN for index, tier in enumerate(tiers)}


def estimated_tier_label(tier: int) -> str:
    """환산 산출 행의 표시명 — '표준환산' 구분을 이름에 고정(렌더러 무수정 반영)."""
    return f"종수술비({tier}종·표준환산)"


OUT_OF_RANGE_LABEL = "종수술비(표 외)"
