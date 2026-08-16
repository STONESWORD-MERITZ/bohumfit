# -*- coding: utf-8 -*-
"""BOHUMFIT-246 회귀 — 비분양식 정본화(집계·스키마 전환). 익명 합성 픽스처(홍길동).

제1원칙(정확도·누락 0)의 총액 대사, [후] 이월 모델의 전=후 동일성, 뇌·심장 단계 파생
(양식 시트3 수식 이식), Y/N 파생, 표시 순서, 238 estimated 생존을 고정한다.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coverage.aggregator import build_before, compute_stage_totals  # noqa: E402
from coverage.consulting import apply_consulting_plan  # noqa: E402
from coverage.constants import GROUP13, GROUP_ETC, NEW_ITEM_ORDER  # noqa: E402
from coverage.v2_mapping import GROUP13_V2, GROUP_APPENDIX_V2, ROW_INDEX  # noqa: E402  (290)
from tests.v2names import find_row  # noqa: E402  (290: 구 이름 → V2 행 투영)


def _rows(coverages):
    """BOHUMFIT-290(S2): 구 이름으로 V2 행을 찾는 매핑 — 값·셀은 그대로, 이름만 투영."""
    from tests.v2names import legacy_form_view
    return legacy_form_view(coverages)


MAN = 10_000


def _contract(idx: int, premium: int = 50_000, pay_cycle: str = "월납") -> dict:
    return {
        "idx": idx, "insurer": f"보험사{idx}", "product": f"합성{idx}", "contract_date": "2024-01-01",
        "pay_cycle": pay_cycle, "pay_years": 20, "pay_months": 240, "maturity": "100세",
        "monthly_premium": premium,
    }


def _raw() -> dict:
    """대사·단계·Y/N을 한 번에 검증하는 합성 케이스(2계약)."""
    return {
        "customer": {"name": "홍길동", "age": 50, "sex": "남자"},
        # BOHUMFIT-246 2차: 일시납은 1회 금액 그대로 이월되어야 전=후 총납입이 동일하다.
        "contracts": [_contract(1), _contract(2, 30_000, "일시납")],
        "matrix": {
            # 사망 배타 대상: 계약1의 일반사망 6,000만이 두 셀에 반영된 A 실측 형태.
            "상해사망": {"by_company": {"1": 6000 * MAN, "2": 1000 * MAN}},
            "질병사망": {"by_company": {"1": 6000 * MAN}},
            "상해후유장해": {"by_company": {"2": 5000 * MAN}},
            "암진단금": {"by_company": {"1": 3000 * MAN}},
            "유사암진단금": {"by_company": {"1": 600 * MAN}},
            "암수술": {"by_company": {"1": 1000 * MAN}},
            # 중입자 배타 대상: 계약1 표적 셀 1.1억 = 표적 6,000만 + 중입자 5,000만(D 실측 형태).
            "표적항암치료": {"by_company": {"1": 11000 * MAN}},
            "뇌혈관질환": {"by_company": {"1": 1000 * MAN}},
            "뇌졸중": {"by_company": {"1": 2000 * MAN}},
            "뇌출혈": {"by_company": {"1": 3000 * MAN}},
            "뇌혈관수술": {"by_company": {"1": 300 * MAN}},
            "허혈성심장질환": {"by_company": {"1": 4000 * MAN}},
            "급성심근경색": {"by_company": {"1": 5000 * MAN}},
            "심혈관수술": {"by_company": {"1": 400 * MAN}},
            "상해수술": {"by_company": {"1": 100 * MAN}},
            "질병수술": {"by_company": {"1": 200 * MAN}},
            "질병입원": {"by_company": {"2": 3 * MAN}},
            "골절진단비": {"by_company": {"2": 30 * MAN}},
            "교통사고처리지원금": {"by_company": {"2": 10000 * MAN}},
        },
        "diagnosis": {}, "notes": {},
        "extra": {
            "일반사망": {
                "agg": "sum", "by_company": {"1": 6000 * MAN},
                "class_amounts": {"1": {"상해사망": 6000 * MAN, "질병사망": 6000 * MAN}},
            },
            "재해사망": {"agg": "sum", "by_company": {"?": 10000 * MAN}},  # 근거 없음 → 기타
            "중입자방사선": {
                "agg": "sum", "by_company": {"1": 5000 * MAN},
                "target_included": {"1": 5000 * MAN},
            },
            "항암약물방사선": {"agg": "sum", "by_company": {"1": 500 * MAN}},
            "순환계 치료비": {"agg": "sum", "by_company": {"1": 5000 * MAN}},
            "응급실": {"agg": "sum", "by_company": {"2": 2 * MAN}},
            "깁스치료비": {"agg": "sum", "by_company": {"2": 50 * MAN}},
            "일반종수술 5종(표준환산)": {"agg": "sum", "by_company": {"1": 1000 * MAN}, "estimated": True},
            "80%이상 후유장해": {"agg": "sum", "by_company": {"2": 100 * MAN}},
        },
        "warnings": [],
    }


def _fix_raw() -> dict:
    return _raw()


def _total(coverages: list[dict]) -> int:
    return sum(c["summary"] or 0 for c in coverages if c["enrolled"])


# ── ★총액 대사: 구총합(원본 입력 합) = 신총합 + 배타 차감액 ─────────────────────
def test_reconciliation_identity():
    raw = _fix_raw()
    # 구총합 = 매트릭스 전 셀 + EXTRA 전 값(전환 이전 표현 — 차감·귀속 이전의 원본 합).
    old_total = sum(
        v for row in raw["matrix"].values() for v in row["by_company"].values() if v
    ) + sum(v for e in raw["extra"].values() for v in e["by_company"].values() if v)

    before = build_before(raw, today="2026-07-25")
    new_total = _total(before["coverages"])
    subtracted = before["death_dedup"]["subtracted_total"]

    # 일반사망 1.2억(상해+질병 셀) + 중입자 5,000만(표적 셀) 차감 = 1.7억.
    assert subtracted == 17000 * MAN
    assert old_total == new_total + subtracted  # ★차이 0


def test_death_promotion_and_unresolved_fallback():
    before = build_before(_fix_raw(), today="2026-07-25")
    rows = _rows(before["coverages"])
    # 승격: 일반사망 6,000만(사망 그룹) + 상해/질병사망 계약1 셀 0.
    assert rows["일반사망"]["group12"] == "사 망" and rows["일반사망"]["summary"] == 6000 * MAN  # 290: V2 대분류 표기
    assert rows["상해사망"]["by_company"]["1"] == 0 and rows["상해사망"]["summary"] == 1000 * MAN
    assert rows["질병사망"]["by_company"]["1"] == 0
    # 근거 없는 재해사망은 승격하지 않고 기타 보존(이중 계상 0 우선).
    assert "재해사망" not in rows
    assert rows["재해사망(계약 미확인)"]["group12"] == GROUP_APPENDIX_V2  # 290: 기타 → 비고
    # 중입자 배타: 표적 1.1억 → 6,000만 + 중입자 5,000만(암 그룹 내 상호배타 분리).
    assert rows["표적항암치료"]["summary"] == 6000 * MAN
    assert rows["중입자방사선"]["group12"] == "암" and rows["중입자방사선"]["summary"] == 5000 * MAN  # V2 radio_carbon


# ── 뇌·심장 단계 파생(양식 시트3 수식 — constants 주석의 원문 그대로) ─────────────
def test_stage_totals_follow_cascade_290():
    """★BOHUMFIT-290(S2): 종합 판정 = 케스케이드 체인 합(246 시트3 수식·공통 가산 폐기).

    같은 픽스처로 246 값과 나란히 적는다 — 이 변화가 **의도된 재정의**임을 남기기 위해서다.
      246: 뇌초기 = 뇌혈관+뇌졸중+뇌출혈+뇌혈관수술+공통(초기가 가장 큼)
      290: 뇌초기 = 뇌혈관 진단 시 지급 = 뇌혈관만 / 뇌중기 = 뇌혈관+뇌졸중 / 뇌말기 = 셋 다
    """
    before = build_before(_fix_raw(), today="2026-07-25")
    stages = before["stage_totals"]
    assert stages["뇌초기"] == 1000 * MAN
    assert stages["뇌중기"] == (1000 + 2000) * MAN
    assert stages["뇌말기"] == (1000 + 2000 + 3000) * MAN
    assert stages["심장초기"] == 4000 * MAN            # 허혈성 (심장질환은 독립 — 체인 밖)
    assert stages["심장중기"] == (4000 + 5000) * MAN   # 허혈성 + 급성
    # ★단조성: 초기 ≤ 중기 ≤ 말기 (246에서는 반대였다 — 272 "뇌초기 > 뇌중기" 이상 해소)
    assert stages["뇌초기"] <= stages["뇌중기"] <= stages["뇌말기"]
    assert stages["심장초기"] <= stages["심장중기"]
    # 구 키(암·심장말기)는 케스케이드에 대응 체인이 없어 사라진다(S3 블록 재설계 항목).
    assert "암" not in stages and "심장말기" not in stages
    # 암 계열은 체인별 행 — 표적 6,000만(차감 후) 체인 = 항암약물 0 + 표적 6,000만.
    assert stages["표적 약물 치료"] == 6000 * MAN


def test_yn_flags():
    before = build_before(_fix_raw(), today="2026-07-25")
    flags = {f["item"]: f["value"] for f in before["yn_flags"]}
    assert flags == {
        "운전자특약": "Y",        # 교통사고처리지원금 가입
        "자동차부상치료비": "N",
        "가족일상배상책임": "N",
        "상해실손의료비": "N",
        "질병실손의료비": "N",
    }


# ── ★[후] 이월 모델: 해지 0·신규 0 → 전=후 완전 동일 ───────────────────────────
def test_after_equals_before_when_no_cancel_no_proposal():
    before = build_before(_fix_raw(), today="2026-07-25")
    after = apply_consulting_plan(before, {"existing": [], "proposals": []})
    # BOHUMFIT-246 2차 강화: None 셀 희소화는 동등하게 보고, 비어 있지 않은 계약값·계약 미상
    # '?' 키·estimated까지 포함한 전 행이 완전 동일한지 비교한다.
    semantic = lambda rows: [(
        row["kb_name"], row["group12"], row["summary"], row["enrolled"],
        {key: value for key, value in row["by_company"].items() if value is not None},
        row.get("estimated"),
    ) for row in rows]
    assert semantic(after["coverages"]) == semantic(before["coverages"])
    unresolved = next(row for row in after["coverages"] if row["kb_name"] == "재해사망(계약 미확인)")
    assert unresolved["by_company"]["?"] == 10000 * MAN
    assert after["premium"] == before["premium"]
    assert after["stage_totals"] == before["stage_totals"]
    assert after["yn_flags"] == before["yn_flags"]


def _overview_raw() -> dict:
    """239 합계-only(전체 보장현황) 변형 — E 실측 구조의 익명 재현(계약별 셀 없음)."""
    return {
        "customer": {"name": "홍길동", "age": 56, "sex": "여자"},
        "contracts": [_contract(1), _contract(2, 30_000)],
        "matrix": {
            "상해사망": {"summary": 30000 * MAN, "by_company": {}, "overview": True},
            "질병사망": {"summary": 20000 * MAN, "by_company": {}, "overview": True},
            "암진단금": {"summary": 10000 * MAN, "by_company": {}, "overview": True},
            "표적항암치료": {"summary": 5000 * MAN, "by_company": {}, "overview": True},
            "뇌출혈": {"summary": 2000 * MAN, "by_company": {}, "overview": True},
            "급성심근경색": {"summary": 3000 * MAN, "by_company": {}, "overview": True},
            "질병수술": {"summary": 80 * MAN, "by_company": {}, "overview": True},
            "교통사고처리지원금": {"summary": 10000 * MAN, "by_company": {}, "overview": True},
            "질병입원의료비": {"summary": 5000 * MAN, "by_company": {}, "overview": True},
        },
        "diagnosis": {}, "notes": {},
        # 상세 검출 EXTRA는 overview 문서에서도 계약 키를 가진다(E 실측과 동일).
        "extra": {
            "중입자방사선": {"agg": "sum", "by_company": {"1": 5000 * MAN}},
            "깁스치료비": {"agg": "sum", "by_company": {"2": 50 * MAN}},
        },
        "warnings": [],
    }


def test_after_equals_before_for_overview_case():
    """★246 회송 보정: 합계-only(overview) 행도 해지 0·신규 0이면 전=후 완전 동일.
    (반려 실측: E 26행 소실·총합 1,542,990,000→142,750,000 — 이 회귀가 재발 방지 고정.)"""
    before = build_before(_overview_raw(), today="2026-07-25")
    after = apply_consulting_plan(before, {"existing": [], "proposals": []})
    semantic = lambda rows: [(
        row["kb_name"], row["group12"], row["summary"], row["enrolled"],
        {key: value for key, value in row["by_company"].items() if value is not None},
        row.get("estimated"), row.get("overview"),
    ) for row in rows]
    assert semantic(after["coverages"]) == semantic(before["coverages"])
    assert len(after["coverages"]) == len(before["coverages"])  # 행수 동일(소실 0)
    total = lambda rows: sum(c["summary"] or 0 for c in rows if c["enrolled"])
    assert total(after["coverages"]) == total(before["coverages"])
    assert after["premium"] == before["premium"]
    assert after["stage_totals"] == before["stage_totals"]
    assert after["yn_flags"] == before["yn_flags"]
    # overview 행의 Y/N도 [전]과 동일하게 산출된다(교통사고처리지원금 → 운전자특약 Y).
    assert dict((f["item"], f["value"]) for f in after["yn_flags"])["운전자특약"] == "Y"


def test_overview_rows_survive_cancel_with_warning():
    """합계형 행은 해지를 반영할 수 없다 — [전] 수준 보존 + 경고(보존+warning 정책 명시)."""
    before = build_before(_overview_raw(), today="2026-07-25")
    after = apply_consulting_plan(before, {"existing": [{"contract_idx": 2, "disposition": "해지"}]})
    rows = _rows(after["coverages"])
    # overview 행: [전] 합계 유지(계약 귀속 없음 → 해지 미반영).
    assert rows["상해사망"]["summary"] == 30000 * MAN and rows["상해사망"]["enrolled"] is True
    # 계약 키가 있는 상세 검출 EXTRA는 정상적으로 해지 반영(계약2 깁스 소멸).
    assert rows["깁스치료비"]["enrolled"] is False
    assert rows["중입자방사선"]["summary"] == 5000 * MAN  # 계약1 유지분 이월
    # 보험료 합계는 유지 계약 기준 재계산 + 경고 명시.
    assert after["premium"]["monthly_total"] == 50_000
    assert any("합계" in w and "해지" in w for w in after["warnings"])


def test_after_cancel_removes_contract_values():
    before = build_before(_fix_raw(), today="2026-07-25")
    after = apply_consulting_plan(before, {"existing": [{"contract_idx": 2, "disposition": "해지"}]})
    rows = _rows(after["coverages"])
    assert rows["상해후유장해"]["enrolled"] is False       # 계약2 전용 담보 소멸
    assert rows["일반사망"]["summary"] == 6000 * MAN       # 계약1 유지분 이월
    assert after["premium"]["monthly_total"] == 50_000     # 해지 계약 보험료 제외


# ── 표시 순서·estimated 생존 ────────────────────────────────────────────────────
def test_display_order_follows_v2_schema():
    """BOHUMFIT-290(S2): 표시 순서 = V2 49행 스키마 순서, 비고행은 뒤."""
    before = build_before(_fix_raw(), today="2026-07-25")
    rows = before["coverages"]
    ids = [c["row_id"] for c in rows if c.get("row_id")]
    assert ids == sorted(ids, key=lambda i: ROW_INDEX[i])
    groups = [c["group12"] for c in rows]
    order = {g: i for i, g in enumerate(GROUP13_V2)}
    assert groups == sorted(groups, key=lambda g: order[g])
    assert all(c["group12"] == GROUP_APPENDIX_V2 for c in rows if not c.get("row_id"))


def test_estimated_flag_survives():
    before = build_before(_fix_raw(), today="2026-07-25")
    # BOHUMFIT-290: 238 환산 라벨은 V2 종수술 5행의 `unspecified` 열로 간다(종별을 잃은 라벨 — 추측 금지).
    row = find_row(before["coverages"], "일반종수술 5종(표준환산)")
    assert row["estimated"] is True and row["group12"] == "수 술" and row["row_id"] == "tier_surgery_5"


def test_new_coverage_rows_exist_for_future_track():
    """신담보 3행([후] 전용 자리)은 [전]에서 미가입 행으로 존재한다."""
    before = build_before(_fix_raw(), today="2026-07-25")
    rows = _rows(before["coverages"])
    # BOHUMFIT-290: 면역·심혈관질환은 V2 행(면역 약물 치료·심 장 질 환)으로 존재. ★`암 주요치료비`는
    #   행이 아니라 **분배 대상**(DISTRIBUTED — S4)이라 행 목록에 없다.
    for name in ("면역항암치료", "심혈관질환"):
        assert name in rows and rows[name]["enrolled"] is False and rows[name]["summary"] is None
    assert "암 주요치료비" not in {c["kb_name"] for c in before["coverages"]}
