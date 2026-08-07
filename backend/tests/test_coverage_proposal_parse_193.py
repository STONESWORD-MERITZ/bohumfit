# -*- coding: utf-8 -*-
"""BOHUMFIT-193 신규 가입제안서 PDF 파싱 회귀.

실 PDF/PII는 저장하지 않는다. 아래 픽스처는 193 조사 명세의 실측 구조와
금액만 익명·합성 텍스트로 재현한 것이다.
"""
from __future__ import annotations

from coverage.compare import build_after_analysis
from coverage.proposal_parser import parse_proposal_texts


MERITZ_ALPHA = """
(무) 메리츠 The좋은 알파Plus종합보장보험2604
보험료 56,950원
계약사항 : 20년납 20년만기 | 월납
1 갱신형 일반상해사망[기본계약] 1억원 2,420
4 갱신형 일반상해후유장해(3-100%) 1억원 2,620
11 갱신형 암진단비(유사암제외) 1백만원 271
32 갱신형 유사암진단비 10만원 8
44 갱신형 뇌혈관질환진단비 1천만원
46 갱신형 뇌혈관질환진단비Ⅱ 1천만원
48 갱신형 허혈성심장질환진단비 1천만원
50 갱신형 허혈성심장질환진단비Ⅱ 1천만원
239 갱신형 상해수술비 1백만원
243 갱신형 질병수술비 20만원
252 131대질병수술비(심장질환) 5백만원
253 131대질병수술비(뇌혈관질환) 5백만원
297 갱신형 골절진단비Ⅱ 30만원
303 갱신형 깁스치료비 50만원
616 가족일상생활중배상책임(Ⅳ) 1억원
151 특정순환계질환 통합치료비 1억원
"""

MERITZ_CANCER = """
(무) 메리츠 또걸려도또받는암보험(연만기형)2601
보험료 35,070원
계약사항 : 20년납 20년만기 | 월납
32 갱신형 암종별(30종)통합암진단비(전이포함)(유사암제외)[기본계약]
64 갱신형 유사암진단비 1천만원
67 갱신형 암진단비(유사암제외) 1백만원
68 암 통합치료비Ⅲ(비급여) 5천만원
78 암 통합치료비(기본형) 8천만원
82 암 통합치료비Ⅱ(비급여) 1억원
암수술 1,000만원 유사암수술 200만원 항암방사선 1,000만원 표적항암 3,000만원
암수술 750만원 항암방사선 750만원 표적항암 2,000만원
"""

MERITZ_DRIVER = """
(무) 메리츠 운전자상해종합보험2604
보험료 12,320원
계약사항 : 20년납 20년만기 | 월납
교통사고처리지원금 2억원
6주미만 교통사고처리지원금 1천만원
변호사선임비용 5백만원
벌금 3천만원
자동차사고부상치료비(14급) 30만원
"""

MIRAE = """
어센틱금융그룹과함께하는M-케어건강보험(갱신형)(무)
미래에셋생명보험(주)
합계 36,874 원
최초계약20년 최대100세만기
주계약[갱신형] 2,000 34 월납 260
암(유사암제외)진단특약 10,000 34 월납 23,500
유사암진단특약 2,000 34 월납 2,660
1-5종수술특약(1종) 20 34 월납 100
1-5종수술특약(2종) 40 34 월납 100
1-5종수술특약(3종) 300 34 월납 100
1-5종수술특약(4종) 1,000 34 월납 100
1-5종수술특약(5종) 1,000 34 월납 100
"""

KB = """
KB 금쪽같은 희망플러스 건강보험
보험료 : 20,940원
20년납 100세만기
1 일반상해사망 1백만원
2 일반상해후유장해(3~100%) 1백만원
117 뇌혈관질환진단비 3천만원
124 심장질환(특정Ⅰ)진단비 2천만원
125 심장질환(특정Ⅱ)진단비 5천만원
127 허혈성심장질환진단비 1천만원
"""


def _parsed() -> dict:
    return parse_proposal_texts(
        [
            ("meritz-alpha.pdf", MERITZ_ALPHA),
            ("meritz-cancer.pdf", MERITZ_CANCER),
            ("meritz-driver.pdf", MERITZ_DRIVER),
            ("mirae.pdf", MIRAE),
            ("kb.pdf", KB),
        ]
    )


