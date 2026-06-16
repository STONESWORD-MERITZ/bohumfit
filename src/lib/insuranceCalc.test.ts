// BOHUMFIT-035 실손 보수적(세대 모름) 추정 + 504 산식 무회귀 회귀 — 익명 합성 입력.
import { describe, it, expect } from "vitest";
import {
  insConservativeEstimate,
  insEstimateClaim,
  insClaimPerRow,
  INS_GEN_RATES,
} from "./insuranceCalc";

const GENS = [1, 2, 3, 4, 5];

function ncOptFor(gen: number): number | null {
  const r = INS_GEN_RATES[gen];
  return r.nonCoveredOptions ? Math.max(...Object.keys(r.nonCoveredOptions).map(Number)) : null;
}

describe("insConservativeEstimate (B: 세대별 최대 공제 세대 기준)", () => {
  const cases: [number, number][] = [
    [1_000_000, 0],
    [0, 500_000],
    [1_234_567, 890_123],
    [3_000_000, 1_500_000],
  ];

  it("보수적 추정 low = 모든 세대 중 최소 환급(low)", () => {
    for (const [cov, nc] of cases) {
      const cons = insConservativeEstimate(cov, nc);
      const allLows = GENS.map((g) => insEstimateClaim(cov, g, nc, ncOptFor(g)).low);
      expect(cons.low).toBe(Math.min(...allLows));
    }
  });

  it("선택된 세대 = low가 최소인 세대(공제 가장 큰 세대)", () => {
    for (const [cov, nc] of cases) {
      const cons = insConservativeEstimate(cov, nc);
      const chosen = insEstimateClaim(cov, cons.gen, nc, ncOptFor(cons.gen));
      expect(cons.low).toBe(chosen.low);
      // 어떤 세대도 더 작은 low 를 줄 수 없음
      for (const g of GENS) {
        expect(insEstimateClaim(cov, g, nc, ncOptFor(g)).low).toBeGreaterThanOrEqual(cons.low);
      }
    }
  });

  it("보수적 추정이 어떤 단일 세대 추정보다 환급이 크지 않다(보수적=환급 작게)", () => {
    for (const [cov, nc] of cases) {
      const cons = insConservativeEstimate(cov, nc);
      for (const g of GENS) {
        const single = insEstimateClaim(cov, g, nc, ncOptFor(g));
        expect(cons.low).toBeLessThanOrEqual(single.high);
      }
    }
  });

  it("결정성: 동일 입력 2회 동일 결과", () => {
    for (const [cov, nc] of cases) {
      expect(insConservativeEstimate(cov, nc)).toEqual(insConservativeEstimate(cov, nc));
    }
  });

  it("입력 없으면(0,0) has=false", () => {
    expect(insConservativeEstimate(0, 0).has).toBe(false);
  });
});

describe("504 산식 보존 (insClaimPerRow = max(정액, 정률))", () => {
  it("정액 > 정률: 정액 공제, 정률 > 정액: 정률 공제", () => {
    // charge 100,000 · 정률 0.2 = 20,000 · 정액 30,000 → max=30,000
    expect(insClaimPerRow(100_000, 0.2, 30_000)).toMatchObject({ finalDeductible: 30_000, reimbursement: 70_000 });
    // 정액 10,000 < 정률 20,000 → max=20,000
    expect(insClaimPerRow(100_000, 0.2, 10_000)).toMatchObject({ finalDeductible: 20_000, reimbursement: 80_000 });
    // 공제 >= 진료비 → 환급 0(lowValue)
    expect(insClaimPerRow(15_000, 0.2, 20_000)).toMatchObject({ reimbursement: 0, lowValue: true });
  });
});
