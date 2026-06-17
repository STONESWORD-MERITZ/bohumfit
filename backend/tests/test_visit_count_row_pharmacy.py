# BOHUMFIT-050 통원 카운트 행(row) 기준 + 약국 기관명 공백 정규화 회귀 — 익명 합성 픽스처.
#
# 확정 사양: 통원 횟수 = 내원 '행' 수(visit_events, 같은날 중복 허용). visit_dates(집합)는
#   pharma cross-ref 앵커 전용으로 분리. 약국(공백 변형 "약 국" 포함)은 통원 카운트에서 제외.
#   5년 창(BOHUMFIT-034)·VISIT-7(≥7) 임계는 불변.
from datetime import datetime, timedelta

from pipeline.disease_aggregator import build_disease_stats, _is_pharmacy
from filters import build_code_based_items, _visit_count_in_range, _subtract_years

TODAY = datetime(2026, 6, 17)
PRODUCT = "건강체/표준체 (일반심사)"
D5 = _subtract_years(TODAY, 5)


def _ymd(days_ago: int) -> str:
    return (TODAY - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def basic(date, code, hosp="행복내과의원", io="외래"):
    return {"진료시작일": date, "병·의원&약국": hosp, "진단과": "내과", "입원/외래": io,
            "주상병코드": code, "주상병명": "테스트", "내원일수": "1", "_ftype": "basic"}


def pharma(date, drug, days, hosp="행복약국"):
    return {"진료시작일": date, "병·의원&약국": hosp, "약품명": drug, "성분명": drug,
            "총투약일수": str(days), "_ftype": "pharma"}


def _stats(recs):
    st, *_ = build_disease_stats(recs, TODAY)
    return st


def _rules(recs, code):
    items = build_code_based_items(_stats(recs), TODAY, PRODUCT)
    return {it.get("_rule_id") for it in items if it.get("code") == code}


# ── ① 같은날 2회 방문(다른 기관) → 행 기준 2회 (일자 기준이면 1) ──────────
def test_same_day_two_visits_counted_as_two():
    recs = [basic(_ymd(100), "M751", "A의원"), basic(_ymd(100), "M751", "B의원")]
    s = _stats(recs)["M75"]
    assert len(s["visit_dates"]) == 1            # 일자(앵커)는 1
    assert len(s["visit_events"]) == 2           # 행(카운트)은 2
    assert _visit_count_in_range(s, D5) == 2


# ── ② 5년 경계 밖 행 → 카운트 제외(034 5년 창 불변) ──────────────────────
def test_over_5y_row_excluded_from_count():
    recs = [basic(_ymd(2000), "M751"), basic(_ymd(100), "M751")]  # 2000일≈5.5년 전 + 100일
    s = _stats(recs)["M75"]
    assert _visit_count_in_range(s, D5) == 1     # 5년 내 1행만


# ── ③ 약국("○○약국") → 통원 카운트 제외 ─────────────────────────────────
def test_pharmacy_name_excluded_from_visit():
    s = _stats([basic(_ymd(100), "M751", "행복약국")])["M75"]
    assert len(s["visit_events"]) == 0 and _visit_count_in_range(s, D5) == 0


# ── ④ 약국 공백("○○약 국") → 통원 카운트 제외 (STEP1 공백 정규화) ─────────
def test_pharmacy_name_with_space_excluded():
    assert _is_pharmacy("OO약 국") and _is_pharmacy("OO약  국")
    assert not _is_pharmacy("튼튼내과의원")
    s = _stats([basic(_ymd(100), "M751", "OO약 국")])["M75"]
    assert len(s["visit_events"]) == 0 and _visit_count_in_range(s, D5) == 0


# ── ⑤ pharma 앵커(visit_dates) 분리 유지 — 같은날 진단+처방 → 투약 부착 ───
def test_pharma_anchor_visit_dates_preserved():
    recs = [basic(_ymd(100), "E785", "고지혈"), pharma(_ymd(100), "ezetimibe", 90, "행복약국")]
    s = _stats(recs)["E78"]
    assert _ymd(100) in s["visit_dates"]         # 앵커 일자 유지
    assert s.get("med_dates_pharma")             # 같은날 처방이 질병에 부착


# ── ⑥ VISIT-7: 5년 내 행 7 → 발동 / 6 → 미발동 ──────────────────────────
def test_visit7_threshold_by_rows():
    r7 = [basic(_ymd(d), "M751") for d in (1700, 1500, 1000, 800, 500, 300, 100)]
    assert "R-H-Q3-VISIT-7" in _rules(r7, "M75")
    r6 = [basic(_ymd(d), "M751") for d in (1500, 1000, 800, 500, 300, 100)]
    assert "R-H-Q3-VISIT-7" not in _rules(r6, "M75")


# ── ⑦ 같은날 7행이면 단일 일자라도 VISIT-7 발동(행 기준 확정 고정) ─────────
def test_visit7_same_day_rows_trigger():
    recs = [basic(_ymd(100), "M751", h) for h in ("A의원", "B의원", "C의원", "D의원", "E의원", "F의원", "G의원")]
    s = _stats(recs)["M75"]
    assert len(s["visit_dates"]) == 1 and _visit_count_in_range(s, D5) == 7
    assert "R-H-Q3-VISIT-7" in _rules(recs, "M75")