def _proposal(result: dict, profile: str) -> dict:
    return next(item for item in result["proposals"] if (item.get("metadata") or {}).get("profile") == profile)


def _amount(proposal: dict, kb_name: str) -> int:
    return next(item["amount"] for item in proposal["coverages"] if item["kb_name"] == kb_name)


def _analysis_for_after() -> dict:
    # BOHUMFIT-246: 담보명·그룹을 비분양식 정식명으로 갱신(파서·레지스트리와 동일 명칭 —
    #   compare가 kb_name 문자열로 결합하므로 합성 [전]도 정식명 기준).
    names = [
        ("암진단금", "암", 100_000_000),
        ("유사암진단금", "암", 20_000_000),
        ("뇌혈관질환", "뇌", 30_000_000),
        ("급성심근경색", "심장", 30_000_000),
        ("뇌혈관수술", "뇌", 10_000_000),
        ("심혈관수술", "심장", 10_000_000),
        ("자동차사고부상", "가입특약(Y/N)", 1_000_000),
    ]
    before = {
        "customer": {"name": "테스트", "age": 34, "sex": "남"},
        "premium": {"monthly_total": 350_000, "paid_total": 84_000_000, "currency": "KRW"},
        "companies": [
            {
                "idx": 1,
                "insurer": "기존A",
                "product": "해지계약",
                "pay_cycle": "월납",
                "pay_months": 240,
                "monthly_premium": 250_000,
                "paid_total": 60_000_000,
                "maturity": "100세",
                "remark": None,
            },
            {
                "idx": 2,
                "insurer": "기존B",
                "product": "유지계약",
                "pay_cycle": "월납",
                "pay_months": 240,
                "monthly_premium": 100_000,
                "paid_total": 24_000_000,
                "maturity": "100세",
                "remark": None,
            },
        ],
        "coverages": [
            {
                "kb_name": name,
                "kb_group": group,
                "group12": group,
                "agg": "sum",
                "summary": None,
                "by_company": {},
                "enrolled": False,
            }
            for name, group, _ in names
        ],
    }
    before["contract_list"] = before["companies"]
    final = {
        "premium": before["premium"],
        "coverages": [
            {
                "group12": group,
                "kb_name": name,
                "agg": "sum",
                "value": None,
                "recommended": recommended,
                "gap": -recommended,
                "status": "미가입",
            }
            for name, group, recommended in names
        ],
        "rollup_by_group12": [],
    }
    return {"before": before, "final": final, "warnings": []}


def _names(proposal: dict) -> set:
    """BOHUMFIT-276a: 담보 행으로 실제 실린 kb_name 집합(폴백 주입 여부 판정용)."""
    return {coverage["kb_name"] for coverage in proposal["coverages"]}


