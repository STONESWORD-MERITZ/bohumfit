# BOHUMFIT-185 consulting-after spec

## Goal
Rebuild the retired consulting-after engine on top of the new KB coverage remodeling parser and report model.

The current 178-181 coverage series produces:
- stage 1 diagnosis: `[전]` company/coverage matrix
- stage 1 final diagnosis: `[최종]` recommendation/value/gap/status table
- Excel/PDF export for those two views

BOHUMFIT-185 is documentation only. It specifies how to add:
- stage 2 consulting decisions: keep/cancel/reduce/increase existing contracts and coverage amounts
- stage 3 new proposals: add proposed contracts and coverages
- recalculated `[후]`
- before-vs-after comparison
- final consulting summary for screen, Excel, and PDF

## Scope
- Create this task packet.
- Create `.agent-harness/tasks/BOHUMFIT-185-after-engine-spec.md`.
- Record investigation results in `.agent-harness/handoff.md`.
- Add a BOHUMFIT-185 lock line in `.agent-harness/locks.md`.

## Non-Goals
- No code changes.
- No renderer changes.
- Do not edit `backend/coverage/*`, `backend/main.py`, or `src/pages/CoverageRemodel.tsx`.
- Do not stage real PDFs, Excel files, or PII.
- Do not rely on uncommitted Cowork work for BOHUMFIT-182~184.

## Investigation Source Rules
- Current data model must be read from `git show HEAD:...`, not from the working tree.
- Deleted consulting-after history must be read from git history:
  - `a7b6c00` BOHUMFIT-041 mapping engine
  - `158a87b` BOHUMFIT-043 consulting after state and after table
  - `a1f4098` BOHUMFIT-044 final comparison table
  - `f7858a2` BOHUMFIT-045 Excel export
  - `752d512` BOHUMFIT-180 deletion/retirement commit

## Stage Checklist
- [x] Stage 0: current model and deletion history reviewed.
- [x] Stage 1: stage-2 keep/cancel/reduce/increase schema specified.
- [x] Stage 2: stage-3 new proposal schema specified.
- [x] Stage 3: `[후]` recalculation rule specified.
- [x] Stage 4: before-vs-after and final summary output structure specified.
- [x] Stage 5: implementation split for BOHUMFIT-186+ specified.

## Verification
- Documentation completeness only.
- Confirm schema, edge cases, PII posture, and Human decisions.
- No tsc/build/pytest required because no code changes are allowed.

## Completion
- Commit only:
  - `.agent-harness/tasks/BOHUMFIT-185-consulting-after-spec.md`
  - `.agent-harness/tasks/BOHUMFIT-185-after-engine-spec.md`
  - `.agent-harness/handoff.md`
  - `.agent-harness/locks.md`

