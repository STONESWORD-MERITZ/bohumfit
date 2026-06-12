# BOHUMFIT-039 Railway Backend Dockerfile

## Owner
Codex (Windows authority)

## Purpose
End Railway builder/start-command nondeterminism for BOHUMFIT report PDF generation by packaging the backend runtime with a Dockerfile.

## Confirmed Diagnosis
- Railway build logs showed `pip install playwright==1.52.0`, but no `python -m playwright install --with-deps chromium`, no Chromium download, and no `fonts-noto-cjk` install.
- Runtime logs showed `report pdf renderer unavailable: Chromium missing`.
- `backend/start.sh` runtime fallback log was absent, so the previous Nixpacks/start fallback was not being executed.

## Implementation
- Add a repo-root `Dockerfile` for Railway services whose Root Directory is the repository root.
- Add `backend/Dockerfile` for Railway services whose Root Directory is `backend/`.
- Use `mcr.microsoft.com/playwright/python:v1.52.0-noble` to match pinned `playwright==1.52.0`.
- Install backend requirements and `fonts-noto-cjk`.
- Keep `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`, aligned with the Playwright base image browser location.
- Reuse `backend/start.sh`; it remains an idempotent runtime fallback and binds uvicorn to Railway `$PORT`.
- Add `railway.json` and `backend/railway.json` with `builder=DOCKERFILE` and `startCommand=null` so Dockerfile `CMD` is used.
- Keep existing `nixpacks.toml` and `backend/nixpacks.toml` for rollback reference.

## Verification Plan
- JSON parse: `railway.json`, `backend/railway.json`.
- Docker static check and, if Docker is available, build and report-PDF smoke check.
- `cd backend && python -m pytest -q`.
- Frontend standard gate: `npx tsc -p tsconfig.app.json --noEmit`, `npx tsc -p tsconfig.node.json --noEmit`, `npm run lint`, `npm test`, `npm run build`.

## Human Follow-Up
- Confirm Railway deployment details show Dockerfile builder/config source.
- If a dashboard Custom Start Command remains, clear it so Dockerfile `CMD` is not bypassed.
- After deploy, run browser E2E PDF downloads for disclosure and insurance reports.
