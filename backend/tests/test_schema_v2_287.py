# -*- coding: utf-8 -*-
"""BOHUMFIT-287(S1) → BOHUMFIT-289(S1b) — 46행 스키마 V2 정의. ★구 40행과 **병존**하며 아무 데도 배선되지 않는다.

★S1의 성패는 "새 상수가 생겼다"가 아니라 **"제품 동작이 하나도 안 바뀌었다"**다.
  그래서 이 파일의 절반은 V2 계약이고, 절반은 **구 상수가 그대로인지** 지키는 스냅샷이다.

★고정하는 계약
  ①**46행**(289 개정) · 대분류 11 · 행 순서가 수기표 신판과 같다
  ②합계제외는 80% 행에만(Q2·243) · 2열 병기는 종수술 5행에만(Q7)
  ③구 40행 **전 항목**이 V2 어딘가에 대응한다(부록·보류 포함) — 조용히 사라지는 담보가 없다
  ④`row_id`는 고유하고 표시명과 분리돼 있다
  ⑤★구 `KB_COVERAGES`·`GROUP12`·`KB_NAME_ALIASES`가 **바이트 단위로 그대로**다
  ⑥★V2 행명이 수기표 원본과 **문자열 단위로 일치**한다(파일이 있을 때)
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from coverage.constants import (
    APPENDIX_ITEMS_V2,
    GROUP12,
    GROUP12_V2,
    KB_COVERAGES,
    KB_COVERAGES_V2,
    KB_NAME_ALIASES,
    LEGACY_APPENDIX_V2,
    LEGACY_PENDING_V2,
    LEGACY_TO_V2,
    NEW_ROWS_V2,
    PENDING_DISPOSITION_V2,
    STANDARD_COUNT_V2,
    SUM_EXCLUDED_NOTE_V2,
)

# ── ★행명은 289로 이관됐다 ─────────────────────────────────────────────────
#   46행 전문·수기표 대조는 `test_schema_v2_rev46_289.py`가 갖는다(신판 기준).
#   이 파일은 **구 40행 병존 증명**과 행 성격 계약만 남긴다.
# ── ① 골격 ────────────────────────────────────────────────────────────────
def test_row_count_and_order_match_the_manual_tables():
    """★42행·순서까지 수기표와 같다 — 순서가 어긋나면 산출물 행이 밀린다."""
    assert STANDARD_COUNT_V2 == 46  # ★289: 암 7행 → 11행


def test_eleven_groups_in_sheet_order():
    assert GROUP12_V2 == (
        "실 비", "수 술", "암", "뇌", "심 장", "입 원", "사 망", "후유장해",
        "골 절", "배상책임", "운전자",
    )
    assert len(GROUP12_V2) == 11


def test_every_row_belongs_to_a_declared_group_and_groups_are_contiguous():
    """대분류가 흩어져 있으면 병합 셀을 만들 수 없다(S3 전제)."""
    groups = [row.group for row in KB_COVERAGES_V2]
    assert set(groups) == set(GROUP12_V2)
    first_seen = []
    for group in groups:
        if group not in first_seen:
            first_seen.append(group)
    assert tuple(first_seen) == GROUP12_V2, "대분류가 시트 순서대로 연속되지 않는다"


def test_row_ids_are_unique_and_ascii():
    """★`row_id`는 표시명과 분리된 안정 키다 — 표기가 흔들려도 코드가 안 흔들리게."""
    ids = [row.row_id for row in KB_COVERAGES_V2]
    assert len(set(ids)) == 46
    for row_id in ids:
        assert row_id.isascii() and row_id.islower(), row_id


# ── ② 행 성격 플래그 ──────────────────────────────────────────────────────
def test_sum_excluded_is_only_the_80_percent_row():
    """★Q2 + 243: 행은 **보이되 더해지지 않는다**. 다른 행에 번지면 합계가 조용히 줄어든다."""
    excluded = [row.row_id for row in KB_COVERAGES_V2 if row.sum_excluded]
    assert excluded == ["disability_80"]
    row = next(r for r in KB_COVERAGES_V2 if r.row_id == "disability_80")
    assert row.display == "상해 질병 후 유 장 해 80%"
    assert SUM_EXCLUDED_NOTE_V2 == "합계 미포함"


def test_dual_column_is_only_the_five_tier_surgery_rows():
    """★Q7: 질병 | 상해 2열은 종수술 5행 전용이다."""
    dual = [row.row_id for row in KB_COVERAGES_V2 if row.dual_column]
    assert dual == [f"tier_surgery_{tier}" for tier in range(1, 6)]


def test_yn_source_rows_cover_every_legacy_yn_item():
    """★Q5: `yn_flags`는 내부 유지하되 표시는 운전자/배상/실비 행으로 분산된다.

    구 `YN_ITEMS`의 원천 담보가 **하나도 빠짐없이** 어떤 yn_source 행으로 흘러가야 한다.
    """
    from coverage.constants import YN_ITEMS

    yn_rows = {row.row_id for row in KB_COVERAGES_V2 if row.yn_source}
    assert yn_rows == {
        "actual_inpatient", "actual_outpatient", "liability_daily",
        "driver_settlement", "driver_lawyer", "driver_fine", "driver_injury_grade",
    }
    for _label, sources in YN_ITEMS:
        for source in sources:
            assert LEGACY_TO_V2[source] in yn_rows, f"{source}의 Y/N 원천 행이 사라졌다"


# ── ③ 구 40행 → V2 대응 ───────────────────────────────────────────────────
def test_every_legacy_row_has_a_disposition():
    """★조용히 사라지는 담보가 없다 — 40행 전 항목이 대응 행·부록·보류 중 하나를 갖는다."""
    legacy = [name for name, _group, _group12, _agg in KB_COVERAGES]
    assert len(legacy) == 40
    missing = [name for name in legacy if name not in LEGACY_TO_V2]
    assert missing == [], f"대응이 정의되지 않은 구 담보: {missing}"


def test_appendix_holds_exactly_the_confirmed_items():
    """★Q4 + 289: 자리 없는 **6항목**이 부록이다. 임의로 7번째를 끼워 넣지 않는다.

    289에서 `장기요양간병비`·`경증치매진단`이 보류 → 부록으로 확정됐다(Human).
    """
    assert APPENDIX_ITEMS_V2 == (
        "고액암", "3대비급여실손", "보철치료비", "화재벌금",
        "장기요양간병비", "경증치매진단",
    )
    appendix = {name for name, target in LEGACY_TO_V2.items() if target == LEGACY_APPENDIX_V2}
    assert appendix == set(APPENDIX_ITEMS_V2)


def test_pending_is_empty_after_289_resolved_all_three():
    """★287이 남긴 보류 3건이 289에서 전부 해소됐다 — 부록 2 + 분배 1.

    ★빈 튜플을 **유지**하는 것이 계약이다. "보류가 없다"를 코드로 남겨,
      다음에 보류가 생기면 여기에 다시 쌓이게 한다.
    """
    from coverage.constants import DISTRIBUTED_ITEMS_V2, LEGACY_DISTRIBUTED_V2

    assert PENDING_DISPOSITION_V2 == ()
    assert LEGACY_PENDING_V2 not in LEGACY_TO_V2.values()
    # `암 주요치료비`는 부록이 아니라 **분배**로 해소됐다(Human 확정).
    assert DISTRIBUTED_ITEMS_V2 == ("암 주요치료비",)
    assert LEGACY_TO_V2["암 주요치료비"] == LEGACY_DISTRIBUTED_V2


def test_legacy_targets_are_real_rows():
    """대응 값이 실재하는 `row_id`이거나 처리 구분이다(오타 방지)."""
    from coverage.constants import LEGACY_DISTRIBUTED_V2

    ids = {row.row_id for row in KB_COVERAGES_V2}
    markers = (LEGACY_APPENDIX_V2, LEGACY_PENDING_V2, LEGACY_DISTRIBUTED_V2)
    for name, target in LEGACY_TO_V2.items():
        assert target in ids or target in markers, (name, target)


def test_new_rows_are_the_ones_without_a_legacy_source():
    """★S4가 매칭 규칙을 만들어야 할 대상 **16행**(289: 암 분리로 13 → 16).

    판정 기준은 287 그대로 — "구 40행 이름을 하나라도 별칭으로 갖는가"다.
    별칭이 비었는지로 세면 종수술 5행(파서·238 환산 라벨을 가짐)을 놓친다.
    """
    assert len(NEW_ROWS_V2) == 16
    assert set(NEW_ROWS_V2) == {
        "tier_surgery_1", "tier_surgery_2", "tier_surgery_3", "tier_surgery_4", "tier_surgery_5",
        "cancer_surgery_davinci", "cancer_drug", "cancer_radiation",
        "radio_imrt", "radio_proton", "radio_carbon",
        "inpatient_private_room", "death_general", "disability_80",
        "fracture_surgery", "cast_treatment",
    }


def test_merged_rows_gather_both_legacy_sources():
    """★병합 행이 양쪽 원천을 모두 가져간다 — 한쪽만 오면 금액이 반만 남는다.

    ★289: `고액항암치료(표적,면역)` 병합은 **해체**됐다 — 표적·면역이 각자 행을 갖는다.
    """
    by_id = {row.row_id: row for row in KB_COVERAGES_V2}
    assert "cancer_high_cost" not in by_id
    assert by_id["cancer_drug_targeted"].aliases == ("표적항암치료",)
    assert by_id["cancer_drug_immune"].aliases == ("면역항암치료",)
    assert set(by_id["caregiver"].aliases) == {"간병인/간호간병상해일당", "간병인/간호간병질병일당"}
    assert set(by_id["actual_inpatient"].aliases) == {"상해입원의료비", "질병입원의료비"}
    assert set(by_id["actual_outpatient"].aliases) == {"상해통원의료비", "질병통원의료비"}


def test_legacy_spelling_variant_is_kept_as_alias():
    """★289에서 Q3가 **폐기**됐다 — 신판이 구형 표기를 쓰므로 표시/별칭이 뒤집혔다."""
    row = next(r for r in KB_COVERAGES_V2 if r.row_id == "radio_carbon")
    assert row.display == "중 입 자 치료"
    assert "중입자 / 정위 방사선" in row.aliases, "287이 채택했던 표기를 별칭으로 보존해야 한다"


# ── ④ ★병존 증명 — 구 상수 스냅샷 ────────────────────────────────────────
#   S1이 지켜야 할 단 하나의 약속: **구 스키마가 그대로다.** 값이 바뀌면 제품 동작이 바뀐다.
LEGACY_SNAPSHOT = {
    "KB_COVERAGES": "2427cd43adfb4646831df4e968d760347884c0b40018077f730999f9d782a511",
    "GROUP12": "a4645963fd415ef02d90d4de1088ae2d4a571e1dcbb77d391d37aee98c0cc436",
    "KB_NAME_ALIASES": "0a833bdae488029a37dba2277e84eeaa39200dcfb25e8556e0c5f251ca36655f",
}


def _sha(value: object) -> str:
    return hashlib.sha256(repr(value).encode()).hexdigest()


def test_legacy_constants_are_untouched():
    """★S1은 **정의만** 한다. 이 테스트가 깨지면 병존 원칙 위반이니 되돌려야 한다."""
    assert _sha(KB_COVERAGES) == LEGACY_SNAPSHOT["KB_COVERAGES"], "구 40행이 변경됐다"
    assert _sha(GROUP12) == LEGACY_SNAPSHOT["GROUP12"], "구 대분류가 변경됐다"
    assert _sha(sorted(KB_NAME_ALIASES.items())) == LEGACY_SNAPSHOT["KB_NAME_ALIASES"], "별칭 테이블이 변경됐다"
    assert len(KB_COVERAGES) == 40 and len(GROUP12) == 10


def test_v2_is_not_wired_anywhere_yet():
    """★무배선 증명 — 집계·산출물이 V2를 참조하면 S1 범위를 넘은 것이다."""
    root = Path(__file__).resolve().parents[1] / "coverage"
    for name in ("aggregator.py", "export_excel.py", "export_pdf.py"):
        text = (root / name).read_text(encoding="utf-8")
        assert "_V2" not in text, f"{name}이 V2를 참조한다 — S2/S3 범위다"
