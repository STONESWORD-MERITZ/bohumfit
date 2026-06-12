// BOHUMFIT-042: 원천자료 엑셀 → 계약 배열 파서 (브라우저 내 처리 전용).
//
// - SheetJS(sheet_to_json header:1) 매트릭스를 입력으로 받아 BOHUMFIT-041 의
//   parseSourceRows 시그니처(SourceRow[] → Contract[])에 연결한다.
// - 고객 계약정보는 민감정보 — 이 모듈은 네트워크 호출이 없고 입력을 저장하지 않는다.
// - 파싱 실패 행은 버리지 않고 경고 목록(ParseWarning)으로 보존한다(드롭 금지).
// - 산식/매핑 로직은 041 lib(coverageMapping.ts)이 원본 — 여기서는 재구현하지 않는다.

import rawCategoriesJson from "./coverageCategories.json";
import {
  COVERAGE_CATEGORIES,
  GENERAL_SURGERY_GROUP,
  mapCoverageName,
  normalizeCoverageName,
  type Contract,
  type ContractCoverage,
  type SourceRow,
} from "./coverageMapping";

// ── 셀/매트릭스 타입 (SheetJS sheet_to_json header:1 결과) ───────────────────

export type SourceCell = string | number | boolean | Date | null | undefined;
export type SourceMatrix = ReadonlyArray<ReadonlyArray<SourceCell>>;

export interface ParseWarning {
  /** 엑셀 기준 행 번호 (1-base, 헤더 포함) */
  rowNo: number;
  reason: string;
  insurer?: string;
  productName?: string;
  coverageName?: string;
}

export interface SourceParseResult {
  contracts: Contract[];
  /** forward-fill 적용된 원천 행 (디버그/그리드용) */
  rows: SourceRow[];
  warnings: ParseWarning[];
  /** 데이터 행 수 (헤더 제외, 빈 행 제외) */
  totalDataRows: number;
}

// ── 헤더 매칭 ────────────────────────────────────────────────────────────────

/** 열 헤더(공백 제거) → SourceRow 필드. '납입기간(년)' 류는 접두 일치로 처리. */
const HEADER_FIELDS: ReadonlyArray<readonly [string, keyof SourceRow]> = [
  ["회사명", "insurer"],
  ["상품명", "productName"],
  ["구분", "role"],
  ["보험시기", "startDate"],
  ["보험종기", "endDate"],
  ["납입주기", "payCycle"],
  ["납입기간", "payYears"],
  ["납입보험료", "premiumWon"],
  ["담보명", "riderName"],
  ["보장명", "coverageName"],
  ["상태", "coverageStatus"],
  ["가입금액", "amountManwon"],
];

/** 필수 열 — 없으면 양식 불일치로 판단해 즉시 에러 */
const REQUIRED_HEADERS = ["회사명", "보장명", "가입금액"] as const;

export class SourceFormatError extends Error {}

// ── 셀 해석 헬퍼 ─────────────────────────────────────────────────────────────

function cellText(v: SourceCell): string {
  if (v === null || v === undefined) return "";
  if (v instanceof Date) return formatDateLocal(v);
  return String(v).trim();
}

