/// <reference types="node" />
// BOHUMFIT-303 — 수술 판정 3단 표시: `수술 여부 확인` 티어(285 C-1).
//
//   ★계약: ①DiseaseCard가 확인 티어를 **실제로 렌더**한다(칩 `수술 여부 확인 N건` — 헬퍼 단위 테스트로 대체 금지)
//   ②확정(빨강)·확인(앰버) 칩 합 = 헤더 "수술 N건"(030~032) ③프런트 memoItem == 서버 _kakao_item 골든(251 4경로)
//   ④프런트 라벨 1상수 == 서버 라벨 ⑤구 payload(tier 부재)는 확정으로 폴백(누락 방향 아님).
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { buildFilteredDisclosureMemo, type DisclosureMemoItem } from "../lib/disclosureMemo";
import { SURGERY_REVIEW_LABEL, labeledSurgeryName, surgeryTierCounts } from "../lib/disclosureWindow";

vi.mock("../lib/auth-context", () => ({
  useAuth: () => ({ session: { access_token: "test-token" } }),
}));

import { DiseaseCard } from "./Disclosure";

type Fixture = {
  review_item: DisclosureMemoItem;
  review_item_expected: string;
  confirmed_item: DisclosureMemoItem;
  confirmed_item_expected: string;
  legacy_item_no_tier: DisclosureMemoItem;
  legacy_item_no_tier_expected: string;
};

const FIXTURE = JSON.parse(
  readFileSync(resolve(process.cwd(), "backend/tests/fixtures/surgery_review_parity_303.json"), "utf8"),
) as Fixture;

/** 서버 main.py SURGERY_REVIEW_LABEL과 글자 단위로 같아야 한다(4경로 동등성). */
const SERVER_MAIN = readFileSync(resolve(process.cwd(), "backend/main.py"), "utf8");

const Q3 = "3번 질문: 10년 이내 입원/수술/7회이상통원/30일이상투약";

// DiseaseCard의 SummaryItem은 DisclosureMemoItem의 상위 집합이 아니다 — 카드 필수 필드만 보강해 넘긴다.
const asCard = (it: DisclosureMemoItem) =>
  ({
    first_diagnosis_date: it.first_date ?? "",
    med_days: 0,
    inpatient_count: 0,
    hospitals: [],
    ...it,
  }) as unknown as Parameters<typeof DiseaseCard>[0]["item"];

afterEach(() => {
  cleanup();
});

