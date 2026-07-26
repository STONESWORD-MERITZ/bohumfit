// Display-cache only: backend/coverage/compare.py is the authority for coverage math.
// BOHUMFIT-211 parity tests lock this cache to the backend result. Do not change
// calculation rules here without updating the backend path and parity fixture.

const STATUS_SUFFICIENT = "충분";
const STATUS_SHORT = "부족";
const STATUS_MISSING = "미가입";

export type Company = {
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
  paid_up?: boolean; // BOHUMFIT-236 A: 납입완료(백엔드 판별 — 일시납 또는 납입기간 경과)
};

export type BeforeCoverage = {
  kb_name: string;
  kb_group: string;
  group12: string;
  agg: string;
  summary: number | null;
  by_company: Record<string, number | null>;
  enrolled: boolean;
  estimated?: boolean; // BOHUMFIT-238: 종수술 표준 환산 산출 행 구분
  overview?: boolean; // BOHUMFIT-246: 전체 보장현황(합계-only) 유래 행 — [후] 이월 시 합계 수준 유지
};

// BOHUMFIT-246/247: 양식 45~49행 Y/N 파생(백엔드 compute_yn_flags와 동일 스키마).
export type YnFlag = {
  item: string;
  value: "Y" | "N";
  sources: { kb_name: string; summary: number | null }[];
};

export type FinalCoverage = {
  group12: string;
  kb_name: string;
  agg: string;
  value: number | null;
  recommended: number | null;
  gap: number | null;
  status: string | null;
};

export type PremiumSummary = {
  monthly_total: number;
  monthly_total_active?: number | null; // BOHUMFIT-236 A: 납입완료 제외 병기 부값(KB 헤더 산식)
  paid_total: number | null;
  currency?: string;
};

export type AnalyzeResult = {
  before: {
    customer: { name: string | null; age: number | null; sex: string | null };
    premium: PremiumSummary;
    companies: Company[];
    contract_list?: Company[];
    coverages: BeforeCoverage[];
    // BOHUMFIT-246 파생치(백엔드 build_before 산출 — [전] 표시는 백엔드 값이 정본).
    stage_totals?: Record<string, number>;
    yn_flags?: YnFlag[];
  };
  final: {
    premium: PremiumSummary;
    coverages: FinalCoverage[];
    rollup_by_group12: { group12: string; status_counts: Record<string, number> }[];
  };
  warnings: string[];
};

export type ContractDecision = {
  disposition: "keep" | "cancel";
};

export type ProposalCoverageDraft = {
  id: string;
  kbName: string;
  amount: string;
  kbGroup?: string;
  group12?: string;
  agg?: string;
};

export type ProposalDraft = {
  id: string;
  insurer: string;
  product: string;
  monthlyPremium: string;
  payMonths: string;
  maturity: string;
  coverages: ProposalCoverageDraft[];
};

export type ProposalPlan = {
  proposal_id: string;
  insurer?: string;
  product?: string;
  monthly_premium: number | null;
  pay_cycle: string;
  pay_months: number | null;
  maturity?: string;
  coverages: { kb_name: string; amount: number | null; kb_group?: string; group12?: string; agg?: string }[];
};

export type ConsultingPlanV1 = {
  version: 1;
  source: "coverage-remodel";
  existing: {
    contract_idx: number | string;
    disposition: "keep" | "cancel";
  }[];
  proposals: ProposalPlan[];
};

export type ComparisonRow = {
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
  manual?: boolean; // BOHUMFIT-236 E: 설계사 수동 입력 담보 구분(세션 상태 — 서버 저장 없음)
};

