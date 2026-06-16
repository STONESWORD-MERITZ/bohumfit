# BOHUMFIT-040 진단과='일반의' 기본진료 통원 미집계(예외 없이 전부 제외) 회귀 — 익명 합성.
from datetime import datetime
from pipeline.disease_aggregator import build_disease_stats

TODAY = datetime(2026, 6, 15)


def basic(date, hosp, code, name, dept, io="외래", days=1):
    return {"진료개시일": date, "요양기관명": hosp, "입내원구분": io, "요양일수": str(days),
            "상병코드": code, "상병명": name, "진단과": dept, "_ftype": "basic"}


def pharma(date, code, drug, days):
    return {"진료개시일": date, "요양기관명": "OO의원", "입내원구분": "외래", "약품명": drug,
            "요양일수": str(days), "상병코드": code, "_ftype": "pharma"}


def stats(recs):
    st, *_ = build_disease_stats(recs, TODAY)
    return st


# ── 1) 일반의 + 유효상병코드 → 통원 미집계(질병군 미생성) ──────────────────
def test_general_valid_code_excluded():
    st = stats([basic("2024-03-10", "OO의원", "AL0201", "위염", dept="일반의")])
    assert "L02" not in st and not any(s.get("visit_dates") for s in st.values())


# ── 2) 일반의 + $ → 통원 미집계(기존과 동일) ─────────────────────────────
def test_general_dollar_excluded():
    st = stats([basic("2024-03-10", "OO의원", "$", "해당없음", dept="일반의")])
    assert all(not s.get("visit_dates") for s in st.values())


# ── 3) 비-일반의(내과) 유효코드 → 통원 정상 집계(무영향) ──────────────────
def test_non_general_dept_counted():
    st = stats([basic("2024-03-10", "OO내과의원", "K297", "위염", dept="내과")])
    assert "K29" in st and "2024-03-10" in st["K29"]["visit_dates"]


# ── 4) 같은 코드 내과+일반의 → 내과만 집계(일반의 행 제외) ────────────────
def test_mixed_only_non_general_counted():
    st = stats([
        basic("2024-03-10", "OO내과의원", "K297", "위염", dept="내과"),
        basic("2024-05-20", "XX의원", "K297", "위염", dept="일반의"),
    ])
    assert st["K29"]["visit_dates"] == {"2024-03-10"}     # 일반의 5/20은 제외


# ── 5) 투약(처방조제) 무영향 — pharma는 게이트 대상 아님 ─────────────────
def test_pharma_medication_unaffected():
    # pharma(처방조제)는 ftype=pharma — 일반의 게이트(basic/unknown) 대상 아님 → 투약 보존.
    st = stats([pharma("2024-04-01", "K30", "위장약", 30)])
    assert any(s.get("med_dates_pharma") for s in st.values())


# ── 6) 결정성 ────────────────────────────────────────────────────────────
def test_determinism():
    recs = [basic("2024-03-10", "OO내과의원", "K297", "위염", dept="내과"),
            basic("2024-05-20", "XX의원", "K297", "위염", dept="일반의")]
    a = sorted(stats(recs)["K29"]["visit_dates"])
    b = sorted(stats(recs)["K29"]["visit_dates"])
    assert a == b
