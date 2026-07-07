# -*- coding: utf-8 -*-
"""BOHUMFIT-179 KB 보장분석 제안서 파서 회귀 테스트.

★PII: 픽스처는 실 PDF가 아니라 178 명세 기준 '익명 합성' 텍스트(성명 '홍길동').
   금액 구조는 문건주 자료의 검증 목표값(573,227 등)을 재현하되 성명은 익명화.
   실 PDF·엑셀은 절대 저장/커밋하지 않는다(A방식: Codex 로컬 실 PDF 보정).
"""
from coverage.amount import parse_amount
from coverage.constants import KB_COVERAGES, GROUP12, AGG_SUM, AGG_REP, STANDARD_COUNT
from coverage.aggregator import _aggregate, build_before, build_final
from coverage.parser import (
    parse_contract_list, parse_matrix, parse_diagnosis, parse_document, KBFormatError,
)

# ── p5 계약리스트(익명) — CONTRACT_LINE_RE 매칭 라인 ──────────────────────────
P5_LINES = """홍길동 (33세 ,남자) 님의 전체 계약리스트   ※ 기준담보/권장금액 : 기본형(37개)/표준형
                                        6                                       573,227
    2          3            1               0
1       KB손보   KB 플러스 운전자상해보험(무배당)(23.11)          2023-11-15   월납    20년      51세         10,000원
2       KB손보   KB Yes!365 건강보험(세만기)(무배당)(23.11)      2023-11-15   월납    25년      90세        101,463원
3       한화손보  한화 3N5 더간편건강보험(세만기형) 무배당           2025-04-18   월납    20년     100세         35,535원
4       삼성화재  무배당 삼성화재 건강보험 새시대건강파트너(1204.5)   2012-05-25   월납    81년     100세         82,249원
5       삼성화재  무배당 삼성화재 건강보험 마이헬스파트너(2402.9)     2024-02-07   월납     5년     100세         10,380원
6       삼성생명  퍼펙트통합보험Ⅰ3.0(無)_표준체                  2013-12-29   월납    15년      종신        333,600원
""".split("\n")

# ── p6 상품별 가입현황(계약 1~4) 익명 ────────────────────────────────────────
P6_LINES = """홍길동 (33세 ,남자) 님의 상품별 가입현황
       상해사망               5억 5,000만                         -                    2억                         -          1억 4,000만
사망     질병사망               1억 3,000만                         -                       -                       -              3,000만
장해     상해80%미만후유장해        4억 1,600만                         -            1억 100만                            -          1억 4,000만
       질병80%미만후유장해                 -                        -                       -                       -                       -
       장기요양간병비                     -                        -                       -                       -                       -
치매     경증치매진단                      -                        -                       -                       -                       -
간병     간병인/간호간병상해일당             27만                         -                       -                  27만                          -
       간병인/간호간병질병일당             27만                         -                       -                  27만                          -
       일반암                       1억                         -              2,000만                           -              3,000만
       유사암                   1,000만                         -                400만                           -                       -
암 진단  고액암                   3,000만                         -                       -                       -              3,000만
       고액(표적)항암치료비           8,000만                         -              8,000만                           -                       -
       뇌혈관질환                 1,000만                         -              1,000만                           -                       -
       뇌졸중                   5,000만                         -                       -                       -                       -
뇌/심장 뇌출혈                     3,000만                         -                       -                       -              3,000만
       허혈성심장질환               1,000만                         -              1,000만                           -                       -
       급성심근경색증            1억 1,000만                         -              3,000만                           -              3,000만
       상해입원의료비               5,000만                         -                       -                       -              5,000만
       상해통원의료비                  30만                         -                       -                       -                  30만
실손     질병입원의료비                  5,000만                         -                       -                       -              5,000만
       질병통원의료비                  30만                         -                       -                       -                  30만
       3대비급여실손                     -                        -                       -                       -                       -
       상해수술비                    50만                         -                  50만                          -                       -
       질병수술비                       -                        -                       -                       -                       -
       암수술비                        -                        -                       -                       -                       -
수술    뇌혈관질환수술비              1,300만                         -              1,000만                           -                       -
       허혈성심장질환수술비            1,000만                         -              1,000만                           -                       -
       상해입원일당                    6만                         -                       -                       -                    3만
       질병입원일당                    6만                         -                       -                       -                    3만
       벌금(대인/스쿨존/대물)         3,500만                1,500만                           -                       -              2,000만
       교통사고처리지원금          1억 8,000만            1억 1,000만                            -                       -              7,000만
       변호사선임비용               5,500만                5,000만                           -                       -                500만
운전자   자동차사고부상                     30만                    20만                          -                       -                  10만
기타     골절진단비                       70만                         -                  20만                          -                  20만
       보철치료비                       -                        -                       -                       -                       -
       가족/일상/자녀배상                1억                         -                       -                       -                    1억
       화재벌금                        -                        -                       -                       -                       -
""".split("\n")

