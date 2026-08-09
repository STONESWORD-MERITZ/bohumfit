# -*- coding: utf-8 -*-
"""BOHUMFIT-276b — 가입제안서 파싱 정확도(T1·T3·T4·T5).

276a가 "없는 값을 지어내는 것"을 멈췄고, 여기서는 **읽어야 할 값을 정확히 읽는다**.
★설계 원칙 승계: 값이 없으면 빈칸 / **읽은 값을 다른 값으로 바꾸지 않는다** / 확신 없으면 경고.

★T2(`80%이상후유장해` 인식)는 **구현하지 않았다** — BOHUMFIT-243 Human 결정
  ("80%이상 후유장해는 후유장해 집계에서 제외·기타 보존")과 충돌하기 때문이다. 사유는 태스크 문서 참조.
"""
from __future__ import annotations

from coverage.proposal_parser import (
    _extract_pay_months,
    _extract_premium,
    _extract_product,
    _is_example_window,
    parse_proposal_text,
)

# 실 PDF(오현지) 구조를 익명·합성으로 재현한다 — 실 PDF/PII는 저장하지 않는다.
REAL_SHAPE = """
(무) 메리츠 The좋은 알파Plus보장보험2607(2.0) (해약환급금미지급형)(납입면제 일반형)
계약사항 : 20년납 20년만기 | 월납 | 자동이체
보장보험료 합계 105,802 원
1회차보험료(할인후) 105,800 원
2회차이후보험료 105,800 원 할인보험료 0 원
가입담보리스트
기본계약 1 갱신형 일반상해사망[기본계약] 1백만원 16
44 갱신형 뇌혈관질환진단비 1천만원
대표계약 기준 : 남자40세,20년납,20년만기,월납,갱신형일반상해사망[기본계약] 5,000만원, 갱신형질병
"""


# ── T1: 예시 줄은 읽지 않는다 ─────────────────────────────────────────────
def test_example_window_is_detected():
    assert _is_example_window("대표계약 기준 : 남자40세,20년납, 갱신형일반상해사망[기본계약] 5,000만원")
    assert _is_example_window("보험료 비교(예시)")
    # 실제 가입담보 줄은 예시로 오판하지 않는다.
    assert not _is_example_window("기본계약 1 갱신형 일반상해사망[기본계약] 1백만원 16")


def test_representative_example_amount_is_not_adopted():
    """★★T1: 실제 100만원 대신 예시 5,000만원을 채택하던 결함이 사라진다."""
    result = parse_proposal_text(REAL_SHAPE, "real.pdf")
    amounts = {coverage["kb_name"]: coverage["amount"] for coverage in result["coverages"]}
    assert amounts["상해사망"] == 1_000_000
    assert 50_000_000 not in amounts.values()


def test_example_line_exclusion_is_line_scoped_not_page_scoped():
    """★샘플이 1건뿐이라 **줄 단위**로만 배제한다 — 같은 문서의 다른 담보는 그대로 읽힌다."""
    result = parse_proposal_text(REAL_SHAPE, "real.pdf")
    amounts = {coverage["kb_name"]: coverage["amount"] for coverage in result["coverages"]}
    assert amounts["뇌혈관질환"] == 10_000_000


# ── T3: 상품명 원문 보존 ──────────────────────────────────────────────────
def test_product_name_comes_from_document():
    """★T3: 프로필 고정 상품명(2604·종합보장보험)이 원문(2607(2.0)·보장보험)을 덮지 않는다."""
    result = parse_proposal_text(REAL_SHAPE, "real.pdf")
    assert result["product"] == (
        "(무) 메리츠 The좋은 알파Plus보장보험2607(2.0) (해약환급금미지급형)(납입면제 일반형)"
    )
    # ★272b 선례: 괄호 수식어를 임의로 깎지 않는다(과잉 절삭 금지).
    assert "(해약환급금미지급형)" in result["product"]
    assert "2604" not in result["product"]


