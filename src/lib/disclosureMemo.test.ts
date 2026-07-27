/// <reference types="node" />

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { buildFilteredDisclosureMemo, withDisclosureSelectionHeader, type DisclosureMemoItem } from "./disclosureMemo";
import { displayJudgmentDetail, filterDisclosureReportsByWindow, subYearsIso } from "./disclosureWindow";

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

describe("BOHUMFIT-217 display detail follows selected window", () => {
  const INPATIENT = "\uC785\uC6D0";
  const SURGERY = "\uC218\uC220";
  const SURGERY_NAME = "\uAD00\uC808\uACBD\uD558\uC218\uC220";
  const DETAIL = `10\uB144\uC774\uB0B4 ${INPATIENT}(4\uC77C)/${SURGERY}: ${SURGERY_NAME}/${INPATIENT}(9\uC77C)`;

  it("removes inpatient segments and keeps only in-window surgery detail", () => {
    const reports = {
      [Q3]: [{
        ...item("2024-10-07", "SURG"),
        latest_date: "2024-10-07",
        inpatient: 9,
        inpatient_count: 1,
        inpatient_periods: [{ start: "2024-10-07", end: "2024-10-15", days: 9, hospital: "H" }],
        surgeries: [SURGERY_NAME],
        surgery_count: 1,
        surgery_events: [{ date: "2024-10-07", hospital: "H", surgeries: [SURGERY_NAME] }],
        detail: DETAIL,
      }],
    };

    const filtered = filterDisclosureReportsByWindow(reports, "2023-07-13");
    const detail = displayJudgmentDetail(filtered[Q3][0]);

    expect(detail).toContain(`${SURGERY}: ${SURGERY_NAME}`);
    expect(detail).not.toContain(INPATIENT);
  });

  it("drops out-of-window surgery from detail and memo copy", () => {
    const reports = {
      [Q3]: [{
        ...item("2022-12-19", "OLD-SURG"),
        latest_date: "2022-12-19",
        surgeries: [SURGERY_NAME],
        surgery_count: 1,
        surgery_events: [{ date: "2022-12-19", hospital: "H", surgeries: [SURGERY_NAME] }],
        detail: DETAIL,
      }],
    };

    const filtered = filterDisclosureReportsByWindow(reports, "2023-07-13");

    expect(filtered[Q3]).toHaveLength(0);

    const memo = buildFilteredDisclosureMemo({
      productLabel: "Product",
      referenceDate: "2026-07-13",
      reports,
      cutoffIso: "2023-07-13",
      selectedYears: 3,
      productQuestionYears: 10,
    });

    expect(memo).not.toContain(SURGERY_NAME);
    expect(memo).not.toContain(DETAIL);
  });
});

// ── BOHUMFIT-251(3차): 합산 중복 제거·미특정 블록·서버-프런트 동등성 골든 ─────────
describe("BOHUMFIT-251(3차) surgery records memo parity", () => {
  type ParityFixture = {
    surgery_item: DisclosureMemoItem;
    surgery_item_expected: string;
    unassigned: { date?: string; surgery_name?: string; hospital?: string }[];
    unassigned_block_expected: string;
  };
  const fixture = JSON.parse(
    readFileSync(resolve(process.cwd(), "backend/tests/fixtures/disclosure_memo_parity_251.json"), "utf8"),
  ) as ParityFixture;

  const buildMemo = (
    reports: Record<string, DisclosureMemoItem[]>,
    unassignedSurgeries: ParityFixture["unassigned"] = [],
  ) =>
    buildFilteredDisclosureMemo({
      productLabel: "간편심사",
      referenceDate: "2026-07-27",
      reports,
      cutoffIso: "2020-01-01",
      selectedYears: 7,
      productQuestionYears: 10,
      unassignedSurgeries,
    });

  it("matches the server _kakao_item golden byte-for-byte (4경로 동등성)", () => {
    const memo = buildMemo({ [Q3]: [fixture.surgery_item] });
    // 서버(main.py _kakao_item)와 동일 골든 — backend/tests/test_disclosure_accuracy_251.py 대응.
    expect(memo).toContain(fixture.surgery_item_expected.trimEnd());
  });

  it("drops the visit aggregate from the summary line when records expand (결함 3)", () => {
    const memo = buildMemo({ [Q3]: [fixture.surgery_item] });
    expect(memo).not.toContain("통원5회");
    expect(memo.split("2023-02-05 / L0221").length - 1).toBe(1); // 건별 1회씩만 — 중복 0
  });

  it("outputs the unassigned block even when regular reports are empty (결함 2)", () => {
    const memo = buildMemo({}, fixture.unassigned);
    expect(memo).not.toContain("고지 대상 없음");
    expect(memo).toContain(fixture.unassigned_block_expected.trimEnd());
  });

  it("shows 고지 대상 없음 only when both reports and unassigned are empty", () => {
    expect(buildMemo({}, [])).toContain("고지 대상 없음");
  });

  it("window-filters surgery_records so filtered path keeps per-event lines", () => {
    const mixed: DisclosureMemoItem = {
      ...fixture.surgery_item,
      surgery_records: [
        ...(fixture.surgery_item.surgery_records ?? []),
        { date: "2019-01-01", code: "L0999", context: "통원1회", name: "옛질환", surgery_name: "옛수술", hospital: "옛병원" },
      ],
    };
    const filtered = filterDisclosureReportsByWindow({ [Q3]: [mixed] }, "2020-01-01");
    expect(filtered[Q3][0].surgery_records?.map((r) => r.date)).toEqual(["2023-02-05", "2023-02-05"]);
    const memo = buildMemo({ [Q3]: [mixed] });
    expect(memo).not.toContain("옛수술");
    expect(memo).toContain("절개술(제1범위)");
  });

  it("window-filters the unassigned block by the same cutoff", () => {
    const memo = buildMemo({}, [
      { date: "2019-01-01", surgery_name: "옛절제술", hospital: "옛병원" },
      ...fixture.unassigned,
    ]);
    expect(memo).not.toContain("옛절제술");
    expect(memo).toContain("절제술(림프절)");
  });
});
