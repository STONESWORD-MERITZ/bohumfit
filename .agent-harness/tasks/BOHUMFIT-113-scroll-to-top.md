# BOHUMFIT-113-scroll-to-top

## Goal
메뉴/라우트 이동 시 이전 페이지의 스크롤 위치가 유지되지 않고 항상 최상단에서 시작되게 한다.

## Scope
- `src/components/ScrollToTop.tsx` 신규
- `src/App.tsx` Router 내부 연결

## Implementation
- `react-router-dom`의 `useLocation`으로 `pathname` 변경을 감지한다.
- `pathname` 변경 시 `window.scrollTo(0, 0)`을 실행한다.
- `BrowserRouter` 내부, `Routes` 외부에 `ScrollToTop`을 배치한다.

## Verification
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run lint`
- `npm test`
- `npm run build`

## Completion
- 검증 통과 후 `BOHUMFIT-113: 메뉴 이동 시 스크롤 최상단 초기화`로 커밋·푸시한다.
