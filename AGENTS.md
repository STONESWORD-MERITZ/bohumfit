# Claude Chat→Claude Code→Codex Operating Rules (Three-Role)

This repository runs a three-role workflow: Claude Chat writes intent-centered task prompts, Claude Code implements and runs first-pass verification directly on Windows, and Codex performs second-pass verification then commits, pushes, and supports deployment checks.

> 구성 변경(BOHUMFIT-224, 2026-07-17): 구현 트랙이 Claude Cowork(샌드박스)에서 Claude Code(Windows 로컬)로 교체됐다. 사유는 마운트 truncation 반복(182~184·195·213 mid-token 절단). 순서는 불변: Chat → Code → Codex. Cowork 관련 과거 규칙은 문서 하단 "[퇴역] Cowork 이력" 섹션 참조.

## Project

- Name: BOHUMFIT
- Local path: `C:\Users\18_rk\BOHUMFIT`
- Task prefix: `BOHUMFIT`
- Project context guide: `CLAUDE.md`

`CLAUDE.md` keeps project knowledge, codebase conventions, and user working preferences. The filename remains for continuity, but the active workflow is the Claude Chat→Claude Code→Codex three-role harness. New work should follow this file, `.agent-harness/WORKFLOW.md`, and the active task file first.

## Root Gate (모든 트랙, 작업 시작 전 필수)

레포를 만지는 모든 트랙(Claude Code·Codex)은 작업 시작 전에 아래 3종을 확인한다.

1. `pwd` = `C:\Users\18_rk\BOHUMFIT`
2. `git remote -v` = `github.com/STONESWORD-MERITZ/bohumfit`
3. 리트머스 파일 존재: `.agent-harness/tasks/BOHUMFIT-219-shared-rls-migration-alignment.md`

하나라도 불일치하면 즉시 중단하고 Human에게 보고한다. 바탕화면 사본·구버전 등 유사 폴더에서 작업하지 않는다.

## Agent Roles

This repository runs a three-role, new-chat-safe flow:

- Claude Chat (prompt author): translates the user's business intent into a task packet. The prompt must state goal, user intent, scope, non-goals, risks, expected verification, and completion criteria. Claude Chat does not edit code or decide that work is complete. 레포 접근 없음. 위험도(저위험/고위험) 판단과 명시도 Chat 책임이다.
- Claude Code (Windows local implementer): plans, reads code, implements, refactors, adds tests, runs first-pass verification directly on Windows (tsc, lint, build, pytest — 로컬 직접 실행, 결과 신뢰 가능), records assumptions, and writes handoff. Claude Code may improve the literal prompt when the user's intent clearly requires a better edge-case, test, or safety guard, but must record the reasoning. git 읽기(pwd·remote·log·diff·status)는 허용, git 쓰기(add/commit/push)는 기본 금지 — 저위험 태스크에서 Chat이 "Code 커밋 허용"을 명시한 경우만 예외(아래 위험도 운영 규칙 참조).
- Codex (second-pass verifier & committer): performs second-pass authoritative verification (tsc, lint, test, build, backend pytest, browser smoke checks), stages only scoped files, commits, pushes, and performs deployment-oriented checks when requested. 검증·반려 전용 — 직접 수정은 한 줄급만 허용하고, 그 이상이 필요하면 반려하여 handoff로 Claude Code에 회송한다.
- User: priority, product direction, production approval, and decisions that affect business behavior or risky data changes.

Each substantive task should be restartable in a new chat from its task packet and latest handoff entry. Old two-track wording and Cowork-era wording in historical handoff entries are archival context only.

## 위험도 운영 규칙

- 저위험(문구·스타일·소규모 UI·문서): Claude Chat이 태스크 패킷에 "Code 커밋 허용"을 명시한 경우, Claude Code가 검증 계약 통과 후 커밋·push까지 수행할 수 있고 Codex 단계는 생략 가능하다.
- 고위험(DB·보안·인증·pipeline·coverage 코어·대형 리팩터·마이그레이션): 풀 하네스를 적용한다 — Claude Code 구현 → Codex 2차 검증·커밋·push. DB 변경은 추가로 Human 게이트를 거친다: SQL은 Chat이 작성하고 Human이 실행한다.
- 위험도 판단·명시는 Chat 책임이다. 명시가 없으면 풀 하네스(기본값)로 처리한다.

## Required Workflow

