# BOHUMFIT-039 Q5 중대질병 코드목록 확장·리네임 + 직장항문 실손전용 회귀 — 익명 합성(PII 없음).
from datetime import datetime, timedelta

import filters
from filters import build_code_based_items, PRODUCT_HEALTH, HEALTH_Q5_CODES, INSURANCE_ONLY_Q5_CODES
from pipeline.disease_aggregator import new_disease
from pipeline.result_builder import build_summary_reports

TODAY = datetime(2026, 6, 15)
REF = datetime(2026, 6, 15)
Q3_TITLE = "[3번질문] 5년 이내 입원·수술·통원·투약"
Q5_TITLE = "[5번질문] 5년 이내 10대질환"


def _ymd(n):
    return (TODAY - timedelta(days=n)).strftime("%Y-%m-%d")


def mk(code, name, visits=None):
    s = new_disease()
    s["diag_code"] = code; s["name"] = name
    for d in (visits or []):
        s["visit_dates"].add(d); s["visit_events"].append(d)
    alld = sorted(visits or [])
    s["first_date"] = alld[0] if alld else "2099-12-31"
    s["latest_date"] = alld[-1] if alld else "2000-01-01"
    return s


def _std(ds):
    items = build_code_based_items(ds, REF, PRODUCT_HEALTH)
    std, *_ = build_summary_reports(ds, items, [], {}, "건강체", TODAY)
    return std


def _q5_rows(ds):
    return {r["code"]: r for r in _std(ds).get(Q5_TITLE, [])}


# ── 리네임 무결성 ────────────────────────────────────────────────────────
def test_rename_no_residual_and_loaded():
    import importlib, pathlib
    src = pathlib.Path(filters.__file__).read_text(encoding="utf-8-sig")
    assert "HEALTH_Q4_10CODES" not in src and "health_q4_10codes" not in src
    assert len(HEALTH_Q5_CODES) == 140


# ── 기존 중대질병 여전히 Q5 ──────────────────────────────────────────────
def test_existing_major_still_q5():
    for code in ["C50", "I63", "I10", "E11", "B20", "I34", "K74", "I20"]:
        ds = {code: mk(code, "중대질환", visits=[_ymd(100)])}
        assert code in _q5_rows(ds), code


# ── ★ 신규: I05(류마티스 승모판)→Q5, K64(치핵)→Q5, K63→Q5 미표시 ──────────
def test_new_codes_q5():
    assert "I05" in _q5_rows({"I05": mk("I05", "류마티스 승모판", visits=[_ymd(100)])})
    assert "K64" in _q5_rows({"K64": mk("K64", "치핵", visits=[_ymd(100)])})


def test_k63_excluded():
    assert "K63" not in _q5_rows({"K63": mk("K63", "결장폴립", visits=[_ymd(100)])})


def test_e78_still_excluded():
    assert "E78" not in _q5_rows({"E78": mk("E78", "고지혈증", visits=[_ymd(100)])})


# ── ★ 직장항문 실손전용 플래그 ───────────────────────────────────────────
def test_anal_q5_only_insurance_only():
    # K64가 Q5에만(1년 초과~5년 이내 진료 1회 → Q1~Q4 없음) → insurance_only
    rows = _q5_rows({"K64": mk("K64", "치핵", visits=[_ymd(500)])})
    assert rows["K64"].get("insurance_only") is True


def test_anal_with_q3_visit_not_insurance_only():
    # K64가 통원 7회로 Q3에도 잡히면 → 실손 전용 아님(일반 고지)
    ds = {"K64": mk("K64", "치핵", visits=[_ymd(d) for d in (300, 280, 260, 240, 220, 200, 180)])}
    std = _std(ds)
    assert "K64" in {r["code"] for r in std.get(Q3_TITLE, [])}     # Q3 통원7
    q5 = {r["code"]: r for r in std.get(Q5_TITLE, [])}
    assert q5.get("K64", {}).get("insurance_only") is not True     # 실손 전용 아님


def test_major_not_insurance_only():
    # 암 등은 실손 전용 안내 없음
    rows = _q5_rows({"C50": mk("C50", "유방암", visits=[_ymd(100)])})
    assert rows["C50"].get("insurance_only") is not True


# ── 결정성 ───────────────────────────────────────────────────────────────
def test_determinism():
    ds = {"K64": mk("K64", "치핵", visits=[_ymd(500)])}
    assert _q5_rows(ds)["K64"].get("insurance_only") == _q5_rows(ds)["K64"].get("insurance_only")
