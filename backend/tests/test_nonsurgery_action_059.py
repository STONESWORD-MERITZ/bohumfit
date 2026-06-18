# BOHUMFIT-059 세부진료 수술 오탐 제거(검사·처치·주사 비수술 행위) — 익명·합성 픽스처(실데이터 아님).
#
# 증상(이민규): K21 식도염→복부초음파(검사), L90 여드름흉터→병변내주입요법(주사)이
#   "수술 1건"으로 오탐. 둘 다 진짜 수술 아님. 검사·처치·주사 행위를 수술 판정에서 제외하되
#   진짜 수술(비용적출술·창상봉합술 등)은 누락 0으로 유지한다.
# detail 행은 같은날·같은기관 basic 행에 링크돼야 집계되므로 basic+detail 쌍으로 구성한다.
from datetime import datetime

from pipeline.disease_aggregator import build_disease_stats, _is_detail_surgery_match
from pipeline.surgery_exclusions import is_non_surgery_action

TODAY = datetime(2026, 6, 15)


def basic(date, code, hosp="OO의원"):
    return {"진료개시일": date, "요양기관명": hosp, "입내원구분": "외래", "요양일수": "1",
            "상병코드": code, "상병명": "질환", "_ftype": "basic"}


def detail(date, proc, hosp="OO의원"):
    return {"진료개시일": date, "요양기관명": hosp, "입내원구분": "외래", "요양일수": "1",
            "처치및수술": proc, "_ftype": "detail"}


def _stats(recs):
    st, *_ = build_disease_stats(recs, TODAY)
    return st


# ── ① 복부초음파(검사) → 수술 미판정, 통원은 유지 ─────────────────────────────
def test_ultrasound_not_surgery_visit_kept():
    recs = [basic("2024-03-10", "K210"), detail("2024-03-10", "복부초음파")]
    s = _stats(recs)["K21"]
    assert not s["surgeries"] and not s["surgery_dates"]   # 수술 오탐 제거
    assert len(s["visit_events"]) >= 1                      # 통원 고지는 유지


# ── ② 병변내주입요법(주사) → 수술 미판정 ─────────────────────────────────────
def test_lesion_injection_not_surgery():
    recs = [basic("2024-04-02", "L900"), detail("2024-04-02", "병변내주입요법-25cm²미만")]
    s = _stats(recs)["L90"]
    assert not s["surgeries"] and not s["surgery_dates"]


# ── ③ 비용적출술(진짜 수술) → 수술 판정 유지(대조군 정탐) ─────────────────────
def test_polyp_removal_still_surgery():
    recs = [basic("2024-05-01", "J340"), detail("2024-05-01", "비용적출술")]
    s = _stats(recs)["J34"]
    assert s["surgeries"] and s["surgery_dates"]


# ── ④ 창상봉합술(진짜 수술) → 수술 판정 유지(대조군 정탐) ─────────────────────
def test_wound_suture_still_surgery():
    recs = [basic("2024-06-01", "S610"), detail("2024-06-01", "창상봉합술")]
    s = _stats(recs)["S61"]
    assert s["surgeries"] and s["surgery_dates"]


# ── ⑤ 비수술 제외돼도 통원/투약 고지 유지(오탐만 제거, 다른 기준 무영향) ──────
def test_nonsurgery_excluded_but_visit_counts():
    # 같은 K21에 검사 detail 2회 + basic 외래 2회 → 수술 0, 통원 2.
    recs = [
        basic("2024-03-10", "K210"), detail("2024-03-10", "복부초음파"),
        basic("2024-07-20", "K210"), detail("2024-07-20", "위내시경검사(상부)"),
    ]
    s = _stats(recs)["K21"]
    assert not s["surgeries"]
    assert len(s["visit_events"]) == 2


# ── ⑥ 단위: is_non_surgery_action / _is_detail_surgery_match (강수술 신호 우선) ─
def test_classifier_unit():
    # 비수술(검사·주사·처치) → True, 수술 미판정.
    for n in ("복부초음파", "병변내주입요법-25cm²미만", "근육내주사", "흉부촬영", "관절강내주사", "드레싱"):
        assert is_non_surgery_action(n) is True, n
        assert _is_detail_surgery_match(n) is False, n
    # 진짜 수술 → 비수술 아님(강수술 신호), 수술 판정 유지.
    for n in ("비용적출술", "창상봉합술", "내시경하종양수술", "내시경적점막절제술",
              "충수절제술", "백내장수술", "치핵절제술"):
        assert is_non_surgery_action(n) is False, n
        assert _is_detail_surgery_match(n) is True, n


# ── ⑦ 공백 변형에도 견고 ─────────────────────────────────────────────────────
def test_robust_to_spacing():
    assert is_non_surgery_action("복부 초음파") is True
    assert is_non_surgery_action("병변내 주입 요법") is True
    assert is_non_surgery_action("비 용 적출술") is False   # 적출 강신호 유지
