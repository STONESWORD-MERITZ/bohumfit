# BOHUMFIT-213: 고지 필터 결과에 원본 근거(진료일·병의원) 부착 회귀 — 익명·합성 픽스처.
#
# 취지: 결과가 "입원 (N일)"처럼 일수만 보여 설계사가 원본 PDF를 다시 뒤지던 병목 제거.
# 원칙: 판정 로직·임계·창 계산(5년/10년/일수)은 불변 — 표시용 근거 필드만 추가.
#  - 입원: inpatient_periods 회차별 {start, end, days, hospital}
#  - 통원: visit_records {date, hospital, count}
#  - 투약: med_records {date, days, hospital}
#  - 수술: surgery_events {date, hospital}
# 복사문(_kakao_item)은 입원 회차 줄 끝에 병의원명을 덧붙인다(없으면 기존 형식 그대로).
import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from filters import build_code_based_items, PRODUCT_EASY, PRODUCT_HEALTH
from pipeline.disease_aggregator import new_disease
from pipeline.helpers import _inpatient_periods_in_range
from pipeline.result_builder import build_summary_reports

import main

TODAY = datetime(2026, 7, 12)
REF = TODAY
Q2_EASY = "[2번질문] 10년 이내 입원·수술"
Q3_HEALTH = "[3번질문] 5년 이내 입원·수술·통원·투약"


def _ymd(days_ago: int) -> str:
    return (TODAY - timedelta(days=days_ago)).strftime("%Y-%m-%d")


# ── 픽스처: 전십자인대 3회 입원(각기 다른 병원) + 수술 1회 — 실사례 구조의 익명 재현 ──

INP = [
    ("2022-12-19", 10, "가온정형외과"),
    ("2024-10-07", 9, "한마음병원"),
    ("2025-08-03", 4, "서울관절의원"),
]


def _s83_stat(hospital_on: bool = True, rows=None):
    s = new_disease()
    s["diag_code"] = "S83"
    s["name"] = "전십자인대의 파열"
    for d, days, hosp in (rows or INP):
        h = hosp if hospital_on else ""
        s["inpatient_dates"].add(d)
        s["inpatient_admissions"].add((d, h))
        s["_inpatient_days_map"][d] = days
        s["inpatient_periods"].append({
            "start": d,
            "end": (datetime.strptime(d, "%Y-%m-%d") + timedelta(days=days - 1)).strftime("%Y-%m-%d"),
            "days": days,
            "hospital": h,
        })
        if h:
            s["hospital_dates"][d] = h
    s["first_date"] = min(d for d, *_ in (rows or INP))
    s["latest_date"] = max(
        (datetime.strptime(d, "%Y-%m-%d") + timedelta(days=days - 1)).strftime("%Y-%m-%d")
        for d, days, *_ in (rows or INP)
    )
    return s


def mk_s83(hospital_on: bool = True):
    s = _s83_stat(hospital_on)
    for d, days, hosp in INP:
        h = hosp if hospital_on else ""
        s["hospitals"].add(h)
    # 수술 1회(입원 2회차와 같은 날)
    s["surgeries"].add("십자인대재건술")
    s["surgery_dates"].add("2024-10-07")
    return {"S83": s}


def mk_s83_split_keys():
    """실 PDF 동형: 같은 대표 코드가 `S83|날짜` 키로 나뉘어도 표시 근거는 합쳐져야 한다."""
    out = {}
    for d, days, hosp in INP:
        s = _s83_stat(rows=[(d, days, hosp)])
        s["hospitals"].add(hosp)
        out[f"S83|{d}"] = s
    out["S83|2024-10-07"]["surgeries"].add("십자인대재건술")
    out["S83|2024-10-07"]["surgery_dates"].add("2024-10-07")
    return out


def _easy_q2_row(ds):
    std, easy, *_ = build_summary_reports(
        ds,
        build_code_based_items(ds, REF, PRODUCT_HEALTH),
        build_code_based_items(ds, REF, PRODUCT_EASY),
        {}, "건강체", TODAY,
    )
    rows = [r for r in easy.get(Q2_EASY, []) if r["code"] == "S83"]
    return rows[0] if rows else None


# ── ① helpers: 회차 dedup 시 병원 보존 ───────────────────────────────────────


