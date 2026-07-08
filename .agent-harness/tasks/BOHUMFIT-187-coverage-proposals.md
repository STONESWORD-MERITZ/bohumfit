# BOHUMFIT-187 coverage proposals

## Goal
Add consulting stage 3: proposed new contracts and coverages join the `[후]` recalculation path.

## Source
- `.agent-harness/tasks/BOHUMFIT-185-after-engine-spec.md`
- Stage 3 model: proposed contract/company/product/premium/pay period plus proposed coverage rows.

## Scope
- `backend/coverage/*`
- `backend/main.py` only if an API wiring endpoint is needed
- `backend/tests/test_coverage_proposal_187.py`
- `src/pages/CoverageRemodel.tsx`

## Non-Goals
- Do not touch disclosure pipeline code.
- Do not change `[전]` parsing/aggregation.
- Do not implement before-vs-after comparison/export; that is BOHUMFIT-188+.

## Acceptance
- New proposals are represented in a consulting plan.
- `[후]` uses kept existing contracts plus proposal contracts.
- Proposal premiums are included in `[후]` monthly totals.
- Proposal coverage values improve 부족/미가입 rows through the same aggregation/diagnosis path.
- 186-style keep/cancel/premium override behavior remains compatible.
- Frontend can add/edit a proposal manually and recalculate `[후]`.
