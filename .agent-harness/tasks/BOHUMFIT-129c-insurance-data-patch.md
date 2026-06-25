# BOHUMFIT-129c 보험사 연락 데이터 패치

## 배경
GPT 대화 조사로 확인한 보험사 연락 데이터 보강.
기존 `InsuranceLinks.tsx` 배열에서 "확인 필요" 또는 빈 값인 항목만 실제 데이터로 교체한다.

## 주의사항
- UI 코드, 타입 정의, 컴포넌트 함수 수정 금지
- 데이터 배열 값만 교체
- "미확인" 값은 "확인 필요"로 통일
- 기존에 이미 실제 값이 있는 항목은 덮어쓰지 않음
- `faxSource` 필드는 `InsuranceLinks.tsx` 타입에 없으면 추가하지 않고 기존 메모 필드에 통합

## 작업 범위
- `src/pages/InsuranceLinks.tsx`의 `INSURANCE_DATA` 배열 값만 수정
- `.agent-harness/handoff.md`
- `.agent-harness/locks.md`

## 검증
- `npx tsc -p tsconfig.app.json --noEmit`
- `npm run build`

## 완료 조건
- 교체된 항목 수 handoff 기록
- 검증 통과
- 커밋 및 푸시
