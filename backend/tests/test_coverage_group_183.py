from __future__ import annotations

from coverage.aggregator import build_before, build_final
from coverage.constants import EXTRA_PATTERNS, GROUP13


# BOHUMFIT-290(S2): 집계 행이 V2 49행으로 바뀌었다 — 구 이름 조회는 투영 헬퍼로(값·셀 불변).
from tests.v2names import find_row as _find_v2  # noqa: E402
from coverage.v2_mapping import GROUP_APPENDIX_V2 as _APPENDIX  # noqa: E402


def _raw() -> dict:
    return {
        "customer": {"name": None, "age": None, "sex": None},
        "contracts": [{"idx": 1, "monthly_premium": 100_000, "pay_months": 120}],
        "notes": {},
        "matrix": {
            "장기요양간병비": {"by_company": {"1": 10_000_000}},
            "경증치매진단": {"by_company": {"1": 5_000_000}},
            "간병인/간호간병상해일당": {"by_company": {"1": 30_000}},
            "질병입원일당": {"by_company": {"1": 20_000}},
            "골절진단비": {"by_company": {"1": 1_000_000}},
            "보철치료비": {"by_company": {"1": 500_000}},
        },
        "extra": {
            "화상": {"agg": "sum", "by_company": {"1": 2_000_000}},
            "N대수술비": {"agg": "sum", "by_company": {"1": 7_000_000}},
            "상급/종합병원 일당": {"agg": "sum", "by_company": {"1": 100_000}},
            "양성종양·폴립": {"agg": "sum", "by_company": {"1": 3_000_000}},
            "통원일당": {"agg": "sum", "by_company": {"1": 10_000}},
        },
    }


def test_group_order_reorganized_without_old_care_or_fracture_buckets() -> None:
    # BOHUMFIT-246: 비분양식 대분류로 정본화(값 무변경 — 귀속·순서만 교체).
    assert GROUP13 == (
        "사망",
        "후유장해",
        "암",
        "뇌",
        "심장",
        "종수술",
        "수술",
        "의료이용",
        "골절",
        "가입특약(Y/N)",
        "기타",
    )


def test_dementia_is_excluded_from_before_and_final_rendering() -> None:
    before = build_before(_raw())
    final = build_final(before, {})
    names = {row["kb_name"] for row in before["coverages"]}

    # BOHUMFIT-290(S2·Human Q4 확정): 구 제외 2행은 **비고행**으로 보존된다(값이 있을 때만) — 대분류 밖.
    for name in ("장기요양간병비", "경증치매진단"):
        if name in names:
            row = next(r for r in before["coverages"] if r["kb_name"] == name)
            assert row["group12"] == _APPENDIX


def test_care_fracture_and_burn_groups_move_without_amount_change() -> None:
    before = build_before(_raw())
    from tests.v2names import legacy_form_view
    by_name = legacy_form_view(before["coverages"])

    # BOHUMFIT-290(S2): 간병인은 V2 `간 병 인`(입 원·상해 열)로 승격, 보철·화상은 비고행 — 값 불변.
    assert by_name["간병인/간호간병상해일당"]["group12"] == "입 원"
    assert by_name["간병인/간호간병상해일당"]["summary"] == 30_000
    assert by_name["골절진단비"]["group12"] == "골 절"
    assert by_name["골절진단비"]["summary"] == 1_000_000
    assert by_name["보철치료비"]["group12"] == _APPENDIX
    assert by_name["화상"]["group12"] == _APPENDIX
    assert by_name["화상"]["summary"] == 2_000_000


def test_selected_non_standard_riders_stay_in_etc() -> None:
    before = build_before(_raw())
    by_name = {row["kb_name"]: row for row in before["coverages"]}

    # ★296: N대수술비는 정규 행(수 술)으로 이관됐다 — 비고에 남지 않는다.
    for label in ("상급/종합병원 일당", "양성종양·폴립", "통원일당"):
        assert by_name[label]["group12"] == _APPENDIX  # 290: 기타 → 비고
    n_row = next(c for c in before["coverages"] if c.get("row_id") == "major_n_surgery")
    assert n_row["group12"] == "수 술" and n_row["summary"] == 7_000_000  # 단건이므로 max=원값


def test_mojibake_extra_pattern_removed() -> None:
    # BOHUMFIT-234: EXTRA_PATTERNS가 4-튜플(bracket 플래그 추가)로 확장됨.
    assert all(r"\d+企.*呪綬" not in pattern.pattern for pattern, _label, _agg, _bracket in EXTRA_PATTERNS)