def test_periods_in_range_keeps_hospital():
    s = new_disease()
    s["inpatient_periods"] = [
        {"start": "2024-10-07", "end": "2024-10-15", "days": 9, "hospital": "한마음병원"},
        # 같은 회차의 중복 행(병원 빈값) — 병원이 있는 값이 보존돼야 한다.
        {"start": "2024-10-07", "end": "2024-10-15", "days": 9, "hospital": ""},
    ]
    out = _inpatient_periods_in_range(s, datetime.min)
    assert len(out) == 1
    assert out[0]["hospital"] == "한마음병원"
    assert out[0]["days"] == 9


def test_periods_in_range_backfills_hospital_on_later_row():
    s = new_disease()
    s["inpatient_periods"] = [
        {"start": "2024-10-07", "end": "2024-10-15", "days": 9},                      # 구형(병원 없음)
        {"start": "2024-10-07", "end": "2024-10-15", "days": 9, "hospital": "한마음병원"},  # 뒤에 병원 등장
    ]
    out = _inpatient_periods_in_range(s, datetime.min)
    assert len(out) == 1 and out[0]["hospital"] == "한마음병원"


# ── ② result_builder: 입원 회차 근거 + 판정 필드 불변 ──────────────────────


def test_easy_q2_item_carries_inpatient_hospital_evidence():
    row = _easy_q2_row(mk_s83())
    assert row is not None
    periods = sorted(row["inpatient_periods"], key=lambda p: p["start"])
    assert [(p["start"], p["days"], p["hospital"]) for p in periods] == [
        ("2022-12-19", 10, "가온정형외과"),
        ("2024-10-07", 9, "한마음병원"),
        ("2025-08-03", 4, "서울관절의원"),
    ]
    # 판정 수치·문구 불변(표시 근거만 추가).
    assert row["inpatient"] == 23
    assert row["inpatient_count"] == 3
    assert "입원" in row["detail"] and "(23일)" in row["detail"]
    # 수술 근거: 날짜 + 당일 병의원.
    assert row["surgery_events"] == [{"date": "2024-10-07", "hospital": "한마음병원"}]

    split_row = _easy_q2_row(mk_s83_split_keys())
    split_periods = sorted(split_row["inpatient_periods"], key=lambda p: p["start"])
    assert [(p["start"], p["days"], p["hospital"]) for p in split_periods] == [
        ("2022-12-19", 10, "가온정형외과"),
        ("2024-10-07", 9, "한마음병원"),
        ("2025-08-03", 4, "서울관절의원"),
    ]
    assert split_row["inpatient"] == 23


def test_judgment_identical_without_hospital_info():
    """병원 정보가 없어도(빈 문자열) 판정 필드·문구는 동일 — 근거는 공란일 뿐."""
    with_h = _easy_q2_row(mk_s83(hospital_on=True))
    no_h = _easy_q2_row(mk_s83(hospital_on=False))
    for k in ("detail", "inpatient", "inpatient_count", "first_date", "latest_date"):
        assert with_h[k] == no_h[k]
    assert all(p["hospital"] == "" for p in no_h["inpatient_periods"])


# ── ③ 통원·투약 근거 (건강체 Q3 — 판정과 동일 창·동일 원천) ────────────────


def mk_k21_visits_med():
    s = new_disease()
    s["diag_code"] = "K21"
    s["name"] = "위-식도역류병"
    visit_days = [_ymd(30 * i + 10) for i in range(7)]  # 5년 내 7일(통원 트리거)
    for d in visit_days:
        s["visit_dates"].add(d)
        s["visit_events"].append(d)
        s["hospital_dates"][d] = "속편한내과"
    s["visit_events"].append(visit_days[0])  # 같은 날 2행 → count=2
    s["hospital_dates"][visit_days[0]] = "속편한내과"
    s["has_pharma"] = True
    s["med_dates_pharma_episode"] = {
        visit_days[0]: {"속편한내과": 20},
        visit_days[1]: {"속편한내과": 12},
    }
    s["med_dates_pharma"] = {visit_days[0]: 20, visit_days[1]: 12}
    s["first_date"] = min(visit_days)
    s["latest_date"] = max(visit_days)
    return {"K21": s}, visit_days


