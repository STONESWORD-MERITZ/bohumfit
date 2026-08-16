# -*- coding: utf-8 -*-
"""BOHUMFIT-290(S2) — 담보명 → 49행 V2 row 매핑 함수 (★V2가 처음으로 실계산에 물리는 지점).

★역할: 파서가 내놓는 이름(구 40행 kb_name · extras 라벨 · 가입제안서 kb_name)을
  V2 `row_id`로 보낸다. 표시명 일치 → 별칭 일치 → 명시적 합산 원천 → 처분(부록/분배) 순으로 본다.
  ★어디에도 못 가는 이름은 **버리지 않고 비고행**으로 보낸다(패킷 Step 2 원칙).

★2열 병기 행(종수술 5·간병인)은 별칭이 어느 열인지도 알려준다. 종별을 잃은 이름
  (238 환산 라벨 `일반종수술 N종(표준환산)`)은 **`unspecified` 열**로 둔다 — 질병/상해를
  추측해서 넣지 않는다(S3 표시·S4 파서 개선에서 해소).

★S4 범위(여기서 하지 않는 것): 분배 규칙 배선(`DISTRIBUTION_RULES_V2`) · 합쳐진 extras
  라벨의 분리(`항암약물방사선`→약물/방사선, `심·뇌혈관수술비`→뇌/심) — 이름만으로 갈라지지
  않는 것은 비고행으로 보내고 기록만 한다.
"""
from __future__ import annotations

from typing import NamedTuple

from .constants import (
    AGG_REP,
    AGG_SUM,
    APPENDIX_ITEMS_V2,
    DISTRIBUTED_ITEMS_V2,
    KB_COVERAGES,
    KB_COVERAGES_V2,
    CoverageRowV2,
)

#: 비고행(부록) 그룹명 — V2 대분류 11개 뒤에 붙는 표시 그룹.
GROUP_APPENDIX_V2 = "비고"
GROUP13_V2: tuple[str, ...] = tuple(dict.fromkeys(row.group for row in KB_COVERAGES_V2)) + (GROUP_APPENDIX_V2,)

COLUMN_DISEASE = "disease"
COLUMN_INJURY = "injury"
COLUMN_UNSPECIFIED = "unspecified"
DUAL_COLUMNS: tuple[str, ...] = (COLUMN_DISEASE, COLUMN_INJURY, COLUMN_UNSPECIFIED)

#: 2열 병기 행의 별칭 → 열. 목록에 없는 별칭은 `unspecified`.
_DUAL_COLUMN_OF_ALIAS: dict[str, str] = {
    "간병인/간호간병질병일당": COLUMN_DISEASE,
    "간병인/간호간병상해일당": COLUMN_INJURY,
}
for _tier in range(1, 6):
    _DUAL_COLUMN_OF_ALIAS[f"N종수술비(질병 {_tier}종)"] = COLUMN_DISEASE
    _DUAL_COLUMN_OF_ALIAS[f"N종수술비(상해 {_tier}종)"] = COLUMN_INJURY
    # 238 환산 라벨은 종별을 잃었다 → unspecified(추측 금지).

KIND_ROW = "row"
KIND_APPENDIX = "appendix"
KIND_DISTRIBUTED = "distributed"


class Target(NamedTuple):
    kind: str
    row_id: str | None
    column: str | None  # 2열 병기 행일 때만


ROWS_BY_ID: dict[str, CoverageRowV2] = {row.row_id: row for row in KB_COVERAGES_V2}
ROW_INDEX: dict[str, int] = {row.row_id: idx for idx, row in enumerate(KB_COVERAGES_V2)}

_BY_DISPLAY: dict[str, str] = {row.display: row.row_id for row in KB_COVERAGES_V2}
_BY_ALIAS: dict[str, str] = {}
for _row in KB_COVERAGES_V2:
    for _alias in _row.aliases:
        # 별칭 충돌은 정의 오류다 — 첫 등록을 지키고 테스트가 잡는다.
        _BY_ALIAS.setdefault(_alias, _row.row_id)

#: BOHUMFIT-290 Human Q6 ③: 별칭(동일 담보명)이 아니라 **독립 특약의 합산 원천**이다.
#:   `재해사망` 금액은 `상해사망` 원천과 함께 `death_injury` 행의 AGG_SUM을 타되,
#:   원천 상세(`sources`)는 두 이름을 분리 보존한다. `(계약 미확인)`은 여기에 없으므로
#:   근거 없는 귀속을 만들지 않고 계속 비고행에 남는다.
ADDITIVE_SOURCE_ROWS_V2: dict[str, str] = {
    "재해사망": "death_injury",
}

#: 구 40행의 agg — V2 행 agg를 유도하는 근거(별칭 중 하나라도 rep이면 rep).
_LEGACY_AGG: dict[str, str] = {name: agg for name, _g, _g12, agg in KB_COVERAGES}


def row_agg(row: CoverageRowV2) -> str:
    """V2 행의 집계 규칙. ★실손·배상 계열(구 rep)은 그대로 rep, 그 외·신설은 sum."""
    if any(_LEGACY_AGG.get(alias) == AGG_REP for alias in row.aliases):
        return AGG_REP
    return AGG_SUM


ROW_AGG: dict[str, str] = {row.row_id: row_agg(row) for row in KB_COVERAGES_V2}


def resolve(name: str | None) -> Target:
    """이름 하나를 V2 목적지로 보낸다. 못 가면 비고행(APPENDIX)."""
    if not name:
        return Target(KIND_APPENDIX, None, None)
    row_id = _BY_DISPLAY.get(name) or _BY_ALIAS.get(name) or ADDITIVE_SOURCE_ROWS_V2.get(name)
    if row_id:
        row = ROWS_BY_ID[row_id]
        column = None
        if row.dual_column:
            column = _DUAL_COLUMN_OF_ALIAS.get(name, COLUMN_UNSPECIFIED)
        return Target(KIND_ROW, row_id, column)
    if name in DISTRIBUTED_ITEMS_V2:
        return Target(KIND_DISTRIBUTED, None, None)
    # APPENDIX_ITEMS_V2 든 아니든 — 자리가 없으면 비고행. 이름은 그대로 보존한다.
    _ = APPENDIX_ITEMS_V2
    return Target(KIND_APPENDIX, None, None)


def combine(current, value, agg: str):
    """같은 계약 키에 두 원천이 겹칠 때 — sum은 더하고 rep은 큰 값. None은 무시."""
    if value is None:
        return current
    if current is None:
        return value
    return current + value if agg == AGG_SUM else max(current, value)


def display_of(row_id: str) -> str:
    return ROWS_BY_ID[row_id].display
