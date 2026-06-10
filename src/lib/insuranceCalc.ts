// SURIT-029: 실손 계산 공용 미러 라이브러리.
// ⚠️ 이 파일은 Disclosure.tsx 인라인 미러 + backend/insurance(constants §4-1~4-4 / calculator)
//    와 동일한 "504조합 검증" 산식을 verbatim 추출한 것이다. 산식 재구현 금지 — 값/로직 변경 시
//    backend/insurance 및 Disclosure.tsx 와 반드시 3중 동기화. (중복 부채 해소는 별도 백로그.)

// §4-1 세대별 자기부담률 (검증 완료)
export const INS_GEN_RATES: Record<number, {
  period: string;
  covered: [number, number];
  nonCovered: [number, number];
  nonCoveredOptions?: Record<number, number>;
}> = {
  1: { period: "~2009.9", covered: [0.0, 0.2], nonCovered: [0.0, 0.2] },
  2: { period: "2009.10~2017.3", covered: [0.1, 0.2], nonCovered: [0.2, 0.2] },
  3: { period: "2017.4~2021.6", covered: [0.1, 0.2], nonCovered: [0.2, 0.3], nonCoveredOptions: { 20: 0.2, 30: 0.3 } },
  4: { period: "2021.7~2026.5", covered: [0.2, 0.2], nonCovered: [0.3, 0.3] },
  5: { period: "2026.5.6~", covered: [0.2, 0.6], nonCovered: [0.5, 0.5] },
};
export const INS_SELF_PAY_CAP = 2_000_000; // §4-2 전 세대 연 200만
export const INS_CAP_SCOPE: Record<number, "both" | "covered"> = { 1: "both", 2: "both", 3: "both", 4: "covered", 5: "covered" };
// §4-3 건보 본인부담상한제 2026 (분위 → [일반, 요양병원 120일 초과]) 단위: 원
export const INS_NHIS_CAP_2026: Record<number, [number, number]> = {
  1: [900000, 1430000], 2: [1120000, 1810000], 3: [1120000, 1810000],
  4: [1730000, 2450000], 5: [1730000, 2450000], 6: [3260000, 4040000],
  7: [3260000, 4040000], 8: [4460000, 5800000], 9: [5360000, 6980000],
  10: [8430000, 10960000],
};
export const INS_DISCLAIMER = "추정값입니다. 정확한 보험금·환급금 지급 여부와 금액은 보험사 약관·심사 및 국민건강보험공단 확인이 필요합니다. 본 안내는 보험 모집·중개·권유를 목적으로 하지 않습니다.";

// §4-4 세대별 통원 최소공제(정액) — 기관 등급별 (SURIT-028)
export const INS_MIN_DEDUCTIBLE_BY_GEN: Record<number, Record<string, number> | null> = {
  1: null,                                          // legacy
  2: { clinic: 10000, general: 15000, tertiary: 20000 },
  3: { clinic: 10000, general: 15000, tertiary: 20000 },
  4: { clinic: 10000, general: 15000, tertiary: 20000 },
  5: null,                                          // 준비중
};
export const INS_MIN_DEDUCTIBLE_DEFAULT_GRADE = "tertiary";
export const INS_GRADE_LABELS: Record<string, string> = {
  clinic: "의원", general: "종합병원", tertiary: "상급종합병원", unknown: "등급 미상(상급 기준)",
};

export function insClassifyProvider(name: string): "clinic" | "unknown" {
  const n = (name || "").replace(/[\s·ㆍ/\\&()[\]_-]+/g, "");
  return n.includes("의원") && !n.includes("병원") ? "clinic" : "unknown";
}

export function insProviderDeductible(gen: number, grade: string): number | null {
  const table = INS_MIN_DEDUCTIBLE_BY_GEN[gen];
  if (!table) return null;
  const g = grade in table ? grade : INS_MIN_DEDUCTIBLE_DEFAULT_GRADE;
  return table[g] ?? table[INS_MIN_DEDUCTIBLE_DEFAULT_GRADE];
}

export function insClaimPerRow(charge: number, copayRate: number, fixedDeductible: number) {
  const c = Math.max(0, Math.round(charge || 0));
  const pct = Math.round(c * (copayRate || 0));
  const fixed = Math.max(0, Math.round(fixedDeductible || 0));
  const finalDeductible = Math.max(fixed, pct);
  const reimbursement = Math.max(0, c - finalDeductible);
  return { charge: c, finalDeductible, reimbursement, lowValue: reimbursement <= 0 };
}

export function insWon(s: string): number {
  return Math.max(0, parseInt((s || "").replace(/[^\d]/g, "") || "0", 10));
}

export function wonToMan(won: number): string {
  if (!won || won <= 0) return "0원";
  return `약 ${Math.round(won / 10000).toLocaleString()}만원`;
}

export function insEstimateClaim(coveredSelfPay: number, gen: number, nonCovered: number, ncOption: number | null) {
  const r = INS_GEN_RATES[gen];
  const [covLo, covHi] = r.covered;
  let ncLo = r.nonCovered[0];
  let ncHi = r.nonCovered[1];
  if (ncOption != null && r.nonCoveredOptions && r.nonCoveredOptions[ncOption] != null) {
    ncLo = r.nonCoveredOptions[ncOption];
    ncHi = r.nonCoveredOptions[ncOption];
  }
  const low = Math.round(coveredSelfPay * (1 - covHi)) + Math.round(nonCovered * (1 - ncHi));
  const high = Math.round(coveredSelfPay * (1 - covLo)) + Math.round(nonCovered * (1 - ncLo));
  const has = coveredSelfPay + nonCovered > 0;
  return { low, high, has, possibility: has ? "청구 대상일 수 있음" : "청구 대상 아닐 수 있음" };
}

export function insCheckSelfPayCap(coveredShare: number, gen: number, nonCoveredShare: number) {
  const scope = INS_CAP_SCOPE[gen];
  const eligible = scope === "covered" ? coveredShare : coveredShare + nonCoveredShare;
  return {
    eligible,
    cap: INS_SELF_PAY_CAP,
    exceeded: eligible > INS_SELF_PAY_CAP,
    excess: Math.max(0, eligible - INS_SELF_PAY_CAP),
    nonCoveredExcluded: scope === "covered",
  };
}

export function insCheckNhisCap(annualCovered: number, bracket: number, nursingLongStay: boolean) {
  const pair = INS_NHIS_CAP_2026[bracket];
  const cap = nursingLongStay ? pair[1] : pair[0];
  return { cap, exceeded: annualCovered > cap, refund: Math.max(0, annualCovered - cap) };
}
