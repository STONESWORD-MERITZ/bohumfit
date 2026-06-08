# -*- coding: utf-8 -*-
"""SURIT-027 추가검사·재검사 판정 정교화 — 양방향 회귀.

과소 방지(고지 누락 > 과검)가 최우선. 결정론 후보 게이트(나)·검사근거 게이팅(B)·
프롬프트(가) 를 고정한다.

설계 메모(과소 방지):
- 결정론(나)은 같은날 '동일검사' 묶음만 횟수 collapse 한다(distinct 진료일). 같은날 '다종'·
  교차일·이상소견 동반 건은 후보로 보존하고, 추적관찰 vs 재검사 최종 판정은 Gemini(가) 몫.
  → 그래서 [제외돼야]의 '같은날 다종 일련검사'·'교차일 추적관찰'은 결정론 단계에서 후보로
     남고(아래 *_for_gemini 테스트), 실제 false 는 프롬프트 4기준으로 판단된다.
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from analyzer import (  # noqa: E402
    _build_medical_judgment_inputs,
    _codes_with_recent_test_evidence,
)
from pipeline.ai_judgment import MEDICAL_JUDGMENT_SYSTEM_PROMPT  # noqa: E402

REF = datetime(2026, 6, 7)
D3M = datetime(2026, 3, 9)
D1Y = datetime(2025, 6, 7)
TODAY = "2026-06-07"


def _te(date, name):
    return {"date": date, "name": name, "hospital": "A의원"}


def _ds(code, test_events, name="질환", latest="2026-03-01"):
    return {
        "diag_code": code, "name": name, "latest_date": latest,
        "test_events": test_events, "_daily_facts": {},
    }


def _type1_codes(ds):
    t1, _t2 = _build_medical_judgment_inputs(ds, D3M, D1Y, TODAY)
    return {c["disease_code"] for c in t1}


# ── (나) same-day collapse — [제외돼야] 결정론에서 후보 탈락 ──
def test_same_day_same_type_collapsed_not_candidate():
    """같은날 동일 검사 3회 → distinct 진료일 1·종류 1 → 후보 아님(한 과정)."""
    ds = {"E041": _ds("E041", [_te("2026-03-01", "갑상선초음파")] * 3)}
    assert "E041" not in _type1_codes(ds)


def test_single_test_not_candidate():
    ds = {"L309": _ds("L309", [_te("2026-03-01", "첩포검사")])}
    assert "L309" not in _type1_codes(ds)


# ── (나) [유지돼야] 과소 방지 — 진짜 후속검사·이상소견 동반 보존 ──
def test_same_day_multi_type_kept_candidate():
    """같은날 다종(유방초음파+조직검사) → types>=2 → 후보 유지(과소 방지)."""
    ds = {"C509": _ds("C509", [_te("2026-03-01", "유방초음파"), _te("2026-03-01", "조직검사")])}
    assert "C509" in _type1_codes(ds)


def test_cross_day_followup_kept_candidate():
    """교차일 초음파→조직검사 → distinct 진료일 2 → 후보 유지."""
    ds = {"C509": _ds("C509", [_te("2026-01-10", "유방초음파"), _te("2026-03-01", "조직검사")])}
    assert "C509" in _type1_codes(ds)


# ── (나) 추적관찰: 결정론은 후보 보존, false 판정은 Gemini(가) ──
def test_followup_monitoring_crossday_still_candidate_for_gemini():
    """추적관찰(동일검사 2일) → distinct 진료일 2 → 결정론 후보 유지(과소 방지).
    실제 '추적관찰 → false' 는 프롬프트 ③ 기준으로 Gemini 가 판단(여기선 후보 보존만 고정)."""
    ds = {"E041": _ds("E041", [_te("2025-09-01", "갑상선초음파"), _te("2026-03-01", "갑상선초음파")])}
    assert "E041" in _type1_codes(ds)


# ── (B) 검사근거 게이팅 ──
def test_evidence_codes_includes_disease_with_test_events():
    ds = {"C509": _ds("C509", [_te("2026-03-01", "유방초음파")])}
    assert "C509" in _codes_with_recent_test_evidence(ds, D1Y)


def test_evidence_codes_excludes_disease_without_test_events():
    """[제외돼야] 화상·피부염처럼 검사 근거 없는 1년 진단 → 의심 소견 미부착."""
    ds = {"T232": _ds("T232", [], name="2도화상"), "L309": _ds("L309", [], name="피부염")}
    ev = _codes_with_recent_test_evidence(ds, D1Y)
    assert "T232" not in ev
    assert "L309" not in ev


def test_evidence_codes_excludes_old_test_events():
    """1년 밖 검사만 있으면 근거 아님(1년 창 필터)."""
    ds = {"E041": _ds("E041", [_te("2024-01-01", "갑상선초음파")])}
    assert "E041" not in _codes_with_recent_test_evidence(ds, D1Y)


# ── (가) 프롬프트 정합 (103↔105 모순 해소 + 4기준 + 과소 방지) ──
def test_prompt_has_4_criteria():
    p = MEDICAL_JUDGMENT_SYSTEM_PROMPT
    assert "선행검사" in p
    assert "후속검사" in p
    assert "추적관찰" in p
    assert ("같은날" in p) or ("같은 날" in p)


def test_prompt_followup_override_and_undercount_guard():
    p = MEDICAL_JUDGMENT_SYSTEM_PROMPT
    # 동일검사 반복만으로 true 금지 (구 line 103 모순 해소)
    assert "동일검사 반복" in p
    # 과소 방지 단서 (고지 누락 방지)
    assert "고지 누락" in p
