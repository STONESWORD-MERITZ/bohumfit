# BOHUMFIT-033 공단(nhis) 5~10년 입원·수술의심 확장 회귀 — 익명·합성 픽스처(실데이터 아님).
#
# 사양: 공단 요양급여내역 = 5~10년 입원·수술'의심'(강/약) 전용. 수술 자동확정 금지.
#  - 입원 총진료비 50만↑=강 / 외래 총진료비 10만↑=약 / 수술키워드 가중 / 062 충돌 강등
#  - 5년 이내(심평원 담당)는 반영하지 않음(경계). nhis 수술은 surgery_suspected(의심)로,
#    심평원 세부진료 확정 수술은 surgeries(확정) 그대로 유지.
from datetime import datetime

from pipeline.disease_aggregator import build_disease_stats
from pipeline.pdf_parser import parse_nhis_text, _extract_nhis_issue_period, _extract_nhis_total_cost
from pipeline.nhis_history_constants import grade_surgery_suspicion

TODAY = datetime(2026, 6, 15)   # 5년 경계 = 2021-06-15, 10년 = 2016-06-15


def nhis(date, io, days, code, name, cost):
    return {"진료개시일": date, "요양기관명": "OO의원", "입내원구분": io, "요양일수": str(days),
            "상병코드": code, "상병명": name, "총진료비": str(cost), "_ftype": "nhis"}


def basic(date, hosp, code, name, io="외래", days=1):
    return {"진료개시일": date, "요양기관명": hosp, "입내원구분": io, "요양일수": str(days),
            "상병코드": code, "상병명": name, "_ftype": "basic"}


def detail(date, hosp, proc):
    return {"진료개시일": date, "요양기관명": hosp, "처치및수술": proc, "_ftype": "detail"}


# 이민규 익명 픽스처: 공단 5~10년 입원 2 + 의심 강 3(M51·K60·K63), 외래 9만 제외,
# 5년 이내 공단 입원은 미반영, 심평원 세부 확정수술은 유지.
def _fixture_records():
    return [
        nhis("2019-03-10", "입원", 5, "M5100", "추간판장애",            1_200_000),  # 강·입원
        nhis("2018-07-20", "입원", 3, "K6030", "치핵",                  700_000),    # 강·입원
        nhis("2019-11-05", "외래", 1, "K6300", "탈장 동반 장질환",       150_000),    # 강(외래10만+키워드 가중)
        nhis("2019-06-20", "외래", 1, "H1000", "결막염",                90_000),     # 외래 9만 → 제외
        nhis("2023-08-01", "입원", 4, "L4000", "건선",                  1_000_000),  # 5년 이내 → 미반영
        basic("2022-05-01", "튼튼정형외과", "S720", "어깨병변", io="외래"),
        detail("2022-05-01", "튼튼정형외과", "관혈적정복술"),                         # 심평원 확정 수술
    ]


def _stats(records):
    st, *_ = build_disease_stats(records, TODAY)
    return st


# ── 1) 입원 2건(M51·K60) ─────────────────────────────────────────────────
def test_inpatient_two_admissions():
    st = _stats(_fixture_records())
    total_adm = sum(len(st[c]["inpatient_admissions"]) for c in ("M51", "K60") if c in st)
    assert total_adm == 2
    assert len(st["M51"]["inpatient_admissions"]) == 1
    assert len(st["K60"]["inpatient_admissions"]) == 1


# ── 2) 수술 의심 강 3건(M51·K60·K63) ─────────────────────────────────────
def test_three_strong_suspicions():
    st = _stats(_fixture_records())
    for c in ("M51", "K60", "K63"):
        assert st[c]["surgery_suspected_grade"] == "강", c
        assert st[c]["surgery_suspected_names"], c