# ── p7 상품별 가입현황(계약 5~6) 익명 ────────────────────────────────────────
P7_LINES = """홍길동 (33세 ,남자) 님의 상품별 가입현황
       상해사망               5억 5,000만                1,000만                        2억
사망     질병사망               1억 3,000만                         -                    1억
장해     상해80%미만후유장해        4억 1,600만                         -          1억 7,500만
       질병80%미만후유장해                 -                        -                       -
       장기요양간병비                     -                        -                       -
치매     경증치매진단                      -                        -                       -
간병     간병인/간호간병상해일당             27만                         -                       -
       간병인/간호간병질병일당             27만                         -                       -
       일반암                       1억                         -              5,000만
       유사암                   1,000만                         -                600만
암 진단  고액암                   3,000만                         -                       -
       고액(표적)항암치료비           8,000만                         -                       -
       뇌혈관질환                 1,000만                         -                       -
       뇌졸중                   5,000만                         -              5,000만
뇌/심장 뇌출혈                     3,000만                         -                       -
       허혈성심장질환               1,000만                         -                       -
       급성심근경색증            1억 1,000만                         -              5,000만
       상해입원의료비               5,000만                         -                       -
       상해통원의료비                  30만                         -                       -
실손     질병입원의료비                  5,000만                         -                       -
       질병통원의료비                  30만                         -                       -
       3대비급여실손                     -                        -                       -
       상해수술비                    50만                         -                       -
       질병수술비                       -                        -                       -
       암수술비                        -                        -                       -
수술    뇌혈관질환수술비              1,300만                         -                300만
       허혈성심장질환수술비            1,000만                         -                       -
       상해입원일당                    6만                         -                    3만
       질병입원일당                    6만                         -                    3만
       벌금(대인/스쿨존/대물)         3,500만                         -                       -
       교통사고처리지원금          1억 8,000만                         -                       -
       변호사선임비용               5,500만                         -                       -
운전자   자동차사고부상                     30만                         -                       -
기타     골절진단비                       70만                         -                  30만
       보철치료비                       -                        -                       -
       가족/일상/자녀배상                1억                         -                       -
       화재벌금                        -                        -                       -
""".split("\n")

# ── p20 전체 담보 진단현황(익명) ─────────────────────────────────────────────
P20_LINES = """홍길동 (33세 ,남자) 님의 전체 담보 진단 현황
       상해사망                                    2억        5억 5,000만        +3억 5,000만    충분
사망     질병사망                                    1억        1억 3,000만           +3,000만    충분
장해     상해80%미만후유장해                             1억        4억 1,600만        +3억 1,600만    충분
       질병80%미만후유장해                             1억               0                -1억   미가입
       장기요양간병비                              3,000만              0            -3,000만   미가입
치매     경증치매진단                                  1억               0                -1억   미가입
간병     간병인/간호간병상해일당                           25만             27만                +2만    충분
       간병인/간호간병질병일당                           25만             27만                +2만    충분
       일반암                                     1억              1억                  0    충분
       유사암                                  2,000만         1,000만            -1,000만    부족
암 진단  고액암                                  5,000만         3,000만            -2,000만    부족
       고액(표적)항암치료비                          3,000만         8,000만            +5,000만    충분
       뇌혈관질환                                3,000만         1,000만            -2,000만    부족
       뇌졸중                                  3,000만         5,000만            +2,000만    충분
뇌/심장 뇌출혈                                  3,000만         3,000만                  0    충분
       허혈성심장질환                              3,000만         1,000만            -2,000만    부족
       급성심근경색증                              3,000만       1억 1,000만           +8,000만    충분
       상해입원의료비                              5,000만         5,000만                  0    충분
       상해통원의료비                                30만             30만                  0    충분
실손     질병입원의료비                              5,000만         5,000만                  0    충분
       질병통원의료비                                30만             30만                  0    충분
       3대비급여실손                               350만               0              -350만   미가입
       상해수술비                                 100만             50만               -50만    부족
       질병수술비                                  50만               0               -50만   미가입
       암수술비                                  300만               0              -300만   미가입
수술    뇌혈관질환수술비                             1,000만         1,300만             +300만     충분
       허혈성심장질환수술비                           1,000만         1,000만                  0    충분
       상해입원일당                                  3만              6만                +3만    충분
       질병입원일당                                  3만              6만                +3만    충분
       벌금(대인/스쿨존/대물)                        3,000만         3,500만             +500만     충분
       교통사고처리지원금                               2억        1억 8,000만           -2,000만    부족
       변호사선임비용                              5,000만         5,500만             +500만     충분
운전자   자동차사고부상                                30만             30만                  0    충분
기타     골절진단비                                 100만             70만               -30만    부족
       보철치료비                                 200만               0              -200만   미가입
       가족/일상/자녀배상                              1억              1억                  0    충분
       화재벌금                                 2,000만              0            -2,000만   미가입
""".split("\n")

MAN = 10_000
EOK = 100_000_000


