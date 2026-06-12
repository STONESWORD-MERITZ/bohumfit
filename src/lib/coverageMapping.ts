// BOHUMFIT-041: 보장분석 매핑 엔진 — 순수 TS lib (UI 없음).
//
// 역할
//  1) 표준 카테고리 36행(표준비분표 '비교분석표' J8:J43 순서) + 보장명→카테고리 사전 로드
//  2) 계약별 담보 배열 → 비분표 열 데이터 변환 (사망 분해 / 일반종수술 자동셋팅 / Y/N형 / 보험료)
//  3) 합계 계산 — 컨설팅 전/후 모두 동일한 순수 함수로 계산한다(후 전용 로직 금지)
//  4) 컨설팅 후 모델(BOHUMFIT-043 대비): 계약 유지/해지 + 담보별 감액 override + 신규 제안 계약
//
// ⚠️ 이 lib 의 산식이 원본(single source of truth)이다 — 이후 화면/백엔드에서 재구현 금지.
// 단위: 가입금액 = 만원(원천자료 L열 그대로), 보험료 = 원.
// 매핑 불가 보장명은 드롭하지 않고 unmapped 로 반환한다(후속 UI 수동 배정용).

import rawCategoriesJson from "./coverageCategories.json";

// ── 타입 ─────────────────────────────────────────────────────────────────────

export type CategoryKind = "amount" | "flag" | "premium";

export interface CoverageCategory {
  id: string;
  label: string;
  kind: CategoryKind;
  /** 일반종수술 1~5종 묶음 등 그룹 식별자 */
  group?: string;
  /** 비분표 행 순서 (1-base) */
  order: number;
}

interface CoverageCategoriesFile {
  version: number;
  source: string;
  amountUnit: string;
  premiumUnit: string;
  categories: CoverageCategory[];
  /** normalize() 적용된 보장명 → 카테고리 id 또는 그룹 id */
  mappings: Record<string, string>;
}

/** 원천자료의 담보 1행 (보장명 + 가입금액) */
export interface ContractCoverage {
  /** 보장명 (원천자료 J열) */
  name: string;
  /** 가입금액 (만원) */
  amountManwon: number;
  /** 컨설팅 감액 override — 유지 계약에서 담보 단위 조정 가입금액 (만원) */
  overrideAmountManwon?: number | null;
}

export type ContractStatus = "유지" | "해지";

export interface Contract {
  id: string;
  insurer: string;
  productName?: string;
  /** 가입일 (YYYY-MM-DD 등 원문 유지) */
  startDate?: string;
  /** 납입주기/납입기간 등 메타 (비분표 가입일·납만기 행용) */
  endDate?: string;
  payCycle?: string;
  payYears?: string;
  /** 납입보험료 (원) */
  premiumWon: number;
  /** 컨설팅 상태 — 기본 "유지" */
  status?: ContractStatus;
  /** 감액 등으로 보험료가 달라질 때 수기 조정값 (원) */
  overridePremiumWon?: number | null;
  coverages: ContractCoverage[];
}

export interface UnmappedCoverage {
  name: string;
  amountManwon: number;
  /** 출처 계약 id (테이블 단위 집계 시) */
  contractId?: string;
}

/** 비분표 한 계약 열 */
export interface ContractColumn {
  contractId: string;
  insurer: string;
  productName?: string;
  startDate?: string;
  payYears?: string;
  /** categoryId → 값. amount/premium 행은 number(만원/원), flag 행은 boolean */
  cells: Record<string, number | boolean>;
  /** 자동셋팅(종수술 제안 등) 칸 표시 — 후속 UI 에서 전 칸 수정 가능해야 함 */
  suggested: Record<string, boolean>;
  /** 매핑 불가 보장명 (드롭 금지 — 수동 배정용) */
  unmapped: UnmappedCoverage[];
  /** 사망 분해/보간 등 자동 처리 설명 */
  notes: string[];
}

export interface CoverageTable {
  columns: ContractColumn[];
  /** categoryId → 합계. amount/premium 은 number 합, flag 는 하나라도 Y면 true */
  totals: Record<string, number | boolean>;
  /** 전체 unmapped 집계 (열 정보 포함) */
  unmapped: UnmappedCoverage[];
}

