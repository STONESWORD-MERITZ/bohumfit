# BOHUMFIT-043 040 롤백 + 약국 기관명 기반 통원 제외 회귀 — 익명 합성 픽스처(실데이터 아님).
#
# 040(_keep_basic_general_row→False)의 진단과='일반의' 행 전체 skip을 전면 롤백.
# 일반의 행은 통원·입원·수술·투약·detail 링크 모두 정상 작동하고,
# 통원(visit_dates) 제외는 '요양기관명에 약국 포함'일 때만 적용한다(행 자체는 보존).
from datetime import datetime
from pipeline.disease_aggregator import build_disease_stats

TODAY = datetime(2026, 6, 15)


def basic(date, hosp, code, name, dept, io="외래", days=1):
    return {"진료개시일": date, "요양기관명": hosp, "입내원구분": io, "요양일수": str(days),
            "상병코드": code, "상병명": name, "진단과": dept, "_ftype": "basic"}


def detail(date, hosp, proc):
    return {"진료개시일": date, "요양기관명": hosp, "처치및수술": proc, "_ftype": "detail"}


def pharma(date, hosp, drug, days, code=""):
    r = {"진료개시일": date, "요양기관명": hosp, "입내원구분": "외래", "약품명": drug,
         "요양일수": str(days), "_ftype": "pharma"}
    if code:
        r["상병코드"] = code
    return r


def stats(recs):
    st, *_ = build_disease_stats(recs, TODAY)
    return st


# ── ① 일반의 + 유효코드 → 통원 정상 집계 (040 롤백 확인) ──────────────────
def test_general_valid_code_now_counted():
    st = stats([basic("2024-03-10", "OO의원", "K297", "위염", dept="일반의")])
    assert "K29" in st and "2024-03-10" in st["K29"]["visit_dates"]


# ── ② 일반의 + 입원 → inpatient 집계 정상 ────────────────────────────────
def test_general_inpatient_counted():
    st = stats([basic("2024-04-10", "OO의원", "S330", "골절", dept="일반의", io="입원", days=5)])
    assert any(s.get("inpatient_dates") for s in st.values())


# ── ③ 일반의 + 같은날 detail 수술 → surgery 집계 정상 (detail-link 복구) ──
def test_general_detail_surgery_counted():
    st = stats([
        basic("2024-04-01", "행복외과의원", "K359", "충수염", dept="일반의"),
        detail("2024-04-01", "행복외과의원", "충수절제술"),
    ])
    assert any(s.get("surgery_dates") for s in st.values())


# ── ④ 일반의 + 같은날 pharma → 질병에 투약 부착 정상 (pharma 앵커 복구) ──
def test_general_pharma_attached():
    st = stats([
        basic("2024-05-01", "OO의원", "K297", "위염", dept="일반의"),
        pharma("2024-05-01", "OO의원", "위장약", 30),
    ])
    # PHARMA| 고립 그룹이 아니라 질병군에 투약이 부착되어야 함.
    assert any(not k.startswith("PHARMA|") and s.get("med_dates_pharma")
               for k, s in st.items())


# ── ⑤ 기관명='약국약국' → visit_dates 미집계 (약국 통원 제외) ─────────────
def test_pharmacy_name_visit_excluded():
    st = stats([basic("2024-03-10", "약국약국", "K297", "위염", dept="내과")])
    assert all(not s.get("visit_dates") for s in st.values())


# ── ⑥ 기관명='내과의원' → visit_dates 정상 집계 ──────────────────────────
def test_clinic_name_visit_counted():
    st = stats([basic("2024-03-10", "행복내과의원", "K297", "위염", dept="내과")])
    assert "K29" in st and "2024-03-10" in st["K29"]["visit_dates"]


# ── ⑦ 약국 기관명이라도 입원은 보존(통원만 제외) ─────────────────────────
def test_pharmacy_name_inpatient_preserved():
    st = stats([basic("2024-04-10", "약국약국", "S330", "골절", dept="내과", io="입원", days=5)])
    assert any(s.get("inpatient_dates") for s in st.values())


# ── ⑧ 결정성(determinism) ────────────────────────────────────────────────
def test_determinism():
    recs = [basic("2024-03-10", "OO의원", "K297", "위염", dept="일반의"),
            basic("2024-05-20", "약국약국", "K297", "위염", dept="내과")]
    a = sorted(stats(recs)["K29"]["visit_dates"])
    b = sorted(stats(recs)["K29"]["visit_dates"])
    assert a == b
