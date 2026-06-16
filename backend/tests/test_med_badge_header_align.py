# BOHUMFIT-031 투약 배지 = 헤더 판정값 정합 회귀 — 익명·합성 픽스처(실데이터 아님).
#
# 배경(BOHUMFIT-030 진단): 초록 "투약 N일" 배지는 result_builder 에서 _max_presc(단일 일자
# 최대)로 산출돼, 헤더 Q3 판정값 _sum_daily_max_presc(날짜별 최대의 누적 합계)와 어긋났다.
# 정답 (A): 배지를 헤더와 동일 집계·동일 원천(med_dates_pharma_episode)·동일 창으로 정합.
#
# ※ BOHUMFIT-032: 건강체 Q3 '투약 30일' 판정창은 고정 1825일이다(입원·수술·통원은 10년 유지).
#   배지(result_builder)도 헤더와 동일 1825일 창·집계를 써 배지==헤더를 유지한다.
from datetime import datetime, timedelta

from filters import (
    _build_q3_health_items,
    _q3_med_since,
    _sum_daily_max_presc,
    _cutoffs,
    Q3_MED_DAYS_THRESHOLD,
)
from pipeline.disease_aggregator import new_disease
from pipeline.result_builder import build_summary_reports

TODAY = datetime(2026, 6, 15)
REF = datetime(2026, 6, 15)
_D3M, _D1Y, _D5Y, _D10Y = _cutoffs(REF)  # 달력 5년 경계
MED5Y = _q3_med_since(REF)              # BOHUMFIT-032: 투약 판정창 1825일

Q3_TITLE = "[3번질문] 5년 이내 입원·수술·통원·투약"  # BOHUMFIT-034


