# Verification

Standard verification for BOHUMFIT:

Codex runs these commands directly in the Windows workspace unless a task states a narrower verification scope.

```powershell
npm run lint
npm test
npm run build
```

For UI changes, also run the app locally and do a browser smoke test:

```powershell
npm run dev
```

## 검증 기준선 (BOHUMFIT-242 실측 · 2026-07-23 갱신)

백엔드 pytest — `cd backend && python -m pytest -q`:

```text
684 passed, 8 skipped
```

프런트 테스트 — `npm test`(라우트 스모크 18건 포함):

```text
79 passed
```

타입체크 — 양쪽 모두 통과해야 한다:

```powershell
npx tsc -p tsconfig.app.json --noEmit
npx tsc -p tsconfig.node.json --noEmit
```

빌드 산출물 청크 — `npm run build`의 `dist/assets/index-*.js`:

```text
343 kB대 (2026-07-23 실측 343.22 kB · gzip 101.81 kB)
```

- 청크가 343 kB대이고 Vite 청크 크기 경고가 없는 것이 **정상**이다. 과거 문서·기록의
  "500 kB chunk size warning만 허용" 표현은 구 빌드 상태의 산물이며 더는 기준이 아니다
  (BOHUMFIT-240 조사: 커밋 `2f041fc` 격리 빌드 342.66 kB = 당시 현행 343.22 kB로 확정).
- **±10%를 초과해 변동하면 진행을 멈추고 원인을 조사·기록한다**(산출물 급감·급증은 이상 신호).

기준선 수치가 바뀌면 이 파일과 `CLAUDE.md`·`AGENTS.md`를 함께 갱신한다.

## 수동 확인 체크리스트

- [ ] (태스크별 수동 확인 항목을 여기에 기록)

Record the exact commands and results in `.agent-harness/handoff.md`.