export interface SurgeryTierSuggestion {
  /** 1종~5종 (만원) */
  values: [number, number, number, number, number];
  /** 자동셋팅 여부 — 후속 UI 수정 가능 표시용 */
  suggested: boolean;
  /** 기준표 정확 일치가 아니라 보간/외삽으로 산출했는지 */
  interpolated: boolean;
  /** 5종 기준 가입금액 (만원) */
  baseManwon: number;
}

export type DeathDecompositionBranch =
  | "none"            // 사망 담보 없음
  | "equal"           // 질병=상해 → 일반사망
  | "injury_excess"   // 질병<상해 → 일반=질병, 재해=차액
  | "disease_excess"  // 질병>상해 → 일반=상해, 질병 행 잔여 유지(보수적)
  | "disease_only"    // 상해 없음 → 질병사망 행 유지
  | "injury_only";    // 질병 없음 → 상해사망 행 유지

export interface DeathDecomposition {
  branch: DeathDecompositionBranch;
  general: number;
  disaster: number;
  injury: number;
  disease: number;
}

// ── 카테고리 데이터 로드 ──────────────────────────────────────────────────────

function assertCategoriesFile(v: unknown): CoverageCategoriesFile {
  const f = v as CoverageCategoriesFile;
  if (!f || !Array.isArray(f.categories) || typeof f.mappings !== "object") {
    throw new Error("coverageCategories.json 형식 오류 — categories/mappings 누락");
  }
  return f;
}

const categoriesFile = assertCategoriesFile(rawCategoriesJson);

/** 비분표 36행 정의 (order 순) */
export const COVERAGE_CATEGORIES: readonly CoverageCategory[] = [...categoriesFile.categories].sort(
  (a, b) => a.order - b.order,
);

export const CATEGORY_BY_ID: Readonly<Record<string, CoverageCategory>> = Object.fromEntries(
  COVERAGE_CATEGORIES.map((c) => [c.id, c]),
);

/** 일반종수술 그룹 id (매핑 사전의 그룹 타깃) */
export const GENERAL_SURGERY_GROUP = "general_surgery";

const GENERAL_SURGERY_TYPE_IDS = [
  "general_surgery_type1",
  "general_surgery_type2",
  "general_surgery_type3",
  "general_surgery_type4",
  "general_surgery_type5",
] as const;

const DEATH_IDS = {
  general: "general_death",
  disaster: "disaster_death",
  injury: "injury_death",
  disease: "disease_death",
} as const;

const PREMIUM_ID = "premium";

// ── 보장명 정규화 · 매핑 ─────────────────────────────────────────────────────

/**
 * 보장명 정규화: NFKC(전각→반각) → 괄호그룹 제거(예: "암진단(갱신)") → 공백 제거.
 * 매핑 사전 키는 모두 이 정규화를 거친 형태로 저장돼 있다.
 */
export function normalizeCoverageName(name: string): string {
  let s = (name ?? "").normalize("NFKC");
  // 괄호 그룹 반복 제거 (중첩 비대응 — 보장명 수준에서는 충분)
  for (let i = 0; i < 3 && /[()]/.test(s); i++) {
    s = s.replace(/\([^()]*\)/g, "");
  }
  return s.replace(/\s+/g, "").trim();
}

/**
 * 보장명 → 카테고리 id 또는 그룹 id(GENERAL_SURGERY_GROUP). 매핑 불가 시 null.
 * null 은 드롭이 아니라 unmapped 처리 대상이다.
 */
export function mapCoverageName(name: string): string | null {
  const key = normalizeCoverageName(name);
  if (!key) return null;
  return categoriesFile.mappings[key] ?? null;
}

// ── 일반종수술 자동셋팅 ───────────────────────────────────────────────────────

/**
 * 종수술 기준표 (만원). key = 5종 가입금액, value = [1종..5종].
 * 구간 사이 금액은 인접 구간 선형 보간으로 1~4종 제안, 5종 = 가입금액.
 * 표 범위 밖(최소 미만/최대 초과)은 경계 행을 비례 스케일(외삽)한다.
 */
