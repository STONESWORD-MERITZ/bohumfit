"""BOHUMFIT-205: 3개월 약 변경 감지 — 동일 성분 브랜드 전환 오탐 수정 회귀 테스트.

실사(실사용 처방조제 데이터 재현·익명화): 3개월 이내 처방이 이전 복용약과 같은 성분인데
브랜드(상품명)만 달라 '새 약 추가/약 종류 변경'으로 오탐됐다.
 - 디스펩틴정 → 모사프리엠정 (모사프리드시트르산염수화물 동일)
 - 거드액 → 알지에액 (알긴산나트륨 동일)
 - 티로파정 → 스파론정 (티로프라미드염산염 동일)
또한 심평원 PDF 셀 줄바꿈(임의 공백)·중첩 괄호로 같은 약이 다른 정규화 키가 되는
결함('가스티렌정)' 잔재 키)을 extract_drug_info 강화로 고정한다.
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.disease_aggregator import detect_drug_changes, new_disease
from pipeline.helpers import extract_drug_info, normalize_ingredient

TODAY = datetime(2026, 4, 25)


def _group(in_90, before_90, ingredient_map=None, last_seen_dates=None, name="위-식도역류병"):
    s = new_disease()
    s["diag_code"] = "K21"
    s["name"] = name
    s["drug_names_in_90"] = set(in_90)
    s["drug_names_before_90"] = set(before_90)
    s["drug_ingredient_map"] = dict(ingredient_map or {})
    s["drug_last_seen_dates"] = dict(last_seen_dates or {})
    return {"K21": s}


# ── 동일 성분 브랜드 전환 = 변경 아님 ─────────────────────────────


def test_same_ingredient_brand_switch_not_flagged():
    """제네릭 브랜드 전환(성분 동일)은 '새 약 추가'가 아니다 — 실데이터 오탐 재현 케이스."""
    stats = _group(
        in_90=["모사프리엠정(모사프 리드시트르산염수화물 )_(5.29mg/1정)"],
        before_90=["디스펩틴정5mg(모사 프리드시트르산염수화 물)_(5.29mg/1정)"],
        ingredient_map={
            "모사프리엠정(모사프 리드시트르산염수화물 )_(5.29mg/1정)": "mosapride citrate hydrate",
            "디스펩틴정5mg(모사 프리드시트르산염수화 물)_(5.29mg/1정)": "mosapride citratehydrate",
        },
    )
    result = detect_drug_changes(stats, TODAY)
    assert result == []
    assert stats["K21"]["drug_change_in_3m"] is False


def test_same_ingredient_switch_with_wrap_spacing_not_flagged():
    """성분명 줄바꿈 공백 변형(알긴산나 트륨 vs 알긴산나트륨)도 동일 성분으로 정규화된다."""
    stats = _group(
        in_90=["알지에액(알긴산나트 륨)_(1.25g/25mL)"],
        before_90=["거드액(알긴산나트륨)_ (1.25g/25mL)"],
        ingredient_map={
            "알지에액(알긴산나트 륨)_(1.25g/25mL)": "sodium alginate",
            "거드액(알긴산나트륨)_ (1.25g/25mL)": "sodiumalginate",
        },
    )
    assert detect_drug_changes(stats, TODAY) == []


def test_really_new_ingredient_still_flagged():
    """진짜 새 성분 추가는 계속 감지한다(민감도 후퇴 금지)."""
    stats = _group(
        in_90=[
            "모사프리엠정(모사프리드시트르산염수화물)_(5.29mg/1정)",
            "환인그란닥신정(토피소팜)_(50mg/1정)",   # 새 성분
        ],
        before_90=["디스펩틴정5mg(모사프리드시트르산염수화물)_(5.29mg/1정)"],
        ingredient_map={
            "모사프리엠정(모사프리드시트르산염수화물)_(5.29mg/1정)": "mosapride citrate hydrate",
            "환인그란닥신정(토피소팜)_(50mg/1정)": "tofisopam",
            "디스펩틴정5mg(모사프리드시트르산염수화물)_(5.29mg/1정)": "mosapride citrate hydrate",
        },
    )
    result = detect_drug_changes(stats, TODAY)
    assert len(result) == 1
    assert result[0]["change_type"] == "새 약 추가"
    assert any("그란닥신" in d for d in result[0]["new"])
    # 동일 성분 전환분(모사프리엠정)은 new 가 아니라 continued 로 분류된다.
    assert not any("모사프리엠" in d for d in result[0]["new"])
    assert any("모사프리엠" in d for d in result[0]["continued"])
    assert stats["K21"]["drug_change_in_3m"] is True


def test_no_ingredient_info_keeps_legacy_behavior():
    """성분명이 없는 데이터는 기존 브랜드 키 판정 그대로(하위 호환) — 브랜드가 다르면 감지."""
    stats = _group(
        in_90=["모사프리엠정_(5.29mg/1정)"],
        before_90=["디스펩틴정_(5.29mg/1정)"],
        ingredient_map={},
    )
    result = detect_drug_changes(stats, TODAY)
    assert len(result) == 1
    assert result[0]["change_type"] == "약 종류 변경"


def test_same_brand_dose_increase_still_flagged():
    """동일 브랜드 용량 증가(악화 신호)는 계속 감지한다."""
    stats = _group(
        in_90=["메트포르민정 1000mg"],
        before_90=["메트포르민정 500mg"],
        ingredient_map={
            "메트포르민정 1000mg": "metformin hydrochloride",
            "메트포르민정 500mg": "metformin hydrochloride",
        },
    )
    result = detect_drug_changes(stats, TODAY)
    assert len(result) == 1
    assert result[0]["change_type"] == "용량 증가"


def test_same_ingredient_brand_switch_with_dose_increase_still_flagged():
    """제네릭 교체라도 용량이 늘면 동일성분 보정으로 고지 후보를 지우지 않는다."""
    stats = _group(
        in_90=["NewBrand 20mg"],
        before_90=["OldBrand 10mg"],
        ingredient_map={
            "NewBrand 20mg": "same ingredient",
            "OldBrand 10mg": "same ingredient",
        },
    )

    result = detect_drug_changes(stats, TODAY)
    assert len(result) == 1
    assert result[0]["change_type"] == "용량 증가"
    assert result[0]["new"] == []
    assert result[0]["dose_increased"] == ["newbrand (10.0→20.0)"]


def test_transient_90_day_drug_is_excluded_when_current_regimen_matches_before():
    """3개월 안의 일시 처방이 있어도 최신 확인 약이 이전과 같으면 고지 후보에서 제외한다."""
    stable = "StableDrug 10mg"
    transient = "TransientDrug 10mg"
    stats = _group(
        in_90=[stable, transient],
        before_90=[stable],
        last_seen_dates={
            transient: "2026-03-01",
            stable: "2026-04-25",
        },
    )

    assert detect_drug_changes(stats, TODAY) == []
    assert stats["K21"]["drug_change_in_3m"] is False


def test_currently_confirmed_new_ingredient_still_flagged():
    """현재 확인 처방에 새 성분이 함께 있으면 2차 확인 후에도 고지 후보를 유지한다."""
    stable = "StableDrug 10mg"
    new_drug = "NewDrug 10mg"
    stats = _group(
        in_90=[stable, new_drug],
        before_90=[stable],
        ingredient_map={stable: "stable ingredient", new_drug: "new ingredient"},
        last_seen_dates={stable: "2026-04-25", new_drug: "2026-04-25"},
    )

    result = detect_drug_changes(stats, TODAY)
    assert len(result) == 1
    assert result[0]["new"] == ["newdrug"]
    assert stats["K21"]["drug_change_in_3m"] is True


def test_currently_confirmed_dose_increase_still_flagged():
    """현재 확인 처방의 증량은 2차 확인이 있어도 고지 후보를 유지한다."""
    stats = _group(
        in_90=["StableDrug 20mg"],
        before_90=["StableDrug 10mg"],
        ingredient_map={
            "StableDrug 20mg": "stable ingredient",
            "StableDrug 10mg": "stable ingredient",
        },
        last_seen_dates={"StableDrug 20mg": "2026-04-25"},
    )

    result = detect_drug_changes(stats, TODAY)
    assert len(result) == 1
    assert result[0]["change_type"] == "용량 증가"
    assert stats["K21"]["drug_change_in_3m"] is True


def test_brand_switch_not_reported_as_stopped():
    """브랜드 전환 시 이전 브랜드는 '중단'으로 보고되지 않는다(성분 지속)."""
    stats = _group(
        in_90=[
            "모사프리엠정(모사프리드시트르산염수화물)_(5.29mg/1정)",
            "환인그란닥신정(토피소팜)_(50mg/1정)",
        ],
        before_90=["디스펩틴정5mg(모사프리드시트르산염수화물)_(5.29mg/1정)"],
        ingredient_map={
            "모사프리엠정(모사프리드시트르산염수화물)_(5.29mg/1정)": "mosapride citrate hydrate",
            "환인그란닥신정(토피소팜)_(50mg/1정)": "tofisopam",
            "디스펩틴정5mg(모사프리드시트르산염수화물)_(5.29mg/1정)": "mosapride citrate hydrate",
        },
    )
    result = detect_drug_changes(stats, TODAY)
    assert len(result) == 1
    assert result[0]["stopped"] == []


# ── extract_drug_info 정규화 강화 ─────────────────────────────────


def test_extract_drug_info_wrap_spacing_stable_key():
    """PDF 셀 줄바꿈 공백 위치가 달라도 같은 키·같은 용량."""
    a = extract_drug_info("휴록스정(록소프로펜 나트륨수화물)_( 68.1mg/1정)")
    b = extract_drug_info("휴록스정(록소프로펜나트륨수화물)_(68.1mg/1정)")
    c = extract_drug_info("휴록스정(록소프로펜 나트륨수화물)_( 6 8.1mg/1정)")  # 용량 중간 절단
    assert a == b == c
    assert a[1] == 68.1


def test_extract_drug_info_nested_parens_no_residue():
    """중첩 괄호('(애엽95%에탄올연조엑스(20→1))')가 잔재(')' 등) 없이 제거된다."""
    base, _ = extract_drug_info("가스티렌정(애엽95% 에탄올연조엑스(20→1 ))_(60mg/1정)")
    assert ")" not in base and "(" not in base
    assert base == extract_drug_info("가스티렌정(애엽95%에탄올연조엑스(20→1))_(60mg/1정)")[0]
    base2, _ = extract_drug_info("모티리톤정_(현호색·견 우자(5:1)50%에탄 올연조엑스(9.5~11.5 →1),30mg/1정)")
    assert ")" not in base2 and "(" not in base2


def test_extract_drug_info_korean_dose_unit_stable_key():
    """'50밀리그램' 한글 용량 표기도 mg 표기와 같은 키가 된다."""
    a, _ = extract_drug_info("가나칸정50밀리그램( 이토프리드염산염)_( 50mg/1정)")
    b, _ = extract_drug_info("가나칸정50mg(이토프리드염산염)_(50mg/1정)")
    assert a == b


def test_extract_drug_info_legacy_contract_kept():
    """기존 계약 유지: 제조사 무관 동일 키·단위 환산·무용량."""
    b1, d1 = extract_drug_info("메트포르민정 500mg (한미제약)")
    b2, d2 = extract_drug_info("메트포르민정 500mg (대웅제약)")
    assert b1 == b2 and d1 == d2 == 500.0
    assert extract_drug_info("약품 1g")[1] == 1000.0
    base, dose = extract_drug_info("아스피린정")
    assert dose == 0.0 and "아스피린" in base


def test_normalize_ingredient_variants():
    """성분명 정규화: 공백·대소문자·괄호 별칭 제거."""
    assert normalize_ingredient("mosapride citrate hydrate") == normalize_ingredient("Mosapride CitrateHydrate")
    assert normalize_ingredient("loxoprofen sodiumhydrate (asloxoprofen sodium)") == \
        normalize_ingredient("loxoprofen sodium hydrate")
    assert normalize_ingredient("") == ""
    assert normalize_ingredient(None) == ""
