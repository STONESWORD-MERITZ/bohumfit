# BOHUMFIT-045 Q3 5년 통원·투약·입원·수술 통합 회귀 — 익명 합성 픽스처(실 PDF/PII 아님).
#
# 배경: 운영 결함은 Q3 통원을 '1년 창'으로 집계해 통원 다수 사례가 1회로 축소되고
#   투약·입원·수술이 미표면화됐다. 현 코드(BOHUMFIT-034)는 Q3 통원·투약·입원·수술을 '5년 창'으로
#   집계한다. 본 회귀는 5년 창에서 통원 10회·투약·입원·수술이 정상 발동·표시됨을 고정해
#   1년 창으로의 회귀를 차단한다.
from datetime import datetime, timedelta

from pipeline.disease_aggregator import build_disease_stats
from filters import build_code_based_items
from pipeline.result_builder import build_summary_reports

TODAY = datetime(2026, 6, 15)
PRODUCT = "건강체/표준체 (일반심사)"
Q3 = "[3번질문] 5년 이내 입원·수술·통원·투약"


def _ymd(days_ago: int) -> str:
    return (TODAY - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def basic(date, code, name, io="외래", days=1, dept="내과", hosp="행복내과의원"):
    return {"진료시작일": date, "병·의원&약국": hosp, "진단과": dept, "입원/외래": io,
            "주상병코드": code, "주상병명": name, "내원일수": str(days), "_ftype": "basic"}


def pharma(date, drug, days, hosp="행복내과의원"):
    return {"진료시작일": date, "병·의원&약국": hosp, "약품명": drug, "성분명": drug,
            "총투약일수": str(days), "_ftype": "pharma"}


def detail(date, proc, hosp="행복내과의원"):
    return {"진료시작일": date, "병·의원&약국": hosp, "진료내역": proc, "코드명": proc, "_ftype": "detail"}


def _q3(recs):
    st, *_ = build_disease_stats(recs, TODAY)
    items = build_code_based_items(st, TODAY, PRODUCT)
    std, _e, _f, _m = build_summary_reports(st, items, [], {}, PRODUCT, TODAY)
    rows = {r["code"]: r for r in std.get(Q3, [])}
    return st, items, rows


def _rules(items, code):
    return {it.get("_rule_id") for it in items if it.get("code") == code}


# ── ① 5년 내 통원 10회 → VISIT-7 발동 + Q3 visit=10 (운영 1년창 축소 회귀 방지) ──
def test_q3_visit_10_in_5y():
    recs = [basic(_ymd(d), "J320", "만성범부비동염")
            for d in (1700, 1600, 1500, 1000, 900, 800, 400, 300, 200, 60)]
    st, items, q3 = _q3(recs)
    assert len(st["J32"]["visit_dates"]) == 10
    assert "R-H-Q3-VISIT-7" in _rules(items, "J32")
    assert "J32" in q3 and q3["J32"]["visit"] == 10


# ── ② 5년 창 경계: 5년 초과 통원은 카운트 제외(7일자 중 5만 in-window → VISIT-7 미발동) ──
def test_q3_visit_excludes_over_5y_boundary():
    # 5년(1825일) 초과 2건 + 이내 5건. 총 7일자지만 in-window 5 → VISIT-7(>=7) 미발동.
    recs = [basic(_ymd(d), "K290", "만성위염")
            for d in (1980, 1900, 1700, 1000, 500, 300, 100)]
    st, items, _ = _q3(recs)
    assert len(st["K29"]["visit_dates"]) == 7      # 전체 일자
    assert "R-H-Q3-VISIT-7" not in _rules(items, "K29")  # 5년 내 5건뿐


# ── ③ 진단코드 + 같은날 처방(고지혈증류) → cross-ref로 MED-30D 발동 ──
def test_q3_med_crossref_to_diagnosis_code():
    recs = [basic(_ymd(200), "E785", "고지혈증"),
            pharma(_ymd(200), "ezetimibe(복합)", 90)]
    st, items, q3 = _q3(recs)
    assert "R-H-Q3-MED-30D" in _rules(items, "E78")
    assert "E78" in q3 and q3["E78"]["med_days"] >= 30


# ── ④ 입원 3일 + 같은날 세부 수술 → INP-5Y + SURG-5Y (detail-link) ──
def test_q3_inpatient_and_detail_surgery():
    recs = [basic(_ymd(300), "B448", "아스페르길루스증", io="입원", days=3),
            basic(_ymd(300), "B448", "아스페르길루스증"),  # 같은날 외래 = detail 링크 앵커
            detail(_ymd(300), "비용적출술(범발성)-내시경하에서실시한경우")]
    st, items, q3 = _q3(recs)
    rids = _rules(items, "B44")
    assert "R-H-Q3-INP-5Y" in rids and "R-H-Q3-SURG-5Y" in rids
    assert q3["B44"]["inpatient_count"] >= 1 and q3["B44"]["surgery_count"] >= 1


# ── ⑤ 창상봉합술 세부수술 → SURG-5Y ──
def test_q3_laceration_repair_surgery():
    recs = [basic(_ymd(250), "S619", "손목및손의 열린상처", hosp="튼튼정형외과의원"),
            detail(_ymd(250), "창상봉합술(안면과경부이외,단순봉합,표재성,길이2.5cm미만)", hosp="튼튼정형외과의원")]
    st, items, q3 = _q3(recs)
    assert "R-H-Q3-SURG-5Y" in _rules(items, "S61")
    assert "S61" in q3 and q3["S61"]["surgery_count"] >= 1


# ── ⑥ 결정성 ──
def test_q3_determinism():
    recs = [basic(_ymd(d), "J320", "만성범부비동염") for d in (1700, 900, 200, 60, 50, 40, 30)]
    a = sorted(_rules(_q3(recs)[1], "J32"))
    b = sorted(_rules(_q3(recs)[1], "J32"))
    assert a == b
