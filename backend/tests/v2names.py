# -*- coding: utf-8 -*-
"""BOHUMFIT-290(S2) — 테스트 공용: 구 40행 이름 → V2 행 조회 헬퍼.

★S2에서 [전]/[후] 집계 행이 V2 49행(표시명·row_id)으로 바뀌었다. 구 담보명으로 행을 찾던
  기존 테스트는 **의미(값·계약별 셀·상태)는 그대로 지키되 조회만** 이 헬퍼로 바꾼다.
  `legacy_form_view()`는 291부터 **테스트 전용**이다(제품 export는 49행 양식 — 어댑터 제거).
"""
from __future__ import annotations

from coverage.constants import KB_COVERAGES_V2, LEGACY_TO_V2
from coverage.v2_mapping import resolve


# ★BOHUMFIT-291(S3): S2 최소 어댑터였던 `legacy_form_view`를 aggregator에서 제거하고 **테스트 전용 투영**으로 옮겼다.
def legacy_form_view(coverages: list[dict]) -> dict[str, dict]:
    """BOHUMFIT-290 → 291: 테스트 전용 — V2 49행 집계를 구 40행 이름으로 비추는 읽기 전용 투영(제품 코드 참조 0).

    구 이름 → V2 행을 `resolve()`로 찾아 값(by_company·summary)을 돌려준다.
      · 병합된 행(실손 입원 2→1 등)은 **같은 V2 행 값**이 두 셀에 실린다.
      · 2열 병기 행은 별칭이 가리키는 **열 값**을 준다(간병인 상해→injury 열 등).
      · 비고행(구 이름 그대로 보존됨)은 그 행을 그대로 준다.
    ★계산은 하지 않는다.
    """
    by_id = {row.get("row_id"): row for row in coverages if row.get("row_id")}
    by_name = {row.get("kb_name"): row for row in coverages}
    view: dict[str, dict] = {}

    def _project(name: str, row: dict, column: str | None) -> dict:
        projected = {**row, "kb_name": name}
        if column and row.get("columns"):
            cell = row["columns"].get(column) or {}
            projected["by_company"] = dict(cell.get("by_company") or {})
            projected["summary"] = cell.get("summary")
            projected["enrolled"] = any(v is not None for v in projected["by_company"].values())
        return projected

    for row in coverages:
        view[row.get("kb_name")] = row  # V2 표시명·비고 라벨 그대로
    for spec in KB_COVERAGES_V2:
        row = by_id.get(spec.row_id)
        if not row:
            continue
        for alias in spec.aliases:
            if alias in by_name:
                continue  # 같은 이름의 비고행이 있으면 그쪽이 우선(정보 보존)
            target = resolve(alias)
            view.setdefault(alias, _project(alias, row, target.column))
    return view



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
