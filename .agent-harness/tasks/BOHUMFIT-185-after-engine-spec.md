# BOHUMFIT-185 after-engine design spec

Internal/private design note. Examples may mention internal validation numbers from local coverage fixtures; do not publish real contract PDFs, Excel files, names, resident numbers, phone numbers, or unmasked screenshots.

## 0. Current Model And Retired History

### Current `HEAD` model
The active coverage parser is backend-first:

```text
PDF bytes
  -> backend.coverage.parser.parse_document()
  -> backend.coverage.aggregator.build_before(raw)
  -> backend.coverage.aggregator.build_final(before, raw.diagnosis)
  -> { before, final, warnings }
```

`before` is the stage-1 `[전]` model.

```ts
before = {
  customer: { name, age, sex },
  premium: { monthly_total, paid_total, currency: "KRW" },
  companies: [
    {
      idx, insurer, product, contract_date, pay_cycle,
      pay_years, pay_months, maturity,
      monthly_premium, paid_total, remark
    }
  ],
  coverages: [
    {
      kb_name, kb_group, group12, agg,
      summary,
      by_company: { [contract_idx: string]: number | null },
      enrolled
    }
  ]
}
```

`final` is the stage-1 `[최종]` diagnosis model.

```ts
final = {
  premium: before.premium,
  coverages: [
    {
      group12, kb_name, agg,
      value, recommended, gap, status
    }
  ],
  rollup_by_group12: [
    { group12, status_counts: { 충분, 부족, 미가입 } }
  ]
}
```

Important current invariants:
- `companies` are sorted by monthly premium descending.
- `coverages.by_company` keys are stringified `idx`.
- `agg=sum` uses sum across contracts; representative rows use max.
- `final` does not mutate `before`; it only compares aggregated values to diagnosis rows.
- Exports (`export_excel.py`, `export_pdf.py`) render the same `before/final` data; they do not reparse PDFs.
- PII is not persisted by the coverage parser/export endpoints.

### Retired 041/043/044/045 engine
The old browser-side engine was removed in commit `752d512`.

Useful ideas to keep:
- `applyConsultingPlan` as a pure input-normalization step.
- `buildAfterTable` rule: `[후] = same calculation path as [전], with changed inputs`.
- Contract-level disposition: `유지`/`해지`.
- Coverage-level override amount for reductions.
- Premium override for adjusted monthly premium.
- Proposed contracts are just extra contracts with a proposal prefix.
- Final comparison should consume already computed before/after totals; no duplicate formula layer.

Ideas to retire:
- Browser-only Excel parsing and SheetJS export as the source of truth.
- Old 36/37 category id map as the primary model; the new KB coverage model uses `kb_name`, `group12`, `agg`, and `by_company`.
- UI-only state as the sole record of consulting decisions. New work should produce an exportable JSON plan.
- Old `CoverageAfterSection` UI shape and raw gray-era styling.

## 1. Stage 2 Model: Existing Contract Disposition

Stage 2 records advisor decisions on current contracts and coverages.

```ts
type ContractDisposition = "keep" | "cancel";

type CoverageOverrideMode =
  | "keep"
  | "reduce"
  | "increase"
  | "remove";

type ConsultingPlanV1 = {
  version: 1;
  reference_date?: string;
  customer_alias?: string;
  source: "coverage-remodel";
  existing: ExistingContractDecision[];
  proposals: ProposalContract[];
  notes?: ConsultingNote[];
};

type ExistingContractDecision = {
  contract_idx: number;
  disposition: ContractDisposition;
  reason?: string;
  adjusted_monthly_premium?: number | null;
  coverage_overrides?: CoverageOverride[];
};

type CoverageOverride = {
  kb_name: string;
  group12?: string;
  mode: CoverageOverrideMode;
  amount?: number | null; // won, same unit as current by_company values
  reason?: string;
};

type ConsultingNote = {
  scope: "contract" | "coverage" | "proposal" | "summary";
  contract_idx?: number;
  kb_name?: string;
  message: string;
};
```

Rules:
- Missing contract decision means `keep`.
- `cancel` excludes that contract from `[후]`.
- `adjusted_monthly_premium` overrides monthly premium for `[후]`; `null` or missing keeps the original.
- Coverage override amounts use won, not manwon, because the new parser emits won-level integers.
- `reduce` and `increase` set the contract-specific value for that `kb_name`.
- `remove` sets the contract-specific value to `null` and makes it absent for aggregation.
- `keep` is explicit no-op and useful for audit trails.
- Contract remark (`계피동일`, `계피상이`) must be carried through to `[후]` unless the contract is cancelled.

