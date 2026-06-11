# BOHUMFIT-023 — 실손 청구 안내 2단계: §4-2 확정 반영 + 계산 보정 + UI 통합

- Owner: Cowork (구현) → 검증·푸시 Codex
- 기준 문서: `.agent-harness/docs/BOHUMFIT_실비기능_설계_v3.md` (v3-1)
- 생성: 2026-06-06
- 전제: BOHUMFIT-022 1단계 완료(상수+계산 모듈+데이터 진단).

## 범위 (잠금)
- `backend/insurance/constants.py` — §4-2 확정값 + 세대별 합산범위
- `backend/insurance/calculator.py` — `check_self_pay_cap` 세대별 합산범위 판정
- `backend/tests/test_insurance_calc.py` — 보강
- `src/pages/Disclosure.tsx` — 실손 청구 탭 UI
- `.agent-harness/docs/BOHUMFIT_실비기능_설계_v3.md`, `.agent-harness/tasks/BOHUMFIT-023-insurance-ui.md`
- **범위 확장(사용자 지시)**: `backend/analyzer.py`, `backend/main.py` — 급여 본인부담 surfacing(additive, 고지 로직 불변)

## A. 계산 보정 (§4-2 확정)
- 실손 자기부담금 연 상한 = 전 세대 **200만원**. 합산 범위 세대별 상이:
  - 1~3세대: 급여 자기부담 + 비급여 자기부담 합산 ≥ 200만 → 초과
  - 4~5세대: 급여 자기부담만 ≥ 200만 (비급여 제외)
- `constants.py`: `SELF_PAY_ANNUAL_CAP`(전 세대 200만) + `SELF_PAY_CAP_SCOPE`(세대별 합산범위 플래그).
- `check_self_pay_cap`: 세대별 합산범위로 판정. 4~5세대는 `non_covered_excluded=True` + 안내 메시지.
- 테스트: 1~3세대(급여+비급여 합산 경계), 4~5세대(급여만 경계 + 비급여 제외 확인), 200만 경계(초과/미달), 결정론.

## 급여 데이터 경로 (사용자 지시 — v3-1 §3-1-b)
- PDF 기본진료정보 진료비 내역을 전부 급여로 간주.
- `analyzer.run_analysis`: `all_records` 삭제(line 718) 전에 `aggregate_covered_self_pay_by_year(all_records)` 호출 → 결과 dict 에 `covered_self_pay_by_year` 추가(additive).
- `main.py`: 분석 응답에 `covered_self_pay_by_year` 전달.
- 고지(알릴의무) 판정·표시 로직은 일절 변경 없음(신규 키만 추가).

## B. UI 통합 (Disclosure.tsx)
- `ResultView` 에 세 번째 탭 "실손 청구" 추가(`productTab` 확장: standard|easy|insurance).
- 기존 `result` 재사용(재업로드 없음). `covered_self_pay_by_year` 로 급여 자동 표시.
- 입력 폼: 실손 세대(1~5+모름) / 3세대 비급여 20·30 옵션 / 비급여 금액 직접 입력(선택) 또는 영수증 첨부(선택) / 소득분위(1~10+모름).
- 표시: ① 실손 청구 가능성(급여+비급여 추정범위) ② 실손 자기부담금 상한제(세대별 합산범위, 4~5세대 비급여 제외 병기) ③ 건보 본인부담상한제(급여 기준, 분위별, 요양병원120일 휴리스틱).
- 계산은 backend/insurance 를 기준으로 TS 미러(프런트는 insurance 모듈을 직접 호출 불가 — HTTP API 부재). 미러 로직은 backend 테스트가 source of truth.
- 출력 톤: "추정"·"~일 수 있음"·"보험사·공단 확인 필요". 보험 모집·추천·권유 표현 금지.

## 하지 말 것
- 알릴의무(standard/easy) 판정·표시 로직 변경 금지.
- 개인정보 저장 금지(세대·분위·비급여 입력 세션 내만, localStorage 금지).
- 설계 v3-1 수치 임의 변경 금지.

## 검증
- `cd backend && python -m pytest -q` (기존 156 + 보강 통과)
- `npx tsc -p tsconfig.app.json --noEmit` / `tsconfig.node.json` / `npm run build`
- 가능 시 오성심 PDF 로 실손 탭 수동 확인(세대 입력 → ①②③ 표시).

## 완료 조건
- A 보정 + 급여 surfacing + UI 탭 동작, pytest/tsc/build 통과.
- handoff 표준 기록(계산 보정·UI·범위확장 사유), Next=Codex 검증·푸시.
- locks 해제.
