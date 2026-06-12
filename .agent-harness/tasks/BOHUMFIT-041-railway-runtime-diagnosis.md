# BOHUMFIT-041 Railway Runtime Diagnosis

## Owner
Codex (diagnose only)

## Scope
- Read-only target files: `backend/start.sh`, `backend/Dockerfile`, `backend/railway.json`
- Harness docs may be updated for diagnosis results.

## Purpose
Diagnose the Railway backend runtime mismatch after BOHUMFIT-039 without changing code.

## Questions
- Does `backend/start.sh` bind uvicorn to `$PORT` or a hard-coded port?
- Does `backend/start.sh` reinstall or verify Playwright Chromium at runtime?
- What `PORT` value is configured in Railway Variables?
- What is the externally observable symptom from the backend public domain?
- Is there a restart loop in Deploy Logs?
- Do build-time and runtime Playwright browser paths disagree?

## Constraints
- Do not modify `backend/start.sh`, `backend/Dockerfile`, or `backend/railway.json`.
- Record findings in handoff.
- Proposed fixes require separate Human approval.