def _ymd(days_ago: int) -> str:
    return (TODAY - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def mk_disease(code, name, episode, visit_days=None):
    """episode: {날짜문자열: {병원: 투약일수}} / visit_days: 통원 날짜 list."""
    s = new_disease()
    s["diag_code"] = code
    s["name"] = name
    s["has_pharma"] = True
    s["med_dates_pharma_episode"] = {d: dict(hosp) for d, hosp in episode.items()}
    # med_dates_pharma 는 날짜별 최대(집계 동치 확인용)
    s["med_dates_pharma"] = {d: max(hosp.values()) for d, hosp in episode.items()}
    all_dates = sorted(episode.keys())
    for d in (visit_days or []):
        s["visit_dates"].add(d)
        s["visit_events"].append(d)
        all_dates.append(d)
    all_dates = sorted(set(all_dates))
    s["first_date"] = all_dates[0]
    s["latest_date"] = all_dates[-1]
    return {code: s}


def _q3_health_items(ds):
    return _build_q3_health_items(ds, REF)


def _q3_summary_row(ds, code):
    items = _q3_health_items(ds)
    std, easy, flagged, merged = build_summary_reports(
        ds, items, [], {}, "건강체", TODAY,
    )
    rows = [r for r in std.get(Q3_TITLE, []) if r["code"] == code]
    return rows[0] if rows else None, items


# ── 1) 핵심: 배지 == 헤더 (기존 MAX≠SUM 입력에서 동일해짐) ────────────────
def test_badge_equals_header_sum_when_max_differs():
    # 두 날짜 20일 + 12일 → SUM=32(헤더), MAX=20(구 배지). 32>=30 → MED-30D 발동.
    ds = mk_disease("J32", "만성부비동염", {_ymd(100): {"이비인후과A": 20}, _ymd(50): {"이비인후과A": 12}})
    header_sum = _sum_daily_max_presc(ds["J32"]["med_dates_pharma_episode"], MED5Y)
    assert header_sum == 32
    row, items = _q3_summary_row(ds, "J32")
    assert row is not None, "Q3 행이 있어야 함(투약 32일 발동)"
    # 배지 == 헤더(SUM) == 32 (구버전이면 20 이었음)
    assert row["med_days"] == 32
    med_item = next(it for it in items if it.get("_rule_id") == "R-H-Q3-MED-30D")
    assert med_item["med_days"] == 32                       # 헤더 항목 값
    assert "32일" in med_item["reason"]                     # 헤더 문구 숫자


# ── 2) 14+14 → 둘 다 28, 30일 미발동 (통원으로 행 확보) ───────────────────
def test_sum_28_no_med_trigger():
    visits = [_ymd(d) for d in (300, 280, 260, 240, 220, 200, 180)]   # 통원 7회 → 행 확보
    ds = mk_disease("N95", "폐경후위축성질염",
                    {_ymd(120): {"산부인과A": 14}, _ymd(80): {"산부인과A": 14}},
                    visit_days=visits)
    assert _sum_daily_max_presc(ds["N95"]["med_dates_pharma_episode"], MED5Y) == 28
    row, items = _q3_summary_row(ds, "N95")
    assert row is not None and row["med_days"] == 28        # 배지 28
    assert not any(it.get("_rule_id") == "R-H-Q3-MED-30D" for it in items)  # 30일 미발동
    assert any(it.get("_rule_id") == "R-H-Q3-VISIT-7" for it in items)


# ── 3) 14+14+3 → 31, 발동 ────────────────────────────────────────────────
def test_sum_31_triggers():
    ds = mk_disease("B35", "체부백선",
                    {_ymd(120): {"피부과A": 14}, _ymd(80): {"피부과A": 14}, _ymd(40): {"피부과A": 3}})
    assert _sum_daily_max_presc(ds["B35"]["med_dates_pharma_episode"], MED5Y) == 31
    row, items = _q3_summary_row(ds, "B35")
    assert row is not None and row["med_days"] == 31
    assert any(it.get("_rule_id") == "R-H-Q3-MED-30D" for it in items)


# ── 4) 단일 30 → 발동 ────────────────────────────────────────────────────
def test_single_30_triggers():
    ds = mk_disease("E11", "당뇨", {_ymd(200): {"내과A": 30}})
    assert _sum_daily_max_presc(ds["E11"]["med_dates_pharma_episode"], MED5Y) == 30
    row, items = _q3_summary_row(ds, "E11")
    assert row is not None and row["med_days"] == 30
    assert any(it.get("_rule_id") == "R-H-Q3-MED-30D" for it in items)


# ── 5) 판정창 경계: 1825일 전 포함(>=), 1826일 전 제외 ─────────────────
def test_window_boundary_include_exact_exclude_past():
    on_day  = _ymd(1825)  # 1825일 전 → 포함
    off_day = _ymd(1826)  # 1826일 전 → 제외
    on = mk_disease("K21", "역류성식도염", {on_day: {"내과A": 30}})
    assert _sum_daily_max_presc(on["K21"]["med_dates_pharma_episode"], MED5Y) == 30
    row_on, items_on = _q3_summary_row(on, "K21")
    assert row_on is not None and row_on["med_days"] == 30
    assert any(it.get("_rule_id") == "R-H-Q3-MED-30D" for it in items_on)
    off = mk_disease("K21", "역류성식도염", {off_day: {"내과A": 30}})
    assert _sum_daily_max_presc(off["K21"]["med_dates_pharma_episode"], MED5Y) == 0
    row_off, items_off = _q3_summary_row(off, "K21")
    assert row_off is None
    assert not any(it.get("_rule_id") == "R-H-Q3-MED-30D" for it in items_off)


# ── 6) 항등: 임의 입력에서 배지 == 헤더(SUM) ─────────────────────────────
def test_badge_header_identity_general():
    ds = mk_disease("M54", "요통",
                    {_ymd(900): {"정형A": 7}, _ymd(600): {"정형A": 28}, _ymd(300): {"정형B": 5}})
    header = _sum_daily_max_presc(ds["M54"]["med_dates_pharma_episode"], MED5Y)  # 7+28+5=40
    assert header == 40
    row, items = _q3_summary_row(ds, "M54")
    assert row is not None
    assert row["med_days"] == header                        # 배지 == 헤더
    med_item = next(it for it in items if it.get("_rule_id") == "R-H-Q3-MED-30D")
    assert row["med_days"] == med_item["med_days"]


# ── 7) 간편 무영향: 동일 disease_stats 의 간편(easy) 판정/플래그 불변 ──────
def test_easy_judgment_unaffected():
    # 간편은 30일 투약 룰 대상 아님 — 간편 풀에 항목을 넣지 않으면 easy 리포트는 비어야 한다.
    ds = mk_disease("J32", "만성부비동염", {_ymd(100): {"이비인후과A": 20}, _ymd(50): {"이비인후과A": 12}})
    items = _q3_health_items(ds)
    std, easy, flagged, merged = build_summary_reports(ds, items, [], {}, "건강체", TODAY)
    # 건강체 Q3 만 채워지고, 간편(easy)은 투약 30일 판정이 없으므로 빈 dict.
    assert sum(len(v) for v in easy.values()) == 0
