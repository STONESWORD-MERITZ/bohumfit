import { useMemo, useState, type ChangeEvent } from "react";
import { Plus, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import ConsentGate from "../components/ConsentGate";
import { useAuth } from "../lib/auth-context";

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");
const STATUS_SUFFICIENT = "충분";
const STATUS_SHORT = "부족";
const STATUS_MISSING = "미가입";
const DISCLAIMER =
  "이 리모델링표는 업로드한 KB 보장분석 제안서 PDF를 기준으로 정리한 참고 자료입니다. 실제 보장 내용, 보험금 지급 여부, 가입 가능 여부는 각 보험사의 약관과 심사 기준에 따라 달라질 수 있습니다.";

type Company = {
  idx: number | string;
  insurer: string | null;
  product: string | null;
  contract_date: string | null;
  pay_cycle: string | null;
  pay_years: number | null;
  pay_months: number | null;
  maturity: string | null;
  monthly_premium: number | null;
  paid_total: number | null;
  remark: string | null;
  consulting_status?: string | null;
};

type BeforeCoverage = {
  kb_name: string;
  kb_group: string;
  group12: string;
  agg: string;
  summary: number | null;
  by_company: Record<string, number | null>;
  enrolled: boolean;
};

type FinalCoverage = {
  group12: string;
  kb_name: string;
  agg: string;
  value: number | null;
  recommended: number | null;
  gap: number | null;
  status: string | null;
};

type PremiumSummary = {
  monthly_total: number;
  paid_total: number | null;
  currency?: string;
};

type AnalyzeResult = {
  before: {
    customer: { name: string | null; age: number | null; sex: string | null };
    premium: PremiumSummary;
    companies: Company[];
    contract_list?: Company[];
    coverages: BeforeCoverage[];
  };
  final: {
    premium: PremiumSummary;
    coverages: FinalCoverage[];
    rollup_by_group12: { group12: string; status_counts: Record<string, number> }[];
  };
  warnings: string[];
};

type CoverageOverrideMode = "keep" | "reduce" | "increase" | "remove";

type ContractDecision = {
  disposition: "keep" | "cancel";
  adjustedMonthlyPremium: string;
  coverageOverrides: Record<string, { mode: CoverageOverrideMode; amount: string }>;
};

type ProposalCoverageDraft = {
  id: string;
  kbName: string;
  amount: string;
};

type ProposalDraft = {
  id: string;
  insurer: string;
  product: string;
  monthlyPremium: string;
  payMonths: string;
  maturity: string;
  coverages: ProposalCoverageDraft[];
};

type ProposalPlan = {
  proposal_id: string;
  insurer?: string;
  product?: string;
  monthly_premium: number | null;
  pay_cycle: string;
  pay_months: number | null;
  maturity?: string;
  coverages: { kb_name: string; amount: number | null }[];
};

type ConsultingPlanV1 = {
  version: 1;
  source: "coverage-remodel";
  existing: {
    contract_idx: number | string;
    disposition: "keep" | "cancel";
    adjusted_monthly_premium?: number | null;
    coverage_overrides?: {
      kb_name: string;
      group12?: string;
      mode: CoverageOverrideMode;
      amount?: number | null;
    }[];
  }[];
  proposals: ProposalPlan[];
};

type ComparisonRow = {
  group12: string;
  kb_name: string;
  recommended: number | null;
  before_value: number | null;
  after_value: number | null;
  before_gap: number | null;
  after_gap: number | null;
  before_status: string | null;
  after_status: string | null;
  status_change: string;
  delta_value: number | null;
  improved: boolean;
  worsened: boolean;
};

type CoverageComparison = {
  premium: {
    before_monthly: number;
    after_monthly: number;
    delta_monthly: number;
    before_paid_total: number | null;
    after_paid_total: number | null;
    delta_paid_total: number | null;
  };
  coverages: ComparisonRow[];
  summary: {
    improved_count: number;
    worsened_count: number;
    missing_to_sufficient: number;
    short_to_sufficient: number;
    before_status_counts: Record<string, number>;
    after_status_counts: Record<string, number>;
    by_group12: {
      group12: string;
      before_status_counts: Record<string, number>;
      after_status_counts: Record<string, number>;
      improved_count: number;
      worsened_count: number;
      missing_to_sufficient: number;
      short_to_sufficient: number;
    }[];
  };
  improvements: { level?: string; message: string; kb_name?: string; group12?: string }[];
  cautions: { level?: string; message: string; kb_name?: string; group12?: string }[];
};

type CoverageAfterResponse = AnalyzeResult & {
  consulting_plan: ConsultingPlanV1;
  after: {
    before: AnalyzeResult["before"];
    final: AnalyzeResult["final"];
  };
  comparison: CoverageComparison;
};

const GROUP_ORDER = [
  "사망",
  "후유장해",
  "암",
  "뇌",
  "심장",
  "수술",
  "입원(간병 포함)",
  "운전자",
  "골절",
  "실손",
  "화재",
  "배상책임",
  "기타",
];

const STATUS_CLASS: Record<string, string> = {
  [STATUS_SUFFICIENT]: "bg-accent-50 text-accent-700",
  [STATUS_SHORT]: "bg-amber-50 text-amber-700",
  [STATUS_MISSING]: "bg-ink-100 text-ink-500",
};

const STATUS_RANK: Record<string, number> = {
  "": 0,
  [STATUS_MISSING]: 1,
  [STATUS_SHORT]: 2,
  [STATUS_SUFFICIENT]: 3,
};

function keyOf(idx: number | string): string {
  return String(idx);
}

function makeProposal(): ProposalDraft {
  const id = `P${Date.now().toString(36)}`;
  return {
    id,
    insurer: "",
    product: "",
    monthlyPremium: "",
    payMonths: "",
    maturity: "",
    coverages: [{ id: `${id}-C1`, kbName: "", amount: "" }],
  };
}

function formatCoverageAmount(value: number | null | undefined): string {
  if (value == null) return "-";
  if (value === 0) return "0";
  const eok = Math.floor(value / 100_000_000);
  const man = Math.floor((value % 100_000_000) / 10_000);
  const parts: string[] = [];
  if (eok) parts.push(`${eok}억`);
  if (man) parts.push(`${man.toLocaleString("ko-KR")}만`);
  return parts.length > 0 ? parts.join(" ") : value.toLocaleString("ko-KR");
}

function formatWon(value: number | null | undefined): string {
  return value == null ? "-" : `${value.toLocaleString("ko-KR")}원`;
}

function formatPremium(value: number | null | undefined): string {
  return value == null ? "미제공" : `${value.toLocaleString("ko-KR")}원`;
}

function formatDeltaWon(value: number | null | undefined): string {
  if (value == null) return "-";
  if (value === 0) return "변동 없음";
  return `${value > 0 ? "+" : "-"}${Math.abs(value).toLocaleString("ko-KR")}원`;
}

function formatPeriod(company: Company): string {
  const pay = company.pay_years ? `${company.pay_years}년납` : "납입기간 미제공";
  const maturity = company.maturity ? `${company.maturity} 만기` : "만기 미제공";
  return `${pay} · ${maturity}`;
}

function toNumberOrNull(value: string): number | null {
  const cleaned = value.replace(/[^\d]/g, "");
  return cleaned ? Number(cleaned) : null;
}

function contractPaidTotal(company: Company): number | null {
  if (company.monthly_premium == null || company.pay_months == null) return null;
  return company.monthly_premium * company.pay_months;
}

function aggregateCoverageValues(byCompany: Record<string, number | null>, agg: string): number | null {
  const values = Object.values(byCompany).filter((value): value is number => value != null);
  if (values.length === 0) return null;
  return agg === "sum" ? values.reduce((sum, value) => sum + value, 0) : Math.max(...values);
}

function gapAndStatus(value: number | null, recommended: number | null): { gap: number | null; status: string | null } {
  if (recommended == null) return { gap: null, status: null };
  if (value == null) return { gap: -recommended, status: STATUS_MISSING };
  const gap = value - recommended;
  return { gap, status: gap >= 0 ? STATUS_SUFFICIENT : STATUS_SHORT };
}

function emptyStatusCounts(): Record<string, number> {
  return { [STATUS_SUFFICIENT]: 0, [STATUS_SHORT]: 0, [STATUS_MISSING]: 0 };
}

function statusCounts(rows: FinalCoverage[]): Record<string, number> {
  return rows.reduce<Record<string, number>>((counts, row) => {
    if (row.status && row.status in counts) counts[row.status] += 1;
    return counts;
  }, emptyStatusCounts());
}

function groupKey(group: string | null | undefined): number {
  return GROUP_ORDER.includes(group || "") ? GROUP_ORDER.indexOf(group || "") : GROUP_ORDER.length;
}

function groupFinalRows(rows: FinalCoverage[]) {
  const grouped = new Map<string, FinalCoverage[]>();
  for (const row of rows) {
    const items = grouped.get(row.group12) || [];
    items.push(row);
    grouped.set(row.group12, items);
  }
  return Array.from(grouped.entries())
    .sort(([left], [right]) => groupKey(left) - groupKey(right))
    .map(([group, groupedRows]) => ({ group, rows: groupedRows }));
}

function groupComparisonRows(rows: ComparisonRow[]) {
  const grouped = new Map<string, ComparisonRow[]>();
  for (const row of rows) {
    const items = grouped.get(row.group12) || [];
    items.push(row);
    grouped.set(row.group12, items);
  }
  return Array.from(grouped.entries())
    .sort(([left], [right]) => groupKey(left) - groupKey(right))
    .map(([group, groupedRows]) => ({ group, rows: groupedRows }));
}

function sortCompanies(companies: Company[]): Company[] {
  return [...companies].sort((left, right) => {
    if (left.monthly_premium == null && right.monthly_premium != null) return 1;
    if (left.monthly_premium != null && right.monthly_premium == null) return -1;
    return (right.monthly_premium || 0) - (left.monthly_premium || 0) || keyOf(left.idx).localeCompare(keyOf(right.idx));
  });
}

function compareFinals(beforeFinal: AnalyzeResult["final"], afterFinal: AnalyzeResult["final"]): CoverageComparison {
  const beforeRows = new Map(beforeFinal.coverages.map((row) => [`${row.group12}::${row.kb_name}`, row]));
  const afterRows = new Map(afterFinal.coverages.map((row) => [`${row.group12}::${row.kb_name}`, row]));
  const keys = Array.from(new Set([...beforeRows.keys(), ...afterRows.keys()])).sort((left, right) => {
    const [leftGroup, leftName] = left.split("::");
    const [rightGroup, rightName] = right.split("::");
    return groupKey(leftGroup) - groupKey(rightGroup) || leftName.localeCompare(rightName);
  });

  const coverages: ComparisonRow[] = [];
  const byGroup = new Map<string, CoverageComparison["summary"]["by_group12"][number]>();
  let improvedCount = 0;
  let worsenedCount = 0;
  let missingToSufficient = 0;
  let shortToSufficient = 0;

  for (const key of keys) {
    const before = beforeRows.get(key);
    const after = afterRows.get(key);
    const group12 = after?.group12 || before?.group12 || "-";
    const kbName = after?.kb_name || before?.kb_name || "-";
    const beforeStatus = before?.status || null;
    const afterStatus = after?.status || null;
    const improved = (beforeStatus === STATUS_SHORT || beforeStatus === STATUS_MISSING) && afterStatus === STATUS_SUFFICIENT;
    const worsened = (STATUS_RANK[afterStatus || ""] || 0) < (STATUS_RANK[beforeStatus || ""] || 0);
    const beforeValue = before?.value ?? null;
    const afterValue = after?.value ?? null;

    if (improved) {
      improvedCount += 1;
      if (beforeStatus === STATUS_MISSING) missingToSufficient += 1;
      if (beforeStatus === STATUS_SHORT) shortToSufficient += 1;
    }
    if (worsened) worsenedCount += 1;

    if (!byGroup.has(group12)) {
      byGroup.set(group12, {
        group12,
        before_status_counts: emptyStatusCounts(),
        after_status_counts: emptyStatusCounts(),
        improved_count: 0,
        worsened_count: 0,
        missing_to_sufficient: 0,
        short_to_sufficient: 0,
      });
    }
    const group = byGroup.get(group12)!;
    if (beforeStatus && beforeStatus in group.before_status_counts) group.before_status_counts[beforeStatus] += 1;
    if (afterStatus && afterStatus in group.after_status_counts) group.after_status_counts[afterStatus] += 1;
    if (improved) group.improved_count += 1;
    if (worsened) group.worsened_count += 1;
    if (beforeStatus === STATUS_MISSING && afterStatus === STATUS_SUFFICIENT) group.missing_to_sufficient += 1;
    if (beforeStatus === STATUS_SHORT && afterStatus === STATUS_SUFFICIENT) group.short_to_sufficient += 1;

    coverages.push({
      group12,
      kb_name: kbName,
      recommended: after?.recommended ?? before?.recommended ?? null,
      before_value: beforeValue,
      after_value: afterValue,
      before_gap: before?.gap ?? null,
      after_gap: after?.gap ?? null,
      before_status: beforeStatus,
      after_status: afterStatus,
      status_change: `${beforeStatus || "-"} -> ${afterStatus || "-"}`,
      delta_value: beforeValue != null && afterValue != null ? afterValue - beforeValue : null,
      improved,
      worsened,
    });
  }

  const beforePaid = beforeFinal.premium.paid_total;
  const afterPaid = afterFinal.premium.paid_total;
  const deltaPaid = beforePaid != null && afterPaid != null ? afterPaid - beforePaid : null;
  return {
    premium: {
      before_monthly: beforeFinal.premium.monthly_total || 0,
      after_monthly: afterFinal.premium.monthly_total || 0,
      delta_monthly: (afterFinal.premium.monthly_total || 0) - (beforeFinal.premium.monthly_total || 0),
      before_paid_total: beforePaid,
      after_paid_total: afterPaid,
      delta_paid_total: deltaPaid,
    },
    coverages,
    summary: {
      improved_count: improvedCount,
      worsened_count: worsenedCount,
      missing_to_sufficient: missingToSufficient,
      short_to_sufficient: shortToSufficient,
      before_status_counts: statusCounts(beforeFinal.coverages),
      after_status_counts: statusCounts(afterFinal.coverages),
      by_group12: Array.from(byGroup.values()).sort((left, right) => groupKey(left.group12) - groupKey(right.group12)),
    },
    improvements: improvedCount
      ? [{ level: "info", message: `부족·미가입에서 충분으로 개선된 담보 ${improvedCount}개` }]
      : [],
    cautions: worsenedCount
      ? [{ level: "warning", message: `컨설팅 후 상태가 낮아진 담보 ${worsenedCount}개` }]
      : [],
  };
}

function buildConsultingPlan(
  analysis: AnalyzeResult,
  decisions: Record<string, ContractDecision>,
  proposals: ProposalDraft[],
): ConsultingPlanV1 {
  const companies = analysis.before.contract_list || analysis.before.companies || [];
  return {
    version: 1,
    source: "coverage-remodel",
    existing: companies.flatMap((company) => {
      const decision = decisions[keyOf(company.idx)];
      if (!decision) return [];
      const adjusted = toNumberOrNull(decision.adjustedMonthlyPremium);
      const coverageOverrides = Object.entries(decision.coverageOverrides)
        .map(([kbName, override]) => {
          if (override.mode === "keep") return null;
          const sourceCoverage = analysis.before.coverages.find((coverage) => coverage.kb_name === kbName);
          return {
            kb_name: kbName,
            group12: sourceCoverage?.group12,
            mode: override.mode,
            amount: override.mode === "remove" ? null : toNumberOrNull(override.amount),
          };
        })
        .filter((override): override is NonNullable<typeof override> => Boolean(override));
      if (decision.disposition === "keep" && adjusted == null && coverageOverrides.length === 0) return [];
      return [
        {
          contract_idx: company.idx,
          disposition: decision.disposition,
          adjusted_monthly_premium: adjusted,
          coverage_overrides: coverageOverrides,
        },
      ];
    }),
    proposals: proposals
      .map((proposal, index) => ({
        proposal_id: `P${index + 1}`,
        insurer: proposal.insurer.trim() || undefined,
        product: proposal.product.trim() || undefined,
        monthly_premium: toNumberOrNull(proposal.monthlyPremium),
        pay_cycle: "월납",
        pay_months: toNumberOrNull(proposal.payMonths),
        maturity: proposal.maturity.trim() || undefined,
        coverages: proposal.coverages
          .filter((coverage) => coverage.kbName)
          .map((coverage) => ({
            kb_name: coverage.kbName,
            amount: toNumberOrNull(coverage.amount),
          })),
      }))
      .filter((proposal) => proposal.monthly_premium != null || proposal.coverages.length > 0),
  };
}

function buildAfterResult(
  analysis: AnalyzeResult,
  decisions: Record<string, ContractDecision>,
  proposals: ProposalDraft[],
): CoverageAfterResponse {
  const plan = buildConsultingPlan(analysis, decisions, proposals);
  const sourceCompanies = analysis.before.contract_list || analysis.before.companies || [];
  const keptIds = new Set<string>();
  const afterCompanies: Company[] = [];

  for (const company of sourceCompanies) {
    const decision = decisions[keyOf(company.idx)];
    if (decision?.disposition === "cancel") continue;
    const adjusted = decision ? toNumberOrNull(decision.adjustedMonthlyPremium) : null;
    const nextCompany: Company = {
      ...company,
      monthly_premium: adjusted ?? company.monthly_premium,
      consulting_status: adjusted != null ? "보험료 조정" : "유지",
    };
    nextCompany.paid_total = contractPaidTotal(nextCompany);
    keptIds.add(keyOf(company.idx));
    afterCompanies.push(nextCompany);
  }

  const proposalAmounts: Record<string, Record<string, number | null>> = {};
  let paidUnknown = false;
  for (const [index, proposal] of plan.proposals.entries()) {
    const proposalId = proposal.proposal_id || `P${index + 1}`;
    if (proposal.monthly_premium == null) continue;
    const proposalCompany: Company = {
      idx: proposalId,
      insurer: proposal.insurer || "신규제안",
      product: proposal.product || proposalId,
      contract_date: null,
      pay_cycle: proposal.pay_cycle,
      pay_years: proposal.pay_months ? Math.floor(proposal.pay_months / 12) : null,
      pay_months: proposal.pay_months,
      maturity: proposal.maturity || null,
      monthly_premium: proposal.monthly_premium,
      paid_total: proposal.pay_months != null ? proposal.monthly_premium * proposal.pay_months : null,
      remark: "신규제안",
      consulting_status: "신규제안",
    };
    if (proposalCompany.paid_total == null) paidUnknown = true;
    afterCompanies.push(proposalCompany);
    for (const coverage of proposal.coverages) {
      if (!coverage.kb_name) continue;
      if (!proposalAmounts[coverage.kb_name]) proposalAmounts[coverage.kb_name] = {};
      proposalAmounts[coverage.kb_name][proposalId] = coverage.amount;
    }
  }

  const afterCoverages = analysis.before.coverages.map((coverage) => {
    const byCompany: Record<string, number | null> = {};
    for (const [companyId, amount] of Object.entries(coverage.by_company || {})) {
      if (keptIds.has(companyId)) byCompany[companyId] = amount;
    }
    for (const [companyId, decision] of Object.entries(decisions)) {
      if (!keptIds.has(companyId)) continue;
      const override = decision.coverageOverrides[coverage.kb_name];
      if (!override || override.mode === "keep") continue;
      if (override.mode === "remove") {
        byCompany[companyId] = null;
      } else {
        const amount = toNumberOrNull(override.amount);
        if (amount != null) byCompany[companyId] = amount;
      }
    }
    Object.assign(byCompany, proposalAmounts[coverage.kb_name] || {});
    const summary = aggregateCoverageValues(byCompany, coverage.agg);
    return {
      ...coverage,
      by_company: byCompany,
      summary,
      enrolled: Object.values(byCompany).some((amount) => amount != null),
    };
  });

  const monthlyTotal = afterCompanies.reduce((sum, company) => sum + (company.monthly_premium || 0), 0);
  const paidTotal = paidUnknown ? null : afterCompanies.reduce((sum, company) => sum + (company.paid_total || 0), 0);
  const sortedCompanies = sortCompanies(afterCompanies);
  const afterBefore: AnalyzeResult["before"] = {
    ...analysis.before,
    premium: {
      monthly_total: monthlyTotal,
      paid_total: paidTotal,
      currency: analysis.before.premium.currency || "KRW",
    },
    companies: sortedCompanies,
    contract_list: sortedCompanies,
    coverages: afterCoverages,
  };

  const finalByName = new Map(analysis.final.coverages.map((row) => [row.kb_name, row]));
  const rollup = new Map<string, Record<string, number>>();
  const afterFinalCoverages = afterCoverages.map<FinalCoverage>((coverage) => {
    const base = finalByName.get(coverage.kb_name);
    const recommended = base?.recommended ?? null;
    const { gap, status } = gapAndStatus(coverage.summary, recommended);
    if (!rollup.has(coverage.group12)) rollup.set(coverage.group12, emptyStatusCounts());
    if (status && status in rollup.get(coverage.group12)!) rollup.get(coverage.group12)![status] += 1;
    return {
      group12: coverage.group12,
      kb_name: coverage.kb_name,
      agg: coverage.agg,
      value: coverage.summary,
      recommended,
      gap,
      status,
    };
  });
  const afterFinal: AnalyzeResult["final"] = {
    premium: afterBefore.premium,
    coverages: afterFinalCoverages,
    rollup_by_group12: GROUP_ORDER.map((group) => ({
      group12: group,
      status_counts: rollup.get(group) || emptyStatusCounts(),
    })),
  };

  return {
    ...analysis,
    consulting_plan: plan,
    after: { before: afterBefore, final: afterFinal },
    comparison: compareFinals(analysis.final, afterFinal),
    warnings: analysis.warnings || [],
  };
}

function StatusBadge({ status }: { status: string | null }) {
  const className = status ? STATUS_CLASS[status] : undefined;
  return (
    <span
      className={`inline-flex min-w-[54px] justify-center rounded-full px-2 py-0.5 text-[11px] font-bold ${
        className || "bg-ink-100 text-ink-500"
      }`}
    >
      {status || "-"}
    </span>
  );
}

function MetricCard({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "default" | "good" | "warn";
}) {
  const toneClass = tone === "good" ? "text-accent-700" : tone === "warn" ? "text-amber-700" : "text-ink-900";
  return (
    <div className="rounded-card border border-line bg-canvas px-4 py-3">
      <p className="text-[12px] text-ink-soft">{label}</p>
      <p className={`mt-1 text-xl font-extrabold ${toneClass}`}>{value}</p>
    </div>
  );
}

export default function CoverageRemodel() {
  const { session } = useAuth();
  const navigate = useNavigate();
  const [agreed, setAgreed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [fileName, setFileName] = useState("");
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [afterResult, setAfterResult] = useState<CoverageAfterResponse | null>(null);
  const [decisions, setDecisions] = useState<Record<string, ContractDecision>>({});
  const [proposals, setProposals] = useState<ProposalDraft[]>([]);
  const [showBefore, setShowBefore] = useState(false);
  const [exporting, setExporting] = useState<"" | "excel" | "pdf">("");

  const companies = useMemo(() => result?.before.contract_list || result?.before.companies || [], [result]);
  const finalGroups = useMemo(() => groupFinalRows(result?.final.coverages || []), [result]);
  const comparisonGroups = useMemo(() => groupComparisonRows(afterResult?.comparison.coverages || []), [afterResult]);
  const statusSummary = useMemo(() => statusCounts(result?.final.coverages || []), [result]);
  const afterStatusSummary = useMemo(() => statusCounts(afterResult?.after.final.coverages || []), [afterResult]);
  const coverageOptions = useMemo(() => result?.before.coverages || [], [result]);

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const token = session?.access_token;
    if (!token) {
      navigate("/login");
      return;
    }
    setBusy(true);
    setError("");
    setResult(null);
    setAfterResult(null);
    setDecisions({});
    setProposals([]);
    setFileName(file.name);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API_BASE}/coverage/analyze`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "보장분석표를 생성하지 못했습니다.");
      }
      setResult((await response.json()) as AnalyzeResult);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "알 수 없는 오류가 발생했습니다.");
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }

  async function exportFile(kind: "excel" | "pdf") {
    if (!result) return;
    const token = session?.access_token;
    if (!token) {
      navigate("/login");
      return;
    }
    setExporting(kind);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/coverage/export/${kind}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(afterResult || result),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "파일을 생성하지 못했습니다.");
      }
      const blob = await response.blob();
      const disposition = response.headers.get("Content-Disposition") || "";
      const match = /filename\*=UTF-8''([^;]+)/.exec(disposition);
      const fallback = kind === "excel" ? "BohumFit_전후비교.xlsx" : "BohumFit_전후비교.pdf";
      const downloadName = match ? decodeURIComponent(match[1]) : fallback;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = downloadName;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : "파일 생성 중 오류가 발생했습니다.");
    } finally {
      setExporting("");
    }
  }

  function updateContractDecision(idx: number | string, patch: Partial<ContractDecision>) {
    const key = keyOf(idx);
    setDecisions((current) => {
      const previous: ContractDecision = current[key] || {
        disposition: "keep",
        adjustedMonthlyPremium: "",
        coverageOverrides: {},
      };
      return { ...current, [key]: { ...previous, ...patch } };
    });
    setAfterResult(null);
  }

  function updateCoverageOverride(
    company: Company,
    coverage: BeforeCoverage,
    patch: Partial<{ mode: CoverageOverrideMode; amount: string }>,
  ) {
    const key = keyOf(company.idx);
    setDecisions((current) => {
      const previous: ContractDecision = current[key] || {
        disposition: "keep",
        adjustedMonthlyPremium: "",
        coverageOverrides: {},
      };
      const previousOverride = previous.coverageOverrides[coverage.kb_name] || {
        mode: "keep" as CoverageOverrideMode,
        amount: "",
      };
      return {
        ...current,
        [key]: {
          ...previous,
          coverageOverrides: {
            ...previous.coverageOverrides,
            [coverage.kb_name]: { ...previousOverride, ...patch },
          },
        },
      };
    });
    setAfterResult(null);
  }

  function addProposal() {
    setProposals((current) => [...current, makeProposal()]);
    setAfterResult(null);
  }

  function updateProposal(id: string, patch: Partial<ProposalDraft>) {
    setProposals((current) => current.map((proposal) => (proposal.id === id ? { ...proposal, ...patch } : proposal)));
    setAfterResult(null);
  }

  function removeProposal(id: string) {
    setProposals((current) => current.filter((proposal) => proposal.id !== id));
    setAfterResult(null);
  }

  function updateProposalCoverage(proposalId: string, coverageId: string, patch: Partial<ProposalCoverageDraft>) {
    setProposals((current) =>
      current.map((proposal) =>
        proposal.id === proposalId
          ? {
              ...proposal,
              coverages: proposal.coverages.map((coverage) =>
                coverage.id === coverageId ? { ...coverage, ...patch } : coverage,
              ),
            }
          : proposal,
      ),
    );
    setAfterResult(null);
  }

  function addProposalCoverage(proposalId: string) {
    setProposals((current) =>
      current.map((proposal) =>
        proposal.id === proposalId
          ? {
              ...proposal,
              coverages: [
                ...proposal.coverages,
                { id: `${proposal.id}-C${Date.now().toString(36)}`, kbName: "", amount: "" },
              ],
            }
          : proposal,
      ),
    );
    setAfterResult(null);
  }

  function removeProposalCoverage(proposalId: string, coverageId: string) {
    setProposals((current) =>
      current.map((proposal) =>
        proposal.id === proposalId
          ? {
              ...proposal,
              coverages:
                proposal.coverages.length > 1
                  ? proposal.coverages.filter((coverage) => coverage.id !== coverageId)
                  : proposal.coverages,
            }
          : proposal,
      ),
    );
    setAfterResult(null);
  }

  function recalculateAfter() {
    if (!result) return;
    setError("");
    setAfterResult(buildAfterResult(result, decisions, proposals));
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 md:px-6">
      <header className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">Coverage Remodeling</p>
        <h1 className="ko-heading mt-2 text-3xl font-extrabold tracking-tight text-ink-900 md:text-4xl">
          컨설팅 전 VS 후 보장 비교
        </h1>
        <p className="ko-text mt-2 break-keep text-[14px] text-ink-soft">
          KB 보장분석의 현재 상태와 유지·해지·신규제안 반영 후 상태를 나란히 비교합니다.
        </p>
      </header>

      <section className="rounded-card border border-line bg-white p-6">
        <h2 className="ko-heading text-lg font-bold text-ink-900">PDF 업로드</h2>
        <ConsentGate
          agreed={agreed}
          onChange={setAgreed}
          note="보장분석 제안서에는 고객 계약정보가 포함될 수 있습니다. 분석 목적에 필요한 범위에서만 사용해 주세요."
          className="mt-3"
        />
        <label
          className={`mt-4 flex h-32 flex-col items-center justify-center rounded-card border-2 border-dashed text-center transition ${
            agreed
              ? "cursor-pointer border-accent-200 bg-accent-50 hover:border-accent-400"
              : "cursor-not-allowed border-line bg-ink-50 opacity-60"
          }`}
        >
          <span className="text-2xl" aria-hidden="true">
            PDF
          </span>
          <span className="mt-2 text-sm font-semibold text-accent-700">
            {busy ? "분석 중입니다..." : "KB 보장분석 제안서 PDF 선택"}
          </span>
          <span className="mt-1 text-xs text-ink-soft">PDF 1개를 업로드해 주세요.</span>
          <input
            type="file"
            accept="application/pdf"
            className="hidden"
            disabled={!agreed || busy}
            onChange={handleUpload}
            aria-label="KB 보장분석 제안서 PDF 업로드"
          />
        </label>
        {fileName && result && !error && <p className="mt-2 text-xs text-accent-600">{fileName} 분석 완료</p>}
        {error && <p className="mt-2 rounded-[8px] bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}
        {result && result.warnings.length > 0 && (
          <p className="mt-2 rounded-[8px] bg-amber-50 px-3 py-2 text-[12px] text-amber-700">
            확인 필요: {result.warnings.join(" / ")}
          </p>
        )}
      </section>

      {result && (
        <>
          <section className="mt-6 rounded-card border border-line bg-white p-6">
            <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
              <div>
                <h2 className="ko-heading text-lg font-bold text-ink-900">컨설팅 전 진단</h2>
                <p className="mt-1 text-xs text-ink-soft">{DISCLAIMER}</p>
              </div>
              <div className="flex flex-col items-start gap-2 md:items-end">
                {result.before.customer.name && (
                  <p className="text-sm font-semibold text-ink-700">고객명 {result.before.customer.name}</p>
                )}
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => void exportFile("excel")}
                    disabled={exporting !== ""}
                    className="button-text rounded-btn border border-line-strong bg-white px-4 py-2 text-[13px] font-bold text-ink-800 hover:bg-ink-50 disabled:opacity-50"
                  >
                    {exporting === "excel" ? "엑셀 생성 중" : "엑셀 저장"}
                  </button>
                  <button
                    type="button"
                    onClick={() => void exportFile("pdf")}
                    disabled={exporting !== ""}
                    className="button-text rounded-btn border border-line-strong bg-white px-4 py-2 text-[13px] font-bold text-ink-800 hover:bg-ink-50 disabled:opacity-50"
                  >
                    {exporting === "pdf" ? "PDF 생성 중" : "PDF 저장"}
                  </button>
                </div>
              </div>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <MetricCard label="월납 보험료 합계" value={formatWon(result.before.premium.monthly_total)} />
              <MetricCard label="총 납입 예정액" value={formatWon(result.before.premium.paid_total)} />
              <MetricCard
                label="부족 / 미가입 담보"
                value={`${statusSummary[STATUS_SHORT]} / ${statusSummary[STATUS_MISSING]}`}
                tone="warn"
              />
            </div>

            <div className="mt-5 space-y-5">
              {finalGroups.map(({ group, rows }) => (
                <div key={group}>
                  <h3 className="ko-heading mb-2 text-sm font-bold text-ink-900">{group}</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[560px] text-[13px]">
                      <thead>
                        <tr className="border-b border-line text-left text-ink-500">
                          <th className="py-2 pr-2">담보</th>
                          <th className="px-2 py-2 text-right">권장</th>
                          <th className="px-2 py-2 text-right">가입</th>
                          <th className="px-2 py-2 text-right">과부족</th>
                          <th className="py-2 pl-2 text-center">상태</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rows.map((coverage) => (
                          <tr key={`${coverage.group12}-${coverage.kb_name}`} className="border-b border-line/60">
                            <td className="break-keep py-1.5 pr-2 font-semibold text-ink-800">{coverage.kb_name}</td>
                            <td className="px-2 py-1.5 text-right text-ink-soft">
                              {formatCoverageAmount(coverage.recommended)}
                            </td>
                            <td className="px-2 py-1.5 text-right text-ink-900">{formatCoverageAmount(coverage.value)}</td>
                            <td
                              className={`px-2 py-1.5 text-right font-semibold ${
                                coverage.gap == null
                                  ? "text-ink-400"
                                  : coverage.gap < 0
                                    ? "text-amber-700"
                                    : coverage.gap > 0
                                      ? "text-accent-700"
                                      : "text-ink-500"
                              }`}
                            >
                              {coverage.gap == null
                                ? "-"
                                : `${coverage.gap > 0 ? "+" : coverage.gap < 0 ? "-" : ""}${formatCoverageAmount(Math.abs(coverage.gap))}`}
                            </td>
                            <td className="py-1.5 pl-2 text-center">
                              <StatusBadge status={coverage.status} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="mt-6 rounded-card border border-line bg-white p-6">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <h2 className="ko-heading text-lg font-bold text-ink-900">컨설팅 후 입력</h2>
                <p className="mt-1 text-xs text-ink-soft">
                  유지·해지, 조정 보험료, 담보별 조정 금액과 신규 제안을 반영합니다.
                </p>
              </div>
              <button
                type="button"
                onClick={recalculateAfter}
                className="button-text rounded-btn bg-accent-600 px-4 py-2 text-[13px] font-bold text-white hover:bg-accent-700"
              >
                전후 비교 계산
              </button>
            </div>

            <div className="mt-5 grid gap-4 lg:grid-cols-2">
              {companies.map((company) => {
                const decision = decisions[keyOf(company.idx)] || {
                  disposition: "keep",
                  adjustedMonthlyPremium: "",
                  coverageOverrides: {},
                };
                const companyCoverages = coverageOptions
                  .filter((coverage) => coverage.by_company?.[keyOf(company.idx)] != null)
                  .slice(0, 6);
                return (
                  <article key={company.idx} className="rounded-card border border-line bg-canvas p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-bold text-ink-900">{company.insurer || `계약 ${company.idx}`}</p>
                        <p className="mt-1 text-xs text-ink-soft">{company.product || "상품명 확인 필요"}</p>
                        <p className="mt-1 text-[11px] font-semibold text-ink-soft">{formatPeriod(company)}</p>
                      </div>
                      <p className="shrink-0 text-sm font-extrabold text-ink-900">{formatPremium(company.monthly_premium)}</p>
                    </div>
                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      <label className="text-[12px] font-semibold text-ink-700">
                        처리
                        <select
                          className="mt-1 w-full rounded-[8px] border border-line bg-white px-3 py-2 text-sm"
                          value={decision.disposition}
                          onChange={(event) =>
                            updateContractDecision(company.idx, {
                              disposition: event.target.value as ContractDecision["disposition"],
                            })
                          }
                        >
                          <option value="keep">유지</option>
                          <option value="cancel">해지</option>
                        </select>
                      </label>
                      <label className="text-[12px] font-semibold text-ink-700">
                        조정 월납 보험료
                        <input
                          className="mt-1 w-full rounded-[8px] border border-line bg-white px-3 py-2 text-sm"
                          inputMode="numeric"
                          placeholder="변동 없으면 비움"
                          value={decision.adjustedMonthlyPremium}
                          onChange={(event) =>
                            updateContractDecision(company.idx, { adjustedMonthlyPremium: event.target.value })
                          }
                        />
                      </label>
                    </div>

                    {companyCoverages.length > 0 && (
                      <div className="mt-4 space-y-2">
                        <p className="text-[12px] font-bold text-ink-700">담보 조정</p>
                        {companyCoverages.map((coverage) => {
                          const override = decision.coverageOverrides[coverage.kb_name] || { mode: "keep", amount: "" };
                          return (
                            <div key={coverage.kb_name} className="grid gap-2 sm:grid-cols-[1fr_108px_120px]">
                              <span className="truncate text-[12px] font-semibold text-ink-700" title={coverage.kb_name}>
                                {coverage.kb_name}
                              </span>
                              <select
                                className="rounded-[8px] border border-line bg-white px-2 py-1.5 text-[12px]"
                                value={override.mode}
                                onChange={(event) =>
                                  updateCoverageOverride(company, coverage, {
                                    mode: event.target.value as CoverageOverrideMode,
                                  })
                                }
                              >
                                <option value="keep">그대로</option>
                                <option value="reduce">감액/조정</option>
                                <option value="increase">증액/보완</option>
                                <option value="remove">삭제</option>
                              </select>
                              <input
                                className="rounded-[8px] border border-line bg-white px-2 py-1.5 text-right text-[12px]"
                                inputMode="numeric"
                                placeholder="금액"
                                disabled={override.mode === "keep" || override.mode === "remove"}
                                value={override.amount}
                                onChange={(event) => updateCoverageOverride(company, coverage, { amount: event.target.value })}
                              />
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </article>
                );
              })}
            </div>

            <div className="mt-6">
              <div className="flex items-center justify-between gap-3">
                <h3 className="ko-heading text-base font-bold text-ink-900">신규 제안</h3>
                <button
                  type="button"
                  onClick={addProposal}
                  className="inline-flex items-center gap-1 rounded-btn border border-line-strong bg-white px-3 py-2 text-[12px] font-bold text-ink-800 hover:bg-ink-50"
                >
                  <Plus size={14} aria-hidden="true" />
                  추가
                </button>
              </div>

              {proposals.length === 0 ? (
                <p className="mt-3 rounded-[8px] bg-canvas px-4 py-3 text-[13px] text-ink-soft">
                  신규 제안이 없다면 기존 계약 조정만으로 비교할 수 있습니다.
                </p>
              ) : (
                <div className="mt-3 space-y-3">
                  {proposals.map((proposal) => (
                    <article key={proposal.id} className="rounded-card border border-line bg-canvas p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="grid flex-1 gap-3 md:grid-cols-5">
                          <input
                            className="rounded-[8px] border border-line bg-white px-3 py-2 text-sm"
                            placeholder="보험사"
                            value={proposal.insurer}
                            onChange={(event) => updateProposal(proposal.id, { insurer: event.target.value })}
                          />
                          <input
                            className="rounded-[8px] border border-line bg-white px-3 py-2 text-sm md:col-span-2"
                            placeholder="상품명"
                            value={proposal.product}
                            onChange={(event) => updateProposal(proposal.id, { product: event.target.value })}
                          />
                          <input
                            className="rounded-[8px] border border-line bg-white px-3 py-2 text-sm"
                            inputMode="numeric"
                            placeholder="월납 보험료"
                            value={proposal.monthlyPremium}
                            onChange={(event) => updateProposal(proposal.id, { monthlyPremium: event.target.value })}
                          />
                          <input
                            className="rounded-[8px] border border-line bg-white px-3 py-2 text-sm"
                            inputMode="numeric"
                            placeholder="납입개월"
                            value={proposal.payMonths}
                            onChange={(event) => updateProposal(proposal.id, { payMonths: event.target.value })}
                          />
                        </div>
                        <button
                          type="button"
                          onClick={() => removeProposal(proposal.id)}
                          className="rounded-btn border border-line-strong bg-white p-2 text-ink-600 hover:bg-ink-50"
                          aria-label="신규 제안 삭제"
                          title="신규 제안 삭제"
                        >
                          <Trash2 size={16} aria-hidden="true" />
                        </button>
                      </div>
                      <input
                        className="mt-3 w-full rounded-[8px] border border-line bg-white px-3 py-2 text-sm"
                        placeholder="만기 예: 100세"
                        value={proposal.maturity}
                        onChange={(event) => updateProposal(proposal.id, { maturity: event.target.value })}
                      />
                      <div className="mt-3 space-y-2">
                        {proposal.coverages.map((coverage) => (
                          <div key={coverage.id} className="grid gap-2 sm:grid-cols-[1fr_140px_36px]">
                            <select
                              className="rounded-[8px] border border-line bg-white px-3 py-2 text-sm"
                              value={coverage.kbName}
                              onChange={(event) =>
                                updateProposalCoverage(proposal.id, coverage.id, { kbName: event.target.value })
                              }
                            >
                              <option value="">보완 담보 선택</option>
                              {coverageOptions.map((option) => (
                                <option key={option.kb_name} value={option.kb_name}>
                                  {option.group12} · {option.kb_name}
                                </option>
                              ))}
                            </select>
                            <input
                              className="rounded-[8px] border border-line bg-white px-3 py-2 text-right text-sm"
                              inputMode="numeric"
                              placeholder="가입금액"
                              value={coverage.amount}
                              onChange={(event) =>
                                updateProposalCoverage(proposal.id, coverage.id, { amount: event.target.value })
                              }
                            />
                            <button
                              type="button"
                              onClick={() => removeProposalCoverage(proposal.id, coverage.id)}
                              className="rounded-btn border border-line-strong bg-white p-2 text-ink-600 hover:bg-ink-50"
                              aria-label="담보 행 삭제"
                              title="담보 행 삭제"
                            >
                              <Trash2 size={15} aria-hidden="true" />
                            </button>
                          </div>
                        ))}
                        <button
                          type="button"
                          onClick={() => addProposalCoverage(proposal.id)}
                          className="inline-flex items-center gap-1 rounded-btn border border-line-strong bg-white px-3 py-2 text-[12px] font-bold text-ink-800 hover:bg-ink-50"
                        >
                          <Plus size={14} aria-hidden="true" />
                          담보 추가
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </div>
          </section>

          {afterResult && (
            <section className="mt-6 rounded-card border border-line bg-white p-6">
              <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
                <div>
                  <h2 className="ko-heading text-lg font-bold text-ink-900">컨설팅 전 VS 후 최종 정리</h2>
                  <p className="mt-1 text-xs text-ink-soft">
                    고객에게 현재 보험이 어떻게 개선됐는지 보여주는 비교 요약입니다.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => void exportFile("excel")}
                    disabled={exporting !== ""}
                    className="button-text rounded-btn border border-line-strong bg-white px-4 py-2 text-[13px] font-bold text-ink-800 hover:bg-ink-50 disabled:opacity-50"
                  >
                    비교 엑셀 저장
                  </button>
                  <button
                    type="button"
                    onClick={() => void exportFile("pdf")}
                    disabled={exporting !== ""}
                    className="button-text rounded-btn border border-line-strong bg-white px-4 py-2 text-[13px] font-bold text-ink-800 hover:bg-ink-50 disabled:opacity-50"
                  >
                    고객용 PDF 저장
                  </button>
                </div>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-4">
                <MetricCard label="월납 증감" value={formatDeltaWon(afterResult.comparison.premium.delta_monthly)} />
                <MetricCard label="총 납입 증감" value={formatDeltaWon(afterResult.comparison.premium.delta_paid_total)} />
                <MetricCard
                  label="부족·미가입 → 충분"
                  value={`${afterResult.comparison.summary.improved_count}개`}
                  tone="good"
                />
                <MetricCard
                  label="후 부족 / 미가입"
                  value={`${afterStatusSummary[STATUS_SHORT]} / ${afterStatusSummary[STATUS_MISSING]}`}
                  tone={afterStatusSummary[STATUS_SHORT] + afterStatusSummary[STATUS_MISSING] > 0 ? "warn" : "good"}
                />
              </div>

              <div className="mt-4 rounded-[8px] bg-accent-50 px-4 py-3 text-[13px] font-semibold text-accent-800">
                미가입→충분 {afterResult.comparison.summary.missing_to_sufficient}개 · 부족→충분{" "}
                {afterResult.comparison.summary.short_to_sufficient}개
              </div>

              <div className="mt-5 space-y-5">
                {comparisonGroups.map(({ group, rows }) => (
                  <div key={group}>
                    <h3 className="ko-heading mb-2 text-sm font-bold text-ink-900">{group}</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[840px] text-[12px]">
                        <thead>
                          <tr className="border-b border-line text-left text-ink-500">
                            <th className="py-2 pr-2">담보</th>
                            <th className="px-2 py-2 text-right">전 가입</th>
                            <th className="px-2 py-2 text-center">전 상태</th>
                            <th className="px-2 py-2 text-right">후 가입</th>
                            <th className="px-2 py-2 text-center">후 상태</th>
                            <th className="px-2 py-2 text-right">증감</th>
                            <th className="py-2 pl-2 text-center">변화</th>
                          </tr>
                        </thead>
                        <tbody>
                          {rows.map((coverage) => (
                            <tr key={`${coverage.group12}-${coverage.kb_name}`} className="border-b border-line/60">
                              <td className="break-keep py-1.5 pr-2 font-semibold text-ink-800">{coverage.kb_name}</td>
                              <td className="px-2 py-1.5 text-right">{formatCoverageAmount(coverage.before_value)}</td>
                              <td className="px-2 py-1.5 text-center">
                                <StatusBadge status={coverage.before_status} />
                              </td>
                              <td className="px-2 py-1.5 text-right font-semibold text-ink-900">
                                {formatCoverageAmount(coverage.after_value)}
                              </td>
                              <td className="px-2 py-1.5 text-center">
                                <StatusBadge status={coverage.after_status} />
                              </td>
                              <td className="px-2 py-1.5 text-right">{formatCoverageAmount(coverage.delta_value)}</td>
                              <td className="py-1.5 pl-2 text-center">
                                <span
                                  className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${
                                    coverage.improved
                                      ? "bg-accent-50 text-accent-700"
                                      : coverage.worsened
                                        ? "bg-amber-50 text-amber-700"
                                        : "bg-ink-100 text-ink-500"
                                  }`}
                                >
                                  {coverage.status_change}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section className="mt-6 rounded-card border border-line bg-white">
            <button
              type="button"
              onClick={() => setShowBefore((value) => !value)}
              aria-expanded={showBefore}
              className="flex w-full items-center justify-between gap-2 px-6 py-4 text-left"
            >
              <span className="ko-heading text-lg font-bold text-ink-900">회사별 가입 현황 [전]</span>
              <span className="text-sm font-semibold text-accent-700">{showBefore ? "접기" : "펼치기"}</span>
            </button>

            {showBefore && (
              <div className="border-t border-line px-6 py-5">
                <div className="mb-4 grid gap-3 md:grid-cols-2">
                  {companies.map((company) => (
                    <div key={company.idx} className="rounded-card border border-line bg-canvas px-4 py-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-bold text-ink-900">{company.insurer || `계약 ${company.idx}`}</p>
                          <p className="mt-1 text-xs text-ink-soft">{company.product || "상품명 확인 필요"}</p>
                          <p className="mt-1 text-[11px] font-semibold text-ink-soft">{formatPeriod(company)}</p>
                        </div>
                        <p className="shrink-0 text-sm font-extrabold text-ink-900">{formatPremium(company.monthly_premium)}</p>
                      </div>
                      {company.remark && <p className="mt-2 text-xs font-semibold text-amber-700">{company.remark}</p>}
                    </div>
                  ))}
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full min-w-[720px] text-[12px]">
                    <thead>
                      <tr className="border-b border-line text-ink-500">
                        <th className="py-2 pr-2 text-left">담보</th>
                        <th className="px-2 py-2 text-right">합산</th>
                        {result.before.companies.map((company) => (
                          <th key={company.idx} className="px-2 py-2 text-right">
                            {company.insurer || `계약 ${company.idx}`}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.before.coverages.map((coverage) => (
                        <tr key={coverage.kb_name} className="border-b border-line/60">
                          <td className="break-keep py-1.5 pr-2 font-semibold text-ink-800">{coverage.kb_name}</td>
                          <td className="px-2 py-1.5 text-right font-semibold text-ink-900">
                            {formatCoverageAmount(coverage.summary)}
                          </td>
                          {result.before.companies.map((company) => (
                            <td key={company.idx} className="px-2 py-1.5 text-right text-ink-soft">
                              {formatCoverageAmount(coverage.by_company[keyOf(company.idx)])}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
