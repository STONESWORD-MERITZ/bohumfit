# BOHUMFIT-095 윤년 컷오프 보정
## 증상
1825일/3650일 고정 상수 사용으로 윤년 포함 시 2~3일 누락.
의미상 "정확히 5년/10년 전" 경계가 되어야 함.
## Scope
- backend/pipeline/helpers.py (날짜 경계 계산)
- backend/filters.py (창 경계 상수 사용 위치)
- backend/tests/test_date_boundary.py (윤년 케이스 추가)
## Out of Scope
- 프런트 무변경
- 다른 백엔드 파일 최소 수정

## ⚠️ Cowork 진단(2026-06-21) — 이미 BOHUMFIT-004로 해결됨
- `filters._cutoffs()`(L281~286)는 d5y=`_subtract_years(ref,5)`, d10y=`_subtract_years(ref,10)`로 **달력 연도 기준** 계산(BOHUMFIT-004). `analyzer.py`(L930~931)도 동일.
- `_subtract_years`(helpers L443 + filters L57 인라인 동본)는 2/29→2/28 보정 포함.
- 프로덕션 코드에 `3650` 상수는 **존재하지 않음**(10년 창은 이미 연도 기준). `1825`는 `Q3_MED_WINDOW_DAYS`(투약 30일 판정창)뿐 — BOHUMFIT-032가 **의도적으로 고정**(header==badge 불변식·전용 경계 테스트 존재). 변경 대상 아님.
- 기존 `test_leap_year_cutoff.py`가 _subtract_years를 이미 광범위 검증(2/29 기준일·경계 >=·filters==helpers 동본).
→ 따라서 helpers.py/filters.py **프로덕션 무변경**. STEP3 취지에 맞춰 `test_date_boundary.py`에 **창 함수(_cutoffs) 레벨 윤년 회귀**만 보강.
