# -*- coding: utf-8 -*-
"""BOHUMFIT-303 — 수술 판정 3단 표시: `수술 여부 확인` 티어(285 C-1 · Human 확정) 계약.

★고정하는 계약
  ① 판정 단일 소스 = surgery_exclusions.surgery_tier — 강수술 신호 → 확정 · 강등 패턴 → 확인 · 그 외 확정.
  ② ★카운트 불변: 확인 티어도 surgeries·surgery_dates에 **그대로** 남는다 → Q1~Q5 헤더·"수술 N건" Δ=0.
  ③ 표시 4경로 동일 라벨 `수술 여부 확인: {명칭}` — 서버 main.SURGERY_REVIEW_LABEL 1상수(프런트와 골든 동등성).
  ④ 구 payload(tier·surgery_review 부재)는 **확정으로 폴백**(누락 방향 아님).
  ⑤ 기존 제외·강수술·보조재 가드 무변경(062·059·104·106·130).

★뮤테이션(303 Step 4): ①강등 목록 비움 → 확인 소멸 검출 ②강등을 카운트 제외로 → 헤더 변화 검출.
★PII: 익명 합성 픽스처만.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main  # noqa: E402
from filters import PRODUCT_EASY, build_code_based_items  # noqa: E402
from pipeline.disease_aggregator import build_disease_stats  # noqa: E402
from pipeline.report_pdf import _surgery_tier_counts  # noqa: E402
from pipeline.result_builder import build_summary_reports  # noqa: E402
from pipeline.surgery_exclusions import (  # noqa: E402
    SURGERY_REVIEW_PATTERNS,
    SURGERY_TIER_CONFIRMED,
    SURGERY_TIER_REVIEW,
    is_non_surgery_action,
    surgery_tier,
)

try:
    from filters import PRODUCT_HEALTH  # noqa: E402
except ImportError:  # pragma: no cover
    PRODUCT_HEALTH = "health"

_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "surgery_review_parity_303.json")
TODAY = datetime(2026, 8, 22)


def _basic(date, code, name, in_out="외래", days=1, cost="18,000", hosp="가나이비인후과의원"):
    return {"_ftype": "basic", "_fname": "합성.pdf", "진료시작일": date, "주상병코드": code, "주상병명": name,
            "병·의원&약국": hosp, "입원/외래": in_out, "내원일수": str(days), "총진료비(건강보험적용분)": cost}


def _detail(date, act_name, hosp="가나이비인후과의원"):
    return {"_ftype": "detail", "_fname": "합성세부.pdf", "진료시작일": date, "병·의원&약국": hosp,
            "진료내역": "처치및수술 (양방)", "코드명": act_name}


# ── ① 티어 판정(한 곳) ──────────────────────────────────────────────────────
def test_tier_review_for_simple_foreign_body_removal():
    """실 고지 오분류 건(285) — `제거`로 확정되지만 강등 패턴 `이물제거술(단순`에 걸려 확인 티어."""
    assert surgery_tier("인두이물제거술(단순[편도상와])") == SURGERY_TIER_REVIEW
    assert surgery_tier("인두이물제거술(단순[편 도상와])") == SURGERY_TIER_REVIEW  # PDF 셀 공백 변형


def test_tier_confirmed_for_real_surgeries():
    for name in ("절개술(제1범위)", "창상봉합술", "종양절제술", "충수절제술", "관혈적정복술", "백내장초음파유화술및인공수정체삽입술"):
        assert surgery_tier(name) == SURGERY_TIER_CONFIRMED, name


def test_strong_keyword_blocks_demotion():
    """강수술 신호 동반 시 강등 패턴이 있어도 확정 유지(누락 0)."""
    assert surgery_tier("흉강천자배농술") == SURGERY_TIER_CONFIRMED        # 천자 + 배농(강)
    assert surgery_tier("이물제거술(단순)및절제술") == SURGERY_TIER_CONFIRMED  # 절제(강)
    assert surgery_tier("유치도뇨관삽입") == SURGERY_TIER_CONFIRMED         # 130: 유치도뇨 강신호


def test_review_patterns_are_narrow_and_exclusion_lists_untouched():
    assert "이물제거술(단순" in SURGERY_REVIEW_PATTERNS
    assert "(단순" not in SURGERY_REVIEW_PATTERNS            # 일반화는 303b 결정지
    for b in ("치료재료", "수술팩", "정맥내주입", "IVPCA", "절삭기"):  # 294 B 유형은 303c
        assert b not in SURGERY_REVIEW_PATTERNS
    assert is_non_surgery_action("창상드레싱")                 # 059 제외는 그대로(강등 목록과 별개)
    assert surgery_tier("") == SURGERY_TIER_CONFIRMED          # 빈 이름 폴백 = 확정


# ── ② 카운트 불변(구조적 보장) + 티어 부가 ─────────────────────────────────
def _records():
    return [
        _basic("2026-04-11", "T17", "(양방)인두의 이물"),
        _detail("2026-04-11", "인두이물제거술(단순[편 도상와])"),
        _basic("2023-02-05", "L05", "(양방)농양이있는 모소낭", in_out="입원", days=4, cost="1,000,000", hosp="가나병원"),
        _detail("2023-02-05", "절개술(제1범위)", hosp="가나병원"),
    ]


def test_aggregator_keeps_confirmed_set_and_adds_review_tier():
    stats, *_ = build_disease_stats(_records(), TODAY)
    t17 = next(s for s in stats.values() if (s.get("diag_code") or "").startswith("T17"))
    l05 = next(s for s in stats.values() if (s.get("diag_code") or "").startswith("L05"))
    # ★확정 집합·날짜는 그대로(카운트 불변) — 강등은 별도 표시 필드로만.
    assert t17["surgeries"] == {"인두이물제거술(단순[편 도상와])"} and t17["surgery_dates"] == {"2026-04-11"}
    assert t17["surgery_review_names"] == {"인두이물제거술(단순[편 도상와])"}
    assert l05["surgeries"] == {"절개술(제1범위)"} and l05["surgery_review_names"] == set()
    assert [r["tier"] for r in t17["surgery_records"]] == [SURGERY_TIER_REVIEW]
    assert [r["tier"] for r in l05["surgery_records"]] == [SURGERY_TIER_CONFIRMED]


def test_q_items_and_counts_are_unchanged_by_tier():
    """★불변식 — 확인 티어가 있어도 Q 판정 항목(reason·is_surgery)·surgery_count는 확정과 동일하게 잡힌다.
    (뮤테이션 ② '강등을 카운트 제외로' 검출점)"""
    stats, *_ = build_disease_stats(_records(), TODAY)
    health = build_code_based_items(stats, TODAY, PRODUCT_HEALTH)
    easy = build_code_based_items(stats, TODAY, PRODUCT_EASY)
    t17_q = [it for it in health if (it.get("code") or "").startswith("T17") and it.get("is_surgery")]
    assert t17_q, "확인 티어도 수술 판정 항목을 그대로 만든다"
    assert any("5년이내 수술" in (it.get("reason") or "") for it in t17_q)
    std, _ez, _flag, _m = build_summary_reports(stats, health, easy, {}, PRODUCT_HEALTH, TODAY)
    q3 = next(v for k, v in std.items() if "3번" in k)
    t17 = next(x for x in q3 if (x.get("code") or "").startswith("T17"))
    assert t17["surgery_count"] == 1 and t17["surgeries"]            # 카운트·확정 그대로
    assert t17["surgery_review"] and all("이물제거술" in n for n in t17["surgery_review"])
    assert _surgery_tier_counts(t17) == (0, 1)                       # 배지 합 = 헤더 1건
    l05 = next(x for x in q3 if (x.get("code") or "").startswith("L05"))
    assert l05["surgery_review"] == [] and _surgery_tier_counts(l05) == (1, 0)


# ── ③ 4경로 라벨 — 서버 골든(프런트 memoItem도 같은 골든) ────────────────────
def test_kakao_item_parity_golden_303():
    with open(_FIXTURE, encoding="utf-8") as f:
        fx = json.load(f)
    assert main.SURGERY_REVIEW_LABEL == "수술 여부 확인"
    out = main._kakao_item(fx["review_item"])
    assert out == fx["review_item_expected"]
    assert f"{main.SURGERY_REVIEW_LABEL}: 인두이물제거술(단순[편도상와])" in out
    assert main._kakao_item(fx["confirmed_item"]) == fx["confirmed_item_expected"]
    assert main.SURGERY_REVIEW_LABEL not in fx["confirmed_item_expected"]


def test_legacy_payload_without_tier_falls_back_to_confirmed():
    """④ 구 payload(tier·surgery_review 없음) — 확정 라벨 유지(누락 방향 아님)."""
    with open(_FIXTURE, encoding="utf-8") as f:
        fx = json.load(f)
    item = fx["legacy_item_no_tier"]
    assert main._kakao_item(item) == fx["legacy_item_no_tier_expected"]
    assert main.SURGERY_REVIEW_LABEL not in fx["legacy_item_no_tier_expected"]
    assert _surgery_tier_counts(item) == (1, 0)


def test_tier_counts_sum_equals_header_count():
    """배지 합 불변식: 확정 N + 확인 M = surgery_count(헤더 "수술 N건")."""
    item = {"surgery_count": 2,
            "surgery_records": [{"date": "2026-01-01", "surgery_name": "a", "tier": "review"},
                                {"date": "2026-02-01", "surgery_name": "b", "tier": "confirmed"}]}
    assert _surgery_tier_counts(item) == (1, 1)
    # 같은 날 확정·확인 공존 → 그 날은 확정으로 센다(누락 방향 아님).
    item2 = {"surgery_count": 1,
             "surgery_records": [{"date": "2026-01-01", "surgery_name": "a", "tier": "review"},
                                 {"date": "2026-01-01", "surgery_name": "b", "tier": "confirmed"}]}
    assert _surgery_tier_counts(item2) == (1, 0)
    assert _surgery_tier_counts({"surgery_count": 0}) == (0, 0)
