# Claude Chat→Cowork→Codex Operating Rules (Three-Role)

This repository runs a three-role workflow: Claude Chat writes intent-centered task prompts, Claude Cowork implements in the sandbox, and Codex verifies on Windows then commits, pushes, and supports deployment checks.

## Project

- Name: BOHUMFIT
- Local path: `C:\Users\18_rk\BOHUMFIT`
- Task prefix: `BOHUMFIT`
- Project context guide: `CLAUDE.md`

`CLAUDE.md` keeps project knowledge, codebase conventions, and user working preferences. The filename remains for continuity, but the active workflow is the Claude Chat→Cowork→Codex three-role harness. New work should follow this file, `.agent-harness/WORKFLOW.md`, and the active task file first.

## Agent Roles

This repository runs a three-role, new-chat-safe flow:

- Claude Chat (prompt author): translates the user's business intent into a task packet. The prompt must state goal, user intent, scope, non-goals, risks, expected verification, and completion criteria. Claude Chat does not edit code or decide that work is complete.
- Claude Cowork (sandbox/mount implementer): plans, reads code, implements, refactors, adds tests, runs feasible /tmp checks, records assumptions, and writes handoff. Cowork may improve the literal prompt when the user's intent clearly requires a better edge-case, test, or safety guard, but must record the reasoning. Cowork never runs git on the mount; staging, commit, and push are deferred to Codex.
- Codex (Windows authority): performs authoritative verification (tsc, lint, test, build, backend pytest, browser smoke checks), rejects incomplete work when needed, applies narrow fixes when safe, stages only scoped files, commits, pushes, and performs deployment-oriented checks when requested.
- User: priority, product direction, production approval, and decisions that affect business behavior or risky data changes.

Each substantive task should be restartable in a new chat from its task packet and latest handoff entry. Old two-track wording in historical handoff entries is archival context only.

## Required Workflow

1. Read this file first.
2. Read `.agent-harness/handoff.md` for the latest project state.
3. Read `CLAUDE.md` as project context when useful.
4. Read `.agent-harness/WORKFLOW.md` for role routing and new-chat handoff rules.
5. Read or create the relevant task file in `.agent-harness/tasks/`.
6. Check `.agent-harness/locks.md` before editing files.
7. Codex checks `git status --short -uall` on Windows before staging. Cowork does not run git on the mount (see `ENV-MOUNT-NOTES.md`).
8. Keep edits inside the task scope unless the user's intent clearly requires a small adjacent fix; record the reason in handoff.
9. Run the verification commands listed in the task or `.agent-harness/verify.md`.
10. Update `.agent-harness/handoff.md` with changed files, verification results, notes, and remaining issues.
11. Release any file locks in `.agent-harness/locks.md`.
12. If the task or user asks to publish, stage only task-scoped files, create a task-labeled commit, push the branch, and record the result.

## Safety Rules

- Do not overwrite user work or unrelated local changes.
- Do not stage, commit, or push unrelated files.
- Do not commit generated build output unless the task explicitly asks for it.
- Do not guess hidden requirements; record assumptions in the task or handoff.
- Do not execute only the literal sentence if the user's intent requires stronger verification, regression coverage, or a safer UX. Improve within scope and explain it.
- If a better result requires a risky product, legal, payment, auth, or data-policy decision, stop at a recommendation and leave it to Human.
- If verification cannot be run, write the exact reason in `handoff.md`.
- Keep task changes small enough to review quickly.
- For production-impacting changes, finish local verification first and leave final live validation to the user unless explicitly asked to check deployment.

## Standard Verification

Verification split (gates and commands unchanged): Claude Chat defines the intended checks in the task packet, Cowork runs feasible sandbox `/tmp` checks and confirms Windows-original integrity, and Codex runs the full PowerShell gate below on Windows as the authority before commit/push.

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
- `.agent-harness/WORKFLOW.md`: three-role new-chat operating model and task packet contract.
- `.agent-harness/ENV-MOUNT-NOTES.md`: 샌드박스 마운트 작업 시 따르는 회피 규칙(마운트 truncation·git 손상 주의, Cowork는 마운트 git 금지).
