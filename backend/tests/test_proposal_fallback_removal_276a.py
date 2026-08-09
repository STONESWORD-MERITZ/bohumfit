# -*- coding: utf-8 -*-
"""BOHUMFIT-276a — 가입제안서 하드코딩 폴백 제거(출혈 차단).

★배경(274 조사): `proposal_registry`의 193 표본 고정값이 담보 행으로 주입돼, 실사용 산출물에
  상해후유장해 1억원(실제 100만원)·깁스치료비 50만원(원문에 문자열 0건)이 실렸다.
  설계사가 이 표로 고객에게 안내하므로 **틀린 숫자보다 빈칸이 안전하다**.

★이 파일이 고정하는 계약
  ①레지스트리 고정값은 **어떤 경로로도 담보 행이 되지 않는다**(fallback·bundle 모두)
  ②못 읽은 담보는 **값을 지어내지 않고** 미확인 경고로 알린다(단일 상수 문구)
  ③고정값이 **텍스트 실측값을 덮어쓰지 않는다**(과거에는 큰 값 채택으로 오염됐다)
  ④월납보험료도 표본 고정값으로 채우지 않는다
"""
from __future__ import annotations

from coverage.proposal_parser import (
    UNRESOLVED_COVERAGE_NOTE,
    parse_proposal_text,
    parse_proposal_texts,
)
from coverage.proposal_registry import INJECT_REGISTRY_FALLBACKS, PRODUCT_PROFILES


# 담보를 하나도 못 읽는 최소 문서 — 프로필만 잡히게 한다.
BARE_ALPHA = """
(무) 메리츠 The좋은 알파Plus종합보장보험2607(2.0)
계약사항 : 20년납 20년만기 | 월납
"""

# 텍스트로 실제 금액이 잡히는 문서 — 고정값(2,000만원)보다 작은 값을 넣어 덮어쓰기 여부를 본다.
TEXT_WINS = """
(무) 메리츠 The좋은 알파Plus종합보장보험2607(2.0)
보험료 105,802원
계약사항 : 20년납 20년만기 | 월납
253 131대질병수술비(뇌혈관질환) 5백만원
252 131대질병수술비(심장질환) 5백만원
"""


def _sources(result: dict) -> set[str]:
    return {str(coverage.get("source")) for coverage in result["coverages"]}


# ── ①고정값은 담보 행이 되지 않는다 ────────────────────────────────────────
def test_registry_fallbacks_are_never_injected_as_coverage_rows():
    """★담보를 하나도 못 읽어도 193 표본 금액이 채워지지 않는다."""
    result = parse_proposal_text(BARE_ALPHA, "bare.pdf")
    assert result["coverages"] == []
    assert INJECT_REGISTRY_FALLBACKS is False


def test_bundle_fixed_values_are_not_injected_either():
    """★`bundle_coverages`는 과거 **존재 확인조차 없이** 주입되던 경로다 — 전부 차단."""
    result = parse_proposal_text(BARE_ALPHA, "bare.pdf")
    names = {coverage["kb_name"] for coverage in result["coverages"]}
    assert names.isdisjoint({"뇌혈관수술", "심혈관수술", "암수술", "표적항암치료", "항암약물방사선"})


def test_no_registry_source_in_any_profile():
    """어떤 프로필로 인식되든 `source=registry`인 담보 행이 나오지 않는다."""
    docs = [
        ("alpha.pdf", BARE_ALPHA),
        ("cancer.pdf", "(무) 메리츠 또걸려도또받는암보험(연만기형)2601\n계약사항 : 20년납"),
        ("driver.pdf", "(무) 메리츠 운전자상해종합보험2604\n계약사항 : 20년납"),
        ("mirae.pdf", "어센틱금융그룹과함께하는M-케어건강보험(갱신형)(무)\n미래에셋생명보험(주)"),
        ("kb.pdf", "KB 금쪽같은 희망플러스 건강보험\n20년납 100세만기"),
    ]
    parsed = parse_proposal_texts(docs)
    for proposal in parsed["proposals"]:
        for coverage in proposal["coverages"]:
            assert "registry" not in str(coverage.get("source")), coverage


