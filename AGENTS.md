# Cowork→Codex Operating Rules (Two-Track)

This repository runs a two-track Cowork→Codex flow: Cowork implements in the sandbox; Codex verifies on Windows and publishes.

## Project

- Name: BOHUMFIT
- Local path: `C:\Users\18_rk\surit-react`
- Task prefix: `BOHUMFIT`
- Project context guide: `CLAUDE.md`

`CLAUDE.md` keeps project knowledge, codebase conventions, and user working preferences. The filename remains for continuity, but the active workflow is a two-track Cowork→Codex flow. New work should follow this file and the active task file first.

## Agent Roles

This repository runs a two-track Cowork→Codex flow:

- Cowork (sandbox/mount): planning, code reading, architecture judgment, implementation, refactoring, /tmp verification (tsc and unit checks against Windows-original integrity), handoff notes, and lock management. Cowork never runs git on the mount; staging, commit, and push are deferred to Codex.
- Codex (Windows authority): authoritative verification (tsc, lint, test, build, backend pytest, browser smoke checks), scoped Git staging, commit, and push when the task or user asks to publish.
- User: priority, product direction, production approval, and decisions that affect business behavior or risky data changes.

Each active task is implemented by Cowork and published by Codex, unless the user explicitly assigns otherwise. Cowork records its lock and handoff; Codex verifies on Windows and publishes. Old Claude/Cowork references in historical handoff entries are archival context only.

## Required Workflow

1. Read this file first.
2. Read `.agent-harness/handoff.md` for the latest project state.
3. Read `CLAUDE.md` as project context when useful.
4. Read or create the relevant task file in `.agent-harness/tasks/`.
5. Check `.agent-harness/locks.md` before editing files.
6. Codex checks `git status --short -uall` on Windows before staging. Cowork does not run git on the mount (see `ENV-MOUNT-NOTES.md`).
7. Keep edits inside the task scope unless the user approves an expanded scope.
8. Run the verification commands listed in the task or `.agent-harness/verify.md`.
9. Update `.agent-harness/handoff.md` with changed files, verification results, notes, and remaining issues.
10. Release any file locks in `.agent-harness/locks.md`.
11. If the task or user asks to publish, stage only task-scoped files, create a task-labeled commit, push the branch, and record the result.

## Safety Rules

- Do not overwrite user work or unrelated local changes.
- Do not stage, commit, or push unrelated files.
- Do not commit generated build output unless the task explicitly asks for it.
- Do not guess hidden requirements; record assumptions in the task or handoff.
- If verification cannot be run, write the exact reason in `handoff.md`.
- Keep task changes small enough to review quickly.
- For production-impacting changes, finish local verification first and leave final live validation to the user unless explicitly asked to check deployment.

## Standard Verification

Track split (gates and commands unchanged): Cowork runs sandbox `/tmp` checks (tsc/unit) and confirms Windows-original integrity; Codex runs the full PowerShell gate below on Windows as the authority, then commits/pushes.

Use `.agent-harness/verify.md` as the source of truth. Current standard commands:

```powershell
npm run lint
npm test
npm run build
```

Backend changes normally also require:

```powershell
cd backend
python -m pytest -q
```

For UI changes, also run the app locally and perform a browser smoke check when practical.

## Harness Files

- `.agent-harness/tasks/`: task queue and task-specific instructions.
- `.agent-harness/handoff.md`: latest implementation notes and completion records.
- `.agent-harness/decisions.md`: persistent decisions.
- `.agent-harness/locks.md`: temporary file ownership during active work.
- `.agent-harness/verify.md`: standard validation commands.
- `.agent-harness/ENV-MOUNT-NOTES.md`: 샌드박스 마운트 작업 시 따르는 회피 규칙(마운트 truncation·git 손상 주의, Cowork는 마운트 git 금지).
