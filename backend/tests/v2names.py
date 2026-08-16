# -*- coding: utf-8 -*-
"""BOHUMFIT-290(S2) — 테스트 공용: 구 40행 이름 → V2 행 조회 헬퍼.

★S2에서 [전]/[후] 집계 행이 V2 49행(표시명·row_id)으로 바뀌었다. 구 담보명으로 행을 찾던
  기존 테스트는 **의미(값·계약별 셀·상태)는 그대로 지키되 조회만** 이 헬퍼로 바꾼다.
  `legacy_form_view()`는 export가 쓰는 것과 같은 투영이라, 테스트가 보는 값 = 산출물이 보는 값이다.
"""
from __future__ import annotations

from coverage.aggregator import legacy_form_view
from coverage.constants import KB_COVERAGES_V2, LEGACY_TO_V2

#: 구 이름 → V2 표시명(비고행으로 간 이름은 그대로).
_DISPLAY = {row.row_id: row.display for row in KB_COVERAGES_V2}
V2NAME = {old: _DISPLAY.get(target, old) for old, target in LEGACY_TO_V2.items()}


def v2name(old: str) -> str:
    return V2NAME.get(old, old)


def find_row(coverages: list[dict], name: str) -> dict:
    """구 이름이든 V2 표시명이든 행을 돌려준다(2열 병기 별칭은 열 값으로 투영)."""
    view = legacy_form_view(coverages)
    if name in view:
        return view[name]
    raise KeyError(name)


def has_row(coverages: list[dict], name: str) -> bool:
    return name in legacy_form_view(coverages)
