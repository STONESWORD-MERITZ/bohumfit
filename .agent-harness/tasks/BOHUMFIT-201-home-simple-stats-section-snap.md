# BOHUMFIT-201 - 메인 하단 지표 단순화 및 섹션 스냅 개선

Owner flow: Human -> Codex Windows
Current owner: Human(배포 확인)

## Intent

- 메인 히어로 하단의 `1분 / 99% / 30초` 지표 영역이 과하게 커 보여 전체 UI 퀄리티를 떨어뜨리므로, 단순하고 깔끔하게 구분되는 요약 바 수준으로 낮춘다.
- 메인 페이지는 `hanjasan.co.kr`처럼 섹션 단위로 딱딱 끊겨 보이는 스크롤감을 적용한다.

## Scope

- 수정 허용:
  - `src/pages/Home.tsx`
  - `src/index.css`
  - 필요한 경우 프론트 테스트
  - `.agent-harness/tasks/BOHUMFIT-201-home-simple-stats-section-snap.md`
  - `.agent-harness/handoff.md`, `.agent-harness/locks.md`
- 수정 금지:
  - `backend/pipeline/`
  - 보험 분석 로직/인증/결제/PII 관련 파일

## Work

1. 지표 카운트업/대형 숫자 UI를 제거하고 정적인 compact stat bar로 변경한다.
2. 홈 전용 wrapper와 section class를 추가해 데스크톱에서 섹션 스냅이 걸리게 한다.
3. 모바일과 `prefers-reduced-motion`에서는 자연 스크롤을 유지한다.
4. 기존 CTA, 브랜드 컬러, 히어로 카피는 유지한다.

## Verification

- `npx tsc -p tsconfig.app.json --noEmit`: 통과.
- `npx tsc -p tsconfig.node.json --noEmit`: 통과.
- `npm test`: `16 passed`.
- `npm run build`: 통과. 기존 Vite chunk-size warning 및 plugin timing warning만 출력.
- 홈 route browser smoke: `http://127.0.0.1:5180/` 200, Chrome headless screenshot 확인.
- `npm run lint`: 실패. 이번 변경 파일의 lint는 해결됐고, 기존 범위 밖 파일 `src/hooks/useCountUp.ts`, `src/pages/CoverageRemodel.tsx`, `src/pages/Disclosure.tsx`, `src/pages/History.tsx`의 기존 lint 오류가 남음.

## Notes

- 외부 사이트는 공개 HTML 기준 KAMAC 랜딩으로 확인. 효과 구현명은 번들 내부에 있어 직접 확인되지 않으므로, 제품 의도는 섹션 스냅/풀페이지식 구분감으로 해석한다.
- 신규 테스트 `src/pages/Home.test.tsx`로 compact stat bar 문구와 홈 스냅 hook class를 고정했다.
