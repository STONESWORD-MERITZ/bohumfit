# SURIT-028 — 실손 최소공제 + 의원 자동분류 (기존 실손에 additive)

- Owner: Cowork (구현) → 검증·푸시 Codex
- 기준: `.agent-harness/docs/BOHUMFIT_실비기능_설계_v4.md` (§4-4/4-5/6-1~6-4)
- 생성: 2026-06-08
- 전제: SURIT-022/023/025 실손 기능. 본 작업은 additive — 기존 ①②③ 불변.

## 범위 (잠금)
- `backend/insurance/constants.py` (§4-4 MIN_DEDUCTIBLE_BY_GEN)
- `backend/insurance/calculator.py` (§6-1 classify_provider/provider_deductible/estimate_claim_per_row/estimate_non_covered_claim_with_deductible)
- `backend/tests/test_min_deductible.py` (§6-3 케이스 1~14)
- `src/pages/Disclosure.tsx` (§6-2 TS 미러 + ①-b 입력/결과)
- `.agent-harness/docs/BOHUMFIT_실비기능_설계_v4.md`, `.agent-harness/tasks/SURIT-028-min-deductible.md`

## A. 백엔드 (§6-1) — 완료
- constants §4-4: `MIN_DEDUCTIBLE_BY_GEN`(2·3·4세대=의원1만/종합1.5만/상급2만, 1·5세대=None), `MIN_DEDUCTIBLE_DEFAULT_GRADE="tertiary"`.
- calculator: `classify_provider`(의원 포함+병원 미포함→clinic, 그외 unknown), `provider_deductible`, `estimate_claim_per_row`(최종공제=max(정액,정률), 보상=max(0,진료비-공제), low_value), `estimate_non_covered_claim_with_deductible`(건별/total_only).
- 기존 ①②③ 함수 불변(별도 함수 추가).

## B. 프론트 (§6-2) — 완료
- `Disclosure.tsx`: TS 미러 `INS_MIN_DEDUCTIBLE_BY_GEN`/`insClassifyProvider`/`insProviderDeductible`/`insClaimPerRow` (백엔드와 동일 상수·산식).
- `InsuranceSection` ①-b "실손 최소공제 적용 추정(선택)": 적용 토글 + 기관명(추정등급+수정) + 급여/비급여 통원·입원 진료비 + 비급여 총액·건별 토글 + 횟수. 결과 보상 추정 + 실익낮음 + §2 안내문구 5종. 입력은 no-print, 결과는 print 포함. 입력값 비저장(useState).

## C. 테스트 (§6-3) — 완료
- `test_min_deductible.py` 16개(케이스 1~14 + 미러 참조값 + additive 회귀).

## ★ 백엔드-TS 미러 일치 (케이스 10)
- 동일 상수(1만/1.5만/2만)·동일 산식(max(정액,정률)). 참조값(`MIRROR_REFERENCE` in test): 의원3만/r20/d1만→2만, 종합20만/r20/d1.5만→16만, 8천/r20/d1만→0.
- Codex 는 프론트 `insClaimPerRow` 가 동일 입력에 동일 결과를 내는지 대조.

## 하지 말 것
- 알릴의무(standard/easy) 로직 변경 금지. 기존 실손 ①②③ 회귀 금지. 새 npm 의존성 금지. 개인정보 저장 금지. v4 수치 임의 변경 금지.

## 검증
- `cd backend && python -m pytest -q` (기준선 170 + 신규 test_min_deductible)
- `npx tsc app·node` / `npm run build` / 백엔드-TS 미러 참조값 대조
