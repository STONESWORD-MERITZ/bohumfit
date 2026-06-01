# SURIT-021: Sentry PII hardening

## Owner
- Codex

## Status
- Completed

## Type
- Security hardening

## Context
- SURIT-020 found that `sentry-sdk==2.60.0` defaults `include_local_variables` to `True`.
- If an exception occurs during analysis, stack locals could include PDF bytes, extracted medical records, `raw_text`, `disease_stats`, Gemini `contents`, or similar sensitive values.
- BOHUMFIT intentionally does not store medical data in DB/Storage, so error-report payloads must also avoid leaking health data to Sentry.

## Scope
- `backend/main.py`
- `.agent-harness/tasks/SURIT-021-sentry-pii-hardening.md`
- `.agent-harness/handoff.md`
- `.agent-harness/locks.md`

## Work Completed
- Set backend Sentry init `include_local_variables=False`.
- Kept and explicitly verified `send_default_pii=False`.
- Set `max_request_body_size="never"` to prevent request body/multipart capture.
- Added defensive `before_send` scrubbing for request body/cookies/env, auth headers, stack locals, breadcrumbs, contexts, and exception payloads.
- Preserved the existing `SENTRY_DSN` guard so local/no-DSN environments keep working.
- Left frontend Sentry out of scope; noted follow-up in handoff.

## Verification
- `cd backend && python -m pytest -q` - 142 passed, 7 skipped.
- Local fake-DSN Sentry init check confirmed:
  - `include_local_variables=False`
  - `max_request_body_size=never`
  - `send_default_pii=False`
- Local `_sanitize_event` payload check confirmed sensitive keys were filtered:
  - `raw_text`, `disease_stats`, `contents`, `active_files`, `pdf_data`, stack `vars`, request body/cookies/env, auth/cookie/API-key headers.
- `npx tsc -p tsconfig.app.json --noEmit` - passed.
- `npx tsc -p tsconfig.node.json --noEmit` - passed.
- `npm run build` - passed, with existing Vite chunk-size warning only.

## Notes
- Sentry remains enabled when `SENTRY_DSN` is configured; only PII capture paths were reduced.
- Analysis logic and exception flow were not changed.
- Frontend Sentry replay is already disabled, but a separate frontend Sentry PII audit can verify headers, breadcrumbs, and event request fields if desired.
