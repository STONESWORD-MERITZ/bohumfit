# BOHUMFIT-032 건강체 Q3 '투약 30일' 판정창 10년→5년 교정 회귀 — 익명 합성 픽스처.
#
# 사양: 투약 30일 누적 SUM 판정창만 고정 1825일. 입원·수술·통원(7회)은 10년(d10y) 불변.
#  배지(result_builder)도 5년 창·집계로 헤더와 일치.
from datetime import datetime, timedelta

from filters import _build_q3_health_items, _build_q4_health_items, _q3_med_since, _sum_daily_max_presc, _cutoffs
from pipeline.disease_aggregator import new_disease
from pipeline.result_builder import build_summary_reports

TODAY = datetime(2026, 6, 15)
REF = datetime(2026, 6, 15)
_D3M, _D1Y, _D5Y, D10Y = _cutoffs(REF)  # _D5Y=달력 5년 경계, D10Y=10년 경계
MED5Y = _q3_med_since(REF)              # 투약 전용 1825일 경계
Q3_TITLE = "[3번질문] 5년 이내 입원·수술·통원·투약"  # BOHUMFIT-034


def _ymd(days_ago: int) -> str:
    return (TODAY - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def mk(code, name, episode=None, inpatient=None, surgery=None, visits=None):
    s = new_disease()
    s["diag_code"] = code
    s["name"] = name
    if episode:
        s["has_pharma"] = True
        s["med_dates_pharma_episode"] = {d: dict(h) for d, h in episode.items()}
        s["med_dates_pharma"] = {d: max(h.values()) for d, h in episode.items()}
    for d in (inpatient or []):
        s["inpatient_dates"].add(d)
        s["inpatient_admissions"].add((d, "OO병원"))
        s["_inpatient_days_map"][d] = 5
    for d in (surgery or []):
        s["surgery_dates"].add(d)
        s["surgeries"].add("관혈적정복술")
    for d in (visits or []):
        s["visit_dates"].add(d)
        s["visit_events"].append(d)
    alld = sorted(set(list((episode or {}).keys()) + (inpatient or []) + (surgery or []) + (visits or [])))
    s["first_date"] = alld[0] if alld else "2099-12-31"
    s["latest_date"] = alld[-1] if alld else "2000-01-01"
    return {code: s}


def _items(ds):
    return _build_q3_health_items(ds, REF)


def _rule_ids(ds):
    return {it.get("_rule_id") for it in _items(ds)}


def _q3_row(ds, code):
    std, easy, flagged, merged = build_summary_reports(ds, _items(ds), [], {}, "건강체", TODAY)
    rows = [r for r in std.get(Q3_TITLE, []) if r["code"] == code]
    return rows[0] if rows else None


# ── 5년 내 누적 판정 ─────────────────────────────────────────────────────
def test_within5y_14_14_3_triggers_31():
    ds = mk("M51", "추간판", {_ymd(400): {"H": 14}, _ymd(300): {"H": 14}, _ymd(200): {"H": 3}})
    assert _sum_daily_max_presc(ds["M51"]["med_dates_pharma_episode"], MED5Y) == 31
    assert "R-H-Q3-MED-30D" in _rule_ids(ds)


def test_within5y_14_14_no_trigger_28():
    ds = mk("M51", "추간판", {_ymd(400): {"H": 14}, _ymd(300): {"H": 14}})
    assert _sum_daily_max_presc(ds["M51"]["med_dates_pharma_episode"], MED5Y) == 28
    assert "R-H-Q3-MED-30D" not in _rule_ids(ds)


def test_within5y_single_30_triggers():
    ds = mk("M51", "추간판", {_ymd(200): {"H": 30}})
    assert "R-H-Q3-MED-30D" in _rule_ids(ds)


# ── 5년 경계: 1825일 포함(>=) / 1826일 제외 ──────────────────────────────
def test_boundary_5y_inclusive():
    on  = mk("M51", "추간판", {_ymd(1825): {"H": 30}})
    off = mk("M51", "추간판", {_ymd(1826): {"H": 30}})
    assert "R-H-Q3-MED-30D" in _rule_ids(on)       # 1825일 전 포함
    assert "R-H-Q3-MED-30D" not in _rule_ids(off)  # 1826일 전 제외


# ── ★ 5~10년 전 투약 30일↑: 창 축소로 미발동 ─────────────────────────────
def test_5to10y_medication_no_longer_triggers():
    ds = mk("M51", "추간판", {_ymd(2555): {"H": 20}, _ymd(2200): {"H": 15}})  # 7년·6년 전, 합 35
    assert _sum_daily_max_presc(ds["M51"]["med_dates_pharma_episode"], D10Y) == 35  # 10년이면 35
    assert _sum_daily_max_presc(ds["M51"]["med_dates_pharma_episode"], MED5Y) == 0   # 5년엔 0
    assert "R-H-Q3-MED-30D" not in _rule_ids(ds)   # 신버전 미발동


# ── ★ BOHUMFIT-034: 5~10년 입원·수술은 Q3가 아니라 신설 Q4, 5~10년 통원은 Q3 미발동 ─
def _q4_rule_ids(ds):
    return {it.get("_rule_id") for it in _build_q4_health_items(ds, REF)}


def test_5to10y_inpatient_surgery_now_in_q4_not_q3():
    # 7년 전 입원 → Q4 INP-510Y (Q3 5년엔 없음)
    ds_inp = mk("S33", "골절", inpatient=[_ymd(2555)])
    assert "R-H-Q4-INP-510Y" in _q4_rule_ids(ds_inp)
    assert "R-H-Q3-INP-5Y" not in _rule_ids(ds_inp)
    # 7년 전 수술 → Q4 SURG-510Y
    assert "R-H-Q4-SURG-510Y" in _q4_rule_ids(mk("K35", "충수", surgery=[_ymd(2555)]))
    # 6~9년 전 통원 7회 → Q3 VISIT-7 미발동(통원은 5년만)
    visits = [_ymd(d) for d in (3200, 3000, 2800, 2600, 2400, 2200, 2000)]
    assert "R-H-Q3-VISIT-7" not in _rule_ids(mk("M54", "요통", visits=visits))


# ── 배지==헤더(5년 SUM): 5~10년 투약은 배지에도 안 잡힘 ───────────────────
def test_badge_equals_header_5y_sum():
    # 입원(7년전)으로 Q3 행 확보 + 투약 20@3년 + 20@7년 → 5년 SUM=20, 10년 SUM=40
    ds = mk("M51", "추간판",
            episode={_ymd(1000): {"H": 20}, _ymd(2555): {"H": 20}},
            inpatient=[_ymd(1000)])  # BOHUMFIT-034: 5년내 입원으로 Q3 행 확보
    header_5y = _sum_daily_max_presc(ds["M51"]["med_dates_pharma_episode"], MED5Y)
    assert header_5y == 20 and _sum_daily_max_presc(ds["M51"]["med_dates_pharma_episode"], D10Y) == 40
    row = _q3_row(ds, "M51")
    assert row is not None
    assert row["med_days"] == 20      # 배지=5년 SUM (10년 40 아님)


# ── 결정성 ───────────────────────────────────────────────────────────────
def test_determinism():
    def snap():
        ds = mk("M51", "추간판", {_ymd(400): {"H": 14}, _ymd(300): {"H": 14}, _ymd(200): {"H": 3}})
        row = _q3_row(ds, "M51")
        return (sorted(_rule_ids(ds)), row["med_days"])
    assert snap() == snap()
