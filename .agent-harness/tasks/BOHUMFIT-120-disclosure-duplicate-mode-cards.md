# BOHUMFIT-120: 알릴의무 필터 고객용/설계사용 중복 카드 제거

## 목적
`/disclosure?mode=agent` 화면에서 상단 탭과 같은 의미의 고객용/설계사용 카드가 한 번 더 노출되는 중복 UI를 제거한다.

## Scope
- `src/pages/Disclosure.tsx`
- `src/pages/Disclosure.test.tsx`
- `.agent-harness/handoff.md`
- `.agent-harness/locks.md`

## 작업 내용
- `DisclosureHub`의 상단 탭은 유지한다.
- `Disclosure.tsx` 내부의 중복 `ModeSwitch` 카드 블록은 제거한다.
- 가이드 투어는 청약 예정일 입력부터 시작하도록 조정한다.

## 검증
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run lint`
- `npm test`
- `npm run build`

## 완료 조건
- 화면에서 빨간 X 표시 영역의 중복 고객용/설계사용 카드가 사라짐
- 기존 업로드/분석 흐름 및 테스트 통과
