// BOHUMFIT-045: 보장분석 결과 엑셀(.xlsx) 내보내기 (브라우저 내 생성·비저장).
//
// - 화면에 이미 있는 041 집계값(전/후 columns·totals, 최종표 매핑)을 **직렬화만** 한다 — 재계산 금지.
// - xlsx(SheetJS)는 dynamic import(042 패턴) — 메인 번들 영향 최소화. 서버 미전송·디스크 비저장.
// - 최종표 행 정의(FINAL_ROWS/KEY_DISEASES)와 매핑 헬퍼를 이 모듈에서 단일 소스로 보유하고,
//   화면(FinalComparison.tsx)이 동일 정의를 import 한다 → 엑셀과 화면 양식이 항상 일치.
import {
  COVERAGE_CATEGORIES,
  type Contract,
  type ContractColumn,
} from "./coverageMapping";

export type Totals = Record<string, number | boolean>;
export type FinalRowKind = "amount" | "flag" | "premium" | "none";

export interface FinalRow {
  label: string;
  /** 합산할 041 카테고리 id (빈 배열 = lib 미분류 표시 전용 행) */
  ids: string[];
  kind: FinalRowKind;
  note?: string;
}

// ── 최종비교분석표 행 정의 (양식 순서 그대로, 약 37행) ──────────────────────
// 상해사망 = injury_death + disaster_death 합산(양식에 재해사망 행이 없어 분해 잔액 손실 방지).
// 일반입원·암입원은 lib 미분류/병합 → 표시 전용 행(값 없음).
export const FINAL_ROWS: FinalRow[] = [
  { label: "일반사망", ids: ["general_death"], kind: "amount" },
  { label: "상해사망", ids: ["injury_death", "disaster_death"], kind: "amount", note: "재해사망 포함" },
  { label: "질병사망", ids: ["disease_death"], kind: "amount" },
  { label: "상해후유장해", ids: ["injury_disability"], kind: "amount" },
  { label: "질병후유장해", ids: ["disease_disability"], kind: "amount" },
  { label: "일반암진단금", ids: ["cancer_diagnosis"], kind: "amount" },
  { label: "유사암진단금", ids: ["minor_cancer_diagnosis"], kind: "amount" },
  { label: "표적항암치료", ids: ["targeted_anticancer"], kind: "amount" },
  { label: "차세대암치료", ids: ["next_gen_anticancer"], kind: "amount" },
  { label: "암수술비", ids: ["cancer_surgery"], kind: "amount" },
  { label: "뇌혈관(초기)", ids: ["cerebrovascular_early"], kind: "amount" },
  { label: "뇌졸중(중기)", ids: ["stroke_mid"], kind: "amount" },
  { label: "뇌출혈(말기)", ids: ["cerebral_hemorrhage_late"], kind: "amount" },
  { label: "뇌혈관수술비", ids: ["cerebrovascular_surgery"], kind: "amount" },
  { label: "허혈성(초기)", ids: ["ischemic_heart_early"], kind: "amount" },
  { label: "급성심(말기)", ids: ["ami_late"], kind: "amount" },
  { label: "심혈관수술비", ids: ["cardiovascular_surgery"], kind: "amount" },
  { label: "일반종수술 1종", ids: ["general_surgery_type1"], kind: "amount" },
  { label: "일반종수술 2종", ids: ["general_surgery_type2"], kind: "amount" },
  { label: "일반종수술 3종", ids: ["general_surgery_type3"], kind: "amount" },
  { label: "일반종수술 4종", ids: ["general_surgery_type4"], kind: "amount" },
  { label: "일반종수술 5종", ids: ["general_surgery_type5"], kind: "amount" },
  { label: "상해수술", ids: ["injury_surgery"], kind: "amount" },
  { label: "질병수술", ids: ["disease_surgery"], kind: "amount" },
  { label: "일반입원", ids: [], kind: "none", note: "표준 카테고리 미분류(원천은 질병/상해입원 매핑)" },
  { label: "상해입원", ids: ["injury_hospitalization"], kind: "amount" },
  { label: "질병입원", ids: ["disease_hospitalization"], kind: "amount", note: "암입원 포함" },
  { label: "암입원", ids: [], kind: "none", note: "질병입원에 포함 — 별도 분리 불가" },
  { label: "골절진단비", ids: ["fracture_diagnosis"], kind: "amount" },
  { label: "화상진단비", ids: ["burn_diagnosis"], kind: "amount" },
  { label: "운전자특약", ids: ["driver_rider"], kind: "flag" },
  { label: "자부상치료비", ids: ["car_injury_treatment"], kind: "flag" },
  { label: "상해의료비", ids: ["injury_medical_indemnity"], kind: "flag" },
  { label: "질병의료비", ids: ["disease_medical_indemnity"], kind: "flag" },
  { label: "가족일상배상", ids: ["family_liability"], kind: "flag" },
  { label: "응급실내원비", ids: ["er_visit"], kind: "amount" },
  { label: "보험료", ids: ["premium"], kind: "premium" },
];

export const KEY_DISEASES: ReadonlyArray<{ label: string; id: string }> = [
  { label: "암", id: "cancer_diagnosis" },
  { label: "뇌 초기", id: "cerebrovascular_early" },
  { label: "뇌 중기", id: "stroke_mid" },
  { label: "뇌 말기", id: "cerebral_hemorrhage_late" },
  { label: "심장 초기", id: "ischemic_heart_early" },
  { label: "심장 말기", id: "ami_late" },
];

