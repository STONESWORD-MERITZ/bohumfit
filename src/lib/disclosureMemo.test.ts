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

  // ── BOHUMFIT-294: 반복 문자열 생략(정보 삭제 아님) ──────────────────────────────
  const repeatItem: DisclosureMemoItem = {
    first_date: "2023-02-05",
    latest_date: "2024-01-07",
    display_code: "L050",
    code: "L05",
    name: "합성질환A",
    display_name: "합성질환A",
    visit: 4,
    inpatient: 0,
    inpatient_periods: [],
    hospitals: ["가나병원"],
    surgeries: ["절개술", "배농술", "절제술", "봉합술"],
    surgery_count: 4,
    surgery_records: [
      { date: "2023-02-05", code: "L050", context: "통원1회", name: "합성질환A", surgery_name: "절개술", hospital: "가나병원", co_diagnoses: [] },
      { date: "2023-07-21", code: "L050", context: "통원1회", name: "합성질환A", surgery_name: "배농술", hospital: "가나병원", co_diagnoses: [] },
      { date: "2023-11-27", code: "L050", context: "통원1회", name: "합성질환A", surgery_name: "절제술", hospital: "가나병원", co_diagnoses: [] },
      { date: "2024-01-07", code: "L050", context: "통원1회", name: "합성질환A", surgery_name: "봉합술", hospital: "가나병원", co_diagnoses: [] },
    ],
  } as DisclosureMemoItem;

  it("omits repeated code/name but keeps them in the header (294 A)", () => {
    const memo = buildMemo({ [Q3]: [repeatItem] });
    expect(memo).toContain("2023-02-05 ~ 2024-01-07 / L050 / (양방)합성질환A");
    // ★같은 값이 헤더 1 + 건별 4 = 5회 → 1회. 줄 수·날짜·수술명·병원은 그대로.
    expect(memo.split("L050").length - 1).toBe(1);
    expect(memo.split("합성질환A").length - 1).toBe(1);
    for (const [date, surgery] of [["2023-02-05", "절개술"], ["2023-07-21", "배농술"], ["2023-11-27", "절제술"], ["2024-01-07", "봉합술"]]) {
      expect(memo).toContain(`${date} / 통원1회 / ${surgery} / 가나병원`);
    }
  });

  it("keeps code/name whenever they differ from the previous line (294 — 251 원문 충실화)", () => {
    const mixed = {
      ...repeatItem,
      surgery_count: 3,
      surgery_records: [
        repeatItem.surgery_records![0],
        { date: "2023-03-10", code: "L0292", context: "통원1회", name: "합성질환B", surgery_name: "배농술", hospital: "가나병원", co_diagnoses: [] },
        { date: "2023-04-01", code: "L0292", context: "통원1회", name: "합성질환B", surgery_name: "절제술", hospital: "가나병원", co_diagnoses: [] },
      ],
    } as DisclosureMemoItem;
    const memo = buildMemo({ [Q3]: [mixed] });
    expect(memo).toContain("2023-03-10 / L0292 / 통원1회 / 합성질환B / 배농술 / 가나병원");  // 값이 바뀌면 출력
    expect(memo).toContain("2023-04-01 / 통원1회 / 절제술 / 가나병원");                      // 같으면 생략
    expect(memo.split("L0292").length - 1).toBe(1);
  });

  it("never compresses inpatient period lines (294 — 205/213 회차별 자기완결)", () => {
    const inpatientItem = {
      ...repeatItem,
      visit: 0,
      inpatient: 17,
      inpatient_periods: [
        { start: "2023-02-05", end: "2023-02-08", days: 4, hospital: "가나병원" },
        { start: "2023-03-22", end: "2023-03-27", days: 6, hospital: "가나병원" },
        { start: "2024-01-07", end: "2024-01-13", days: 7, hospital: "가나병원" },
      ],
      surgery_count: 2,
      surgery_records: [
        { date: "2023-02-05", code: "L050", context: "입원4일", name: "합성질환A", surgery_name: "절개술", hospital: "가나병원", co_diagnoses: [] },
        { date: "2023-03-22", code: "L050", context: "입원6일", name: "합성질환A", surgery_name: "배농술", hospital: "가나병원", co_diagnoses: [] },
      ],
    } as DisclosureMemoItem;
    const memo = buildMemo({ [Q3]: [inpatientItem] });
    expect(memo).toContain("2023-02-05 ~ 2023-02-08 / 입원4일 / L050 / (양방)합성질환A / 가나병원");
    expect(memo).toContain("2023-03-22 ~ 2023-03-27 / 입원6일 / L050 / (양방)합성질환A / 가나병원");  // 회차줄 무압축
    expect(memo).toContain("→ 입원 총 3회 · 합산 17일");
    expect(memo).toContain("2023-02-05 / 입원4일 / 절개술 / 가나병원");    // record 줄만 생략
    expect(memo.split("L050").length - 1).toBe(3);                        // 회차 3줄 유지
  });

  it("leaves legacy payloads without surgery_records untouched (294)", () => {
    const legacy = { ...repeatItem, surgery_records: [], surgery_count: 2, surgeries: ["절개술", "배농술"] } as DisclosureMemoItem;
    const memo = buildMemo({ [Q3]: [legacy] });
    expect(memo).toContain("2023-02-05 ~ 2024-01-07 / 통원4회 / L050 / (양방)합성질환A / 가나병원");
    expect(memo).toContain("절개술, 배농술");
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
