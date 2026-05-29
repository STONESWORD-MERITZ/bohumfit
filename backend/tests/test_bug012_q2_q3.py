# -*- coding: utf-8 -*-
"""SURIT-BUG-012 회귀 테스트.

- 건강체 Q3: 입원·수술 OR 통원7회 OR 투약30일(누적 경로=_max_presc) 단독 트리거 + 경계.
- 간편 Q2: 입원·수술만 (통원·투약·1년진단 미혼입).
"""
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from filters import (  # noqa: E402
    _build_q3_health_items,
    _build_q2_easy_items,
    Q3_VISIT_COUNT_THRESHOLD,
    Q3_MED_DAYS_THRESHOLD,
)

REF = datetime(2026, 5, 12)
# 10년 창 = 2016-05-12. 아래 날짜는 모두 창 내부.


def _disease(*, code="K21", name="역류성식도염", first="", latest="",
             visits=(), inpatients=(), surgeries=(), pharma_dates=None):
    return {
        "visit_dates": set(visits),
        "inpatient_dates": set(inpatients),
        "surgery_dates": set(surgeries),
        "surgeries": {"수술"} if surgeries else set(),
        "med_dates_pharma": dict(pharma_dates or {}),
        "_inpatient_days_map": {d: 1 for d in (inpatients or [])},
        "hospitals": {"서울내과"},
        "visit_events": [],
        "first_date": first or "2099-12-31",
        "latest_date": latest or "2000-01-01",
        "diag_code": code,
        "name": name,
    }


def _rule_ids(items):
    return {it["_rule_id"] for it in items}


# ── 건강체 Q3: 통원 7회 경계 ──────────────────────────────

def test_q3_health_visit_7_flags():
    """통원 7회 → R-H-Q3-VISIT-7 발동 (입원/수술 없이 단독)."""
    visits = [f"2020-01-{d:02d}" for d in range(1, 8)]  # 7개 distinct
    ds = {"K21": _disease(visits=visits, first="2020-01-01", latest="2020-01-07")}
    items = _build_q3_health_items(ds, REF)
    assert "R-H-Q3-VISIT-7" in _rule_ids(items)
    # 입원·수술 트리거는 없어야 함
    assert "R-H-Q3-INP-10Y" not in _rule_ids(items)
    assert "R-H-Q3-SURG-10Y" not in _rule_ids(items)


def test_q3_health_visit_6_not_flagged():
    """통원 6회 → 미발동 (임계 미만)."""
    visits = [f"2020-01-{d:02d}" for d in range(1, 7)]  # 6개
    ds = {"K21": _disease(visits=visits, first="2020-01-01", latest="2020-01-06")}
    items = _build_q3_health_items(ds, REF)
    assert "R-H-Q3-VISIT-7" not in _rule_ids(items)


def test_q3_visit_threshold_is_7():
    assert Q3_VISIT_COUNT_THRESHOLD == 7


# ── 건강체 Q3: 투약 30일 경계 ─────────────────────────────

def test_q3_health_med_30_flags():
    """투약 30일 → R-H-Q3-MED-30D 발동 (단독)."""
    ds = {"K21": _disease(pharma_dates={"2020-06-15": 30}, first="2020-06-15", latest="2020-06-15")}
    items = _build_q3_health_items(ds, REF)
    assert "R-H-Q3-MED-30D" in _rule_ids(items)


def test_q3_health_med_29_not_flagged():
    """투약 29일 → 미발동."""
    ds = {"K21": _disease(pharma_dates={"2020-06-15": 29}, first="2020-06-15", latest="2020-06-15")}
    items = _build_q3_health_items(ds, REF)
    assert "R-H-Q3-MED-30D" not in _rule_ids(items)


def test_q3_med_threshold_is_30():
    assert Q3_MED_DAYS_THRESHOLD == 30


# ── 건강체 Q3: 입원·수술 유지 ─────────────────────────────

def test_q3_health_inpatient_and_surgery_still_work():
    ds = {
        "K21": _disease(inpatients=["2020-03-10"], first="2020-03-10"),
        "M17": _disease(code="M17", name="무릎관절증", surgeries=["2020-07-15"], first="2020-07-15"),
    }
    items = _build_q3_health_items(ds, REF)
    ids = _rule_ids(items)
    assert "R-H-Q3-INP-10Y" in ids
    assert "R-H-Q3-SURG-10Y" in ids


# ── 간편 Q2: 입원·수술만 (통원·투약 미혼입) ───────────────

