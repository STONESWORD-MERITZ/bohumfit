/* BOHUMFIT-236 E: 수동 담보 병합 — 표시명 "(수동)" 구분·manual 필드·대분류 합계 반영 고정. */
import { describe, expect, it } from "vitest";
import type { CoverageComparison } from "./coverageAfterDisplayCache";
import { manualRiderRowName, mergeManualRiders } from "./coverageManualRiders";

const BASE: CoverageComparison = {
  premium: {
    before_monthly: 100_000,
    after_monthly: 90_000,
    delta_monthly: -10_000,
    before_paid_total: null,
    after_paid_total: null,
    delta_paid_total: null,
  },
  coverages: [
    {
      group12: "암",
      kb_name: "일반암",
      recommended: null,
      before_value: 10_000_000,
      after_value: 10_000_000,
      before_gap: null,
      after_gap: null,
      before_status: null,
      after_status: null,
      status_change: "same",
      delta_value: 0,
      improved: false,
      worsened: false,
    },
  ],
  summary: {
    improved_count: 0,
    worsened_count: 0,
    missing_to_sufficient: 0,
    short_to_sufficient: 0,
    before_status_counts: {},
    after_status_counts: {},
    by_group12: [],
  },
  improvements: [],
  cautions: [],
};

describe("mergeManualRiders", () => {
  it("빈 목록이면 원본을 그대로 반환한다", () => {
    expect(mergeManualRiders(BASE, [])).toBe(BASE);
  });

  it("수동 담보를 '(수동)' 구분 표시·manual 필드와 함께 병합하고 원본은 불변이다", () => {
    const merged = mergeManualRiders(BASE, [
      { id: "m1", name: "2대주요치료비(뇌·심) 수술비", group12: "기타", amount: 5_000_000 },
    ]);
    expect(BASE.coverages).toHaveLength(1);
    expect(merged.coverages).toHaveLength(2);
    const row = merged.coverages[1];
    expect(row.kb_name).toBe("2대주요치료비(뇌·심) 수술비 (수동)");
    expect(row.manual).toBe(true);
    expect(row.before_value).toBe(0);
    expect(row.after_value).toBe(5_000_000);
    expect(row.delta_value).toBe(5_000_000);
    // 월납 합계 등 premium은 변경하지 않는다(보장금액만 반영).
    expect(merged.premium).toEqual(BASE.premium);
  });

  it("소속 계약을 지정하면 표시명에 계약 번호가 포함된다", () => {
    expect(
      manualRiderRowName({ id: "m2", name: "화상수술비", group12: "골절", amount: 500_000, contractIdx: "4" }),
    ).toBe("화상수술비 (수동·계약 4)");
  });

  it("대분류 합계 계산에 합류할 수 있도록 group12를 보존한다(미지정은 기타)", () => {
    const merged = mergeManualRiders(BASE, [
      { id: "m3", name: "담보", group12: "", amount: 1_000 },
      { id: "m4", name: "담보2", group12: "뇌", amount: 2_000 },
    ]);
    expect(merged.coverages[1].group12).toBe("기타");
    expect(merged.coverages[2].group12).toBe("뇌");
  });
});
