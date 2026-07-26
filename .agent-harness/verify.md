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

빌드 산출물 — `npm run build && npm run build:verify`(BOHUMFIT-248 게이트):

```text
정상 참조치: 프로덕션(Vercel) 786 kB대 (2026-07-26 실측 786,541 B)
판정: scripts/build-verify.mjs — ①크기 하한 600 kB ②필수 앱 문자열 ③index.html 참조 무결
```

- ★기준선 정정(BOHUMFIT-248 · 2026-07-26): 과거 "343 kB대 정상"(240 조사·242 문서화)은 **폐기**.
  로컬 Windows 번들 343 kB대는 rolldown 네이티브 바인딩 부재로 앱 코드가 통째로 빠진 껍데기였고
  (247 실측: 번들 내 앱 문자열 0건·vite preview 본문 공백·조용한 exit 0), 240의 격리 빌드 대조는
  동일하게 고장난 로컬 빌더 위에서 수행돼 오판이 재생산됐다. 이력 보존을 위해 기록한다.
- ※현 로컬 Windows: Application Control이 신규 네이티브 바이너리를 차단(248 P1 실측 — rolldown
  1.1.5·tailwind oxide 4.3.3 로드 차단, 구 설치본은 허용)하고 rolldown WASI는 Windows 절대경로를
  해석하지 못해 클린 재생성으로도 복구 불가. **로컬은 build:verify FAIL이 정직 상태**이며 기능
  판정은 소스 게이트(tsc·lint·vitest) + Codex의 프로덕션 번들 대체 검증으로 한다(Human 결정).
  근본 해결 후보: 정책 예외 등록(Human·관리자) / WSL·CI 빌드 검증 — 카탈로그 참조.

기준선 수치가 바뀌면 이 파일과 `CLAUDE.md`·`AGENTS.md`를 함께 갱신한다.

## 수동 확인 체크리스트

- [ ] (태스크별 수동 확인 항목을 여기에 기록)

Record the exact commands and results in `.agent-harness/handoff.md`.