def test_easy_q2_pure_inpatient_surgery_only():
    ds = {
        "K21": _disease(inpatients=["2020-03-10"], first="2020-03-10"),
        "M17": _disease(code="M17", name="무릎관절증", surgeries=["2020-07-15"], first="2020-07-15"),
    }
    items = _build_q2_easy_items(ds, REF)
    ids = _rule_ids(items)
    assert "R-E-Q2-INP-10Y" in ids
    assert "R-E-Q2-SURG-10Y" in ids
    # 통원·투약·진단 룰 id 가 섞이면 안 됨
    assert not any("VISIT" in r or "MED" in r or "DIAG" in r for r in ids)


def test_easy_q2_visit_and_med_do_not_trigger():
    """통원 7회 + 투약 30일만 있고 입원·수술 없으면 간편 Q2 항목 0건."""
    visits = [f"2020-01-{d:02d}" for d in range(1, 8)]
    ds = {"K21": _disease(visits=visits, pharma_dates={"2020-06-15": 30}, first="2020-01-01")}
    items = _build_q2_easy_items(ds, REF)
    assert items == [], f"간편 Q2 는 입원·수술만이어야 하나 발동됨: {_rule_ids(items)}"
    # 같은 데이터로 건강체 Q3 는 통원·투약 단독 발동
    q3 = _build_q3_health_items(ds, REF)
    assert {"R-H-Q3-VISIT-7", "R-H-Q3-MED-30D"} <= _rule_ids(q3)


# ── 통원 누락 버그 (질염 14회) — 집계 단계 회귀 ─────────────
# 실측: 기침(R05) 통원 7회 / 급성질염(N76.0) 통원 14회인데 질염이 7회 룰에
# 안 잡힘. 원인은 helpers.row_is_junk — 행 전체에 '$'/'해당없음'이 하나라도
# 있으면 행 통째 폐기 → 질염 병원행의 약국코드 칸 '$ 해당없음' 때문에 14건 전부
# 탈락. 기침행은 약국코드가 R05계열이라 생존. (SURIT-BUG-012)

def _basic_row(date, code, name, dept, hosp, pharma_code=""):
    r = {"_ftype": "basic", "진료개시일": date, "주상병코드": code, "주상병명": name,
         "진단과": dept, "병·의원": hosp, "입내원구분": "외래", "내원일수": "1"}
    if pharma_code:
        r["약국코드"] = pharma_code
    return r


def test_row_is_junk_keeps_diag_row_with_pharma_placeholder():
    """약국코드 칸이 '$ 해당없음'이라도 진단 식별 내용이 있으면 junk 아님."""
    import pandas as pd
    from pipeline.helpers import row_is_junk
    keep = _basic_row("2024-04-01", "AN760", "급성질염", "산부인과", "우리산부인과",
                      pharma_code="$ 해당없음")
    drop = {"_ftype": "basic", "주상병코드": "$ 해당없음", "주상병명": "해당없음",
            "약품명": "$"}
    assert row_is_junk(pd.DataFrame([keep]).iloc[0]) is False
    assert row_is_junk(pd.DataFrame([drop]).iloc[0]) is True


def test_vulvovaginitis_visit_14_triggers_q3_rule():
    """질염 통원 14회가 집계에서 누락되지 않고 7회 룰에 걸린다 (vs 기침 7회)."""
    from datetime import datetime as _dt
    from pipeline.disease_aggregator import build_disease_stats
    from filters import _visit_count_in_range, _cutoffs

    today = _dt(2026, 5, 30)
    recs = []
    for i in range(1, 8):  # 기침 R05 — 통원 7회, 약국코드 정상
        recs.append(_basic_row("2024-03-%02d" % i, "AR05", "기침", "내과",
                               "행복내과", pharma_code="AR05"))
    for i in range(1, 15):  # 질염 N76.0 — 통원 14회, 약국코드 '$ 해당없음'
        recs.append(_basic_row("2024-04-%02d" % i, "AN760", "급성질염", "산부인과",
                               "우리산부인과", pharma_code="$ 해당없음"))

    ds, _, _, _, _ = build_disease_stats(recs, today)
    assert "N760" in ds, f"질염 그룹 누락: {list(ds.keys())}"
    d10y = _cutoffs(today)[3]
    assert _visit_count_in_range(ds["N760"], d10y) >= 14
    q3 = _build_q3_health_items(ds, today)
    vulvo = [it for it in q3 if it["code"] == "N760" and it["_rule_id"] == "R-H-Q3-VISIT-7"]
    assert vulvo, f"질염 통원 7회 룰 미발동: {_rule_ids(q3)}"
