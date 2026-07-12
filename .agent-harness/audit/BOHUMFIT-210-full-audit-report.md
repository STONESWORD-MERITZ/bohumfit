# BOHUMFIT-210 Full Audit Report

Date: 2026-07-12
Owner: Codex Windows
Scope: full repository audit plus safe fixes only

## Guardrails

- No real PDF, medical record, customer name, resident number, API key, secret, or rendered real-data image was committed or written into this report.
- `backend/pipeline/`, `backend/coverage/`, DB/RLS/Supabase Auth policy, and phone verification policy were treated as report-only risk areas.
- Allowed automatic changes were limited to hCaptcha fail-open UX safety, logic-free lint cleanup, a pure helper split, baseline docs, harness docs, and tests.

## Executive Summary

- Core coverage values passed read-only smoke checks against local real PDFs in memory only:
  `[전]` monthly `573,227`, paid total `181,984,128`, injury death `550,000,000`, general cancer `100,000,000`, warnings `0`.
- BOHUMFIT-193 proposal parsing passed read-only smoke with 5 proposal PDFs:
  total premium `162,154`, bundle splits and special amounts matched measured anchors, warnings `0`.
- BOHUMFIT-205 drug-change logic has bilateral regression coverage: same-ingredient/generic and transient 90-day cases are suppressed, while new ingredient and dose increase still fire.
- Real security bug found and fixed: hCaptcha could block OAuth when the widget failed. OAuth is now independent of hCaptcha, and email auth fails open only when the widget is unavailable.
- Lint was failing with 7 errors. All were fixed with low-risk mechanical changes; `npm run lint` is now clean.
- Main report-only risks are server-side `phone_verified` enforcement, partial-text/image PDF diagnostics, GA/logo placeholder slots, and numbering hygiene.

## PASS 1 - Correctness / Reliability

### P1-OK-01 Coverage baseline smoke

Read-only local smoke, in-memory only:

| Area | Observed |
| --- | ---: |
| Before monthly premium | `573,227` |
| Before paid total | `181,984,128` |
| Injury death | `550,000,000` |
| General cancer | `100,000,000` |
| Parser warnings | `0` |

Targeted regression command:

```text
cd backend; python -m pytest tests/test_coverage_parser_179.py tests/test_coverage_parser_179b.py tests/test_coverage_parser_182.py tests/test_coverage_proposal_parse_193.py tests/test_coverage_compare_188.py tests/test_coverage_hold_cancel_190.py tests/test_drug_change_205.py tests/test_pdf_parser.py -q
```

Result: `78 passed`.

### P1-OK-02 BOHUMFIT-193 proposal smoke

Read-only local smoke, in-memory only:

| Anchor | Observed |
| --- | ---: |
| Proposal PDFs found | `5` |
| Premium total | `162,154` |
| Company order | `KB손해보험`, `메리츠화재`, `메리츠화재`, `메리츠화재`, `미래에셋생명` |
| 암수술비 bundle split | `17,500,000` |
| 고액(표적)항암치료비 | `80,500,000` |
| 항암방사선약물치료 | `20,500,000` |
| 미래 유사암 | `20,000,000` |
| KB 특정Ⅱ mapped amount | `50,000,000` |
| 자동차사고부상 14급 | `300,000` |
| Parser warnings | `0` |

### P1-OK-03 BOHUMFIT-182/196 insurer split smoke

Read-only local smoke, in-memory only:

| Anchor | Observed |
| --- | ---: |
| Monthly total | `96,000` |
| Contract count | `6` |
| Insurers | `AIA생명`, `KB손보`, `메리츠화재`, `현대해상`, `현대해상`, `흥국생명` |
| Missing-premium rows | `1` |
| Parser warnings | `0` |

### P1-OK-04 BOHUMFIT-185 same-path principle

- Backend before/after path is intact: `backend/coverage/compare.py::build_after_analysis` imports and uses the same `aggregate_coverage_values` path as before aggregation.
- `backend/coverage/consulting.py` also builds final values through `aggregate_coverage_values` and `build_final`.
- No automatic backend coverage change was made.

### P1-FIND-01 Frontend after-calculation duplication

Severity: 🟡건강