export const SURGERY_TIER_TABLE: ReadonlyArray<readonly [number, readonly [number, number, number, number, number]]> = [
  [100, [5, 15, 25, 50, 100]],
  [500, [10, 30, 50, 100, 500]],
  [600, [20, 60, 100, 200, 600]],
  [1000, [20, 50, 100, 500, 1000]],
  [3000, [50, 100, 200, 1000, 3000]],
];

export function suggestSurgeryTiers(amountManwon: number): SurgeryTierSuggestion | null {
  const base = Math.max(0, Math.round(amountManwon || 0));
  if (base <= 0) return null;

  const table = SURGERY_TIER_TABLE;
  const exact = table.find(([k]) => k === base);
  if (exact) {
    const [, row] = exact;
    return { values: [row[0], row[1], row[2], row[3], base], suggested: true, interpolated: false, baseManwon: base };
  }

  const first = table[0];
  const last = table[table.length - 1];
  let v: [number, number, number, number, number];

  if (base < first[0]) {
    // 최소 구간 미만 — 첫 행 비례 스케일 (외삽)
    const r = base / first[0];
    v = [first[1][0] * r, first[1][1] * r, first[1][2] * r, first[1][3] * r, base];
  } else if (base > last[0]) {
    // 최대 구간 초과 — 마지막 행 비례 스케일 (외삽)
    const r = base / last[0];
    v = [last[1][0] * r, last[1][1] * r, last[1][2] * r, last[1][3] * r, base];
  } else {
    // 인접 구간 선형 보간
    let lo = first;
    let hi = last;
    for (let i = 0; i < table.length - 1; i++) {
      if (base > table[i][0] && base < table[i + 1][0]) {
        lo = table[i];
        hi = table[i + 1];
        break;
      }
    }
    const t = (base - lo[0]) / (hi[0] - lo[0]);
    const lerp = (a: number, b: number) => a + (b - a) * t;
    v = [lerp(lo[1][0], hi[1][0]), lerp(lo[1][1], hi[1][1]), lerp(lo[1][2], hi[1][2]), lerp(lo[1][3], hi[1][3]), base];
  }

  // 만원 정수 반올림 (제안값 — 후속 UI 에서 전 칸 수정 가능)
  const rounded = v.map((x) => Math.round(x)) as [number, number, number, number, number];
  rounded[4] = base; // 5종 = 가입금액 고정
  return { values: rounded, suggested: true, interpolated: true, baseManwon: base };
}

// ── 사망 분해 룰 ─────────────────────────────────────────────────────────────

/**
 * 사망 분해 (계약 단위, 카테고리 합산 후 적용):
 *  - 질병=상해 → 일반사망 (재해 0)
 *  - 질병<상해 → 일반=질병, 재해=상해-질병   (검증례: 질병 1억 + 상해 3억 → 일반 1억 + 재해 2억)
 *  - 질병사망 없음 → 상해사망 행 유지
 *  - 상해사망 없음 → 질병사망 행 유지
 *  - 질병>상해(미명세) → 보수적으로 일반=상해, 질병 행 잔여=차액 유지
 */
export function decomposeDeath(diseaseManwon: number, injuryManwon: number): DeathDecomposition {
  const disease = Math.max(0, diseaseManwon || 0);
  const injury = Math.max(0, injuryManwon || 0);
  if (disease <= 0 && injury <= 0) {
    return { branch: "none", general: 0, disaster: 0, injury: 0, disease: 0 };
  }
  if (disease <= 0) {
    return { branch: "injury_only", general: 0, disaster: 0, injury, disease: 0 };
  }
  if (injury <= 0) {
    return { branch: "disease_only", general: 0, disaster: 0, injury: 0, disease };
  }
  if (disease === injury) {
    return { branch: "equal", general: disease, disaster: 0, injury: 0, disease: 0 };
  }
  if (disease < injury) {
    return { branch: "injury_excess", general: disease, disaster: injury - disease, injury: 0, disease: 0 };
  }
  return { branch: "disease_excess", general: injury, disaster: 0, injury: 0, disease: disease - injury };
}

// ── 계약 → 비분표 열 변환 ────────────────────────────────────────────────────