# ── 단위 ─────────────────────────────────────────────────────────────────────
def test_amount_tokenizer():
    assert parse_amount("5억 5,000만") == 550_000_000
    assert parse_amount("27만") == 270_000
    assert parse_amount("-") is None
    assert parse_amount("0") == 0
    assert parse_amount("1억 1,000만") == 110_000_000


def test_mapping_37_12_rep():
    assert STANDARD_COUNT == 37
    assert len(GROUP12) == 12
    reps = [n for (n, _, _, a) in KB_COVERAGES if a == AGG_REP]
    assert reps == ["상해입원의료비", "상해통원의료비", "질병입원의료비",
                    "질병통원의료비", "3대비급여실손", "가족/일상/자녀배상"]


def test_aggregate_sum_vs_rep():
    # 입원일당 = 합산 (3만+3만=6만)
    assert _aggregate({"1": 30000, "2": 30000}, AGG_SUM) == 60000
    # 실손 대표값 = 다건 최대값 (5,000만 vs 3,000만 → 5,000만, 합산 8,000만 아님)
    assert _aggregate({"1": 5000 * MAN, "2": 3000 * MAN}, AGG_REP) == 5000 * MAN
    assert _aggregate({"1": None, "2": None}, AGG_SUM) is None


# ── p5 계약·납입 ─────────────────────────────────────────────────────────────
def test_parse_contracts_and_premiums():
    contracts = parse_contract_list(P5_LINES)
    assert len(contracts) == 6
    pm = {c["idx"]: c["pay_months"] for c in contracts}
    assert pm == {1: 240, 2: 300, 3: 240, 4: 972, 5: 60, 6: 180}  # 81년→972, 15년→180
    prem = {c["idx"]: c["monthly_premium"] for c in contracts}
    assert prem[2] == 101463 and prem[4] == 82249 and prem[6] == 333600
    assert contracts[5]["maturity"] == "종신"
    assert contracts[0]["insurer"] == "KB손보" and contracts[2]["insurer"] == "한화손보"


def _build():
    raw = {
        "customer": {"name": "홍길동", "age": 33, "sex": "남"},
        "contracts": parse_contract_list(P5_LINES),
        "matrix": parse_matrix([P6_LINES, P7_LINES]),
        "diagnosis": parse_diagnosis(P20_LINES),
        "warnings": [],
    }
    before = build_before(raw)
    final = build_final(before, raw["diagnosis"])
    return raw, before, final


def test_premium_totals():
    _, before, _ = _build()
    assert before["premium"]["monthly_total"] == 573_227
    assert before["premium"]["paid_total"] == 181_984_128


def test_companies_sorted_desc():
    _, before, _ = _build()
    prem = [c["monthly_premium"] for c in before["companies"]]
    assert prem == sorted(prem, reverse=True)
    assert prem[0] == 333600 and prem[-1] == 10000


def _cov(before, name):
    return next(c for c in before["coverages"] if c["kb_name"] == name)


def test_matrix_sum_coverages():
    _, before, _ = _build()
    assert _cov(before, "상해사망")["summary"] == 5 * EOK + 5000 * MAN     # 5억5천
    assert _cov(before, "일반암")["summary"] == 1 * EOK                    # 1억
    assert _cov(before, "교통사고처리지원금")["summary"] == 1 * EOK + 8000 * MAN  # 1억8천


def test_ildang_sum_and_silson_rep():
    _, before, _ = _build()
    # 입원일당 합산: (4)3만 + (6)3만 = 6만
    assert _cov(before, "상해입원일당")["summary"] == 6 * MAN
    # 실손 대표값(문건주는 단건 5,000만)
    assert _cov(before, "상해입원의료비")["summary"] == 5000 * MAN
    assert _cov(before, "상해입원의료비")["agg"] == "rep"


def test_all_37_present_and_matrix_columns():
    raw, before, _ = _build()
    assert len(before["coverages"]) == 37
    # 매트릭스 열 = 계약 6
    ncol = max(len(v["by_company"]) for v in raw["matrix"].values())
    assert ncol == 6, ncol
    # 상해사망 by_company 합 == summary
    row = raw["matrix"]["상해사망"]
    assert sum(v for v in row["by_company"].values() if v) == row["summary"]


def test_diagnosis_and_final():
    _, _, final = _build()
    d = {c["kb_name"]: c for c in final["coverages"]}
    assert d["상해사망"]["recommended"] == 2 * EOK and d["상해사망"]["status"] == "충분"
    assert d["유사암"]["status"] == "부족"
    assert d["질병80%미만후유장해"]["status"] == "미가입"
    # value = 집계값(합산) 유지
    assert d["상해사망"]["value"] == 5 * EOK + 5000 * MAN


def test_non_kb_defense():
    import pytest
    # 텍스트 레이어는 있으나 KB 힌트 없는 문서 → KBFormatError (parse_document는 pdf 필요하므로 힌트 로직만 별도 확인)
    from coverage.parser import KB_FORMAT_HINTS  # noqa
    # 손상 PDF 바이트 → KBFormatError
    with pytest.raises(KBFormatError):
        parse_document(b"%PDF-1.4 not a real kb pdf")