export type CoverageComparison = {
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

export type CoverageAfterResponse = AnalyzeResult & {
  consulting_plan: ConsultingPlanV1;
  after: {
    before: AnalyzeResult["before"];
    final: AnalyzeResult["final"];
  };
  comparison: CoverageComparison;
};

// BOHUMFIT-246: 비분양식 대분류로 교체(백엔드 constants.GROUP13과 동일 순서 — 정본화).
export const GROUP_ORDER = [
  "사망",
  "후유장해",
  "암",
  "뇌",
  "심장",
  "종수술",
  "수술",
  "의료이용",
  "골절",
  "가입특약(Y/N)",
  "기타",
];

const STATUS_RANK: Record<string, number> = {
  "": 0,
  [STATUS_MISSING]: 1,
  [STATUS_SHORT]: 2,
  [STATUS_SUFFICIENT]: 3,
};

// BOHUMFIT-247: 표시 순서 = 비분양식 시트2 10~49행(백엔드 constants.NEW_ITEM_ORDER 미러 —
// 계산이 아닌 표시 정렬 전용. 목록 밖 라벨은 그룹 내 뒤).
export const ITEM_ORDER = [
  "일반사망", "재해사망", "질병사망", "상해사망",
  "상해후유장해", "질병후유장해",
  "암진단금", "유사암진단금", "암수술", "항암약물방사선", "표적항암치료",
  "면역항암치료", "중입자방사선", "암 주요치료비",
  "뇌혈관질환", "뇌졸중", "뇌출혈", "뇌혈관수술",
  "심혈관질환", "허혈성심장질환", "급성심근경색", "심혈관수술", "순환계 치료비",
  "일반종수술 1종(표준환산)", "일반종수술 2종(표준환산)", "일반종수술 3종(표준환산)",
  "일반종수술 4종(표준환산)", "일반종수술 5종(표준환산)", "종수술비", "종수술비(표 외)",
  "상해수술", "질병수술",
  "응급실", "질병입원", "상해입원",
  "골절진단비", "깁스치료비",
  "벌금(대인/스쿨존/대물)", "교통사고처리지원금", "변호사선임비용", "자동차사고부상",
  "가족/일상/자녀배상", "상해입원의료비", "상해통원의료비", "질병입원의료비", "질병통원의료비",
];

const ITEM_ORDER_IDX = new Map(ITEM_ORDER.map((name, index) => [name, index]));

export function itemOrderKey(name: string | null | undefined): number {
  const idx = ITEM_ORDER_IDX.get(name || "");
  return idx == null ? ITEM_ORDER.length : idx;
}

// BOHUMFIT-247: [전] 원문이 없는 신담보 3행 — "신규 설계 반영 대상" 구분(오독 방지 문구용).
export const NEW_COVERAGE_PLACEHOLDERS = ["면역항암치료", "암 주요치료비", "심혈관질환"];

// BOHUMFIT-246/247: Y/N 파생 미러(백엔드 constants.YN_ITEMS · COUNTA 수식 의미 등가) —
// [후]는 클라이언트 이월 결과에서 재산출한다(211 패리티: 규칙 변경 시 백엔드와 동시 수정).
export const YN_ITEMS: [string, string[]][] = [
  ["운전자특약", ["벌금(대인/스쿨존/대물)", "교통사고처리지원금", "변호사선임비용"]],
  ["자동차부상치료비", ["자동차사고부상"]],
  ["가족일상배상책임", ["가족/일상/자녀배상"]],
  ["상해실손의료비", ["상해입원의료비", "상해통원의료비"]],
  ["질병실손의료비", ["질병입원의료비", "질병통원의료비"]],
];

export function computeYnFlags(coverages: BeforeCoverage[]): YnFlag[] {
  const byName = new Map(coverages.map((coverage) => [coverage.kb_name, coverage]));
  return YN_ITEMS.map(([item, sources]) => ({
    item,
    value: sources.some((name) => byName.get(name)?.enrolled) ? "Y" : "N",
    sources: sources.map((name) => ({ kb_name: name, summary: byName.get(name)?.summary ?? null })),
  }));
}

// BOHUMFIT-246/247: 종합비교 단계 파생 미러(백엔드 constants.STAGE_COMPONENTS — 비분양식
// 시트3 수식 이식. 원문 수식은 backend/coverage/constants.py 주석 참조. K7 이중합산 미이식).
export const STAGE_COMMON_ADD = ["일반종수술 5종(표준환산)", "질병수술"];
export const STAGE_COMPONENTS: [string, string[]][] = [
  ["암", ["암진단금", "유사암진단금", "암수술", "항암약물방사선", "표적항암치료", "면역항암치료", "중입자방사선"]],
  ["뇌초기", ["뇌혈관질환", "뇌졸중", "뇌출혈", "뇌혈관수술"]],
  ["뇌중기", ["뇌졸중", "뇌출혈", "뇌혈관수술"]],
  ["뇌말기", ["뇌출혈", "뇌혈관수술"]],
  ["심장초기", ["심혈관질환", "허혈성심장질환", "급성심근경색", "심혈관수술"]],
  ["심장중기", ["허혈성심장질환", "급성심근경색", "심혈관수술"]],
  ["심장말기", ["급성심근경색", "심혈관수술"]],
];

export function computeStageTotals(coverages: BeforeCoverage[]): Record<string, number> {
  const byName = new Map(coverages.map((coverage) => [coverage.kb_name, coverage]));
  const value = (name: string) => byName.get(name)?.summary || 0;
  const common = STAGE_COMMON_ADD.reduce((sum, name) => sum + value(name), 0);
  return Object.fromEntries(
    STAGE_COMPONENTS.map(([stage, names]) => [stage, names.reduce((sum, name) => sum + value(name), 0) + common]),
  );
}

export function keyOf(idx: number | string): string {
  return String(idx);
}

export function toNumberOrNull(value: string): number | null {
  const cleaned = value.replace(/[^\d]/g, "");
  return cleaned ? Number(cleaned) : null;
}

function contractPaidTotal(company: Company): number | null {
  if (company.monthly_premium == null || company.pay_months == null) return null;
  return company.monthly_premium * company.pay_months;
}

export function aggregateCoverageValues(byCompany: Record<string, number | null>, agg: string): number | null {
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

export function groupKey(group: string | null | undefined): number {
  return GROUP_ORDER.includes(group || "") ? GROUP_ORDER.indexOf(group || "") : GROUP_ORDER.length;
}

function sortCompanies(companies: Company[]): Company[] {
  // BOHUMFIT-236 B: 계약 번호 숫자 오름차순(백엔드 _company_sort_key와 동일 규칙) —
  // 보험사 가나다 + 문자열 idx 사전식("1,10,11,…,2") 정렬을 대체. 숫자 아님(신규제안 P1 등)은 뒤로.
  return [...companies].sort((left, right) => {
    const leftNum = Number(left.idx);
    const rightNum = Number(right.idx);
    const leftIsNum = Number.isFinite(leftNum);
    const rightIsNum = Number.isFinite(rightNum);
    if (leftIsNum && rightIsNum && leftNum !== rightNum) return leftNum - rightNum;
    if (leftIsNum !== rightIsNum) return leftIsNum ? -1 : 1;
    const leftId = keyOf(left.idx);
    const rightId = keyOf(right.idx);
    if (leftId !== rightId) return leftId < rightId ? -1 : 1;
    return 0;
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
      ? [{ level: "info", message: `부족/미가입에서 충분으로 개선된 담보 ${improvedCount}개` }]
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
      if (decision.disposition === "keep") return [];
      return [
        {
          contract_idx: company.idx,
          disposition: decision.disposition,
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
            kb_group: coverage.kbGroup,
            group12: coverage.group12,
            agg: coverage.agg,
          })),
      }))
      .filter((proposal) => proposal.monthly_premium != null || proposal.coverages.length > 0),
  };
}