1. Pass the Root Gate checks above (pwd, remote, 리트머스 파일).
2. Read this file first.
3. Read `.agent-harness/handoff.md` for the latest project state.
4. Read `CLAUDE.md` as project context when useful.
5. Read `.agent-harness/WORKFLOW.md` for role routing and new-chat handoff rules.
6. Read or create the relevant task file in `.agent-harness/tasks/`.
7. Check `.agent-harness/locks.md` before editing files.
8. Codex checks `git status --short -uall` on Windows before staging. Claude Code may use read-only git (status, log, diff, remote) at any time but does not stage, commit, or push unless the task grants low-risk commit permission.
9. Keep edits inside the task scope unless the user's intent clearly requires a small adjacent fix; record the reason in handoff.
10. Run the verification commands listed in the task or `.agent-harness/verify.md`. Claude Code runs the first pass directly on Windows; Codex reruns the gate as the second-pass authority before commit/push.
11. Update `.agent-harness/handoff.md` with changed files, verification results, notes, and remaining issues.
12. Release any file locks in `.agent-harness/locks.md`.
13. If the task or user asks to publish, stage only task-scoped files, create a task-labeled commit, push the branch, and record the result. 커밋·push 주체는 기본 Codex이며, 저위험 + "Code 커밋 허용" 명시 시에만 Claude Code가 수행한다.

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
- STEP 0 실측 없이 수정하지 않는다. 최소 수정 원칙 — 스펙 밖 발견은 기록만 하고 Human이 결정한다.
- 이상 신호(빌드 산출물 급감, 핵심 구조 "없음" 보고, 파일 절단 징후, 과거 커밋으로의 회귀) 감지 시 즉시 중단하고 보고한다.

## Standard Verification

Verification split (gates and commands unchanged): Claude Chat defines the intended checks in the task packet, Claude Code runs the full first-pass gate directly on Windows(tsc·lint·build·pytest 직접 실행·신뢰), and Codex reruns the gate as the second-pass authority before commit/push. 저위험 + "Code 커밋 허용" 태스크에서는 Claude Code의 1차 통과가 커밋 게이트가 된다.

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

### 커밋 전 검증 계약

커밋 주체(Codex 또는 저위험 허용 시 Claude Code)와 무관하게, 커밋 전에 아래를 모두 만족해야 한다.

- `npx tsc -p tsconfig.app.json --noEmit` / `npx tsc -p tsconfig.node.json --noEmit`
- `npm run lint` / `npm run build`
- `cd backend && python -m pytest -q` — 기준선 `618 passed, 8 skipped` (기준선 변경 시 `verify.md` 동시 갱신)
- 도메인 계약 grep: `SURIT` 0건, 구브랜드 색상(`#15663D` 등 구 그린) 0건 — 기존 계약 유지
- 보호 영역 diff 검사: `backend/pipeline/`, `backend/coverage/` 코어, `supabase/`, 인증(auth) 관련 파일에 diff가 발생했는데 태스크에 명시돼 있지 않으면 커밋 금지

## Harness Files

- `.agent-harness/tasks/`: task queue and task-specific instructions.
- `.agent-harness/handoff.md`: latest implementation notes and completion records.
- `.agent-harness/decisions.md`: persistent decisions.
- `.agent-harness/locks.md`: temporary file ownership during active work.
- `.agent-harness/verify.md`: standard validation commands.
- `.agent-harness/WORKFLOW.md`: three-role new-chat operating model and task packet contract.
- `.agent-harness/ENV-MOUNT-NOTES.md`: [퇴역] 과거 Cowork 샌드박스 마운트 회피 규칙(과거 handoff 해석용 이력 문서).

## [퇴역] Cowork 이력 (과거 handoff 해석용)

2026-07-17 BOHUMFIT-224로 Claude Cowork(샌드박스/마운트) 구현 트랙은 퇴역했다. 사유: 마운트 truncation 반복(182~184·195·213 mid-token 절단). 아래 규칙은 삭제하지 않고 과거 handoff·task·locks 기록 해석용으로 보존한다.

- Claude Cowork (sandbox/mount implementer): planned, read code, implemented, refactored, added tests, ran feasible `/tmp` checks, recorded assumptions, and wrote handoff. Cowork never ran git on the mount; staging, commit, and push were deferred to Codex.
- Cowork-era verification split: Cowork ran feasible sandbox `/tmp` checks and confirmed Windows-original integrity; Codex ran the full Windows gate as the authority.
- 마운트 truncation/git 손상 회피 규칙: `.agent-harness/ENV-MOUNT-NOTES.md` 참조.
- 과거 handoff/locks의 "Cowork - 완료", "/tmp 검증", "마운트 truncation" 표기는 모두 이 퇴역 트랙의 기록이다.
