/// <reference types="node" />

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  buildAfterResult,
  type AnalyzeResult,
  type ContractDecision,
  type CoverageAfterResponse,
  type ProposalDraft,
} from "./coverageAfterDisplayCache";

type Fixture = {
  analysis: AnalyzeResult;
  decisions: Record<string, ContractDecision>;
  proposals: ProposalDraft[];
};

type CompanyValue = NonNullable<AnalyzeResult["before"]["contract_list"]>[number];
type CoverageValue = AnalyzeResult["before"]["coverages"][number];
type FinalValue = AnalyzeResult["final"]["coverages"][number];
type ComparisonValue = CoverageAfterResponse["comparison"]["coverages"][number];

const fixture = JSON.parse(
  readFileSync(resolve(process.cwd(), "backend/tests/fixtures/coverage_after_parity_211.json"), "utf8"),
) as Fixture;

const rowKey = (row: { group12?: string | null; kb_name?: string | null }) =>
  `${row.group12 || ""}::${row.kb_name || ""}`;

const sortByCoverageName = <T extends { group12?: string | null; kb_name?: string | null }>(rows: T[]): T[] =>
  [...rows].sort((left, right) => rowKey(left).localeCompare(rowKey(right), "ko-KR"));

const normalizeCompany = (company: CompanyValue) => ({
  idx: company.idx,
  insurer: company.insurer,
  product: company.product,
  pay_months: company.pay_months,
  maturity: company.maturity,
  monthly_premium: company.monthly_premium,
  paid_total: company.paid_total,
  consulting_status: company.consulting_status ?? null,
});

const normalizeCoverage = (coverage: CoverageValue) => ({
  group12: coverage.group12,
  kb_name: coverage.kb_name,
  agg: coverage.agg,
  summary: coverage.summary,
  by_company: coverage.by_company,
  enrolled: coverage.enrolled,
});

const normalizeFinal = (coverage: FinalValue) => ({
  group12: coverage.group12,
  kb_name: coverage.kb_name,
  agg: coverage.agg,
  value: coverage.value,
  recommended: coverage.recommended,
  gap: coverage.gap,
  status: coverage.status,
});

const normalizeComparison = (row: ComparisonValue) => ({
  group12: row.group12,
  kb_name: row.kb_name,
  recommended: row.recommended,
  before_value: row.before_value,
  after_value: row.after_value,
  before_gap: row.before_gap,
  after_gap: row.after_gap,
  before_status: row.before_status,
  after_status: row.after_status,
  status_change: row.status_change,
  delta_value: row.delta_value,
  improved: row.improved,
  worsened: row.worsened,
});

function normalizeAfterResult(result: CoverageAfterResponse) {
  const afterBefore = result.after.before;
  return {
    premium: result.comparison.premium,
    after_premium: afterBefore.premium,
    companies: [...(afterBefore.contract_list || [])].map(normalizeCompany),
    coverages: sortByCoverageName(afterBefore.coverages).map(normalizeCoverage),
    final_coverages: sortByCoverageName(result.after.final.coverages).map(normalizeFinal),
    comparison_coverages: sortByCoverageName(result.comparison.coverages).map(normalizeComparison),
    comparison_summary: result.comparison.summary,
  };
}

describe("coverage after display cache", () => {
  it("stays parity-compatible with backend build_after_analysis for the same input", () => {
    const frontend = normalizeAfterResult(buildAfterResult(fixture.analysis, fixture.decisions, fixture.proposals));

    expect(frontend.premium).toEqual({
      before_monthly: 170000,
      after_monthly: 150000,
      delta_monthly: -20000,
      before_paid_total: 20400000,
      after_paid_total: 18000000,
      delta_paid_total: -2400000,
    });
    expect(frontend.final_coverages).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ kb_name: "일반사망", value: 180000000, status: "부족" }),
        expect.objectContaining({ kb_name: "암진단", value: 50000000, status: "충분" }),
        expect.objectContaining({ kb_name: "수술비", value: 20000000, status: "충분" }),
        expect.objectContaining({ kb_name: "자동차사고부상", value: 200000, status: "충분" }),
        expect.objectContaining({ kb_name: "표적항암치료비", value: 80000000, status: null }),
      ]),
    );
    // BOHUMFIT-236 B: 계약 번호 숫자 정렬(보험사 가나다 정렬 대체 — 양측 동일 규칙).
    expect(frontend.companies.map((company) => company.insurer)).toEqual(["가나생명", "마바손보", "나눔손보"]);

    const backendExpected = process.env.BOHUMFIT_PARITY_EXPECTED
      ? (JSON.parse(process.env.BOHUMFIT_PARITY_EXPECTED) as ReturnType<typeof normalizeAfterResult>)
      : null;
    if (backendExpected) {
      expect(frontend).toEqual(backendExpected);
    }
  });
});
