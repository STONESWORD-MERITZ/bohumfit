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
  row_id?: string; // BOHUMFIT-298: V2 49행 안정 키(서버 payload가 실어 보낸다). 종합비교 미러가 이 키로 케스케이드를 센다.
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

// ★BOHUMFIT-298(층위 3): 종합비교 미러를 **케스케이드 17키**로 이관한다(백엔드 `PAYOUT_CASCADE_V2` 1:1).
//   구 7키(암·뇌초기·뇌중기·뇌말기·심장초기·심장중기·심장말기 + 공통 가산)는 폐기됐다(290이 3단 종합비교를
//   17행으로 교체). 이 미러는 **`stage_totals`가 없는 구 payload(90일 히스토리)** 폴백에서만 쓰인다 —
//   새 payload는 `displayStageTotals`가 서버 `stage_totals`(17키)를 그대로 쓴다(295 헬퍼 불변).
//   ★값은 `row_id` 기준으로 센다. 구 payload는 `row_id`가 없으므로 구 담보명→row_id(`LEGACY_TO_V2` 이식)로 투영한다.
export const STAGE_CHAINS_V2: [string, string[]][] = [
  ["뇌초기", ["cerebral_disease"]],
  ["뇌중기", ["cerebral_disease", "stroke"]],
  ["뇌말기", ["cerebral_disease", "stroke", "cerebral_hemorrhage"]],
  ["심장초기", ["ischemic_heart"]],
  ["심장중기", ["ischemic_heart", "acute_mi"]],
  ["암 수 술 (레보아이 포함)", ["cancer_surgery"]],
  ["유사암 수술", ["cancer_minor_surgery"]],
  ["다빈치(일반암)", ["cancer_surgery", "cancer_surgery_davinci"]],
  ["다빈치(전립선)", ["cancer_surgery", "cancer_surgery_davinci_specific"]],
  ["다빈치(갑상선)", ["cancer_minor_surgery", "cancer_surgery_davinci_specific"]],
  ["항암 약물 치료", ["cancer_drug"]],
  ["표적 약물 치료", ["cancer_drug", "cancer_drug_targeted"]],
  ["면역 약물 치료", ["cancer_drug", "cancer_drug_targeted", "cancer_drug_immune"]],
  ["방사선 치료", ["cancer_radiation"]],
  ["세기조절 방사선 치료", ["cancer_radiation", "radio_imrt"]],
  ["양성자 방사선 치료", ["cancer_radiation", "radio_proton"]],
  ["중 입 자 치료", ["cancer_radiation", "radio_carbon"]],
];

// BOHUMFIT-298: 구 payload(row_id 없음) 투영용 — 백엔드 `LEGACY_TO_V2` 중 **케스케이드 체인에 쓰이는 row_id**만.
//   비고행(APPENDIX)·분배(DISTRIBUTED)로 가는 이름은 담지 않는다(체인에 안 쓰이므로 불필요).
export const LEGACY_TO_V2_ROW_ID: Record<string, string> = {
  암수술: "cancer_surgery",
  "암 수 술 / 로 봇 암 수 술": "cancer_surgery",
  유사암수술: "cancer_minor_surgery",
  "다빈치(일반암)": "cancer_surgery_davinci",
  "다빈치(종별 미상)": "cancer_surgery_davinci",
  "다빈치(전립선)": "cancer_surgery_davinci_specific",
  "다빈치(갑상선)": "cancer_surgery_davinci_specific",
  "다빈치(특정암)": "cancer_surgery_davinci_specific",
  항암약물치료비: "cancer_drug",
  표적항암치료: "cancer_drug_targeted",
  면역항암치료: "cancer_drug_immune",
  항암방사선치료비: "cancer_radiation",
  "세기조절 / 양성자 방사선": "radio_imrt",
  세기조절방사선: "radio_imrt",
  양성자방사선: "radio_proton",
  중입자방사선: "radio_carbon",
  "중입자 / 정위 방사선": "radio_carbon",
  뇌혈관질환: "cerebral_disease",
  뇌졸중: "stroke",
  뇌출혈: "cerebral_hemorrhage",
  허혈성심장질환: "ischemic_heart",
  급성심근경색: "acute_mi",
};

export function computeStageTotals(coverages: BeforeCoverage[]): Record<string, number> {
  // ★BOHUMFIT-298: row_id 기준 합산(서버 `compute_stage_totals`와 동일 규칙). 구 payload는 담보명→row_id 투영.
  //   같은 row_id에 여러 원천이 오면 더한다(구 payload는 row_id당 원천 1개라 이중 계상 없음).
  const byRowId = new Map<string, number>();
  for (const coverage of coverages) {
    const rowId = coverage.row_id ?? LEGACY_TO_V2_ROW_ID[coverage.kb_name];
    if (!rowId) continue; // 투영 실패(체인 밖 담보) — 조용히 0을 만들지 않고 그냥 기여하지 않는다.
    byRowId.set(rowId, (byRowId.get(rowId) ?? 0) + (coverage.summary ?? 0));
  }
  return Object.fromEntries(
    STAGE_CHAINS_V2.map(([stage, ids]) => [stage, ids.reduce((sum, id) => sum + (byRowId.get(id) ?? 0), 0)]),
  );
}