Edge cases:
- If an override references an unknown `contract_idx`, reject the plan with a validation warning.
- If an override references an unknown `kb_name`, reject unless Human later approves an "unmapped proposal/other" bucket.
- Negative premium and negative coverage amounts are invalid.
- `0` coverage amount is allowed only if mode is `remove` or Human explicitly wants zero-valued display.
- Cancelling all contracts is allowed, but `[후]` should still render with zero monthly premium and only proposals if present.

## 2. Stage 3 Model: New Proposal Contracts

Stage 3 adds proposed contracts after stage-2 edits.

```ts
type ProposalContract = {
  proposal_id: string; // e.g. "proposal-1"
  insurer: string;
  product: string;
  monthly_premium: number;
  pay_cycle?: string | null;
  pay_years?: number | null;
  pay_months?: number | null;
  maturity?: string | null;
  remark?: string | null;
  coverages: ProposalCoverage[];
};

type ProposalCoverage = {
  kb_name: string;
  group12?: string;
  agg?: "sum" | "rep";
  amount: number; // won
  reason?: string;
};
```

Rules:
- Proposal contract ids are not numeric `idx`; when merged into `[후]`, generate stable synthetic ids such as `P1`, `P2`.
- Proposal coverage must map to an existing `kb_name` where possible.
- If `agg` is omitted, inherit the active KB coverage row's aggregation rule.
- New proposal premiums contribute to `[후].premium.monthly_total`.
- `paid_total` for proposals uses `monthly_premium * pay_months` if `pay_months` exists; otherwise mark `paid_total` as `null` and add a warning.
- Proposal remark should support `신규제안`, `조건부`, `심사필요`, and freeform notes.

Human decision needed:
- Whether proposal inputs are manual-only first or can upload a proposal PDF/Excel later.
- Whether "other/기타" proposal coverages that are not in current `KB_COVERAGES` are allowed in the first implementation.

## 3. `[후]` Recalculation

Core principle:

```text
[전] raw before data
  + consulting plan
  -> normalized after input
  -> same aggregation function as [전]
  -> after_before_like
  -> same diagnosis comparison function as [최종]
  -> after_final
```

Do not build a separate after-only formula layer.

Recommended backend functions for BOHUMFIT-186+:

```py
def apply_consulting_plan(before: dict, plan: dict) -> dict:
    """Return a before-shaped dict for [후]."""

def build_after(before: dict, plan: dict, diagnosis: dict | None = None) -> dict:
    after_before = apply_consulting_plan(before, plan)
    after_final = build_final(after_before, diagnosis or diagnosis_from_current_result)
    return {"before": after_before, "final": after_final, "warnings": [...]}

def compare_before_after(before_final: dict, after_final: dict) -> dict:
    """Return comparison rows and summary deltas."""
```

Implementation detail:
- Refactor the current `_aggregate(by_company, agg)` into a small public helper or reuse it internally.
- `[후].coverages` should be generated for the same coverage row universe as `[전]`, plus approved proposal-only rows if enabled.
- For each coverage row:
  - start with original `by_company`
  - drop cancelled contracts
  - apply per-contract overrides
  - add proposal contract values
  - recompute `summary` using the row's `agg`
  - recompute `enrolled`
- For premium:
  - start with kept contract premiums, applying adjusted premium overrides
  - add proposal monthly premiums
  - recompute paid totals from kept/proposal contract terms
- For diagnosis:
  - compare `[후]` values to the same recommended/gap basis as `[전]`
  - status rules remain `충분`/`부족`/`미가입`

Validation targets:
- 문건주 fixture baseline must remain `[전]`: monthly `573,227`, paid `181,984,128`.
- Example flow: cancel one high-premium contract, reduce death coverage on one kept contract, add one 신규 proposal. `[후]` monthly must equal kept adjusted premiums plus proposal premium; coverage rows must show the same `sum` or `rep` behavior as `[전]`.
- 황종철 validation requires a local fixture from Human; none was present in the current repository scan. Spec should reserve a named fixture slot, not invent real numbers.

## 4. Before VS After And Final Summary

### Data shape

```ts
type CoverageAfterResult = {
  before: AnalyzeResult["before"];
  final: AnalyzeResult["final"];
  consulting_plan: ConsultingPlanV1;
  after: {
    before: AnalyzeResult["before"];
    final: AnalyzeResult["final"];
  };
  comparison: {
    premium: {
      before_monthly: number;
      after_monthly: number;
      delta_monthly: number;
      before_paid_total: number | null;
      after_paid_total: number | null;
      delta_paid_total: number | null;
    };
    coverages: ComparisonCoverageRow[];
    improvements: SummaryItem[];
    cautions: SummaryItem[];
  };
  warnings: string[];
};

type ComparisonCoverageRow = {
  group12: string;
  kb_name: string;
  recommended: number | null;
  before_value: number | null;
  after_value: number | null;
  before_gap: number | null;
  after_gap: number | null;
  before_status: string | null;
  after_status: string | null;
  delta_value: number | null;
  improved: boolean;
};

type SummaryItem = {
  level: "info" | "warning" | "critical";
  message: string;
  kb_name?: string;
  group12?: string;
};
```