`src/pages/CoverageRemodel.tsx` keeps a local `aggregateCoverageValues` / `buildAfterResult` path for instant UI updates while backend export/API uses `backend/coverage`. Current tests and smoke values are OK, but this is a drift risk because a future rule change could land in backend and miss frontend.

Human task: keep frontend as display cache only and add a parity test or endpoint-backed recompute check before future coverage rule changes.

### P1-OK-05 BOHUMFIT-205 drug-change bidirectional audit

Static and targeted test audit found the intended balance:

- Same ingredient/generic brand switch: suppressed.
- Wrapped Korean spacing in ingredient/drug names: normalized.
- Transient 90-day prescription followed by current regimen matching the pre-90-day regimen: suppressed.
- Real new ingredient: still flagged.
- Same or different brand dose increase: still flagged.
- Missing ingredient data: legacy brand-key behavior remains.

The helper `_current_confirmation_matches_before` returns true only when the latest confirmed prescription token set exactly matches the pre-90-day token set. Missing latest data or extra/new ingredients keep conservative disclosure sensitivity.

### P1-OK-06 10-to-0-year result window

`src/pages/Disclosure.tsx` applies the 10-to-0-year selector only as a display/confirmation filter. It does not change server judgment, legal product-question periods, copy text, or PDF report payloads.

### P1-FIND-02 Mixed/partial image PDF diagnostics

Severity: 🟠완결성

BOHUMFIT-198 image-PDF guidance is correct for zero-text PDFs. The current diagnostic key is still first-page text oriented: if a mixed PDF has enough text on page 1 but later pages are image-only, the parser can return a generic "no recognizable table" style failure rather than the clearer image-PDF guidance for the image-only pages.

No silent success was found: extraction returning zero records still surfaces an error/warning path. The gap is diagnostic specificity, not data silently accepted.

Human task: add a follow-up parser diagnostic that records per-page text character counts and warns when some pages are textless/image-like while others have text. This belongs in `backend/pipeline/` and was not auto-fixed.

## PASS 2 - Completeness / UX

### P2-OK-01 Main flows and routes

Static route/link scan did not show an obvious dead top-level route:

- Public/entry: `/`, `/login`, `/signup`, `/check`, `/disclosure/sample`, `/download-guide`, `/coverage-guide`, `/insurance-links`, `/subscription`, `/why`, legal aliases.
- Protected: `/disclosure`, `/coverage-compare`, `/history`, `/dashboard`, `/insurance`.
- `/check` correctly redirects to customer disclosure mode.

### P2-OK-02 Proposal parsing connection

`src/pages/CoverageRemodel.tsx` calls `/coverage/proposals/parse` for proposal upload and fills proposal cards automatically. Manual proposal input remains available as fallback.

### P2-FIND-01 GA/profile/logo slots still placeholder

Severity: 🟠완결성

Coverage report export still has GA/logo placeholders:

- `backend/coverage/export_pdf.py`: `GA LOGO`
- `backend/coverage/export_excel.py`: `GA 로고`, `슬롯 준비`

This is user-visible in exported artifacts and blocks a fully polished consultant packet.

Human task: split or revive BOHUMFIT-192 profile/GA/logo implementation. Requires product/profile schema decisions, not a safe audit auto-fix.

### P2-FIND-02 5th-generation 실손 is explicitly not implemented

Severity: 🟡건강

The 5th generation insurance calculator path remains `null` / "준비중" in frontend and shared calculator constants. This is transparent to the user but should be tracked as a product decision when 5th generation rules are finalized.

Human task: create a product/rules task for 5th generation 실손 once authoritative terms are available.

### P2-FIND-03 Legacy current/proposal coverage parser has transparent precision warning

Severity: 🟠완결성

`backend/pipeline/coverage_parser.py` still includes a warning that precise coverage-to-contract mapping is not fully implemented for the older generic coverage parser path. This is transparent, not silent, but it is a completeness gap if that route remains product-facing.

Human task: either retire the old path from user-facing flows or implement precise contract mapping with fixtures.

### P2-FIND-04 Phone verification remains a stubbed user journey

Severity: 🔴보안

Signup and `/phone-verify` still depend on stubbed phone verification behavior. BOHUMFIT-206 correctly scoped this into OTP/unique-number/server-gate follow-up work. This audit did not modify the flow.

