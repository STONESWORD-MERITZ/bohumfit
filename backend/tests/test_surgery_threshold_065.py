# BOHUMFIT-065 수술의심 임계 재검토(약 오탐) + 판정근거 문구 + 파일명 회귀.
#
# 오탐(실 PDF): K01(상악제3대구치 매복, 외래 합산 39,320원)·K05류가 '매복/발치' 수술 키워드만으로
#   '약' 판정. 원인=키워드 가중(+1)이 외래 cost 문턱(10만)을 우회. 수정=키워드 가중을 cost>=10만일
#   때만 적용. 입원 고액(>=50만→강)·정상 외래 고액은 영향 0.
from datetime import datetime

from pipeline.nhis_history_constants import (
    grade_surgery_suspicion,
    INPATIENT_STRONG_COST,
    OUTPATIENT_WEAK_COST,
)
from pipeline.pdf_parser import _extract_patient_name


# ── ① 저액 외래 + 수술 키워드 → 미판정(K01/K05류 오탐 제거) ───────────────────
def test_low_cost_outpatient_keyword_not_flagged():
    # K01: 외래 39,320(<10만) + '매복' 키워드 → 종전 '약' → 이제 ''.
    assert grade_surgery_suspicion("외래", 39_320, True, False) == ""
    assert grade_surgery_suspicion("외래", 50_000, True, False) == ""
    assert grade_surgery_suspicion("외래", 99_999, True, False) == ""   # 문턱 직전


# ── ② 입원 고액 → 강 유지(대조군 M51/K60/K63) ────────────────────────────────
def test_inpatient_high_cost_strong_preserved():
    assert grade_surgery_suspicion("입원", 561_190, False, False) == "강"   # M51
    assert grade_surgery_suspicion("입원", 1_035_220, False, False) == "강"  # K60
    assert grade_surgery_suspicion("입원", INPATIENT_STRONG_COST, False, False) == "강"
    assert grade_surgery_suspicion("입원", INPATIENT_STRONG_COST - 1, False, False) == ""


# ── ③ 외래 임계 경계 + 키워드 게이트 동작 ────────────────────────────────────
def test_outpatient_threshold_and_keyword_gate():
    # 외래 고액(>=10만): cost만으로는 미표시, cost+키워드 → 강.
    assert grade_surgery_suspicion("외래", OUTPATIENT_WEAK_COST, False, False) == ""
    assert grade_surgery_suspicion("외래", OUTPATIENT_WEAK_COST, True, False) == "강"
    assert grade_surgery_suspicion("외래", OUTPATIENT_WEAK_COST - 1, False, False) == ""
    # 키워드만(저액)으론 못 올라감 — 이번 수정의 핵심.
    assert grade_surgery_suspicion("외래", OUTPATIENT_WEAK_COST - 1, True, False) == ""
    # 062 비수술 제외(강등)는 유지: 입원 60만 + 제외 → 약.
    assert grade_surgery_suspicion("입원", 600_000, False, True) == "약"


# ── ④ 임계 상수값(문구·정합 기준) ────────────────────────────────────────────
def test_threshold_constants():
    assert INPATIENT_STRONG_COST == 500_000
    assert OUTPATIENT_WEAK_COST == 100_000


# ── ⑤ 파일명용 성명 추출(주민번호 등 다른 PII 미추출·없으면 "") ──────────────
def test_extract_patient_name():
    assert _extract_patient_name("성명 홍길동 주민등록번호 900101-1******") == "홍길동"
    assert _extract_patient_name("성 명 김철수 주민등록번호 800101-2******") == "김철수"
    # 주민번호 등 다른 값은 반환에 절대 포함되지 않음.
    out = _extract_patient_name("성명 홍길동 주민등록번호 900101-1******")
    assert "900101" not in out and "주민" not in out
    # 성명 없는 텍스트 → "".
    assert _extract_patient_name("건강보험 요양급여내역\n발급번호 2026...") == ""
    assert _extract_patient_name("") == ""
