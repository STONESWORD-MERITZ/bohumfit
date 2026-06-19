# BOHUMFIT-066 간편 Q2 수술의심 동기화 + 합산 명칭 + 비급여 합산 회귀 — 익명·합성.
#
# (A) 간편 Q2(10년 입원·수술)의 공단 수술 의심 등급(강/약)을 일반 Q4와 동일하게 노출.
# (B) "공단 진료비 기준" → "진료비 합산(공단부담금+본인부담금) 기준" 명칭 정정.
# (C) 합산 total_cost = 공단부담금(1줄) + 본인부담금(2줄). 비급여성(공단=0)은 본인부담금으로 잡힘.
from datetime import datetime, timedelta

from filters import build_code_based_items, PRODUCT_HEALTH, PRODUCT_EASY
from pipeline.disease_aggregator import new_disease
from pipeline.result_builder import build_summary_reports
from pipeline.nhis_history_constants import grade_surgery_suspicion
from pipeline.pdf_parser import parse_nhis_text

TODAY = datetime(2026, 6, 15)
REF = datetime(2026, 6, 15)
Q4_HEALTH = "[4번질문] 5년 초과 10년 이내 입원·수술"
Q2_EASY = "[2번질문] 10년 이내 입원·수술"


def _ymd(days_ago):
    return (TODAY - timedelta(days=days_ago)).strftime("%Y-%m-%d")


def mk(code, name="추간판", suspected=None, grade="", inpatient=None):
    s = new_disease()
    s["diag_code"] = code
    s["name"] = name
    for d in (suspected or []):
        s["surgery_suspected_dates"].add(d)
        s["surgery_suspected_names"].add("관혈적정복술")
    for d in (inpatient or []):
        s["inpatient_dates"].add(d)
        s["inpatient_admissions"].add((d, "OO병원"))
        s["_inpatient_days_map"][d] = 5
    if grade:
        s["surgery_suspected_grade"] = grade
    alld = sorted((suspected or []) + (inpatient or []))
    s["first_date"] = alld[0] if alld else "2099-12-31"
    s["latest_date"] = alld[-1] if alld else "2000-01-01"
    return {code: s}


def _rows(ds, product, title):
    # build_summary_reports 는 health·easy 풀을 별도 인자로 받는다. 둘 다 빌드해 해당 탭에서 읽는다.
    std, easy, *_ = build_summary_reports(
        ds,
        build_code_based_items(ds, REF, PRODUCT_HEALTH),
        build_code_based_items(ds, REF, PRODUCT_EASY),
        {}, "건강체", TODAY,
    )
    return (easy if product == PRODUCT_EASY else std).get(title, [])


# ── ① 간편 Q2 수술 의심 등급 == 일반 Q4 (동기화) ─────────────────────────────
def test_easy_q2_grade_matches_health_q4():
    ds = mk("M51", suspected=[_ymd(2555)], grade="강")   # 7년 전 공단 의심(강)
    h = _rows(ds, PRODUCT_HEALTH, Q4_HEALTH)
    e = _rows(ds, PRODUCT_EASY, Q2_EASY)
    assert h and h[0]["surgery_suspected_grade"] == "강"
    assert e and e[0]["surgery_suspected_grade"] == "강"   # BOHUMFIT-066: 간편도 동일 등급
    assert h[0]["surgery_suspected_grade"] == e[0]["surgery_suspected_grade"]


# ── ① 약 등급도 동기화 ───────────────────────────────────────────────────────
def test_easy_q2_grade_weak_synced():
    ds = mk("K60", "치핵", suspected=[_ymd(2555)], grade="약")
    e = _rows(ds, PRODUCT_EASY, Q2_EASY)
    assert e and e[0]["surgery_suspected_grade"] == "약"


# ── ① 입원 동반 시에도 등급 노출(기존 입원행에 등급 부착) ─────────────────────
def test_easy_q2_grade_with_inpatient():
    ds = mk("M51", suspected=[_ymd(2555)], grade="강", inpatient=[_ymd(2555)])
    e = _rows(ds, PRODUCT_EASY, Q2_EASY)
    assert e and any(r["surgery_suspected_grade"] == "강" for r in e)


# ── ④ filters reason 명칭 정정("진료비 합산(공단부담금+본인부담금)") ──────────
def test_reason_text_corrected():
    ds = mk("M51", suspected=[_ymd(2555)], grade="강")
    for product in (PRODUCT_HEALTH, PRODUCT_EASY):
        items = build_code_based_items(ds, REF, product)
        susp = [it for it in items if "SURG-SUSP" in it.get("_rule_id", "")]
        assert susp, product
        assert any("진료비 합산(공단부담금+본인부담금)" in it.get("reason", "") for it in susp), product
        assert all("공단 진료비 기준" not in it.get("reason", "") for it in susp), product


# ── ② 합산 total_cost = 공단(1줄)+본인(2줄) ──────────────────────────────────
def test_total_cost_is_gongdan_plus_bonin():
    sample = (
        "건강보험 요양급여내역\n발급기간 2019.01.01 ~ 2019.12.31\n"
        "2019.03.10 1 행복병원 02-111-2222 399,690\n1\n입원 10 추간판전위 M512 161,500\n"
    )
    recs = parse_nhis_text(sample, "익명.pdf")
    assert recs and int(recs[0]["총진료비"]) == 561_190   # 399,690 + 161,500


# ── ③ 비급여성(공단=0, 본인 고액) → 합산이 본인부담금을 포함(누락 0) ──────────
def test_non_covered_includes_bonin():
    # 1줄 공단부담금 0(전액본인부담/비급여성), 2줄 본인부담금 600,000 입원.
    sample = (
        "건강보험 요양급여내역\n발급기간 2019.01.01 ~ 2019.12.31\n"
        "2019.05.01 1 OO병원 02-871-2870 0\n1\n입원 3 어떤수술상병 Z998 600,000\n"
    )
    recs = parse_nhis_text(sample, "익명.pdf")
    # 핵심: 본인부담금(600,000)이 합산에 포함된다(누락 0). 공단=0 행은 날짜·전화 숫자
    #   잔여가 미세하게 더해질 수 있으나 본인부담금은 절대 빠지지 않는다.
    assert recs and int(recs[0]["총진료비"]) >= 600_000
    # 입원 + 본인부담금 60만(≥50만) → 강(합산이 본인부담금만으로도 임계 충족).
    assert grade_surgery_suspicion("입원", int(recs[0]["총진료비"]), False, False) == "강"


# ── ⑤ 임계 '이상' 경계(50만/10만) ────────────────────────────────────────────
def test_threshold_inclusive_boundaries():
    assert grade_surgery_suspicion("입원", 500_000, False, False) == "강"    # 50만 '이상'
    assert grade_surgery_suspicion("입원", 499_999, False, False) == ""
    assert grade_surgery_suspicion("외래", 100_000, True, False) == "강"     # 10만 '이상'+키워드
    assert grade_surgery_suspicion("외래", 99_999, True, False) == ""


# ── ⑥ 065 회귀 유지: K01(저액 외래+키워드)·K05(고액 외래·키워드 없음) 해제 ────
def test_065_regression_preserved():
    assert grade_surgery_suspicion("외래", 39_320, True, False) == ""    # K01 매복 저액
    assert grade_surgery_suspicion("외래", 118_550, False, False) == ""  # K05 치은염 고액·키워드 없음
