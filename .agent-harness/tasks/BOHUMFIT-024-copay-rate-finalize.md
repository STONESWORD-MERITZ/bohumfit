# BOHUMFIT-024: Copay rate finalize

## Owner
- Codex

## Status
- Completed

## Type
- Copy/constant-name cleanup

## Scope
- `backend/insurance/constants.py`
- `backend/insurance/calculator.py`
- `src/pages/Disclosure.tsx`
- `.agent-harness/docs/BOHUMFIT_실비기능_설계_v3.md`
- `.agent-harness/tasks/BOHUMFIT-024-copay-rate-finalize.md`
- `.agent-harness/handoff.md`
- `.agent-harness/locks.md`

## Work
- Remove draft naming from §4-1 copay-rate verification flag.
- Keep all numeric copay values unchanged.
- Update backend and TS mirror wording so the UI no longer says the rates are draft.
- Re-run backend, frontend, build, and TS-vs-backend mirror consistency checks.

## Completed
- Renamed backend flag `COPAY_RATE_DRAFT` to `COPAY_RATE_VERIFIED`.
- Kept `GENERATION_COPAY_RATES` numeric values unchanged.
- Updated inactive backend caveat to trigger only when `COPAY_RATE_VERIFIED` is false.
- Updated insurance tab wording from draft copy to 2026-06 terms-confirmed copy.
- Updated design doc §4-1 heading/notes from draft to verified.

## Verification
- `ast.parse(..., encoding="utf-8")` OK for `backend/insurance/constants.py` and `backend/insurance/calculator.py`.
- `cd backend && python -m pytest -q` - 160 passed, 7 skipped.
- `npx tsc -p tsconfig.app.json --noEmit` - passed.
- `npx tsc -p tsconfig.node.json --noEmit` - passed.
- `npm run build` - passed; existing Vite chunk-size warning only.
- TS mirror vs backend consistency - passed over 504 generated cases.