def test_parse_real_trace_193_synthetic_five_pdfs() -> None:
    result = _parsed()

    assert result["premium"]["monthly_total"] == 162_154
    assert result["premium_total"] == 162_154
    assert result["metadata"]["company_order"] == ["KB손해보험", "메리츠화재", "메리츠화재", "메리츠화재", "미래에셋생명"]

    cancer = _proposal(result, "meritz-cancer")
    bundle = {(item["kb_name"], item["amount"]) for item in cancer["metadata"]["bundle_subbenefits"]}
    assert ("암수술", 17_500_000) in bundle  # 246 개명
    # BOHUMFIT-245 ⑦: 표적항암 통합 — 표준행·레지스트리 개명(고액(표적)항암치료비→표적항암치료,
    # 값 이관·금액 불변). compare kb_name 결합 정합을 위해 레지스트리도 동일 명칭 사용.
    assert ("표적항암치료", 80_500_000) in bundle
    assert ("항암약물방사선", 20_500_000) in bundle  # 246: EXTRA 라벨과 명칭 통일
    # ★BOHUMFIT-276a: bundle 고정값은 **담보 행으로 삽입하지 않는다**(메타로만 남는다).
    #   기존 기대값(`_amount(cancer, "암수술") == 17_500_000`)은 193 표본 고정값이 담보로
    #   주입되던 상태를 고정한 것이라 **테스트 쪽이 틀렸다**. 274에서 이 경로로 실사용 산출물에
    #   유령 담보가 실린 것이 확인돼, 주입 없음을 새 기대값으로 삼는다.
    assert _names(cancer).isdisjoint({"암수술", "표적항암치료", "항암약물방사선"})

    # BOHUMFIT-246: 레지스트리 정식명 개명분 — ★아래 3건은 **원문 텍스트에서 추출**되므로 불변이다
    #   (폴백 제거의 영향이 텍스트로 잡히는 담보에는 미치지 않음을 함께 고정한다).
    assert _amount(_proposal(result, "mirae-mcare"), "유사암진단금") == 20_000_000
    assert _amount(_proposal(result, "kb-hope"), "급성심근경색") == 50_000_000
    assert _amount(_proposal(result, "meritz-driver"), "자동차사고부상") == 300_000
    # ★276a 불변식: 어떤 제안서에도 **레지스트리 고정값 유래 담보 행이 없다**(픽스처와 무관한 계약).
    assert all(
        "registry" not in str(coverage.get("source"))
        for proposal in result["proposals"]
        for coverage in proposal["coverages"]
    )
    # ★276a: 이 합성 픽스처의 meritz-alpha는 13행 전부 원문 텍스트로 잡힌다 — 폴백이 필요 없었다.
    alpha = _proposal(result, "meritz-alpha")
    assert len(alpha["coverages"]) == 13
    assert {c["kb_name"] for c in alpha["coverages"] if "registry" in str(c.get("source"))} == set()


def test_parsed_proposals_recalculate_after_and_use_two_stage_aggregation() -> None:
    parsed = _parsed()
    result = build_after_analysis(
        _analysis_for_after(),
        {
            "existing": [{"contract_idx": 1, "disposition": "해지"}],
            "proposals": parsed["proposals"],
        },
    )

    assert result["comparison"]["premium"]["delta_monthly"] == -87_846
    after = {row["kb_name"]: row for row in result["after"]["final"]["coverages"]}
    # BOHUMFIT-246 정식명 — 합산 값 자체는 불변(개명만).
    # ★BOHUMFIT-276a: 기존 151,000,000은 meritz-cancer의 `암진단금` 5,000만원 **레지스트리 고정값**이
    #   합산에 포함된 값이었다. 그 표본 금액은 현재 문서의 실제 가입액이라는 근거가 없어 제거했고,
    #   텍스트로 실제 추출된 값만 남아 101,000,000이 된다(테스트 기대값을 폴백 없는 상태로 갱신).
    assert after["암진단금"]["value"] == 101_000_000
    assert after["유사암진단금"]["value"] == 30_100_000
    assert after["뇌혈관질환"]["value"] == 40_000_000
    assert after["급성심근경색"]["value"] == 50_000_000
    # ★★BOHUMFIT-276a: 기존 20,000,000은 bundle 고정값이었다. 원문 텍스트는 이 담보를 **500만원**으로
    #   이미 잡고 있었는데, `_merge_entries`가 큰 값을 채택하는 탓에 **고정값이 실측값을 덮어썼다**.
    #   즉 폴백은 "못 읽은 자리를 채우는" 데 그치지 않고 **읽은 값을 오염**시키고 있었다.
    assert after["뇌혈관수술"]["value"] == 5_000_000
    assert after["심혈관수술"]["value"] == 5_000_000
    assert after["자동차사고부상"]["value"] == 300_000
    # ★★BOHUMFIT-276a: 기존 `>= 5`는 폴백이 만든 수치였다. 뇌혈관수술·심혈관수술은 실제 제안값이
    #   각 500만원(권장 1,000만원)이라 **부족**인데, 고정값 2,000만원이 덮어써 **"충분"으로 판정**되고
    #   미가입→충분 건수에 잡혔다. 즉 폴백은 금액뿐 아니라 **보장 충분성 판정 자체를 조작**하고 있었다.
    #   실제 값 기준의 정상 건수는 4다.
    assert result["comparison"]["summary"]["missing_to_sufficient"] == 4
