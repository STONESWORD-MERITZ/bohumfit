from __future__ import annotations

from coverage.aggregator import build_before, build_final
from coverage.constants import EXTRA_PATTERNS, GROUP13


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
    assert GROUP13 == (
        "사망",
        "후유장해",
        "암",
        "뇌/심장",
        "수술",
        "입원일당",
        "실손의료비",
        "상해",
        "운전자",
        "배상책임",
        "화재",
        "기타",
    )


def test_dementia_is_excluded_from_before_and_final_rendering() -> None:
    before = build_before(_raw())
    final = build_final(before, {})
    names = {row["kb_name"] for row in before["coverages"]}

    assert "장기요양간병비" not in names
    assert "경증치매진단" not in names
    assert all(row["kb_name"] not in {"장기요양간병비", "경증치매진단"} for row in final["coverages"])


def test_care_fracture_and_burn_groups_move_without_amount_change() -> None:
    before = build_before(_raw())
    by_name = {row["kb_name"]: row for row in before["coverages"]}

    assert by_name["간병인/간호간병상해일당"]["group12"] == "입원일당"
    assert by_name["간병인/간호간병상해일당"]["summary"] == 30_000
    assert by_name["골절진단비"]["group12"] == "상해"
    assert by_name["골절진단비"]["summary"] == 1_000_000
    assert by_name["보철치료비"]["group12"] == "상해"
    assert by_name["화상"]["group12"] == "상해"
    assert by_name["화상"]["summary"] == 2_000_000


def test_selected_non_standard_riders_stay_in_etc() -> None:
    before = build_before(_raw())
    by_name = {row["kb_name"]: row for row in before["coverages"]}

    for label in ("N대수술비", "상급/종합병원 일당", "양성종양·폴립", "통원일당"):
        assert by_name[label]["group12"] == "기타"


def test_mojibake_extra_pattern_removed() -> None:
    assert all(r"\d+企.*呪綬" not in pattern.pattern for pattern, _label, _agg in EXTRA_PATTERNS)