# ── ②미확인은 지어내지 않고 알린다 ────────────────────────────────────────
def test_unresolved_coverages_are_warned_with_single_constant():
    """★문구는 단일 상수이고, 못 읽은 담보 이름을 함께 알린다(행동 지침형)."""
    result = parse_proposal_text(BARE_ALPHA, "bare.pdf")
    warnings = " ".join(result["parse_warnings"])
    assert UNRESOLVED_COVERAGE_NOTE in warnings
    # 193 표본 목록이 미확인으로 올라온다(값이 아니라 **이름만**).
    assert "상해후유장해" in warnings and "깁스치료비" in warnings
    # ★금액이 문구에 섞여 나가지 않는다 — "0원"으로 읽히면 미가입으로 오해된다.
    assert "원" not in UNRESOLVED_COVERAGE_NOTE.split("빈칸")[0] or "0원" not in warnings


def test_note_says_blank_not_zero():
    """★'0원'이 아니라 '빈칸'임을 명시한다(미가입 오해 방지)."""
    assert "빈칸" in UNRESOLVED_COVERAGE_NOTE
    assert "0원" not in UNRESOLVED_COVERAGE_NOTE


def test_registry_hints_remain_as_metadata_only():
    """고정값 데이터는 지우지 않고 **수기 확인용 힌트**로만 남는다(276b가 쓴다)."""
    result = parse_proposal_text(BARE_ALPHA, "bare.pdf")
    hints = result["metadata"]["registry_hints"]
    assert hints, "힌트까지 사라지면 276b가 쓸 근거가 없어진다"
    assert all(hint["source"] == "registry-hint" for hint in hints)
    assert result["metadata"]["unresolved_coverages"]


# ── ③고정값이 텍스트 실측값을 덮어쓰지 않는다 ─────────────────────────────
def test_fixed_values_no_longer_overwrite_parsed_amounts():
    """★★과거 결함: 텍스트가 500만원으로 잡은 담보를 고정값 2,000만원이 덮어썼다.

    `_merge_entries`가 큰 금액을 채택하기 때문이며, 그 결과 보장 충분성 판정까지 바뀌었다
    (권장 1,000만원 대비 부족 → 충분). 이제 실측값이 그대로 남는다.
    """
    result = parse_proposal_text(TEXT_WINS, "text.pdf")
    amounts = {coverage["kb_name"]: coverage["amount"] for coverage in result["coverages"]}
    assert amounts["뇌혈관수술"] == 5_000_000
    assert amounts["심혈관수술"] == 5_000_000
    assert _sources(result) == {"text"}


# ── ④보험료 폴백도 제거 ───────────────────────────────────────────────────
def test_premium_is_none_when_not_found():
    """★프로필 고정 보험료(193 표본)를 쓰지 않는다 — 못 읽으면 값 없음 + 수기 확인 경고."""
    result = parse_proposal_text(BARE_ALPHA, "bare.pdf")
    assert result["monthly_premium"] is None
    assert any("월납보험료" in warning for warning in result["parse_warnings"])


def test_premium_is_kept_when_parsed():
    """★BOHUMFIT-276c: 항목은 `보장보험료 합계`(276b) 그대로이고 **원 단위 절삭**만 추가됐다."""
    result = parse_proposal_text(TEXT_WINS, "text.pdf")
    assert result["monthly_premium"] == 105_800


# ── 보호 영역 ─────────────────────────────────────────────────────────────
def test_registry_data_is_preserved_for_276b():
    """레지스트리 정의 자체는 삭제하지 않는다(276b 정확 파싱의 입력이다)."""
    assert len(PRODUCT_PROFILES) == 5
    alpha = next(profile for profile in PRODUCT_PROFILES if profile.key == "meritz-alpha")
    assert len(alpha.fallback_coverages) == 9
    assert len(alpha.bundle_coverages) == 2
