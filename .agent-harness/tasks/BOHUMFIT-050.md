# BOHUMFIT-050 통원 카운트 행 기준 + 약국 기관명 공백 정규화
## Owner
- Cowork (구현+회귀) → Codex (Windows 검증·git)

## 확정 사양 (Human 승인)
- 통원 카운트 단위 = 내원 행(visit_events, 같은날 중복 허용). visit_dates(집합)는 pharma 앵커 전용 분리.
- 집계 기간 = 5년 창 유지(BOHUMFIT-034 불변). 약국 제외 유지(043) + 공백 정규화.
- K29가 5년 내 행 기준 9 미만이어도 정상(사양대로).

## 1단계 진단 — 현행 코드 실측(중요)
- **통원 카운트는 이미 행 기준**: `_visit_count_in_range`가 `visit_events`(행 리스트)를 사용하고 `_dts_in_range`는 중복을 보존 → 같은날 2행 합성 케이스 = **2** 반환(일자 기준이면 1). VISIT-7(filters L578)·result_builder(L169) 모두 events 사용.
- **앵커 분리도 이미 존재**: visit_dates(집합)=pharma cross-ref 앵커, visit_events(리스트)=카운트.
- **통원 약국 가드도 이미 공백 처리**: 043이 `_norm_provider_name`(공백 strip)으로 공백 변형 약국명도 제외. (049의 "약국 공백 버그"는 진단 시 raw `"약국" in hosp`를 쓴 부정확. 실제 통원 경로는 정상.)
- 단, **약국 검사가 경로마다 불일치**: 통원(L341)=정규화, 그러나 detail-link 인덱스(L224)·hospital_dates(L348)·표시 hospitals(L518)는 raw `"약국" in hospital` → 공백 변형 약국이 이들 경로에선 누수.

## 구현 (완료)
- `pipeline/disease_aggregator.py`:
  - 신규 `_is_pharmacy(name)` = `"약국" in re.sub(r"\s+","",name)`(공백만 제거 — 정밀).
  - 약국 검사 4곳 일원화: L224(detail-link)·통원(visit 분기)·hospital_dates·표시 hospitals → 모두 `_is_pharmacy`. 공백 변형("약 국") 일관 제외.
  - 통원 분기 주석에 단위=행(visit_events)·앵커=visit_dates 분리 명시.
- `filters.py`: `_visit_count_in_range`에 행 기준(visit_events) 확정 주석. **로직 무변경**(이미 행 기준).
- tests: 신규 `test_visit_count_row_pharmacy.py`(7).

## 3단계 J32/K29 전후(실 PDF, ref=2026-06-17)
- **J32**: 전체 일자 10 / 행 10 → 5년 행 카운트 **10**(정답표 10 일치). (같은날 중복 없어 일자=행)
- **K29**: 전체 일자 7 / 행 7 → 5년 행 카운트 **5**(2건 2020-12 5년 초과). 사양대로 <7 미발동.
- 앵커 분리: K29 visit_dates=7 / visit_events=7.
- 약국 정규화: K29 약국행 검출 1→**3**(일반 약국명 1 + 공백 변형 약국명 2). 단, 해당 약국일자는 같은날 의원행이 있어 K29 카운트(5)는 불변.
- **결론: J32=10·K29=5 전후 불변**(이미 행 기준·통원 약국 정규화). 050은 약국 검사 전 경로 일관화 + 행기준·앵커분리 고정.

## 검증
- /tmp pytest **292 passed**(신규 7 포함, 회귀 0; `test_main_launch_guardrails`만 sandbox app-import 제외 → Codex/Windows 권위). 기준선 291(047 후) + 7.
- 자체 점검: ☑약국 공백 정규화 ☑통원 행 기준(이미·고정) ☑5년 창 불변 ☑pharma 앵커 유지 ☑VISIT-7 임계 동일 ☑J32/K29 기록 ☑회귀0.
- ⚠ disease_aggregator/filters 마운트 view 절단은 tail 재구성으로 보정 검증.

## 작업 범위
- disease_aggregator.py·filters.py·tests. helpers 무변경(불요). 5년 창·VISIT-7 임계·Q구조·간편·결정론 불변.
