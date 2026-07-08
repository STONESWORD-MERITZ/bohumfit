# BOHUMFIT-188 before/after comparison and final summary

## Goal
Show the customer how their coverage changed after consulting:

- `[전]`: KB coverage analysis baseline.
- `[후]`: BOHUMFIT-186 keep/cancel decisions plus BOHUMFIT-187 proposal contracts.
- Summary: monthly premium delta, total paid delta, and shortage/missing coverage improvements.

## Source
- `.agent-harness/tasks/BOHUMFIT-185-after-engine-spec.md`
- `.agent-harness/tasks/BOHUMFIT-187-coverage-proposals.md`

## Scope
- `backend/coverage/*`
- `backend/tests/test_coverage_compare_188.py`
- `src/pages/CoverageRemodel.tsx`
- `backend/coverage/export_excel.py`
- `backend/coverage/export_pdf.py`

## Non-Goals
- Do not touch the disclosure pipeline.
- Do not change the `[전]` KB parser baseline.
- Do not regress BOHUMFIT-186 keep/cancel or BOHUMFIT-187 proposal behavior.
- Do not use legacy brand colors outside FIT v1.1 emerald/ink.

## Acceptance
- Before/after coverages render side by side by major category.
- Each coverage row exposes `before_status`, `after_status`, `status_change`, value delta, and improvement/worsening flags.
- Summary includes monthly premium delta, total paid delta, improved coverage count, `미가입 → 충분`, and `부족 → 충분`.
- Excel export includes after company detail, before/after comparison, and consulting summary sheets.
- PDF export includes a customer-facing before/after comparison page, FIT v1.1 brand color, and disclaimer.
- Synthetic tests verify side-by-side rows, status changes, premium/paid deltas, improvement counts, Excel sheets, and PDF HTML.

## Verification
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run build`
- `npm test`
- `cd backend && python -m pytest -q`
- `python -m pytest backend/tests/test_coverage_after_186.py backend/tests/test_coverage_proposal_187.py backend/tests/test_coverage_compare_188.py -q`
- `python -m pytest backend/tests/test_coverage_compare_188.py -vv`
- Real KB PDF smoke in memory only: 문건주 PDF → proposal payload → Excel/PDF bytes.