### Screen structure
- Keep the current first screen:
  - PDF upload
  - `[최종]` diagnosis
  - `[전] 회사별 가입 현황`
- Add stage-2 editor:
  - contract cards sorted like `[전].companies`
  - disposition toggle: 유지/해지
  - adjusted monthly premium input
  - expandable coverage override rows
- Add stage-3 editor:
  - proposal contract cards
  - add/remove proposal
  - coverage rows mapped to KB coverage names
- Add `[후]`:
  - same layout as `[전]`, but badges mark 유지/해지/감액/증액/신규
- Add `전 VS 후`:
  - side-by-side premium summary
  - coverage rows grouped by `group12`
  - highlight rows where `after_status` improves from 부족/미가입 to 충분
  - warn when a cancelled/reduced row worsens a core guarantee
- Add final consulting summary:
  - "월납 X원 감소/증가"
  - "부족 N개 -> M개"
  - "신규 제안 보험료"
  - freeform advisor memo

### Excel export structure
Recommended sheets:
1. `최종 보장진단`
2. `전 회사별세부`
3. `후 회사별세부`
4. `전후 비교`
5. `컨설팅 요약`

Rules:
- Sheet 1 and 2 must stay backward compatible with BOHUMFIT-181.
- Sheet 3 mirrors Sheet 2 with after values.
- Sheet 4 shows before/after/recommended/gap/status/delta.
- Sheet 5 shows dispositions, proposal contracts, and advisor memo.

### PDF export structure
Recommended sections:
1. Cover header and disclaimer.
2. Current `[최종]` diagnosis.
3. Consulting decisions: 유지/해지/감액/증액/신규.
4. `[후]` diagnosis and matrix.
5. Before-vs-after summary.
6. Advisor memo and disclaimer.

PII posture:
- Exports may contain customer alias only by default.
- Real name should require explicit user input and must not be inferred from the PDF unless already allowed by the existing customer-name flow.
- Never persist source PDFs or generated files server-side.

## 5. Implementation Split

### BOHUMFIT-186: backend after model and pure recalculation
- Add `backend/coverage/consulting.py`.
- Add dataclass or typed dict validation for `ConsultingPlanV1`.
- Add `apply_consulting_plan`, `build_after`, and comparison helpers.
- Add tests with synthetic data:
  - cancel contract
  - reduce coverage
  - premium override
  - add proposal
  - sum vs rep aggregation preserved
  - warnings for unknown contract/coverage
- No UI beyond optional API smoke.

### BOHUMFIT-187: CoverageRemodel stage-2 UI
- Contract cards for 유지/해지/감액/보험료 조정.
- Local state generates `ConsultingPlanV1`.
- Preview `[후]` via backend endpoint.
- No proposal flow yet.

### BOHUMFIT-188: stage-3 new proposals
- Add proposal contract/coverage editor.
- Add mapping to KB coverage rows.
- Add validation and warnings.
- Recompute `[후]` with proposals.

### BOHUMFIT-189: before-vs-after screen summary
- Add `전 VS 후` view and final consulting summary.
- Add advisor memo.
- Add smoke tests for stable rendering.

### BOHUMFIT-190: Excel/PDF export for after/comparison
- Extend export endpoints to accept full `CoverageAfterResult`.
- Keep BOHUMFIT-181 export backward compatible.
- Add sheets/sections for `[후]`, comparison, and consulting summary.

### BOHUMFIT-191: fixture validation and product decisions
- Add 문건주 fixture-based private local validation instructions.
- Add 황종철 fixture when Human provides it.
- Decide whether proposal-only unmapped coverages are allowed.
- Decide whether consulting plans should be saveable in history.

## Human Decisions
- Should consulting plans be saved to analysis history or remain session-only?
- Should generated `[후]` exports include real customer name, alias, or no name by default?
- Are proposal-only/unmapped coverages allowed in v1?
- Is premium reduction considered positive, neutral, or needs advisor memo because lower premium may reduce coverage?
- Should "감액" support both amount reduction and rider-level removal?
- Should total paid amount for proposals without pay period be hidden or estimated?

## Reuse / Discard Summary

Reuse conceptually:
- `applyConsultingPlan` pure normalization.
- `buildAfterTable` same-path recomputation principle.
- Final comparison consuming already computed before/after totals.
- Three export sections: before, after, final comparison.

Discard technically:
- Old browser-only `coverageMapping.ts` as source of truth.
- Old SheetJS export and deleted UI components.
- Old category ids as canonical keys.
- Any row math duplicated in frontend rendering.

