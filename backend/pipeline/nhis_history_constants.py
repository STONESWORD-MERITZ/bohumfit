"""BOHUMFIT-033: 국민건강보험공단 '요양급여내역'(nhis) 5~10년 수술 의심 등급 상수·로직.

공단 자료에는 '수술' 컬럼이 없다. 따라서 수술은 **자동 확정하지 않고**, 진료비·입내원구분·
수술 키워드를 근거로 '의심(확인 필요)' 등급만 부여한다. 등급은 (B) 사양의 점수식:
  - 입원 + 총진료비 >= INPATIENT_STRONG_COST → 강 후보(+2)
  - 외래 + 총진료비 >= OUTPATIENT_WEAK_COST → 약 후보(+1)
  - 수술 키워드(폴립·절제·내시경 등) 매칭 → 가중(+1)
  - 062 surgery_exclusions 충돌(비수술 코드명) → 강등(-1)
점수 >=2 → '강', ==1 → '약', <=0 → 없음('').
임계는 추후 튜닝을 위해 상수로 분리한다.
"""
from __future__ import annotations

# 금액 임계 (원). 추후 튜닝 대상.
INPATIENT_STRONG_COST = 500_000   # 입원 총진료비 50만 이상 → 강 후보
OUTPATIENT_WEAK_COST  = 100_000   # 외래 총진료비 10만 이상 → 약 후보

GRADE_STRONG = "강"
GRADE_WEAK   = "약"
_GRADE_RANK  = {"": 0, GRADE_WEAK: 1, GRADE_STRONG: 2}


def grade_surgery_suspicion(
    in_out: str,
    total_cost: int,
    has_surgery_keyword: bool,
    is_non_surgery_excluded: bool,
) -> str:
    """수술 의심 등급을 반환한다('강'|'약'|'').

    in_out: '입원' | '외래' | 그 외(약국 등은 호출 측에서 제외).
    total_cost: 총진료비(공단부담+본인부담) 원.
    has_surgery_keyword: 수술 키워드 매칭 여부(가중).
    is_non_surgery_excluded: 062 비수술 제외 코드명 여부(강등).
    """
    score = 0
    if in_out == "입원":
        if total_cost >= INPATIENT_STRONG_COST:
            score += 2
    else:  # 외래 등
        # BOHUMFIT-065: 외래는 비용 단독으로 수술의심을 만들지 않는다. 10만원 이상 비용과
        #   수술 키워드가 함께 있을 때만 의심으로 본다. K05처럼 치주/치은 외래 비용이 10만원을
        #   넘지만 수술 키워드가 없는 행은 해제하고, K63처럼 고액+폴립 키워드가 있는 행은 유지한다.
        if total_cost >= OUTPATIENT_WEAK_COST and has_surgery_keyword:
            score += 2
    if in_out == "입원" and has_surgery_keyword and total_cost >= OUTPATIENT_WEAK_COST:
        score += 1
    if is_non_surgery_excluded:
        score -= 1

    if score >= 2:
        return GRADE_STRONG
    if score == 1:
        return GRADE_WEAK
    return ""


def stronger_grade(a: str, b: str) -> str:
    """두 등급 중 더 강한 쪽을 반환('강' > '약' > '')."""
    return a if _GRADE_RANK.get(a, 0) >= _GRADE_RANK.get(b, 0) else b
