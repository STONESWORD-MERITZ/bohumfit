# BOHUMFIT 실비(실손) 청구 안내 — 설계 문서 v4
> 작성일: 2026-06-08 (SURIT-028)
> 성격: v3-1 확장(additive). 실손 **최소공제(정액↔정률 max)** + **의원 자동분류** 추가.
> v3-1(BOHUMFIT_실비기능_설계_v3.md)의 ①실손청구 ②자기부담금상한 ③건보상한제 로직은 **불변**.
> 본 문서는 그 위에 "통원 최소공제" 옵션과 기관 등급 추정을 더한다.

## 0. 원칙 (v3 승계)
- 추정 안내형. 확정 금액 단정 금지. "추정"·"~일 수 있음"·"보험사·공단 확인 필요".
- 보험 모집·상품추천·가입권유 금지. 개인정보 비저장(입력값 세션 내만, localStorage 금지).
- 최소공제는 **기본 OFF 옵션**(additive) — 켜야 ①에 반영. 기존 ①②③ 회귀 없음.

## §2. 안내 문구 (최소공제 관련 5종 — UI/PDF 공통)
1. "통원 1회 자기부담은 정액공제와 정률공제(진료비×자기부담률) 중 **큰 값**으로 추정합니다."
2. "진료비가 정액공제 이하면 보상이 없어 **청구 실익이 낮을 수 있습니다**."
3. "기관 등급은 기관명으로 **추정**한 값이며 실제와 다를 수 있습니다 — 직접 수정할 수 있습니다."
4. "비급여는 **회차별(1회 금액×횟수)** 입력 시 더 정확합니다. 총액만 입력하면 공제를 1회만 적용합니다."
5. "1세대(legacy)·5세대(준비중)는 통원 정액공제를 적용하지 않습니다. 입원은 정액 통원공제가 없습니다."

## §4-4. 세대별 통원 최소공제(정액) — 기관 등급별
| 세대 | 의원(clinic) | 종합병원(general) | 상급종합(tertiary) | 비고 |
|---|---|---|---|---|
| 1세대 | — | — | — | legacy(상품별 상이) → 미적용(None) |
| 2·3·4세대 | 1만원 | 1.5만원 | 2만원 | 표준 |
| 5세대 | — | — | — | 준비중(약관 확정 후) → 미적용(None) |
- 기관 등급 미상(unknown) → **기본 상급 2만원**(보수적).
- 입원은 정액 통원공제 없음(정률만).
- 상수: `constants.MIN_DEDUCTIBLE_BY_GEN`, `MIN_DEDUCTIBLE_DEFAULT_GRADE="tertiary"`.

## §4-5. 기관 자동분류 규칙 (classify_provider)
- 기관명 정규화 후 **'의원' 포함 + '병원' 미포함 → clinic**. 그 외 → **unknown**(기본 2만).
- 종합/상급은 자동 판별하지 않음 — 사용자가 직접 등급 선택/수정.
- '삼성서울병원' 등 '병원' 포함 명칭은 unknown(의원 오분류 방지).

## §6-1. 백엔드 (calculator.py, additive)
- `classify_provider(name) -> "clinic"|"unknown"` (§4-5).
- `provider_deductible(gen, grade) -> int|None` — 세대·등급 정액공제. 1·5세대·미정 None.
- `estimate_claim_per_row(charge, copay_rate, fixed_deductible) -> dict`:
  · 정률 = round(charge×copay_rate). 최종공제 = max(정액, 정률). 보상 = max(0, charge−최종공제).
  · `low_value = 보상<=0` (청구 실익 낮음).
- `estimate_non_covered_claim_with_deductible(...)`:
  · 건별(per_visit_amount+visit_count): 회차마다 공제 후 합산. `total_only=False`.
  · 총액만(total_amount): 공제 1회만. `total_only=True` + 한계 안내.
- 기존 `estimate_insurance_claim`/`check_self_pay_cap`/`check_nhis_out_of_pocket_cap` 불변.

## §6-2. 프론트 (Disclosure.tsx InsuranceSection, TS 미러)
- "실손 최소공제 설정" 입력영역: 적용여부(체크) / 급여통원·비급여통원·입원 각 진료비 / 비급여 총액·건별 토글(+1회금액·횟수).
- 기관명 입력 + 추정 등급 표시("추정이며 실제와 다를 수 있음") + 사용자 등급 수정(select).
- 백엔드와 **동일 산식 TS 미러**(`insMinDeductible`, `insClassifyProvider`, `insClaimPerRow`). 상수 동일(1만/1.5만/2만).
- 결과 ①에 최소공제 적용 시: 보상 추정 + "청구 실익 낮음" 표시 + §2 문구 5종.

## §6-3. 테스트 케이스 (1~14)
| # | 시나리오 | 입력 | 기대 |
|---|---|---|---|
| 1 | 정액 우세(의원) | 3만, rate0.20, 정액1만 | 정률6천<정액1만 → 보상 2만 |
| 2 | 정률 우세(종합) | 20만, rate0.20, 정액1.5만 | 정률4만>정액 → 보상 16만 |
| 3 | 경계(정률=정액) | 5만, rate0.20, 정액1만 | 정률1만=정액 → 보상 4만 |
| 4 | 비급여 건별≠총액 | 1회3만×3 vs 총9만, 의원1만, rate0.30 | 건별 6만 ≠ 총액 6.3만 |
| 5 | 입원(정액 없음) | 10만, rate0.20, 정액0 | 보상 8만(정률만) |
| 6 | 미상기관 기본2만 | provider_deductible(4,"unknown") | 2만(상급) |
| 7 | 1세대 legacy | provider_deductible(1,"clinic") | None |
| 8 | 5세대 준비중 | provider_deductible(5,"clinic") | None |
| 9 | 최소공제 미사용 | 정액0 | 정률만(=기존 산식 일치) |
| 10 | 백엔드-TS 미러 일치 | 동일 입력 | Python==TS 결과 동일 |
| 11 | 의원 분류 | "서울정형외과의원" | clinic |
| 12 | 오분류 방지 | "삼성서울병원" | unknown |
| 13 | 실익 낮음 | 8천, rate0.20, 정액1만 | 보상 0, low_value True |
| 14 | 비급여 총액만 | total_amount만 | total_only True + 안내 |

## §6-4. 하지 말 것
- 알릴의무(standard/easy) 로직·표시 변경 금지. 기존 실손 ①②③ 회귀 금지(최소공제 additive).
- 새 npm 의존성 금지. 개인정보 저장 금지. v4 수치 임의 변경 금지.

## 7. 면책 (v3 승계)
본 기능은 청구·환급 "가능성"을 안내하는 보조 도구이며, 실제 보험금·환급금은 보험사 약관·심사 및
국민건강보험공단 기준에 따라 결정됩니다. 수치는 변경될 수 있으며 정확한 계산은 약관·공단 확인이 필요합니다.
