# BOHUMFIT-056 헤더 워드마크 크기·우측 네비 간격 조정

## Owner
Codex 단독

## Goal
헤더의 `BohumFit 보험핏` 텍스트 워드마크를 핏히어 비율에 맞춰 현재 대비 약 0.7배로 줄이고, 우측 네비 항목 간격을 같은 톤으로 정돈한다. 영문/한글 상대 크기, baseline 정렬, 색상, 폰트, 파비콘은 유지한다.

## Scope
- 허용: `src/components/Layout.tsx`, `src/components/Logo.tsx`의 헤더 크기·gap 관련 토큰
- 하네스: task, handoff, locks
- 금지: 산식, 라우팅, 페이지 본문, favicon/meta, 색상/폰트 변경

## Plan
1. 현재 `Logo` 호출 크기와 데스크톱 네비 gap 확인.
2. 헤더에서만 워드마크 크기를 약 0.7배로 축소.
3. 우측 네비 항목 간격을 FitHere식 여백감에 맞춰 조정.
4. 타입·린트·빌드·테스트와 dev 헤더 육안 확인.

## Verify
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run lint`
- `npm test`
- `npm run build`
- `npm run dev` 헤더 육안/스모크
