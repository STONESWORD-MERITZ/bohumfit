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

Backend pytest baseline:

```text
611 passed, 8 skipped
```

## 수동 확인 체크리스트

- [ ] (태스크별 수동 확인 항목을 여기에 기록)

Record the exact commands and results in `.agent-harness/handoff.md`.