Human task: execute 207/208/209 sequence from BOHUMFIT-206 before relying on 1-person-1-account as an enforced security boundary.

## PASS 3 - Security

### P3-FIX-01 hCaptcha fail-open and OAuth unblock

Severity: 🔴보안

Problem found:

- `Login.tsx` and `Signup.tsx` required a captcha token before OAuth handlers.
- With `VITE_HCAPTCHA_SITEKEY` set and the hCaptcha script blocked or failed, Kakao/Google could be blocked by a token that Supabase OAuth does not officially consume.

Safe fix applied:

- OAuth handlers no longer call the captcha requirement.
- `HCaptcha` now reports `onReady` and `onUnavailable`.
- Email auth requires a token only when hCaptcha is configured and available.
- If the widget fails to load or returns an error callback, the auth screens clear the token and continue via the existing flow.
- The hCaptcha script loader resets after load rejection so retries/tests are not pinned to a rejected promise.

Regression tests:

- `src/components/HCaptcha.test.tsx`: widget unavailable callback.
- `src/pages/AuthCaptcha.test.tsx`: keyless login render, OAuth independent of captcha, email fail-open when widget load fails, signup OAuth independent of captcha.

### P3-FIND-01 Server APIs rely on `verify_jwt` without phone verification

Severity: 🔴보안

`backend/main.py` protected APIs depend on `verify_jwt`, but no server-side `phone_verified` dependency is applied to analysis/report/history/coverage APIs. This means the frontend phone gate is not the final boundary for direct API calls.

Human task: BOHUMFIT-209 should add `require_verified_phone` on cost-bearing and sensitive APIs after OTP/unique-number work is decided. This audit did not modify auth policy.

### P3-FIND-02 Supabase profile policy/index cleanup remains Human-owned

Severity: 🔴보안

Prior handoff and decisions note duplicate/legacy `profiles` policy/index concerns. This repository cannot safely validate or alter shared Supabase state from code alone, and shared BOHUMFIT/FitHere impact remains.

Human task: run reviewed SQL during low traffic, after checking FitHere shared-table impact.

### P3-OK-01 Hardcoded secret scan

Scan result: no hardcoded secret values detected. Matches were environment variable names/references only:

- `backend/main.py`: `HCAPTCHA_SECRET`
- `src/pages/Subscription.tsx`: `VITE_TOSS_CLIENT_KEY`

`public/.well-known/security.txt` uses `contact@bohumfit.ai`, not a personal Gmail.

## PASS 4 - Code Health / Numbering / Baseline

### P4-FIX-01 Lint 7 errors fixed

Severity: 🟡건강

`npm run lint` initially failed with 7 errors and 1 warning:

- `useCountUp.ts`: synchronous setState in effect.
- `CoverageRemodel.tsx`: unused destructured variable.
- `Disclosure.tsx`: component-only export, synchronous restore state in effect, `Date.now()` purity reports, unused eslint-disable.
- `History.tsx`: effect directly calling state-setting fetch callback.

Safe fixes applied:

- Schedule count-up zero reset through `requestAnimationFrame`.
- Replace unused destructuring with object copy plus `delete`.
- Move `resultItemInWindow` to `src/lib/disclosureWindow.ts`.
- Cache restored-result age in state instead of calling `Date.now()` in render.
- Defer restore state updates via `queueMicrotask`.
- Schedule initial history fetch through `window.setTimeout`.

### P4-FIX-02 Baseline docs updated

Severity: 🟡건강

`.agent-harness/verify.md` and `CLAUDE.md` were still on `572 passed, 8 skipped`. They are now updated to the BOHUMFIT-205 verified baseline:

```text
592 passed, 8 skipped
```

### P4-FIND-01 Numbering history has reusable/mislabel debt

Severity: 🟡건강

Recent numbering state:

| Number | State |
| --- | --- |
| 196 | Post-facto correction for contract-list insurer split/missing premium. |
| 198 | Used by image-PDF guidance; also appears in older UI/report work history. Do not rewrite pushed history. |
| 204 | F-02 OAuth/hCaptcha/rate-limit after 197 conflict. |
| 205 | Completed and verified; baseline 592/8. |
| 206 | Docs-only 1-person-1-account spec. |
| 207/208/209 | Planned follow-up sequence from 206. |
| 210 | This audit. |