function emptyCells(): Record<string, number | boolean> {
  const cells: Record<string, number | boolean> = {};
  for (const c of COVERAGE_CATEGORIES) {
    cells[c.id] = c.kind === "flag" ? false : 0;
  }
  return cells;
}

function effectiveCoverageAmount(cov: ContractCoverage): number {
  const amount =
    cov.overrideAmountManwon !== undefined && cov.overrideAmountManwon !== null
      ? cov.overrideAmountManwon
      : cov.amountManwon;
  return Math.max(0, amount || 0);
}

/**
 * 계약 1건 → 비분표 열. 순수 함수 — 전/후 공용.
 * (감액 override 가 담보에 남아 있으면 여기서 반영된다. 해지 제외는 applyConsultingPlan 책임.)
 */
export function buildContractColumn(contract: Contract): ContractColumn {
  const cells = emptyCells();
  const suggested: Record<string, boolean> = {};
  const unmapped: UnmappedCoverage[] = [];
  const notes: string[] = [];

  let surgeryGroupBase = 0; // 일반종수술 그룹 가입금액 합 (5종 기준)

  for (const cov of contract.coverages) {
    const target = mapCoverageName(cov.name);
    const amount = effectiveCoverageAmount(cov);

    if (target === null) {
      unmapped.push({ name: cov.name, amountManwon: amount, contractId: contract.id });
      continue;
    }
    if (target === GENERAL_SURGERY_GROUP) {
      surgeryGroupBase += amount;
      continue;
    }
    const cat = CATEGORY_BY_ID[target];
    if (!cat) {
      // 사전이 모르는 id 를 가리키는 경우 — 드롭 금지, unmapped 로 보존
      unmapped.push({ name: cov.name, amountManwon: amount, contractId: contract.id });
      continue;
    }
    if (cat.kind === "flag") {
      cells[cat.id] = true; // Y/N형 — 금액 아닌 존재 여부
    } else if (cat.kind === "amount") {
      cells[cat.id] = (cells[cat.id] as number) + amount;
    }
    // kind === "premium" 인 카테고리로의 직접 매핑은 사전에 없음 (보험료는 계약 메타)
  }

  // 일반종수술 자동셋팅 (기준표 + 보간) — suggested 플래그
  if (surgeryGroupBase > 0) {
    const tier = suggestSurgeryTiers(surgeryGroupBase);
    if (tier) {
      GENERAL_SURGERY_TYPE_IDS.forEach((id, i) => {
        cells[id] = tier.values[i];
        suggested[id] = true;
      });
      notes.push(
        `일반종수술 ${tier.baseManwon}만원: 기준표 ${tier.interpolated ? "보간" : "일치"} 자동셋팅(1~4종 제안, 5종=가입금액)`,
      );
    }
  }

  // 사망 분해 (직접 매핑된 일반/재해사망 금액에 가산)
  const dd = decomposeDeath(cells[DEATH_IDS.disease] as number, cells[DEATH_IDS.injury] as number);
  if (dd.branch !== "none") {
    cells[DEATH_IDS.general] = (cells[DEATH_IDS.general] as number) + dd.general;
    cells[DEATH_IDS.disaster] = (cells[DEATH_IDS.disaster] as number) + dd.disaster;
    cells[DEATH_IDS.injury] = dd.injury;
    cells[DEATH_IDS.disease] = dd.disease;
    const branchLabel: Record<DeathDecompositionBranch, string> = {
      none: "",
      equal: "질병=상해 → 일반사망",
      injury_excess: "질병<상해 → 일반=질병, 재해=차액",
      disease_excess: "질병>상해 → 일반=상해, 질병 잔여 유지(보수적)",
      disease_only: "상해 없음 → 질병사망 유지",
      injury_only: "질병 없음 → 상해사망 유지",
    };
    if (dd.branch !== "injury_only" && dd.branch !== "disease_only") {
      notes.push(`사망 분해: ${branchLabel[dd.branch]}`);
    }
  }

  // 보험료 행 (원) — override 가 계약에 남아 있으면 반영
  const premium =
    contract.overridePremiumWon !== undefined && contract.overridePremiumWon !== null
      ? contract.overridePremiumWon
      : contract.premiumWon;
  cells[PREMIUM_ID] = Math.max(0, premium || 0);

  return {
    contractId: contract.id,
    insurer: contract.insurer,
    productName: contract.productName,
    startDate: contract.startDate,
    payYears: contract.payYears,
    cells,
    suggested,
    unmapped,
    notes,
  };
}

