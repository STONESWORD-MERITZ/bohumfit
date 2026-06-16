# BOHUMFIT-034 질문 재편 회귀 — 익명 합성 픽스처(실데이터 아님).
#  Q3=0~5년 입원·수술·통원·투약 / Q4 신설=5~10년 입원(확정)·수술(확정+공단 의심 강/약)
#  / 기존 Q4 중대질환→Q5. 입원·수술 Q3(0~5)·Q4(5~10) 비중첩.
from datetime import datetime, timedelta

from filters import build_code_based_items, PRODUCT_HEALTH
from pipeline.disease_aggregator import new_disease
from pipeline.result_builder import build_summary_reports

TODAY = datetime(2026, 6, 15)
REF = datetime(2026, 6, 15)
Q4_TITLE = "[4번질문] 5년 초과 10년 이내 입원·수술"
Q3_TITLE = "[3번질문] 5년 이내 입원·수술·통원·투약"
Q5_TITLE = "[5번질문] 5년 이내 10대질환"


def _ymd(days_ago):
    return (TODAY - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def mk(code, name="질환", inpatient=None, surgery=None, suspected=None, grade="", major_visit=None):
    s = new_disease()
    s["diag_code"] = code
    s["name"] = name
    for d in (inpatient or []):
        s["inpatient_dates"].add(d)
        s["inpatient_admissions"].add((d, "OO병원"))
        s["_inpatient_days_map"][d] = 5
    for d in (surgery or []):
        s["surgery_dates"].add(d); s["surgeries"].add("관혈적정복술")
    for d in (suspected or []):
        s["surgery_suspected_dates"].add(d)
    if grade:
        s["surgery_suspected_grade"] = grade
    for d in (major_visit or []):
        s["visit_dates"].add(d); s["visit_events"].append(d)
    alld = sorted((inpatient or []) + (surgery or []) + (suspected or []) + (major_visit or []))
    s["first_date"] = alld[0] if alld else "2099-12-31"
    s["latest_date"] = alld[-1] if alld else "2000-01-01"
    return {code: s}


def _rids(ds):
    return {it["_rule_id"] for it in build_code_based_items(ds, REF, PRODUCT_HEALTH)}


def _rows(ds, title):
    std, *_ = build_summary_reports(ds, build_code_based_items(ds, REF, PRODUCT_HEALTH), [], {}, "건강체", TODAY)
    return std.get(title, [])


# ── 1) 5~10년 입원(확정) → Q4 INP-510Y, Q3엔 없음 ────────────────────────
def test_inpatient_5to10y_in_q4_not_q3():
    ds = mk("S33", "골절", inpatient=[_ymd(2555)])   # 7년 전
    ids = _rids(ds)
    assert "R-H-Q4-INP-510Y" in ids
    assert "R-H-Q3-INP-5Y" not in ids
    assert any(r["code"] == "S33" for r in _rows(ds, Q4_TITLE))


# ── 2) 0~5년 입원 → Q3 INP-5Y, Q4엔 없음 ─────────────────────────────────
def test_inpatient_0to5y_in_q3_not_q4():
    ds = mk("S33", "골절", inpatient=[_ymd(1000)])   # 2.7년 전
    ids = _rids(ds)
    assert "R-H-Q3-INP-5Y" in ids
    assert "R-H-Q4-INP-510Y" not in ids


# ── 3) ★ 비중복: 입원 3년전+7년전 → Q3·Q4 각각, 중복 아님 ─────────────────
def test_inpatient_split_q3_q4_no_overlap():
    ds = mk("S33", "골절", inpatient=[_ymd(1000), _ymd(2555)])
    ids = _rids(ds)
    assert "R-H-Q3-INP-5Y" in ids and "R-H-Q4-INP-510Y" in ids
    # 각 질문 행의 입원일이 서로 겹치지 않음
    q3 = [r for r in _rows(ds, Q3_TITLE) if r["code"] == "S33"][0]
    q4 = [r for r in _rows(ds, Q4_TITLE) if r["code"] == "S33"][0]
    assert set(q3["inpatient_dates"]).isdisjoint(set(q4["inpatient_dates"]))
    assert _ymd(1000) in q3["inpatient_dates"] and _ymd(2555) in q4["inpatient_dates"]


# ── 4) 5~10년 확정 수술 → Q4 SURG-510Y ───────────────────────────────────
def test_confirmed_surgery_5to10y_in_q4():
    ds = mk("K35", "충수", surgery=[_ymd(2555)])
    assert "R-H-Q4-SURG-510Y" in _rids(ds)


# ── 5) ★ 공단 수술 '의심'(강) 5~10년 → Q4 SURG-SUSP-510Y + 등급 배지 Q4 한정 ─
def test_nhis_suspected_surgery_5to10y_in_q4_with_grade():
    ds = mk("M51", "추간판", suspected=[_ymd(2555)], grade="강")
    assert "R-H-Q4-SURG-SUSP-510Y" in _rids(ds)
    q4 = [r for r in _rows(ds, Q4_TITLE) if r["code"] == "M51"]
    assert q4 and q4[0]["surgery_suspected_grade"] == "강"   # 등급은 Q4 행에 노출


def test_suspected_grade_not_on_q3():
    # 5년내 입원(Q3) + 공단 의심(5~10년) 동시 → 등급 배지는 Q4에만, Q3엔 빈값
    ds = mk("M51", "추간판", inpatient=[_ymd(1000)], suspected=[_ymd(2555)], grade="약")
    q3 = [r for r in _rows(ds, Q3_TITLE) if r["code"] == "M51"]
    assert q3 and q3[0]["surgery_suspected_grade"] == ""     # Q3엔 등급 미노출


# ── 6) ★ 중대질환 → Q5 (기존 Q4에서 이동), 판정 불변 ─────────────────────
def test_major_disease_moved_to_q5():
    ds = mk("C50", "유방암", major_visit=[_ymd(1000)])   # 5년내 진료 + 10대질환
    ids = _rids(ds)
    assert "R-H-Q5-MAJOR-5Y" in ids
    assert "R-H-Q4-MAJOR-5Y" not in ids                  # 구 rule_id 소멸
    assert any(r["code"] == "C50" for r in _rows(ds, Q5_TITLE))


# ── 7) 라벨에 "10년 이내" 잔존 없음(Q3=5년, Q4=5년 초과 10년) ──────────────
def test_labels_no_stale_10y():
    ds = mk("S33", "골절", inpatient=[_ymd(1000), _ymd(2555)])
    std, *_ = build_summary_reports(ds, build_code_based_items(ds, REF, PRODUCT_HEALTH), [], {}, "건강체", TODAY)
    titles = " ".join(std.keys())
    assert "10년 이내 입원·수술·통원·투약" not in titles      # 구 Q3 라벨 소멸
    assert "5년 이내 입원·수술·통원·투약" in titles
    assert "5년 초과 10년 이내 입원·수술" in titles


# ── 8) 결정성 ────────────────────────────────────────────────────────────
def test_determinism():
    def snap():
        ds = mk("S33", "골절", inpatient=[_ymd(1000), _ymd(2555)], suspected=[_ymd(2555)], grade="강")
        return sorted(_rids(ds))
    assert snap() == snap()