Human task: maintain a single append-only task registry in harness docs to avoid future post-facto renumbering. Do not rewrite pushed commits.

### P4-FIND-02 `stash@{0}` pre-resync remains

Severity: 🟡건강

`git stash list` shows:

```text
stash@{0}: On main: pre-resync-20260708
```

Per prior instruction, this was not applied, popped, dropped, or inspected destructively.

Human task: decide separately whether/when to archive or delete the pre-resync stash.

## Automatic Changes

Code/tests:

- `src/components/HCaptcha.tsx`
- `src/components/HCaptcha.test.tsx`
- `src/pages/AuthCaptcha.test.tsx`
- `src/pages/Login.tsx`
- `src/pages/Signup.tsx`
- `src/hooks/useCountUp.ts`
- `src/pages/CoverageRemodel.tsx`
- `src/pages/Disclosure.tsx`
- `src/pages/Disclosure.test.tsx`
- `src/pages/History.tsx`
- `src/lib/disclosureWindow.ts`

Docs/harness:

- `.agent-harness/audit/BOHUMFIT-210-full-audit-report.md`
- `.agent-harness/tasks/BOHUMFIT-210-full-audit-safe-fixes.md`
- `.agent-harness/verify.md`
- `.agent-harness/locks.md`
- `CLAUDE.md`

## Human Task Split

| ID | Severity | Task |
| --- | --- | --- |
| BF210-H1 | 🟠완결성 | Add per-page mixed text/image PDF diagnostics in `backend/pipeline/`; do not silently treat partial image pages as generic format failure. |
| BF210-H2 | 🔴보안 | Implement BOHUMFIT-209 server-side `phone_verified` gate after OTP/unique-number decisions. |
| BF210-H3 | 🔴보안 | Review shared Supabase/FitHere RLS and duplicate profile policies/indexes during low traffic. |
| BF210-H4 | 🟠완결성 | Implement GA/profile/logo cover slots for PDF/Excel coverage reports. |
| BF210-H5 | 🟡건강 | Decide and implement 5th-generation 실손 calculator rules when terms are authoritative. |
| BF210-H6 | 🟠완결성 | Retire or complete the legacy generic coverage parser contract mapping path. |
| BF210-H7 | 🟡건강 | Create/maintain a single task-number registry to prevent future renumber confusion. |
| BF210-H8 | 🟡건강 | Add backend/frontend after-aggregation parity checks before future coverage rule changes. |

## Verification Log

Pre-report and targeted:

- `cd backend; python -m pytest tests/test_coverage_parser_179.py tests/test_coverage_parser_179b.py tests/test_coverage_parser_182.py tests/test_coverage_proposal_parse_193.py tests/test_coverage_compare_188.py tests/test_coverage_hold_cancel_190.py tests/test_drug_change_205.py tests/test_pdf_parser.py -q` -> `78 passed`.
- `npm test -- src/components/HCaptcha.test.tsx src/pages/Disclosure.test.tsx --run` -> `5 passed`.
- `npm test -- src/pages/AuthCaptcha.test.tsx src/components/HCaptcha.test.tsx --run` -> `7 passed`.
- `npm run lint` -> passed after fixes.
- `npx tsc -p tsconfig.app.json --noEmit` -> passed after fixes.
- `npx tsc -p tsconfig.node.json --noEmit` -> passed.

Final full verification:

- `npm run lint` -> passed.
- `npm test` -> `6 passed` test files, `24 passed` tests.
- `npx tsc -p tsconfig.app.json --noEmit` -> passed.
- `npx tsc -p tsconfig.node.json --noEmit` -> passed.
- `cd backend && python -m pytest -q` -> `592 passed, 8 skipped`.
- `npm run build` -> passed. Existing Vite chunk-size warning only.

## Intent Fit

BOHUMFIT is close to the intended product posture in its core analytic flows: major parsers are covered by regression anchors, the 193 proposal path changes actual after-state, and 205 preserves sensitivity for real drug-change disclosure. The remaining trust gaps are not in isolated UI polish; they are mostly boundary guarantees: server-side phone verification enforcement, richer mixed-PDF diagnostics, export packet identity/profile completeness, and avoiding future frontend/backend aggregation drift. Those should be handled as explicit Human-approved tasks rather than opportunistic audit edits.
