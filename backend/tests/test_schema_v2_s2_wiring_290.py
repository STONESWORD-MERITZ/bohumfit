# -*- coding: utf-8 -*-
"""BOHUMFIT-290(S2) — 49행 V2 스키마 **집계 배선** 계약.

★S1(287)·S1b(289)의 무배선 증명은 이 단계에서 의도적으로 깨지고 아래 배선 증명으로 대체된다.

★고정하는 계약
  ①매핑: 이름 → V2 행(표시명 → 별칭 → 처분). 못 가면 **비고행** — 버리지 않는다
  ②병합: 같은 계약 키의 원천은 행 agg로 합친다(rep=큰 값 → 실손 입원 2행이 이중 계상되지 않는다)
  ③2열 병기: 종수술 5행·간병인은 `columns`(disease/injury/unspecified) — 종별을 잃은 라벨은 unspecified
  ④Q2: 80% 행은 값을 보존하고 `sum_excluded` — `group_rollup_v2`가 대분류 합계에서 뺀다
  ⑤케스케이드: 종합 판정 = 체인 합. 뇌 초기≤중기≤말기 · 심장 초기≤중기 **단조**
  ⑥yn_flags: 항목 5종·값·계약별 Y **불변**(원천만 V2 행으로)
  ⑦분배 규칙은 **아직 배선되지 않는다**(S4)
  ⑧[후]: 제안서 담보(구 이름)도 같은 매핑으로 V2 행에 착지한다(2열 병기는 열별로)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from coverage.aggregator import (
    build_before,
    build_final,
    build_v2_rows,
    compute_stage_totals,
    compute_yn_flags,
    group_rollup_v2,
)
from tests.v2names import legacy_form_view  # 291: 테스트 전용 투영으로 이관
from coverage.compare import build_after_analysis
from coverage.constants import KB_COVERAGES_V2, PAYOUT_CASCADE_V2, YN_ITEMS_V2
from coverage.service import analyze_kb_coverage
from coverage.v2_mapping import (
    ADDITIVE_SOURCE_ROWS_V2,
    COLUMN_DISEASE,
    COLUMN_INJURY,
    COLUMN_UNSPECIFIED,
    GROUP13_V2,
    GROUP_APPENDIX_V2,
    KIND_APPENDIX,
    KIND_ROW,
    resolve,
)

MAN = 10_000
BY_ID = {row.row_id: row for row in KB_COVERAGES_V2}


def _raw(matrix=None, extra=None, contracts=1):
    return {
        "customer": {"name": "테스트", "age": 40, "sex": "여자"},
        "contracts": [
            {"idx": i, "insurer": f"손보{i}", "product": f"상품{i}", "contract_date": "2024-01-01",
             "pay_cycle": "월납", "pay_years": 20, "pay_months": 240, "maturity": "100세",
             "monthly_premium": 10_000 * i}
            for i in range(1, contracts + 1)
        ],
        "matrix": matrix or {}, "diagnosis": {}, "notes": {}, "extra": extra or {}, "warnings": [],
    }


# ── ① 매핑 ────────────────────────────────────────────────────────────────
def test_resolve_display_alias_and_appendix():
    assert resolve("상 해 사 망") == (KIND_ROW, "death_injury", None)
    assert resolve("상해사망") == (KIND_ROW, "death_injury", None)          # 별칭(구 40행)
    assert resolve("80%이상 후유장해") == (KIND_ROW, "disability_80", None)  # extras 라벨
    assert resolve("골절수술비") == (KIND_ROW, "fracture_surgery", None)
    assert resolve("N종수술비(질병 3종)") == (KIND_ROW, "tier_surgery_3", COLUMN_DISEASE)
    assert resolve("N종수술비(상해 3종)") == (KIND_ROW, "tier_surgery_3", COLUMN_INJURY)
    assert resolve("일반종수술 3종(표준환산)") == (KIND_ROW, "tier_surgery_3", COLUMN_UNSPECIFIED)
    assert resolve("간병인/간호간병상해일당") == (KIND_ROW, "caregiver", COLUMN_INJURY)
    assert resolve("화재벌금").kind == KIND_APPENDIX      # Human Q4 부록
    assert resolve("N대수술비(119대)").kind == KIND_APPENDIX  # 미매칭 → 비고(버리지 않는다)


def test_disaster_death_is_an_explicit_additive_source_not_an_alias():
    """Human Q6 ③: 재해사망은 동의어가 아니라 상해사망 행에 더하는 독립 특약이다."""
    assert "재해사망" not in BY_ID["death_injury"].aliases
    assert ADDITIVE_SOURCE_ROWS_V2 == {"재해사망": "death_injury"}
    assert resolve("재해사망") == (KIND_ROW, "death_injury", None)

    rows = build_v2_rows(
        {"상해사망": {"by_company": {"1": 80 * MAN}, "agg": "sum"}},
        {"재해사망": {"by_company": {"1": 20 * MAN}, "agg": "sum"}},
    )
    row = next(c for c in rows if c.get("row_id") == "death_injury")
    assert row["summary"] == 100 * MAN
    assert row["sources"] == {
        "상해사망": {"1": 80 * MAN},
        "재해사망": {"1": 20 * MAN},
    }
    assert all(c.get("kb_name") != "재해사망" for c in rows if not c.get("row_id"))


def test_disaster_death_addition_preserves_246_dedup_total():
    """지급사유 중복분은 먼저 차감하고, 독립 재해사망 특약은 같은 행에 다시 합산한다."""
    raw = _raw(
        matrix={"상해사망": {"by_company": {"1": 100 * MAN}, "agg": "sum"}},
        extra={"재해사망": {
            "agg": "sum",
            "by_company": {"1": 20 * MAN},
            "class_amounts": {"1": {"상해사망": 20 * MAN}},
        }},
    )
    before = build_before(raw, today="2026-08-16")
    row = next(c for c in before["coverages"] if c.get("row_id") == "death_injury")
    assert row["summary"] == 100 * MAN  # 상해 80 + 재해 20 — 구 매트릭스 총액과 동일
    assert before["death_dedup"]["subtracted_total"] == 20 * MAN


def test_unmatched_names_are_kept_as_appendix_rows_not_dropped():
    before = build_before(_raw(extra={"화상진단비": {"agg": "sum", "by_company": {"1": 300 * MAN}}}), today="2026-08-16")
    row = next(c for c in before["coverages"] if c["kb_name"] == "화상진단비")
    assert row["group12"] == GROUP_APPENDIX_V2 and row["summary"] == 300 * MAN and row["enrolled"]


def test_v2_rows_always_present_in_schema_order_then_appendix():
    before = build_before(_raw(), today="2026-08-16")
    ids = [c.get("row_id") for c in before["coverages"] if c.get("row_id")]
    assert ids == [row.row_id for row in KB_COVERAGES_V2]
    assert all(c["group12"] in GROUP13_V2 for c in before["coverages"])


# ── ② 병합 ────────────────────────────────────────────────────────────────
def test_merged_actual_medical_rows_use_rep_not_sum():
    """★실손 입원 2행(상해·질병)이 한 행이 될 때 같은 계약의 5,000만이 두 번 더해지지 않는다."""
    matrix = {
        "상해입원의료비": {"by_company": {"1": 5000 * MAN}, "agg": "rep"},
        "질병입원의료비": {"by_company": {"1": 5000 * MAN}, "agg": "rep"},
    }
    before = build_before(_raw(matrix), today="2026-08-16")
    row = next(c for c in before["coverages"] if c.get("row_id") == "actual_inpatient")
    assert row["agg"] == "rep" and row["summary"] == 5000 * MAN and row["by_company"] == {"1": 5000 * MAN}
    assert set(row["sources"]) == {"상해입원의료비", "질병입원의료비"}


# ── ③ 2열 병기 ────────────────────────────────────────────────────────────
def test_caregiver_dual_columns_keep_injury_and_disease_apart():
    matrix = {
        "간병인/간호간병상해일당": {"by_company": {"2": 32 * MAN}},
        "간병인/간호간병질병일당": {"by_company": {"2": 32 * MAN}},
    }
    before = build_before(_raw(matrix, contracts=2), today="2026-08-16")
    row = next(c for c in before["coverages"] if c.get("row_id") == "caregiver")
    assert row["columns"][COLUMN_INJURY]["summary"] == 32 * MAN
    assert row["columns"][COLUMN_DISEASE]["summary"] == 32 * MAN
    assert row["summary"] == 64 * MAN  # 행 합 = 두 열 합(표시는 S3가 열로 나눈다)


def test_estimated_tier_labels_land_in_unspecified_column():
    """238 환산 라벨은 종별을 잃었다 — 질병/상해를 추측하지 않고 unspecified 열에 둔다."""
    extra = {"일반종수술 3종(표준환산)": {"agg": "sum", "by_company": {"1": 50 * MAN}, "estimated": True}}
    before = build_before(_raw(extra=extra), today="2026-08-16")
    row = next(c for c in before["coverages"] if c.get("row_id") == "tier_surgery_3")
    assert row["columns"][COLUMN_UNSPECIFIED]["summary"] == 50 * MAN
    assert row["columns"][COLUMN_DISEASE]["summary"] is None
    assert row["estimated"] is True


# ── ④ Q2 ──────────────────────────────────────────────────────────────────
def test_group_rollup_excludes_the_80_percent_row_but_keeps_its_value():
    matrix = {"상해후유장해": {"by_company": {"1": 5000 * MAN}}}
    extra = {"80%이상 후유장해": {"agg": "sum", "by_company": {"1": 2000 * MAN}}}
    before = build_before(_raw(matrix, extra), today="2026-08-16")
    row80 = next(c for c in before["coverages"] if c.get("row_id") == "disability_80")
    assert row80["summary"] == 2000 * MAN and row80["sum_excluded"] is True
    assert group_rollup_v2(before["coverages"])["후유장해"] == 5000 * MAN
    assert build_final(before, {})["group_totals"]["후유장해"] == 5000 * MAN


# ── ⑤ 케스케이드 ──────────────────────────────────────────────────────────
def test_stage_totals_follow_cascade_chains_one_to_one():
    matrix = {
        "뇌혈관질환": {"by_company": {"1": 1000 * MAN}},
        "뇌졸중": {"by_company": {"1": 2000 * MAN}},
        "뇌출혈": {"by_company": {"1": 3000 * MAN}},
        "허혈성심장질환": {"by_company": {"1": 4000 * MAN}},
        "급성심근경색": {"by_company": {"1": 5000 * MAN}},
        "심혈관질환": {"by_company": {"1": 7000 * MAN}},   # 독립 — 어느 체인에도 안 들어간다
        "암수술": {"by_company": {"1": 100 * MAN}},
        "표적항암치료": {"by_company": {"1": 300 * MAN}},
    }
    before = build_before(_raw(matrix), today="2026-08-16")
    stages = before["stage_totals"]
    assert len(stages) == len(PAYOUT_CASCADE_V2)  # 블록 행 = 체인 1:1
    assert stages["뇌초기"] == 1000 * MAN
    assert stages["뇌중기"] == 3000 * MAN
    assert stages["뇌말기"] == 6000 * MAN
    assert stages["심장초기"] == 4000 * MAN
    assert stages["심장중기"] == 9000 * MAN            # 심장질환 7,000만은 들어가지 않는다
    assert stages["다빈치(일반암)"] == 100 * MAN         # 암수술 + 다빈치(0)
    assert stages["표적 약물 치료"] == 300 * MAN         # 항암약물(0) + 표적
    assert stages["면역 약물 치료"] == 300 * MAN         # + 면역(0)
    assert "암" not in stages and "심장말기" not in stages


REAL = Path(__file__).resolve().parents[2] / "보장분석" / "비교분석표"


@pytest.mark.parametrize("name", [
    "이인숙-INPUT.pdf",
    "라금실INPUT.pdf",
    "20260805_오현지님_보장분석.pdf",
    "20260729_우O균님_보장분석.pdf",
])
def test_cascade_is_monotonic_on_real_documents(name):
    """★실문서 4건에서 뇌·심장·암 케스케이드가 모두 단조다."""
    path = REAL / name
    if not path.exists():
        pytest.skip("실 PDF 없음(gitignore 폴더)")
    stages = analyze_kb_coverage(path.read_bytes())["before"]["stage_totals"]
    assert stages["뇌초기"] <= stages["뇌중기"] <= stages["뇌말기"]
    assert stages["심장초기"] <= stages["심장중기"]
    assert stages["암 수 술 (레보아이 포함)"] <= stages["다빈치(일반암)"]
    assert stages["유사암 수술"] <= stages["다빈치(갑상선)"]
    assert stages["항암 약물 치료"] <= stages["표적 약물 치료"] <= stages["면역 약물 치료"]
    for sibling in ("세기조절 방사선 치료", "양성자 방사선 치료", "중 입 자 치료"):
        assert stages["방사선 치료"] <= stages[sibling]


# ── ⑥ yn_flags ────────────────────────────────────────────────────────────
def test_yn_flags_keep_items_values_and_per_company_after_wiring():
    matrix = {
        "벌금(대인/스쿨존/대물)": {"by_company": {"1": 300 * MAN, "2": None}},
        "상해입원의료비": {"by_company": {"1": None, "2": 5000 * MAN}, "agg": "rep"},
    }
    before = build_before(_raw(matrix, contracts=2), today="2026-08-16")
    flags = {f["item"]: f for f in before["yn_flags"]}
    assert set(flags) == {item for item, _ in YN_ITEMS_V2}
    assert flags["운전자특약"]["value"] == "Y" and flags["운전자특약"]["by_company"] == {"1": "Y"}
    assert flags["상해실손의료비"]["value"] == "Y" and flags["상해실손의료비"]["by_company"] == {"2": "Y"}
    # ★같은 V2 행(실비)에 합쳐졌지만 질병실손 원천은 없으므로 N — 원천 상세로 구분한다.
    assert flags["질병실손의료비"]["value"] == "N"


# ── ⑦ 분배 규칙 미배선 ────────────────────────────────────────────────────
def test_distribution_source_is_not_split_yet():
    """`암 주요치료비`(분배 대상)는 S4 전까지 값이 있으면 비고행으로만 보존된다."""
    matrix = {"암 주요치료비": {"by_company": {"1": 3000 * MAN}}}
    before = build_before(_raw(matrix), today="2026-08-16")
    row = next(c for c in before["coverages"] if c["kb_name"] == "암 주요치료비")
    assert row["group12"] == GROUP_APPENDIX_V2
    for rid in ("cancer_surgery", "cancer_drug", "cancer_radiation"):
        assert next(c for c in before["coverages"] if c.get("row_id") == rid)["summary"] is None


# ── ⑧ [후] 제안서 착지 ────────────────────────────────────────────────────
def test_proposal_coverages_land_on_v2_rows_including_dual_columns():
    before = build_before(_raw(), today="2026-08-16")
    analysis = {"before": before, "final": build_final(before, {})}
    plan = {"existing": [], "proposals": [{
        "proposal_id": "P1", "insurer": "메리츠화재", "product": "알파Plus", "monthly_premium": 77_470,
        "pay_months": 240,
        "coverages": [
            {"kb_name": "상해사망", "amount": 100 * MAN, "group12": "사망", "agg": "sum"},
            {"kb_name": "N종수술비(질병 5종)", "amount": 400 * MAN, "group12": "수술", "agg": "sum"},
            {"kb_name": "N종수술비(상해 5종)", "amount": 1000 * MAN, "group12": "수술", "agg": "sum"},
            {"kb_name": "듣도보도못한담보", "amount": 7 * MAN, "group12": "기타", "agg": "sum"},
        ],
    }]}
    result = build_after_analysis(analysis, plan)
    after = {c.get("row_id") or c["kb_name"]: c for c in result["after"]["before"]["coverages"]}
    assert after["death_injury"]["by_company"]["P1"] == 100 * MAN
    tier5 = after["tier_surgery_5"]
    assert tier5["columns"][COLUMN_DISEASE]["by_company"]["P1"] == 400 * MAN
    assert tier5["columns"][COLUMN_INJURY]["by_company"]["P1"] == 1000 * MAN
    assert tier5["summary"] == 1400 * MAN
    assert after["듣도보도못한담보"]["group12"] == GROUP_APPENDIX_V2  # 버리지 않는다


# ── 최소 어댑터(export 투영) ─────────────────────────────────────────────
def test_legacy_form_view_projects_v2_rows_onto_old_names():
    matrix = {
        "상해사망": {"by_company": {"1": 100 * MAN}},
        "간병인/간호간병상해일당": {"by_company": {"1": 10 * MAN}},
        "간병인/간호간병질병일당": {"by_company": {"1": 20 * MAN}},
    }
    before = build_before(_raw(matrix), today="2026-08-16")
    view = legacy_form_view(before["coverages"])
    assert view["상해사망"]["summary"] == 100 * MAN and view["상 해 사 망"]["summary"] == 100 * MAN
    assert view["간병인/간호간병상해일당"]["summary"] == 10 * MAN   # injury 열 투영
    assert view["간병인/간호간병질병일당"]["summary"] == 20 * MAN   # disease 열 투영
    assert view["간 병 인"]["summary"] == 30 * MAN
