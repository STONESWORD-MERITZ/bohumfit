# BOHUMFIT-056 공단(nhis) 입원일수 파싱(입내원일수 1줄) + 수술의심 금액(공단+본인 합산) 회귀.
#   익명 합성 공단 요양급여내역 텍스트(실데이터 아님). 2줄 1세트:
#     1줄: 진료개시일 입내원일수 요양기관명 연락처 공단부담금
#     2줄: 입내원구분 요양(투약)일수 상병명 상병코드 본인부담금
from datetime import datetime

from pipeline.pdf_parser import parse_nhis_text
from pipeline.disease_aggregator import build_disease_stats
from pipeline.helpers import get_val
from pipeline.nhis_history_constants import grade_surgery_suspicion

# M512: 입내원일수 2(입원 2일), 요양일수 10, 공단 800,000 + 본인 200,000 = 100만
# K603: 입내원일수 3(입원 3일), 요양일수 5,  공단 600,000 + 본인 150,000 = 75만
NHIS_TEXT = (
    "건강보험 요양급여내역\n"
    "2020.02.24 2 청주성모병원 043-123-4567 800000\n"
    "1\n"
    "입원 10 척추협착 M5120 200000\n"
    "2018.07.20 3 행복병원 02-555-1234 600000\n"
    "2\n"
    "입원 5 치핵 K6030 150000\n"
)


def _recs():
    return parse_nhis_text(NHIS_TEXT, "test.pdf")


def _rec(code):
    return next(r for r in _recs() if r["상병코드"] == code)


# ── ① 입원일수 = 입내원일수(1줄), 요양일수(2줄) 아님 ──────────────────────
def test_inpatient_days_from_visit_column():
    m = _rec("M5120")
    assert m["내원일수"] == "2"        # 입내원일수(1줄) = 2 (요양일수 10 아님)
    k = _rec("K6030")
    assert k["내원일수"] == "3"        # K605 입원 3일


# ── ② 입원일수/투약일수 분리 ─────────────────────────────────────────────
def test_visit_days_vs_med_days_separated():
    m = _rec("M5120")
    assert m["내원일수"] == "2" and m["투약일수"] == "10"   # 분리 유지
    # aggregator 경로(get_val 우선순위)도 입내원일수를 입원일수로 사용
    assert get_val(m, ["내원일수", "투약일수", "요양일수"]) == "2"


# ── ③ 수술의심 금액 = 공단부담금(1줄) + 본인부담금(2줄) 합산 ───────────────
def test_total_cost_is_gongdan_plus_bonin():
    assert int(_rec("M5120")["총진료비"]) == 1_000_000   # 800,000 + 200,000
    assert int(_rec("K6030")["총진료비"]) == 750_000     # 600,000 + 150,000


# ── ④ 입원 고액 건 → 수술의심 '강'(합산 기준 50만↑) ──────────────────────
def test_inpatient_high_cost_surgery_suspect_strong():
    assert grade_surgery_suspicion("입원", int(_rec("M5120")["총진료비"]), False, False) == "강"
    assert grade_surgery_suspicion("입원", int(_rec("K6030")["총진료비"]), False, False) == "강"


# ── ⑤ 집계: 입원일수 2(요양일수 10 아님) + 입원 고액 수술의심 등급 부여 ────
def test_aggregator_inpatient_days_and_suspect():
    st, *_ = build_disease_stats(_recs(), datetime(2026, 6, 17))  # 2018·2020 = 5~10년
    assert "M51" in st
    dm = st["M51"]["_inpatient_days_map"]
    assert max(dm.values()) == 2                      # 입내원일수 2 (10 아님)
    assert st["M51"].get("surgery_suspected_grade")   # 고액 입원 → 수술의심 등급


# ── ⑥ 의심(공단 추정) ≠ 확정(세부 수술): nhis 의심은 surgery_dates 미설정 ──
def test_suspect_distinct_from_confirmed_surgery():
    st, *_ = build_disease_stats(_recs(), datetime(2026, 6, 17))
    # nhis 고액 입원은 '수술 의심'만 — 확정 수술(surgery_dates)로 굳지 않는다.
    assert not st["M51"].get("surgery_dates")
    assert st["M51"].get("surgery_suspected_names")