describe("BOHUMFIT-303 수술 여부 확인 티어", () => {
  it("④ 프런트 라벨 상수 == 서버 라벨 상수", () => {
    expect(SURGERY_REVIEW_LABEL).toBe("수술 여부 확인");
    expect(SERVER_MAIN).toContain(`SURGERY_REVIEW_LABEL = "${SURGERY_REVIEW_LABEL}"`);
  });

  /**
   * 칩 요소 매처 — 숫자는 AnimatedNumber 자식 span(애니메이션)이라 **칩의 자기 텍스트**("수술 건"/"수술 여부 확인 건")로 찾는다.
   * 숫자 값의 정합은 ②의 surgeryTierCounts 단언이, 칩의 **실제 렌더 여부**는 여기가 고정한다(295 표준: 헬퍼 단위 테스트로 대체 금지).
   */
  const chipOwnText = (el: Element) =>
    Array.from(el.childNodes).filter((n) => n.nodeType === 3).map((n) => n.textContent ?? "").join("").replace(/\s+/g, "");
  const chipEl = (own: string) =>
    Array.from(document.querySelectorAll("span")).filter((el) => chipOwnText(el) === own);

  it("① DiseaseCard가 확인 티어 칩과 최종 건수를 실제로 렌더하고 확정 칩은 내지 않는다", async () => {
    render(<DiseaseCard item={asCard(FIXTURE.review_item)} qNum="Q3" />);
    // ★뮤테이션 ③(프런트 티어 분기 제거) 검출점 — 헬퍼가 아니라 **렌더 결과**를 본다.
    expect(chipEl("수술여부확인건").length).toBe(1);
    expect(chipEl("수술건").length).toBe(0); // 확정 0건이면 빨간 '수술 N건' 칩 없음
    expect(chipEl("수술여부확인건")[0].className).toMatch(/amber/); // 회색 강등 아님 — "직접 확인" 톤
    await waitFor(() => {
      const count = chipEl("수술여부확인건")[0].querySelector('span[aria-label="1"]');
      expect(count).not.toBeNull();
      expect(count).toHaveTextContent("1");
    });
  });

  it("① 확정 수술은 종전 그대로 빨간 '수술 N건' 칩", () => {
    render(<DiseaseCard item={asCard(FIXTURE.confirmed_item)} qNum="Q3" />);
    expect(screen.queryByText(/수술 여부 확인/)).toBeNull();
    expect(chipEl("수술건").length).toBe(1);
    expect(chipEl("수술건")[0].className).toMatch(/red/);
  });

  it("② 칩 합 = 헤더 수술 N건 (확정+확인 = surgery_count)", () => {
    for (const it of [FIXTURE.review_item, FIXTURE.confirmed_item, FIXTURE.legacy_item_no_tier]) {
      const { confirmed, review } = surgeryTierCounts(it);
      expect(confirmed + review).toBe(it.surgery_count ?? 0);
    }
    // 혼합(같은 항목 안 확정 1 + 확인 1) — 둘 다 렌더되고 합이 2.
    const mixed: DisclosureMemoItem = {
      ...FIXTURE.confirmed_item,
      surgery_count: 2,
      surgery_dates: ["2023-02-05", "2026-04-11"],
      surgeries: ["절개술(제1범위)", "인두이물제거술(단순[편도상와])"],
      surgery_review: ["인두이물제거술(단순[편도상와])"],
      surgery_records: [
        ...(FIXTURE.confirmed_item.surgery_records ?? []),
        ...(FIXTURE.review_item.surgery_records ?? []),
      ],
    };
    expect(surgeryTierCounts(mixed)).toEqual({ confirmed: 1, review: 1 });
    render(<DiseaseCard item={asCard(mixed)} qNum="Q3" />);
    expect(chipEl("수술건").length).toBe(1);        // 확정 칩
    expect(chipEl("수술여부확인건").length).toBe(1); // 확인 칩 — 둘 다 렌더(합 2 = surgery_count)
  });

  it("③ memoItem == 서버 _kakao_item 골든 (확인·확정·구 payload 3종)", () => {
    const build = (item: DisclosureMemoItem) =>
      buildFilteredDisclosureMemo({
        productLabel: "간편심사",
        referenceDate: "2026-08-22",
        reports: { [Q3]: [item] },
        cutoffIso: "2016-08-22",
        selectedYears: 10,
        productQuestionYears: 10,
        unassignedSurgeries: [],
      });
    expect(build(FIXTURE.review_item)).toContain(FIXTURE.review_item_expected.trimEnd());
    expect(build(FIXTURE.confirmed_item)).toContain(FIXTURE.confirmed_item_expected.trimEnd());
    expect(build(FIXTURE.legacy_item_no_tier)).toContain(FIXTURE.legacy_item_no_tier_expected.trimEnd());
  });

  it("⑤ 구 payload(tier·surgery_review 부재)는 확정으로 폴백", () => {
    expect(labeledSurgeryName(FIXTURE.legacy_item_no_tier, "충수절제술")).toBe("충수절제술");
    expect(labeledSurgeryName(FIXTURE.review_item, "인두이물제거술(단순[편도상와])")).toBe(
      `${SURGERY_REVIEW_LABEL}: 인두이물제거술(단순[편도상와])`,
    );
    expect(labeledSurgeryName(FIXTURE.review_item, "x", "confirmed")).toBe("x");
  });
});