def test_product_falls_back_with_warning_when_absent():
    """원문에서 못 읽으면 대표 상품명으로 표기하되 **버전 확인 경고**를 남긴다."""
    text = "The좋은알파Plus 종합\n계약사항 : 20년납"
    result = parse_proposal_text(text, "noproduct.pdf")
    assert any("상품명" in warning for warning in result["parse_warnings"])


def test_extract_product_ignores_unrelated_lines():
    assert _extract_product("계약사항 : 20년납\n보장보험료 합계 105,802 원", None) is None


# ── T4: 납입기간 폴백 제거 ────────────────────────────────────────────────
def test_pay_months_is_none_when_not_found():
    """★T4: 240개월(20년) 가정 제거 — 못 읽으면 값 없음."""
    assert _extract_pay_months("보장보험료 합계 105,802 원") is None


def test_pay_months_still_read_when_present():
    assert _extract_pay_months("계약사항 : 20년납 20년만기") == 240


def test_missing_pay_months_warns_instead_of_assuming():
    result = parse_proposal_text("(무) 메리츠 The좋은 알파Plus보장보험2607(2.0)\n보장보험료 합계 1,000 원", "nopay.pdf")
    assert result["pay_months"] is None
    assert any("납입기간" in warning for warning in result["parse_warnings"])


# ── T5: 월납보험료 원문 일치 ──────────────────────────────────────────────
def test_premium_uses_document_total_not_first_installment():
    """★★T5: 2원 차는 반올림이 아니라 **다른 항목을 읽던 것**이었다.

    원문에 `보장보험료 합계 105,802 원`과 `1회차보험료(할인후) 105,800 원`이 둘 다 있는데
    후자를 먼저 잡았다(할인보험료는 0원). 고객·파일명이 인식하는 금액은 합계다.
    """
    # ★BOHUMFIT-276c: 읽는 **항목**은 여기서 고정한 대로 `보장보험료 합계`(105,802)이고,
    #   그 위에 원 단위 절삭이 적용돼 산출은 105,800이 된다. 항목 교정(T5)의 계약은 그대로다.
    assert _extract_premium(REAL_SHAPE, None) == 105_800
    assert parse_proposal_text(REAL_SHAPE, "real.pdf")["monthly_premium"] == 105_800
    # ★1회차보험료(105,800)를 읽은 것이 **아니라** 합계를 읽고 절삭한 결과임을 구분해 고정한다.
    from coverage.proposal_parser import truncate_premium
    assert truncate_premium(105_802) == 105_800


def test_first_installment_still_used_when_no_total():
    """합계 표기가 없는 양식에서는 기존 패턴이 그대로 폴백으로 동작한다(패턴 삭제 0)."""
    assert _extract_premium("1회차보험료(할인후) 90,000 원", None) == 90_000  # 절삭해도 동일


# ── 276a 계약 유지 ────────────────────────────────────────────────────────
def test_276a_fallback_removal_is_not_reverted():
    """★276a가 비운 담보가 다시 채워지지 않는다(PDF에 없는 담보는 계속 빈칸)."""
    result = parse_proposal_text(REAL_SHAPE, "real.pdf")
    names = {coverage["kb_name"] for coverage in result["coverages"]}
    assert "깁스치료비" not in names
    assert all("registry" not in str(coverage.get("source")) for coverage in result["coverages"])


def test_registry_hints_do_not_leak_into_values():
    """★`metadata.registry_hints`는 힌트로만 쓰고 담보 값으로 새지 않는다."""
    result = parse_proposal_text(REAL_SHAPE, "real.pdf")
    hint_names = {hint["kb_name"] for hint in result["metadata"]["registry_hints"]}
    value_names = {coverage["kb_name"] for coverage in result["coverages"]}
    injected = {
        name
        for name in hint_names & value_names
        if any(
            coverage["kb_name"] == name and "registry" in str(coverage.get("source"))
            for coverage in result["coverages"]
        )
    }
    assert injected == set()
