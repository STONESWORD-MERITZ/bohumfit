# BOHUMFIT-202 - 홈 자연 스크롤 및 신뢰 레이아웃 개선

Owner flow: Human -> Codex Windows
Current owner: Codex Windows

## Intent

- 홈 마지막 콘텐츠가 강제 섹션 스냅/최소 화면 높이에 가려지지 않도록 자연스럽게 끝까지 스크롤한다.
- `How it works`와 `Features`를 하나의 안내 섹션으로 묶어, 설계사가 제품 흐름과 핵심 기능을 한 번에 신뢰감 있게 이해하게 한다.
- 히어로의 `상담 준비 요약` 바를 화면 하단에 붙이지 않고 충분한 여백을 둔다.

## Scope

- Allowed: `src/pages/Home.tsx`, `src/index.css`, `src/pages/Home.test.tsx`, harness task/handoff/locks.
- Excluded: backend, authentication, billing, PII, `backend/pipeline/`.

## Work

1. 홈 전용 `scroll-snap` 및 섹션 최소 화면 높이를 제거한다.
2. 사용 흐름과 핵심 기능을 단일 `#features` 섹션으로 통합한다.
3. 히어로와 요약 바의 상하 여백 및 구획을 재조정한다.
4. 자연 스크롤, 끝 콘텐츠, 데스크톱/모바일 홈 UI를 테스트와 브라우저로 검증한다.

## Completion Criteria

- 마지막 CTA와 푸터가 자연스럽게 이어지고 빈 고정 화면이 남지 않는다.
- `How it works`와 `Features`가 단일 홈 섹션에서 함께 렌더링된다.
- 요약 바가 히어로 하단에 붙어 보이지 않는다.

## Verification

- `npx tsc -p tsconfig.app.json --noEmit`: passed.
- `npx tsc -p tsconfig.node.json --noEmit`: passed.
- `npx eslint src/pages/Home.tsx src/pages/Home.test.tsx`: passed.
- `npm test`: `16 passed`.
- `npm run build`: passed; existing Vite chunk-size warning only.
- Browser smoke: desktop top/guide/bottom and mobile `390x844` screenshots confirmed. Desktop bottom reached `scrollY=2477/maxScrollY=2477`, `scrollSnap=none`, no old snap hooks or error overlay; mobile has no horizontal overflow.
