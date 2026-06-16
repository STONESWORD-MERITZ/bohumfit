# BOHUMFIT-061 입원/통원 집계 회귀 — 익명 합성 픽스처(실데이터 아님).
from datetime import datetime
from pipeline.disease_aggregator import build_disease_stats
from pipeline.helpers import normalize_code, disclosure_group_code
from filters import _build_q3_health_items, _adm_in_range, _subtract_years

TODAY = datetime(2026, 6, 15)
REF = datetime(2026, 6, 15)
D5Y = _subtract_years(REF, 5)


def mk(date, hosp, days, code, name="요추 염좌", io="입원", dept=""):
    return {"진료개시일": date, "요양기관명": hosp, "입내원구분": io, "요양일수": str(days),
            "상병코드": code, "상병명": name, "진단과": dept, "_ftype": "basic"}


def stats(recs):
    st, *_ = build_disease_stats(recs, TODAY)
    return st


# 1) 입원 2건: 같은 KCD3(S33), 같은날 다른 병원 6일+2일 → admission 2건
def test_two_admissions_same_day_diff_hospital():
    st = stats([mk("2024-03-10", "한방병원A", 6, "S335"), mk("2024-03-10", "요양병원B", 2, "S336")])
    assert "S33" in st and set(st) == {"S33"}        # KCD3 한 그룹
    adm = st["S33"]["inpatient_admissions"]
    assert len(adm) == 2                              # 같은날 다른 병원 = 별개
    assert _adm_in_range(adm, D5Y) == 2


# 2) 같은날 같은 병원 + 0일 분리 → 0일 무시, 1건
def test_zeroday_ignored_same_hospital():
    st = stats([mk("2024-03-10", "한방병원A", 6, "S335"), mk("2024-03-10", "한방병원A", 0, "S335")])
    assert len(st["S33"]["inpatient_admissions"]) == 1
    assert st["S33"]["inpatient_dates"] == {"2024-03-10"}
    assert _adm_in_range(st["S33"]["inpatient_admissions"], D5Y) == 1


# 3) M75 통원 7회 → Q3 통원 트리거
def test_m75_visit_7_triggers_q3():
    recs = [mk(f"2024-{m:02d}-05", "정형외과의원", 1, "M751", io="외래") for m in range(1, 8)]
    st = stats(recs)
    items = _build_q3_health_items(st, REF)
    assert any("통원" in (it.get("reason") or "") and it.get("visit_count", 0) >= 7 for it in items)


# 4) L02 9회 통원 + 약국 1행 → 약국은 통원에서 제외(9회)
def test_l02_visit_excludes_pharmacy():
    recs = [mk(f"2024-{m:02d}-05", "피부과의원", 1, "L020", io="외래") for m in range(1, 10)]
    recs.append(mk("2024-10-06", "OO약국", 1, "L020", io="약국"))
    st = stats(recs)
    assert len(st["L02"]["visit_dates"]) == 9        # 약국 제외


# 5) 진단과='일반의' 기본진료 → BOHUMFIT-040: 유효코드라도 통원 미집계(예외 없이 제외)
def test_general_dept_excluded():
    st = stats([mk("2024-03-10", "OO의원", 1, "K297", name="위염", io="외래", dept="일반의")])
    assert "K29" not in st


# 6) 정규화·KCD3 그룹핑 단위
def test_normalize_and_kcd3_grouping():
    assert normalize_code("AS33.5") == "S335"        # 양방 A 접두 제거
    assert normalize_code("BM75.1") == "M751"        # 한방 B 접두 제거
    assert disclosure_group_code("S335") == "S33"
    assert disclosure_group_code("M751") == "M75"
    assert disclosure_group_code("M545") == "M54"
    assert disclosure_group_code("M790") == "M79"
    assert disclosure_group_code("M54") != disclosure_group_code("M79")   # 3자리 분리 유지
    assert disclosure_group_code("$") == ""           # 공란/$ 제외
