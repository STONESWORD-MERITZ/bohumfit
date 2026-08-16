from __future__ import annotations

from coverage.aggregator import build_before, build_final
from coverage.constants import EXTRA_LABEL_GROUP, GROUP13, coverage_meta


# BOHUMFIT-246: 비분양식 대분류로 정본화 — 189 당시 v2 순서를 대체(값 무변경·귀속만 교체).
EXPECTED_GROUP_ORDER_V2 = (
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


# BOHUMFIT-290(S2): 집계 행이 V2 49행으로 바뀌었다 — 구 이름 조회는 투영 헬퍼로(값·셀 불변).
from tests.v2names import find_row as _find_v2  # noqa: E402
from coverage.v2_mapping import GROUP_APPENDIX_V2 as _APPENDIX  # noqa: E402


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
            # BOHUMFIT-246: 합성 matrix 키는 파서가 별칭으로 산출하는 정식명 기준.
            "뇌혈관수술": {"by_company": {"1": 3_000_000}},
            "심혈관수술": {"by_company": {"1": 4_000_000}},
            "간병인/간호간병상해일당": {"by_company": {"1": 30_000}},
            "상해입원": {"by_company": {"1": 20_000}},
            "골절진단비": {"by_company": {"1": 1_000_000}},
            "보철치료비": {"by_company": {"1": 2_000_000}},
            "상해입원의료비": {"by_company": {"1": 50_000_000}},
        },
        "extra": {"화상": {"agg": "sum", "by_company": {"1": 5_000_000}}},
    }


def test_group_order_v2_matches_customer_report_sequence() -> None:
    assert GROUP13 == EXPECTED_GROUP_ORDER_V2


def test_brain_and_heart_diagnosis_split_while_surgery_stays_in_surgery() -> None:
    # BOHUMFIT-246: 부위 수술은 해당 부위 그룹으로 이동(뇌혈관수술→뇌, 심혈관수술→심장 —
    #   비분양식 24~31행). 구명칭 조회는 별칭으로 동작(파서 경로 동일).
    assert _group("뇌혈관질환") == "뇌"
    assert _group("뇌졸중") == "뇌"
    assert _group("뇌출혈") == "뇌"
    assert _group("허혈성심장질환") == "심장"
    assert _group("급성심근경색증") == "심장"
    assert _group("뇌혈관질환수술비") == "뇌"
    assert _group("허혈성심장질환수술비") == "심장"


def test_fracture_burn_and_inpatient_labels_without_amount_change() -> None:
    before = build_before(_raw())
    from tests.v2names import legacy_form_view
    by_name = legacy_form_view(before["coverages"])

    # BOHUMFIT-290(S2): 귀속이 V2 대분류로 이동 — 값 전부 불변(246과 같은 원칙).
    #   간병인→입 원(상해 열) · 상해입원→입 원 · 골절진단비→골 절 · 보철·화상→비고 ·
    #   상해입원의료비→실 비(yn_source 행 — 구 가입특약(Y/N) 그룹은 소멸, 플래그는 yn_flags에 유지).
    assert by_name["간병인/간호간병상해일당"]["group12"] == "입 원"
    assert by_name["간병인/간호간병상해일당"]["summary"] == 30_000
    assert by_name["상해입원"]["group12"] == "입 원"
    assert by_name["상해입원"]["summary"] == 20_000
    assert by_name["골절진단비"]["group12"] == "골 절"
    assert by_name["골절진단비"]["summary"] == 1_000_000
    assert by_name["보철치료비"]["group12"] == _APPENDIX
    assert by_name["화상"]["group12"] == _APPENDIX
    assert by_name["화상"]["summary"] == 5_000_000
    assert by_name["상해입원의료비"]["group12"] == "실 비"
    assert by_name["상해입원의료비"]["summary"] == 50_000_000


def test_final_rollup_uses_group_order_v2() -> None:
    before = build_before(_raw())
    final = build_final(before, {})
    # BOHUMFIT-290(S2): 롤업 순서 = V2 대분류 11 + 비고.
    from coverage.v2_mapping import GROUP13_V2
    assert [row["group12"] for row in final["rollup_by_group12"]] == list(GROUP13_V2)
    assert "화상" not in EXTRA_LABEL_GROUP  # 246: 화상은 기타 기본값(귀속 해제)
