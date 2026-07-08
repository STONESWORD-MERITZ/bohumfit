from __future__ import annotations

from coverage.aggregator import build_before, build_final
from coverage.constants import EXTRA_LABEL_GROUP, GROUP13, coverage_meta


EXPECTED_GROUP_ORDER_V2 = (
    "사망",
    "후유장해",
    "암",
    "뇌",
    "심장",
    "수술",
    "입원(간병 포함)",
    "운전자",
    "골절",
    "실손",
    "화재",
    "배상책임",
    "기타",
)


def _group(kb_name: str) -> str:
    meta = coverage_meta(kb_name)
    assert meta is not None
    return meta[2]


def _raw() -> dict:
    return {
        "customer": {"name": None, "age": None, "sex": None},
        "contracts": [{"idx": 1, "monthly_premium": 50_000, "pay_months": 240}],
        "notes": {},
        "matrix": {
            "뇌혈관질환": {"by_company": {"1": 10_000_000}},
            "뇌졸중": {"by_company": {"1": 20_000_000}},
            "뇌출혈": {"by_company": {"1": 30_000_000}},
            "허혈성심장질환": {"by_company": {"1": 40_000_000}},
            "급성심근경색증": {"by_company": {"1": 50_000_000}},
            "뇌혈관질환수술비": {"by_company": {"1": 3_000_000}},
            "허혈성심장질환수술비": {"by_company": {"1": 4_000_000}},
            "간병인/간호간병상해일당": {"by_company": {"1": 30_000}},
            "상해입원일당": {"by_company": {"1": 20_000}},
            "골절진단비": {"by_company": {"1": 1_000_000}},
            "보철치료비": {"by_company": {"1": 2_000_000}},
            "상해입원의료비": {"by_company": {"1": 50_000_000}},
        },
        "extra": {"화상": {"agg": "sum", "by_company": {"1": 5_000_000}}},
    }


def test_group_order_v2_matches_customer_report_sequence() -> None:
    assert GROUP13 == EXPECTED_GROUP_ORDER_V2


def test_brain_and_heart_diagnosis_split_while_surgery_stays_in_surgery() -> None:
    assert _group("뇌혈관질환") == "뇌"
    assert _group("뇌졸중") == "뇌"
    assert _group("뇌출혈") == "뇌"
    assert _group("허혈성심장질환") == "심장"
    assert _group("급성심근경색증") == "심장"
    assert _group("뇌혈관질환수술비") == "수술"
    assert _group("허혈성심장질환수술비") == "수술"


def test_fracture_burn_and_inpatient_labels_without_amount_change() -> None:
    before = build_before(_raw())
    by_name = {row["kb_name"]: row for row in before["coverages"]}

    assert by_name["간병인/간호간병상해일당"]["group12"] == "입원(간병 포함)"
    assert by_name["간병인/간호간병상해일당"]["summary"] == 30_000
    assert by_name["상해입원일당"]["group12"] == "입원(간병 포함)"
    assert by_name["상해입원일당"]["summary"] == 20_000
    assert by_name["골절진단비"]["group12"] == "골절"
    assert by_name["골절진단비"]["summary"] == 1_000_000
    assert by_name["보철치료비"]["group12"] == "골절"
    assert by_name["화상"]["group12"] == "골절"
    assert by_name["화상"]["summary"] == 5_000_000
    assert by_name["상해입원의료비"]["group12"] == "실손"
    assert by_name["상해입원의료비"]["summary"] == 50_000_000


def test_final_rollup_uses_group_order_v2() -> None:
    before = build_before(_raw())
    final = build_final(before, {})
    assert [row["group12"] for row in final["rollup_by_group12"]] == list(EXPECTED_GROUP_ORDER_V2)
    assert EXTRA_LABEL_GROUP["화상"] == "골절"