// ★BOHUMFIT-295: 종합비교·Y/N 표시값 선택 — **[전]과 [후]가 같은 규칙을 쓰도록** 한 곳에 둔다.
//   종전에는 [전]만 백엔드 파생값을 쓰고 [후]는 무조건 클라 미러로 재산출해 비대칭이었고,
//   미러가 구 40행 `kb_name` 기준이라 V2 payload에서 전부 0/N이 됐다(제안서가 없어도 [후]가 무너짐).
//   백엔드 파생값이 있으면 그것이 정본, 없으면(구 payload) 종전 미러로 폴백한다.
export function displayStageTotals(payload: AnalyzeResult["before"] | null | undefined) {
  if (!payload) return null;
  return payload.stage_totals ?? computeStageTotals(payload.coverages);
}

export function displayYnFlags(payload: AnalyzeResult["before"] | null | undefined) {
  if (!payload) return null;
  return payload.yn_flags ?? computeYnFlags(payload.coverages);
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

/**
 * BOHUMFIT-182(D-12): 합계형(overview) 문서 해지 경고 문구 — ★246/247에서 확정된 원문 그대로다.
 *   화면이 이 항목만 골라 전용 배너로 올릴 수 있도록 **상수로 뽑았을 뿐, 문구·조건은 바뀌지 않았다**.
 *   (backend `compare.py`가 내는 문구와도 같아야 한다 — 수정 시 양쪽을 함께 고칠 것.)
 */
export const OVERVIEW_CANCEL_CAUTION =
  "전체 보장현황(합계형) 문서는 계약별 보장 귀속이 없어 해지를 보장 합계에 반영할 수 없습니다 — 해당 보장행은 [전] 합계 수준으로 유지됩니다.";

// BOHUMFIT-260: 서버 `aggregator.carry_coverage_row`(249 정본 · 259 확장)와 동일 판정 —
//   by_company에 실제 값이 하나라도 있으면 "계약 귀속된" 행이다(overview 여부와 무관).
function isAttributedRow(coverage: { by_company?: Record<string, number | null> }): boolean {
  return Object.values(coverage.by_company || {}).some((amount) => amount != null);
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
    // ★BOHUMFIT-260: 단 256~258로 계약 귀속(by_company)이 채워진 overview 행은 해지를 회사
    //   단위로 반영할 수 있다 — 서버 aggregator.carry_coverage_row(259)와 동일하게 아래
    //   일반 경로(keep/cancel 필터 + '?' 이월 + 재집계)를 태운다.
    if (coverage.overview && !isAttributedRow(coverage)) {
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
  // ★BOHUMFIT-295: `{...analysis.before}` 스프레드가 [전]의 파생값(stage_totals·yn_flags)을 그대로
  //   복사해 왔다(254·272가 지목한 스프레드 경로). 파생값은 **coverages에서 나오므로**, 입력인
  //   coverages가 그대로면 여전히 유효하고 바뀌면 stale이다 — 그 판정을 여기서 한 번만 한다.
  //   · 해지 0·제안 0(= [후] 담보가 [전]과 동일) → [전] 파생값 유지 → 화면 [후] == [전](불변식 복원)
  //   · 해지/제안 있음 → **stale 값을 지운다**. 조용히 [전] 값을 [후]인 척 보여주지 않는다.
  //     (그 경우 표시는 종전처럼 클라 미러 폴백으로 떨어진다 — 프런트가 아직 V2 스키마를 모르는
  //      층위 3 미이관 상태라 정확한 [후] 재산출은 그 태스크에서 해결한다. 이번 변경으로 나빠지지 않는다.)
  const coverageFingerprint = (rows: BeforeCoverage[]) =>
    rows.map((row) => `${row.kb_name}\u0001${row.summary ?? ""}\u0001${row.enrolled ? 1 : 0}`).join("\u0002");
  const derivedStillValid =
    coverageFingerprint(afterCoverages) === coverageFingerprint(analysis.before.coverages);
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
    stage_totals: derivedStillValid ? analysis.before.stage_totals : undefined,
    yn_flags: derivedStillValid ? analysis.before.yn_flags : undefined,
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
  // ★BOHUMFIT-260: 귀속된 overview 행은 해지가 회사 단위로 반영되므로 경고 대상이 아니다 —
  //   서버 `aggregator.overview_rows_need_cancel_warning`(259)과 동일 조건.
  if (
    plan.existing.some((entry) => entry.disposition === "cancel") &&
    analysis.before.coverages.some((coverage) => coverage.overview && !isAttributedRow(coverage))
  ) {
    comparison.cautions.push({ level: "warning", message: OVERVIEW_CANCEL_CAUTION });
  }

  return {
    ...analysis,
    consulting_plan: plan,
    after: { before: afterBefore, final: afterFinal },
    comparison,
    warnings: analysis.warnings || [],
  };
}