def test_q3_visit_and_med_records_evidence():
    ds, visit_days = mk_k21_visits_med()
    std, _easy, *_ = build_summary_reports(
        ds,
        build_code_based_items(ds, REF, PRODUCT_HEALTH),
        build_code_based_items(ds, REF, PRODUCT_EASY),
        {}, "건강체", TODAY,
    )
    rows = [r for r in std.get(Q3_HEALTH, []) if r["code"] == "K21"]
    assert rows, "Q3 통원/투약 항목이 있어야 함"
    row = rows[0]
    # 통원 근거: 날짜별 {병원, 행수} — 판정 카운트(visit)와 합이 일치.
    vr = row["visit_records"]
    assert {v["date"] for v in vr} == set(visit_days)
    assert all(v["hospital"] == "속편한내과" for v in vr)
    assert sum(v["count"] for v in vr) == row["visit"] == 8  # 7일 + 중복 1행
    dup = [v for v in vr if v["date"] == sorted(visit_days)[0] or v["count"] == 2]
    assert any(v["count"] == 2 for v in vr)
    # 투약 근거: 처방일·일수·병원 — 판정 med_days(합산)와 정합.
    mr = sorted(row["med_records"], key=lambda m: m["date"])
    assert [(m["days"], m["hospital"]) for m in mr] == [(20, "속편한내과"), (12, "속편한내과")] or \
           [(m["days"], m["hospital"]) for m in mr] == [(12, "속편한내과"), (20, "속편한내과")]
    assert row["med_days"] == 32
    assert dup is not None


# ── ④ 복사문: 회차 줄 병원 표기 + 폴백/무병원 하위 호환 ─────────────────────


def _kakao(items):
    return main._build_kakao_message("간편심사", date(2026, 7, 12), {Q2_EASY: items})


def _base_item(**over):
    base = {
        "first_date": "2022-12-19", "latest_date": "2025-08-06",
        "display_code": "S83", "code": "S83", "name": "전십자인대의 파열",
        "visit": 0, "med_days": 0, "inpatient": 23, "inpatient_count": 3,
        "inpatient_periods": [], "surgeries": [], "surgery_suspected": [],
        "surgery_suspected_grade": "", "detail": "10년이내 입원 (23일)",
        "hospitals": ["가온정형외과", "한마음병원"],
    }
    base.update(over)
    return base


def test_kakao_period_lines_include_hospital():
    item = _base_item(inpatient_periods=[
        {"start": d, "end": (datetime.strptime(d, "%Y-%m-%d") + timedelta(days=n - 1)).strftime("%Y-%m-%d"),
         "days": n, "hospital": h}
        for d, n, h in INP
    ])
    msg = _kakao([item])
    assert "2022-12-19 ~ 2022-12-28 / 입원10일 / S83 / (양방)전십자인대의 파열 / 가온정형외과" in msg
    assert "2024-10-07 ~ 2024-10-15 / 입원9일 / S83 / (양방)전십자인대의 파열 / 한마음병원" in msg
    assert "2025-08-03 ~ 2025-08-06 / 입원4일 / S83 / (양방)전십자인대의 파열 / 서울관절의원" in msg
    assert "입원 총 3회 · 합산 23일" in msg


def test_kakao_period_line_without_hospital_keeps_legacy_format():
    item = _base_item(
        inpatient=10, inpatient_count=1, detail="10년이내 입원 (10일)",
        inpatient_periods=[{"start": "2022-12-19", "end": "2022-12-28", "days": 10, "hospital": ""}],
    )
    msg = _kakao([item])
    # 병원이 없으면 꼬리(" / ") 없이 기존 형식 그대로 줄이 끝난다.
    assert "2022-12-19 ~ 2022-12-28 / 입원10일 / S83 / (양방)전십자인대의 파열\n" in msg


def test_kakao_outpatient_fallback_appends_hospital_summary():
    item = _base_item(
        inpatient=0, inpatient_count=0, visit=5,
        first_date="2025-01-01", latest_date="2025-02-01",
        code="K21", display_code="K21", name="위-식도역류병",
        detail="통원 5회", inpatient_periods=[],
        hospitals=["속편한내과", "우리가정의원"],
    )
    msg = _kakao([item])
    assert "2025-01-01 ~ 2025-02-01 / 통원5회 / K21 / (양방)위-식도역류병 / 속편한내과 외 1곳" in msg