/**
 * 합계 — amount/premium 은 수치 합, flag 는 하나라도 Y 면 true. 순수 함수(전/후 공용).
 */
export function sumColumns(columns: readonly ContractColumn[]): Record<string, number | boolean> {
  const totals = emptyCells();
  for (const col of columns) {
    for (const c of COVERAGE_CATEGORIES) {
      if (c.kind === "flag") {
        totals[c.id] = (totals[c.id] as boolean) || (col.cells[c.id] as boolean);
      } else {
        totals[c.id] = (totals[c.id] as number) + ((col.cells[c.id] as number) || 0);
      }
    }
  }
  return totals;
}

/**
 * 계약 배열 → 비분표 (열 + 합계 + unmapped 집계). 전/후 공용 순수 함수.
 */
export function buildCoverageTable(contracts: readonly Contract[]): CoverageTable {
  const columns = contracts.map(buildContractColumn);
  const unmapped = columns.flatMap((c) => c.unmapped);
  return { columns, totals: sumColumns(columns), unmapped };
}

// ── 컨설팅 후 모델 (BOHUMFIT-043 대비) ───────────────────────────────────────

/**
 * 컨설팅 의사결정 반영 — 순수 전처리:
 *  - status "해지" 계약 제외
 *  - 유지 계약의 담보별 감액 override(overrideAmountManwon)·보험료 수기 조정(overridePremiumWon)을
 *    실효값으로 굳혀 plain Contract 배열 반환
 * 이후 계산은 전과 동일한 buildCoverageTable 을 그대로 사용한다(입력만 다름).
 */
export function applyConsultingPlan(contracts: readonly Contract[]): Contract[] {
  return contracts
    .filter((ct) => (ct.status ?? "유지") !== "해지")
    .map((ct) => ({
      ...ct,
      status: "유지" as const,
      premiumWon:
        ct.overridePremiumWon !== undefined && ct.overridePremiumWon !== null
          ? Math.max(0, ct.overridePremiumWon)
          : ct.premiumWon,
      overridePremiumWon: null,
      coverages: ct.coverages.map((cov) => ({
        name: cov.name,
        amountManwon: effectiveCoverageAmount(cov),
        overrideAmountManwon: null,
      })),
    }));
}

/**
 * 후(After) 비분표 = 유지 계약(감액 override 반영) + 신규 제안 계약.
 * 별도 후 전용 계산 로직 없음 — applyConsultingPlan 전처리 후 동일 함수 호출.
 */
export function buildAfterTable(
  contracts: readonly Contract[],
  proposals: readonly Contract[] = [],
): CoverageTable {
  return buildCoverageTable(applyConsultingPlan([...contracts, ...proposals]));
}

// ── 원천자료 파싱 (BOHUMFIT-042 구현 예정 — 시그니처만 정의) ─────────────────

/** 원천자료 1행 (헤더: 회사명/상품명/구분/보험시기/보험종기/납입주기/납입기간(년)/납입보험료/담보명/보장명/상태/가입금액(만원)) */
export interface SourceRow {
  insurer?: string;
  productName?: string;
  role?: string;
  startDate?: string;
  endDate?: string;
  payCycle?: string;
  payYears?: string;
  premiumWon?: number;
  riderName?: string;
  coverageName?: string;
  coverageStatus?: string;
  amountManwon?: number;
}

/**
 * 원천자료 양식(SheetJS 로 읽은 행 배열) → 계약 배열.
 * 병합 셀(회사명/상품명/보험료) 전파·계약 경계 분리·해지 행 처리 포함 예정.
 * @throws BOHUMFIT-042 에서 구현한다 — 현재는 자리만 정의.
 */
export function parseSourceRows(rows: readonly SourceRow[]): Contract[] {
  throw new Error(`parseSourceRows(${rows.length}행)는 BOHUMFIT-042에서 구현 예정입니다.`);
}
