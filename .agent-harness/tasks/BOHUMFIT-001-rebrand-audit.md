# BOHUMFIT-001: BOHUMFIT → BOHUMFIT 리브랜딩 전수 감사

project: BOHUMFIT
owner: Codex
status: completed

## Goal

코드베이스 전체에서 `bohumfit`/`BOHUMFIT` 잔존 항목을 전수 조사하고, 사용자 노출 표시 문자열 중 안전하게 교체 가능한 항목만 반영한다. 외부 인프라·remote·환경변수·이력 추적용 태스크 ID는 자동 변경하지 않고 사용자 결정 대기 항목으로 보고한다.

## Scope

Editable files:

- `.agent-harness/tasks/BOHUMFIT-001-rebrand-audit.md`
- `.agent-harness/handoff.md`
- `.agent-harness/locks.md`

Do not edit without explicit approval:

- `git remote`
- Vercel/Railway/Supabase dashboard settings
- `package.json` / `package-lock.json` package name
- backend CORS/API URL environment defaults
- historical `BOHUMFIT-*` task IDs, comments, audit docs, local folder references

## Requirements

- Run case-insensitive `bohumfit` search and classify findings.
- Confirm user-facing HTML/meta/logo/footer/Kakao strings.
- Confirm settings: package name, CI env API URL, frontend env, backend CORS, Sentry env usage, git remote.
- Replace only safe display strings if any remain.
- Record all risky/external settings as Human decision items.

## Verify

- `git diff --check`
- If runtime code is changed: `npx tsc -p tsconfig.app.json --noEmit`, `npm run build`, `npm run lint`

## Publish

- Commit/push audit documentation only if no runtime safe replacement is needed.
- Commit message: `BOHUMFIT-001: 리브랜딩 잔존 BOHUMFIT 전수 감사 및 외부 설정 결정항목 정리`

## Notes

- This task intentionally preserves `BOHUMFIT-*` history identifiers for traceability.