# ── 3) nhis 수술의심은 surgery_suspected, 확정 surgeries 아님 ─────────────
def test_nhis_goes_suspected_not_confirmed():
    st = _stats(_fixture_records())
    for c in ("M51", "K60", "K63"):
        assert st[c]["surgeries"] == set(), f"{c} 확정수술로 새면 안 됨"


# ── 4) 심평원 세부진료 확정 수술은 surgeries(확정) 유지 ───────────────────
def test_hira_detail_surgery_still_confirmed():
    st = _stats(_fixture_records())
    assert "S72" in st
    assert st["S72"]["surgeries"], "심평원 세부 확정 수술이 유지돼야 함"
    assert st["S72"]["surgery_suspected_grade"] == ""   # 확정이지 의심 아님


# ── 5) 외래 9만 → 의심 제외 ──────────────────────────────────────────────
def test_outpatient_below_threshold_excluded():
    st = _stats(_fixture_records())
    assert st["H10"]["surgery_suspected_grade"] == ""
    assert st["H10"]["surgery_suspected_names"] == set()


# ── 6) 5년 이내 공단 입원은 미반영(경계) ─────────────────────────────────
def test_within_5y_nhis_ignored():
    st = _stats(_fixture_records())
    # L40 그룹은 존재할 수 있으나 임상 기여(입원·의심)는 없어야 함
    if "L40" in st:
        assert st["L40"]["inpatient_admissions"] == set()
        assert st["L40"]["surgery_suspected_grade"] == ""


# ── 7) 결정성: 동일 입력 2회 → 동일 결과 ─────────────────────────────────
def test_determinism():
    def snap():
        st = _stats(_fixture_records())
        return {c: (sorted(st[c]["inpatient_admissions"]),
                    sorted(st[c]["surgery_suspected_names"]),
                    st[c]["surgery_suspected_grade"],
                    sorted(st[c]["surgeries"]))
                for c in sorted(st)}
    assert snap() == snap()


# ── 8) 파서: 2줄·총진료비(공단1줄+본인2줄 합)·발급기간 ───────────────────
def test_parse_nhis_text_cost_and_period():
    # BOHUMFIT-056: 실제 공단 양식 — 공단부담금은 1줄, 본인부담금은 2줄. 총진료비=둘의 합.
    #   입내원일수(1줄) = 입원/내원 일수, 요양(투약)일수(2줄)는 별도.
    sample = (
        "건강보험 요양급여내역\n발급기간 2017.01.01 ~ 2017.12.31\n"
        "2017.03.10 1 행복의원 02-111-2222 900,000\n1\n입원 5 추간판장애 M51 300,000\n"
        "2017.06.20 2 OO의원 031-333-4444 60,000\n2\n외래 1 결막염 H10 30,000\n"
    )
    recs = parse_nhis_text(sample, "익명.pdf")
    assert _extract_nhis_issue_period(sample) == "2017.01.01 ~ 2017.12.31"
    assert len(recs) == 2
    assert recs[0]["총진료비"] == "1200000" and recs[0]["_issue_period"] == "2017.01.01 ~ 2017.12.31"  # 900,000+300,000
    assert recs[0]["내원일수"] == "1" and recs[0]["투약일수"] == "5"   # 입내원일수(1줄)/요양일수(2줄) 분리
    assert recs[1]["총진료비"] == "90000"   # 60,000+30,000


# ── 9) 등급 경계 단위 ────────────────────────────────────────────────────
def test_grade_thresholds_unit():
    assert grade_surgery_suspicion("입원", 500_000, False, False) == "강"
    assert grade_surgery_suspicion("입원", 499_999, False, False) == ""
    assert grade_surgery_suspicion("외래", 100_000, False, False) == "약"
    assert grade_surgery_suspicion("외래", 99_999, False, False) == ""
    assert grade_surgery_suspicion("외래", 100_000, True, False) == "강"   # 키워드 가중
    assert grade_surgery_suspicion("입원", 600_000, False, True) == "약"   # 062 강등