// ── 매핑 헬퍼 (표시·직렬화 공용, 순수) ───────────────────────────────────────
export function numOf(totals: Totals, ids: string[]): number {
  return ids.reduce((s, id) => s + (typeof totals[id] === "number" ? (totals[id] as number) : 0), 0);
}
export function flagOf(totals: Totals, ids: string[]): boolean {
  return ids.some((id) => totals[id] === true);
}
/** 방향: 1 증가 / -1 감소 / 0 동일 */
export function dir(before: number, after: number): -1 | 0 | 1 {
  return after > before ? 1 : after < before ? -1 : 0;
}

/** 납만기 표시: 납입기간(년) 우선, 없으면 보험종기(9999 = 종신) — CoverageTableView 와 동일 규칙(표시 전용) */
function payEndLabel(payYears?: string, endDate?: string): string {
  if (payYears && payYears !== "00") return `${parseInt(payYears, 10) || payYears}년`;
  if (endDate?.startsWith("9999")) return "종신";
  return endDate || "-";
}

// ── 워크북 데이터 ────────────────────────────────────────────────────────────
export type Cell = string | number | null;

export interface SideData {
  columns: ContractColumn[];
  totals: Totals;
  contracts: readonly Contract[];
}

export interface CoverageExportInput {
  before: SideData;
  after: SideData;
  memo: string;
}

/** 비분표(전/후 공용) 1시트 AOA. 숫자 셀은 number 타입으로 유지(문자열 금지). */
function bunpyoAOA(side: SideData): Cell[][] {
  const cols = side.columns;
  const endDateOf = (contractId: string) => side.contracts.find((c) => c.id === contractId)?.endDate;

  const rows: Cell[][] = [
    ["회사", ...cols.map((c) => c.insurer), "합계"],
    ["상품", ...cols.map((c) => c.productName ?? ""), ""],
    ["가입일", ...cols.map((c) => c.startDate ?? ""), ""],
    ["납만기", ...cols.map((c) => payEndLabel(c.payYears, endDateOf(c.contractId))), ""],
  ];
  for (const cat of COVERAGE_CATEGORIES) {
    if (cat.kind === "flag") {
      rows.push([
        cat.label,
        ...cols.map((c) => (c.cells[cat.id] === true ? "Y" : "")),
        side.totals[cat.id] === true ? "Y" : "",
      ]);
    } else {
      rows.push([
        cat.label,
        ...cols.map((c) => (typeof c.cells[cat.id] === "number" ? (c.cells[cat.id] as number) : 0)),
        typeof side.totals[cat.id] === "number" ? (side.totals[cat.id] as number) : 0,
      ]);
    }
  }
  return rows;
}

/** 최종비교분석표 AOA. FINAL_ROWS(화면과 동일 정의) 기준. */
function finalAOA(before: Totals, after: Totals, memo: string): Cell[][] {
  const rows: Cell[][] = [["리모델링 전", "주요보장", "리모델링 후"]];
  for (const r of FINAL_ROWS) {
    const label = r.note ? `${r.label} (${r.note})` : r.label;
    if (r.kind === "none") {
      rows.push(["", label, ""]);
    } else if (r.kind === "flag") {
      rows.push([flagOf(before, r.ids) ? "Y" : "", label, flagOf(after, r.ids) ? "Y" : ""]);
    } else {
      rows.push([numOf(before, r.ids), label, numOf(after, r.ids)]);
    }
  }
  rows.push([]);
  rows.push(["핵심 질병", "전", "후"]);
  for (const k of KEY_DISEASES) rows.push([k.label, numOf(before, [k.id]), numOf(after, [k.id])]);
  rows.push([]);
  rows.push(["특이사항(설계사 메모)"]);
  rows.push([memo || ""]);
  return rows;
}

/** 입력 → 3시트 AOA. 순수 함수(테스트용). */
export function buildSheets(input: CoverageExportInput): { name: string; aoa: Cell[][] }[] {
  return [
    { name: "비교분석표(전)", aoa: bunpyoAOA(input.before) },
    { name: "비교분석표(후)", aoa: bunpyoAOA(input.after) },
    { name: "최종비교분석표", aoa: finalAOA(input.before.totals, input.after.totals, input.memo) },
  ];
}

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

/** 파일명: 보험핏_보장분석_YYYYMMDD.xlsx (한글) */
export function coverageFileName(d: Date = new Date()): string {
  return `보험핏_보장분석_${d.getFullYear()}${pad2(d.getMonth() + 1)}${pad2(d.getDate())}.xlsx`;
}

/**
 * 워크북 생성 + 다운로드. xlsx 는 dynamic import — 호출 시점에만 로드한다.
 * @returns 생성한 파일명
 */
export async function exportCoverageXlsx(
  input: CoverageExportInput,
  fileName: string = coverageFileName(),
): Promise<string> {
  const XLSX = await import("xlsx");
  const wb = XLSX.utils.book_new();
  for (const sheet of buildSheets(input)) {
    const ws = XLSX.utils.aoa_to_sheet(sheet.aoa);
    XLSX.utils.book_append_sheet(wb, ws, sheet.name);
  }
  XLSX.writeFile(wb, fileName);
  return fileName;
}
