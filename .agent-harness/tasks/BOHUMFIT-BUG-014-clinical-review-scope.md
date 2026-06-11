# BOHUMFIT-BUG-014: 추가검사·재검사 표시 범위와 전건 표시 보정

## Owner
- Codex

## Status
- Completed

## Context
- 건강체 Q2 일부 카드에서 추가검사·재검사 확인 문구가 보이지 않는다.
- 건강체 Q3와 간편 Q2에는 추가검사·재검사/치료 중 보조 판단이 불필요하게 노출될 수 있다.
- 사용자 정책:
  - 추가검사·재검사 확인 필요 문항은 건강체 Q1, 건강체 Q2, 간편 Q1만이다.
  - 간편 Q2는 입원·수술만 확인한다.

## Scope
- `backend/analyzer.py`
- `backend/pipeline/result_builder.py`
- `backend/tests/test_q_restructure.py`
- `src/pages/Disclosure.tsx`
- `.agent-harness/handoff.md`
- `.agent-harness/locks.md`

## Verification
- `cd backend && python -m pytest -q`
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run lint`
- `npm test`
- `npm run build`

## Expected Result
- 건강체 Q1/Q2와 간편 Q1의 모든 결과 카드에 추가검사·재검사 확인 줄이 표시된다.
- 건강체 Q3/Q4와 간편 Q2/Q3에는 추가검사·재검사/치료 중 보조 판단이 표시되지 않는다.
- 간편 Q2 결과 카드는 입원·수술 지표만 표시한다.