function formatDateLocal(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** 엑셀 직렬값(1900 체계) → YYYY-MM-DD (UTC 기준 계산으로 TZ 드리프트 회피) */
function excelSerialToDate(serial: number): string {
  const ms = Date.UTC(1899, 11, 30) + Math.round(serial) * 86_400_000;
  const d = new Date(ms);
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** 날짜 셀: Date 인스턴스 / 엑셀 직렬값 / 문자열 모두 YYYY-MM-DD 로 통일 */
function cellDate(v: SourceCell): string | undefined {
  if (v === null || v === undefined || v === "") return undefined;
  if (v instanceof Date) return formatDateLocal(v);
  if (typeof v === "number" && Number.isFinite(v) && v > 59) return excelSerialToDate(v);
  const s = String(v).trim();
  return s || undefined;
}

/** 금액 셀: 숫자 또는 "1,000" 형 문자열 → number. 해석 불가 시 null. */
function cellNumber(v: SourceCell): number | null {
  if (v === null || v === undefined || v === "") return null;
  if (typeof v === "number") return Number.isFinite(v) ? v : null;
  if (v instanceof Date || typeof v === "boolean") return null;
  const s = String(v).replace(/[,\s원]/g, "");
  if (!s || !/^-?\d+(\.\d+)?$/.test(s)) return null;
  return parseFloat(s);
}

// ── 1) 매트릭스 → SourceRow[] (헤더 탐지 + 병합셀 forward-fill) ──────────────

interface HeaderInfo {
  rowIndex: number;
  columnOf: Partial<Record<keyof SourceRow, number>>;
}

function findHeader(matrix: SourceMatrix): HeaderInfo {
  const scanLimit = Math.min(matrix.length, 10);
  for (let r = 0; r < scanLimit; r++) {
    const row = matrix[r] ?? [];
    const texts = row.map((c) => cellText(c).replace(/\s+/g, ""));
    if (!texts.some((t) => t === "회사명") || !texts.some((t) => t === "보장명")) continue;

    const columnOf: Partial<Record<keyof SourceRow, number>> = {};
    texts.forEach((t, idx) => {
      if (!t) return;
      for (const [prefix, field] of HEADER_FIELDS) {
        if (columnOf[field] === undefined && t.startsWith(prefix)) {
          columnOf[field] = idx;
          break;
        }
      }
    });

    const missing = REQUIRED_HEADERS.filter(
      (h) => !HEADER_FIELDS.some(([p, f]) => p === h && columnOf[f] !== undefined),
    );
    if (missing.length > 0) {
      throw new SourceFormatError(`원천자료 필수 열 누락: ${missing.join(", ")} — 양식을 확인해 주세요.`);
    }
    return { rowIndex: r, columnOf };
  }
  throw new SourceFormatError(
    "원천자료 헤더 행(회사명·보장명 열)을 찾지 못했습니다. 헤더 2행 양식의 엑셀인지 확인해 주세요.",
  );
}

function isEmptyRow(row: ReadonlyArray<SourceCell>): boolean {
  return row.every((c) => cellText(c) === "");
}

/**
 * SheetJS 매트릭스 → forward-fill 된 SourceRow[].
 * 회사명·상품명 병합셀(아래 행 빈 값)은 직전 값으로 채우고,
 * 계약 메타(보험시기/종기/납입주기/기간/보험료)도 같은 계약 블록 안에서 전파한다.
 */
export function matrixToSourceRows(matrix: SourceMatrix): { rows: SourceRow[]; headerRowIndex: number } {
  const header = findHeader(matrix);
  const col = header.columnOf;
  const rows: SourceRow[] = [];

  let fill: Partial<SourceRow> = {};

  for (let r = header.rowIndex + 1; r < matrix.length; r++) {
    const raw = matrix[r] ?? [];
    if (isEmptyRow(raw)) continue;

    const at = (f: keyof SourceRow): SourceCell =>
      col[f] === undefined ? undefined : raw[col[f] as number];

    const rawInsurer = cellText(at("insurer"));
    const rawProduct = cellText(at("productName"));
    // 새 계약 블록 시작: 회사명 또는 상품명 셀에 실제 값이 있는 행 (병합셀 패턴)
    if (rawInsurer || rawProduct) {
      fill = {
        insurer: rawInsurer || fill.insurer,
        productName: rawProduct || undefined,
      };
    }

    const startDate = cellDate(at("startDate")) ?? fill.startDate;
    const endDate = cellDate(at("endDate")) ?? fill.endDate;
    const payCycle = cellText(at("payCycle")) || fill.payCycle;
    const payYears = cellText(at("payYears")) || fill.payYears;
    const premiumWon = cellNumber(at("premiumWon")) ?? fill.premiumWon;
    fill = { ...fill, startDate, endDate, payCycle, payYears, premiumWon };

    const amount = cellNumber(at("amountManwon"));
    rows.push({
      insurer: fill.insurer,
      productName: fill.productName,
      role: cellText(at("role")) || undefined,
      startDate,
      endDate,
      payCycle,
      payYears,
      premiumWon: premiumWon ?? undefined,
      riderName: cellText(at("riderName")) || undefined,
      coverageName: cellText(at("coverageName")) || undefined,
      coverageStatus: cellText(at("coverageStatus")) || undefined,
      amountManwon: amount === null ? undefined : amount,
      // 경고 표시용 원본 행 번호(1-base)
      sourceRowNo: r + 1,
    } as SourceRow & { sourceRowNo: number });
  }
  return { rows, headerRowIndex: header.rowIndex };
}

// ── 2) SourceRow[] → Contract[] (BOHUMFIT-041 시그니처 연결) ─────────────────

/** 담보 상태가 비분표 제외 대상인지 (해지·실효 등) */
const INACTIVE_STATUS_RE = /해지|실효|소멸|취소|만기/;

function rowNoOf(row: SourceRow): number {
  const n = (row as SourceRow & { sourceRowNo?: number }).sourceRowNo;
  return typeof n === "number" ? n : 0;
}

/** 계약 경계 식별 키 — 같은 키가 연속되는 행을 한 계약으로 묶는다. */
function contractKey(row: SourceRow): string {
  return [row.insurer ?? "", row.productName ?? "", row.startDate ?? "", row.payYears ?? ""].join("|");
}

export function parseSourceRowsDetailed(rows: readonly SourceRow[]): {
  contracts: Contract[];
  warnings: ParseWarning[];
} {
  const contracts: Contract[] = [];
  const warnings: ParseWarning[] = [];

  let current: Contract | null = null;
  let currentKey = "";
  let premiumSeen: number | undefined;

  const warn = (row: SourceRow, reason: string) => {
    warnings.push({
      rowNo: rowNoOf(row),
      reason,
      insurer: row.insurer,
      productName: row.productName,
      coverageName: row.coverageName,
    });
  };

  for (const row of rows) {
    if (!row.insurer && !current) {
      warn(row, "회사명 없는 행 — 계약에 연결하지 못했습니다.");
      continue;
    }
    const key = contractKey(row);
    if (!current || key !== currentKey) {
      current = {
        id: `ct${contracts.length + 1}`,
        insurer: row.insurer ?? "(회사 미상)",
        productName: row.productName,
        startDate: row.startDate,
        endDate: row.endDate,
        payCycle: row.payCycle,
        payYears: row.payYears,
        premiumWon: row.premiumWon ?? 0,
        coverages: [],
      };
      contracts.push(current);
      currentKey = key;
      premiumSeen = row.premiumWon;
    } else if (
      row.premiumWon !== undefined &&
      premiumSeen !== undefined &&
      row.premiumWon !== premiumSeen
    ) {
      warn(row, `계약 내 납입보험료가 행마다 다릅니다(${premiumSeen.toLocaleString()} vs ${row.premiumWon.toLocaleString()}) — 첫 값을 사용합니다.`);
      premiumSeen = row.premiumWon; // 동일 경고 반복 방지
    } else if (current.premiumWon === 0 && row.premiumWon !== undefined && row.premiumWon > 0) {
      // 첫 행에 보험료가 비어 있던 계약 — 뒤 행 값으로 보충
      current.premiumWon = row.premiumWon;
      premiumSeen = row.premiumWon;
    }

    // 담보 행 검증 — 실패 행은 버리지 않고 경고로 보존
    if (!row.coverageName) {
      warn(row, "보장명이 비어 있어 비분표에 반영하지 못했습니다.");
      continue;
    }
    if (row.amountManwon === undefined) {
      warn(row, "가입금액을 해석하지 못해 비분표에 반영하지 못했습니다.");
      continue;
    }
    const status = (row.coverageStatus ?? "").trim();
    if (status && INACTIVE_STATUS_RE.test(status)) {
      warn(row, `담보 상태 '${status}' — 유효 보장이 아니어서 비분표에서 제외했습니다.`);
      continue;
    }
    if (status && status !== "정상" && status !== "유지") {
      warn(row, `담보 상태 '${status}' — 정상으로 간주해 포함했습니다. 확인해 주세요.`);
    }

    const coverage: ContractCoverage = {
      name: row.coverageName,
      amountManwon: row.amountManwon,
    };
    current.coverages.push(coverage);
  }

  return { contracts, warnings };
}

/** BOHUMFIT-041 coverageMapping.parseSourceRows 와 동일 시그니처 (실구현). */
export function parseSourceRows(rows: readonly SourceRow[]): Contract[] {
  return parseSourceRowsDetailed(rows).contracts;
}

/** SheetJS 매트릭스 → 계약/경고 일괄 파싱 (페이지 진입점). */
export function parseSourceMatrix(matrix: SourceMatrix): SourceParseResult {
  const { rows } = matrixToSourceRows(matrix);
  const { contracts, warnings } = parseSourceRowsDetailed(rows);
  return { contracts, rows, warnings, totalDataRows: rows.length };
}

// ── 3) 수동 배정 (2단계 매핑 확인 — 세션 내 한정, 저장 없음) ─────────────────

/** 수동 배정에서 '제외' 선택값 */
export const MANUAL_EXCLUDE = "__exclude__";

interface CategoriesFileShape {
  mappings: Record<string, string>;
}

const MAPPINGS = (rawCategoriesJson as CategoriesFileShape).mappings;

/** 카테고리(또는 종수술 그룹) → 사전에 등록된 대표 보장명 (수동 배정 시 이름 재작성용) */
const CANONICAL_NAME_BY_TARGET: Readonly<Record<string, string>> = (() => {
  const out: Record<string, string> = {};
  for (const [name, target] of Object.entries(MAPPINGS)) {
    if (out[target] === undefined) out[target] = name;
  }
  return out;
})();

export interface AssignableTarget {
  value: string;
  label: string;
}

/**
 * 수동 배정 가능한 타깃 목록 — 36행 중 보험료 행 제외, 일반종수술 1~5종은
 * 그룹 1개 항목(자동셋팅)으로 제공한다. '제외' 옵션 포함.
 */
export function listAssignableTargets(): AssignableTarget[] {
  const targets: AssignableTarget[] = [];
  let surgeryAdded = false;
  for (const c of COVERAGE_CATEGORIES) {
    if (c.kind === "premium") continue;
    if (c.group === GENERAL_SURGERY_GROUP) {
      if (!surgeryAdded) {
        targets.push({ value: GENERAL_SURGERY_GROUP, label: "일반종수술 (1~5종 자동셋팅)" });
        surgeryAdded = true;
      }
      continue;
    }
    targets.push({ value: c.id, label: c.label });
  }
  targets.push({ value: MANUAL_EXCLUDE, label: "제외 (비분표 미반영)" });
  return targets;
}

/**
 * 수동 배정 적용 — 순수 함수.
 * assignments: normalizeCoverageName(보장명) → 카테고리 id | 종수술 그룹 | MANUAL_EXCLUDE.
 * 배정된 담보는 해당 타깃의 대표 보장명으로 이름을 재작성해 041 사전 매핑을 그대로 태운다
 * (lib 수정 없이 연결 — 산식/매핑 로직 재구현 아님). 제외는 담보를 뺀다.
 */
export function applyManualAssignments(
  contracts: readonly Contract[],
  assignments: Readonly<Record<string, string>>,
): Contract[] {
  return contracts.map((ct) => ({
    ...ct,
    coverages: ct.coverages.flatMap((cov): ContractCoverage[] => {
      if (mapCoverageName(cov.name) !== null) return [{ ...cov }]; // 자동 매핑 우선
      const target = assignments[normalizeCoverageName(cov.name)];
      if (!target) return [{ ...cov }]; // 미배정 — unmapped 로 유지(드롭 금지)
      if (target === MANUAL_EXCLUDE) return [];
      const canonical = CANONICAL_NAME_BY_TARGET[target];
      if (!canonical) return [{ ...cov }]; // 알 수 없는 타깃 — 안전하게 원본 유지
      return [{ ...cov, name: canonical }];
    }),
  }));
}
