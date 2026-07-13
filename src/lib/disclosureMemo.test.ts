import { describe, expect, it } from "vitest";
import { buildFilteredDisclosureMemo, withDisclosureSelectionHeader, type DisclosureMemoItem } from "./disclosureMemo";
import { filterDisclosureReportsByWindow, subYearsIso } from "./disclosureWindow";

const Q3 = "[3번질문] 5년 이내 입원·수술·통원·투약";

function item(date: string, code: string): DisclosureMemoItem {
  return {
    first_date: date,
    latest_date: date,
    display_code: code,
    code,
    name: `테스트질환 ${code}`,
    visit: 7,
    med_days: 0,
    inpatient: 0,
    inpatient_count: 0,
    inpatient_periods: [],
    surgeries: [],
    surgery_suspected: [],
    detail: "5년 이내 통원",
    hospitals: ["테스트병원"],
  };
}

describe("BOHUMFIT-215 disclosure memo window policy", () => {
  it("subtracts calendar years for the selected output window", () => {
    expect(subYearsIso("2026-07-13", 3)).toBe("2023-07-13");
    expect(subYearsIso("2024-02-29", 1)).toBe("2023-02-28");
  });

  it("filters screen/copy reports by selected years", () => {
    const reports = { [Q3]: [item("2022-07-12", "OLD"), item("2024-01-01", "NEW")] };
    const filtered = filterDisclosureReportsByWindow(reports, "2023-07-13");

    expect(filtered[Q3]).toHaveLength(1);
    expect(filtered[Q3][0].code).toBe("NEW");
  });

  it("prunes out-of-window inpatient periods and recalculates display inpatient days", () => {
    const reports = {
      [Q3]: [{
        ...item("2022-07-12", "MIX"),
        latest_date: "2025-08-06",
        inpatient: 23,
        inpatient_count: 3,
        inpatient_periods: [
          { start: "2022-12-19", end: "2022-12-28", days: 10, hospital: "오래된병원" },
          { start: "2024-10-07", end: "2024-10-15", days: 9, hospital: "최근병원" },
          { start: "2025-08-03", end: "2025-08-06", days: 4, hospital: "최근병원" },
        ],
      }],
    };

    const filtered = filterDisclosureReportsByWindow(reports, "2023-07-13");

    expect(filtered[Q3]).toHaveLength(1);
    expect(filtered[Q3][0].inpatient_periods?.map((p) => p.start)).toEqual(["2024-10-07", "2025-08-03"]);
    expect(filtered[Q3][0].inpatient).toBe(13);
    expect(filtered[Q3][0].inpatient_count).toBe(2);
  });

  it("builds copy memo with policy header and drops out-of-window items", () => {
    const reports = { [Q3]: [item("2022-07-12", "OLD"), item("2024-01-01", "NEW")] };
    const memo = buildFilteredDisclosureMemo({
      productLabel: "건강체/표준체",
      referenceDate: "2026-07-13",
      reports,
      cutoffIso: "2023-07-13",
      selectedYears: 3,
      productQuestionYears: 10,
    });

    expect(memo).toContain("가입예정상품 10년 고지형 · 선택 3년 고지");
    expect(memo).toContain("NEW");
    expect(memo).not.toContain("OLD");
  });

  it("copy memo removes old inpatient period lines inside a mixed item", () => {
    const reports = {
      [Q3]: [{
        ...item("2022-07-12", "MIX"),
        latest_date: "2025-08-06",
        inpatient: 23,
        inpatient_count: 3,
        inpatient_periods: [
          { start: "2022-12-19", end: "2022-12-28", days: 10, hospital: "오래된병원" },
          { start: "2024-10-07", end: "2024-10-15", days: 9, hospital: "최근병원" },
        ],
      }],
    };
    const memo = buildFilteredDisclosureMemo({
      productLabel: "간편심사",
      referenceDate: "2026-07-13",
      reports,
      cutoffIso: "2023-07-13",
      selectedYears: 3,
      productQuestionYears: 10,
    });

    expect(memo).toContain("2024-10-07 ~ 2024-10-15 / 입원9일");
    expect(memo).not.toContain("2022-12-19");
    expect(memo).not.toContain("입원 총 2회 · 합산 23일");
  });

  it("prefixes full backend memo when selected years is 10", () => {
    const memo = withDisclosureSelectionHeader("기존 전체 메모", 10, 10);

    expect(memo).toBe("가입예정상품 10년 고지형 · 선택 10년 고지\n\n기존 전체 메모");
  });
});