export function buildAfterResult(
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
    const nextCompany: Company = {
      ...company,
      consulting_status: "유지",
    };
    nextCompany.paid_total = contractPaidTotal(nextCompany);
    keptIds.add(keyOf(company.idx));
    afterCompanies.push(nextCompany);
  }

  const proposalAmounts: Record<string, Record<string, number | null>> = {};
  const proposalMeta: Record<string, Pick<BeforeCoverage, "kb_name" | "kb_group" | "group12" | "agg">> = {};
  const knownCoverages = new Set(analysis.before.coverages.map((coverage) => coverage.kb_name));
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
      if (!knownCoverages.has(coverage.kb_name) && coverage.group12 && coverage.agg) {
        proposalMeta[coverage.kb_name] ||= {
          kb_name: coverage.kb_name,
          kb_group: coverage.kb_group || coverage.group12,
          group12: coverage.group12,
          agg: coverage.agg,
        };
      }
      if (!proposalAmounts[coverage.kb_name]) proposalAmounts[coverage.kb_name] = {};
      const currentAmount = proposalAmounts[coverage.kb_name][proposalId];
      proposalAmounts[coverage.kb_name][proposalId] =
        currentAmount == null || coverage.amount == null ? coverage.amount : Math.max(currentAmount, coverage.amount);
    }
  }

  const knownContractIds = new Set(sourceCompanies.map((company) => keyOf(company.idx)));
  const afterCoverages = analysis.before.coverages.map((coverage) => {
    // BOHUMFIT-246 회송 보정(247 패리티 반영): 전체 보장현황(합계-only) 행은 계약별 셀이
    // 없어 재집계 시 값이 소실된다 — 해지 체크 불가 행이므로 합계 수준(summary·enrolled)을
    // 그대로 이월한다(backend consulting.apply_consulting_plan과 동일 규칙).
    if (coverage.overview) {
      const byCompany: Record<string, number | null> = { ...(proposalAmounts[coverage.kb_name] || {}) };
      const proposalSum = aggregateCoverageValues(byCompany, coverage.agg);
      return {
        ...coverage,
        by_company: byCompany,
        // 신규 제안 가산은 표준 경로와 동일하게 합계에 더한다(sum 기준 — 246 이월 모델).
        summary:
          proposalSum == null
            ? coverage.summary
            : coverage.agg === "sum"
              ? (coverage.summary || 0) + proposalSum
              : Math.max(coverage.summary || 0, proposalSum),
        enrolled: coverage.enrolled || proposalSum != null,
      };
    }
    const byCompany: Record<string, number | null> = {};
    for (const [companyId, amount] of Object.entries(coverage.by_company || {})) {
      // BOHUMFIT-246: 계약 미상 키('?' 등)는 해지 대상이 아니므로 이월(backend 동일 규칙).
      if (keptIds.has(companyId) || !knownContractIds.has(companyId)) byCompany[companyId] = amount;
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
  for (const [kbName, meta] of Object.entries(proposalMeta)) {
    const byCompany = proposalAmounts[kbName] || {};
    afterCoverages.push({
      ...meta,
      by_company: byCompany,
      summary: aggregateCoverageValues(byCompany, meta.agg),
      enrolled: Object.values(byCompany).some((amount) => amount != null),
    });
  }

  // BOHUMFIT-234/236: 일시납은 월납 합산 제외, 납입완료 제외 부값 병기(백엔드 compare.py와 동일 규칙).
  const monthlyTotal = afterCompanies.reduce(
    (sum, company) => sum + (company.pay_cycle === "일시납" ? 0 : company.monthly_premium || 0),
    0,
  );
  const monthlyTotalActive = afterCompanies.reduce(
    (sum, company) => sum + (company.pay_cycle === "일시납" || company.paid_up ? 0 : company.monthly_premium || 0),
    0,
  );
  const paidTotal = paidUnknown ? null : afterCompanies.reduce((sum, company) => sum + (company.paid_total || 0), 0);
  const sortedCompanies = sortCompanies(afterCompanies);
  const afterBefore: AnalyzeResult["before"] = {
    ...analysis.before,
    premium: {
      monthly_total: monthlyTotal,
      monthly_total_active: monthlyTotalActive,
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

  const comparison = compareFinals(analysis.final, afterFinal);
  // BOHUMFIT-246/247: 합계형(overview) 문서 + 해지 요청 — 보존+경고 정책(backend 동일 문구).
  if (
    plan.existing.some((entry) => entry.disposition === "cancel") &&
    analysis.before.coverages.some((coverage) => coverage.overview)
  ) {
    comparison.cautions.push({
      level: "warning",
      message:
        "전체 보장현황(합계형) 문서는 계약별 보장 귀속이 없어 해지를 보장 합계에 반영할 수 없습니다 — 해당 보장행은 [전] 합계 수준으로 유지됩니다.",
    });
  }

  return {
    ...analysis,
    consulting_plan: plan,
    after: { before: afterBefore, final: afterFinal },
    comparison,
    warnings: analysis.warnings || [],
  };
}
