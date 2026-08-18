/// <reference types="node" />
// BOHUMFIT-295b(R1) — ★화면 배선 회귀 테스트.
//
//   295는 표시 선택을 헬퍼(displayStageTotals·displayYnFlags)로 대칭화하고 buildAfterResult에
//   stale 판정을 넣어 "제안서 없으면 [후]==[전]" 불변식을 복원했다. 그러나 헬퍼 **로직**만
//   단위 테스트하면, 컴포넌트가 그 헬퍼를 실제로 쓰는지(=배선)는 검증되지 않는다 —
//   Codex 반려 실증: `CoverageRemodel`의 네 useMemo를 종전 비대칭 구현으로 되돌려도 `410 passed`.
//
//   이 파일은 **CoverageRemodel을 실제로 렌더**해 종합비교·Y/N 표시 셀을 단언한다. 헬퍼 단위
//   테스트로 대체 불가 — 대상이 "컴포넌트 → 헬퍼 배선" 그 자체다.
//
//   ★회귀 재현 픽스처의 핵심: coverages는 **V2 표시명**(구 40행 이름 미러가 조회 실패 → 0)이고,
//   서버가 내려주는 before.stage_totals·yn_flags는 **비어 있지 않다**. 종전 비대칭([후]=구 미러
//   강제 재산출)에서는 [후]가 0/N으로 무너지고, 대칭 배선에서는 서버 값(=[전])이 그대로 표시된다.
//
//   ★PII: 전부 익명 합성(담보명·회사명·인물 0). 골든 픽스처(211)에서 shape만 빌리고 값은 합성.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { type AnalyzeResult } from "../lib/coverageAfterDisplayCache";

vi.mock("../lib/auth-context", () => ({
  useAuth: () => ({ session: { access_token: "test-token" }, loading: false }),
}));

import CoverageRemodel from "./CoverageRemodel";

const MAN = 10_000;
const shape = JSON.parse(
  readFileSync(resolve(process.cwd(), "backend/tests/fixtures/coverage_after_parity_211.json"), "utf8"),
) as { analysis: AnalyzeResult };

// ★V2 회귀 재현 분석본 — shape(회사·premium·final)만 빌리고 담보·파생값은 합성으로 교체한다.
//   담보 이름은 290 이후 산출물처럼 **V2 표시명**(띄어쓰기 포함)이라 구 40행 이름 미러가 못 찾는다.
function v2Analysis(): AnalyzeResult {
  const clone = JSON.parse(JSON.stringify(shape.analysis)) as AnalyzeResult;
  clone.before.coverages = [
    { kb_name: "뇌 혈 관 질 환", kb_group: "뇌", group12: "뇌", agg: "sum", summary: 4000 * MAN, by_company: { "1": 4000 * MAN, "2": null, "3": null }, enrolled: true },
    { kb_name: "상 해/질 병 입 원", kb_group: "실 비", group12: "실 비", agg: "rep", summary: 5000 * MAN, by_company: { "1": 5000 * MAN, "2": null, "3": null }, enrolled: true },
    // 292 Phase E 결합 담보 — 비고행이라 **구 이름 그대로** 남는다(회귀 때 암 체인 오염의 통로).
    { kb_name: "항암약물방사선", kb_group: "비고", group12: "비고", agg: "sum", summary: 1410 * MAN, by_company: { "1": null, "2": 1410 * MAN, "3": null }, enrolled: true },
  ];
  // 서버 파생값(정본 · ★BOHUMFIT-298: 케스케이드 17키) — [전]은 이 값을, 대칭 배선이면 [후]도 이 값을 표시한다.
  clone.before.stage_totals = {
    뇌초기: 4000 * MAN, 뇌중기: 4000 * MAN, 뇌말기: 4000 * MAN,
    심장초기: 2000 * MAN, 심장중기: 2000 * MAN,
    "암 수 술 (레보아이 포함)": 3000 * MAN, "유사암 수술": 0,
    "다빈치(일반암)": 0, "다빈치(전립선)": 0, "다빈치(갑상선)": 0,
    "항암 약물 치료": 0, "표적 약물 치료": 0, "면역 약물 치료": 0,
    "방사선 치료": 0, "세기조절 방사선 치료": 0, "양성자 방사선 치료": 0, "중 입 자 치료": 0,
  };
  clone.before.yn_flags = [
    { item: "운전자특약", value: "N", sources: [] },
    { item: "자동차부상치료비", value: "N", sources: [] },
    { item: "가족일상배상책임", value: "N", sources: [] },
    { item: "상해실손의료비", value: "Y", sources: [{ kb_name: "상 해/질 병 입 원", summary: 5000 * MAN }] },
    { item: "질병실손의료비", value: "Y", sources: [{ kb_name: "상 해/질 병 입 원", summary: 5000 * MAN }] },
  ];
  return clone;
}

function setDesktop() {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: (query: string) => ({
      matches: false, media: query, onchange: null,
      addEventListener: () => {}, removeEventListener: () => {},
      addListener: () => {}, removeListener: () => {}, dispatchEvent: () => false,
    }),
  });
}

function stubAnalyze(analysis: AnalyzeResult) {
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => analysis })) as unknown as typeof fetch);
}

beforeEach(() => setDesktop());
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function renderUploaded() {
  const utils = render(
    <MemoryRouter>
      <CoverageRemodel />
    </MemoryRouter>,
  );
  fireEvent.click(screen.getByLabelText("고객 본인 동의 확인"));
  await act(async () => {
    fireEvent.change(screen.getByLabelText("KB 보장분석 제안서 PDF 업로드"), {
      target: { files: [new File(["%PDF-1.4"], "t.pdf", { type: "application/pdf" })] },
    });
  });
  await waitFor(() => expect(screen.getByText("전후 비교 계산")).toBeTruthy());
  return utils;
}

/** stage-comparison 표에서 라벨 행의 [전]·[후] 셀 텍스트를 읽는다. */
function stageRow(container: HTMLElement, label: string): { before: string; after: string } {
  const table = within(container).getByTestId("stage-comparison");
  const row = within(table)
    .getAllByRole("row")
    .find((tr) => within(tr).queryByText(label));
  if (!row) throw new Error(`stage row not found: ${label}`);
  // ★`→` 셀은 aria-hidden이라 접근성 트리에서 빠진다 → cells = [라벨, 전, 후, 개선]. 후 = cells[2].
  const cells = within(row).getAllByRole("cell");
  return { before: cells[1].textContent || "", after: cells[2].textContent || "" };
}

/** yn-flags 표에서 항목 행의 [전]·[후] 배지 텍스트를 읽는다. */
function ynRow(container: HTMLElement, item: string): { before: string; after: string } {
  const table = within(container).getByTestId("yn-flags");
  const row = within(table)
    .getAllByRole("row")
    .find((tr) => within(tr).queryByText(item));
  if (!row) throw new Error(`yn row not found: ${item}`);
  const cells = within(row).getAllByRole("cell");
  return { before: (cells[1].textContent || "").trim(), after: (cells[2].textContent || "").trim() };
}

function cancelCheckboxes(container: HTMLElement): HTMLInputElement[] {
  return Array.from(container.querySelectorAll<HTMLInputElement>('input[type="checkbox"]')).filter((box) =>
    box.className.includes("accent-accent-700"),
  );
}

describe("BOHUMFIT-295b(R1) — CoverageRemodel 화면 배선 회귀", () => {
  it("★제안서·해지 0이면 렌더된 [후] 종합비교·Y/N이 [전]과 같다(비대칭 배선이면 [후]가 0/N으로 무너짐)", async () => {
    stubAnalyze(v2Analysis());
    const { container } = await renderUploaded();
    // 해지·제안 0 상태에서 버튼으로 [후]를 만든다.
    await act(async () => {
      fireEvent.click(screen.getByText("전후 비교 계산"));
    });

    // 종합비교 — 뇌 초기: [전]=[후]=4,000만원(비대칭 배선이면 [후]=0원).
    const brain = stageRow(container, "뇌 초기");
    expect(brain.before).toBe("4,000만원");
    expect(brain.after).toBe(brain.before);
    expect(brain.after).not.toBe("0원");
    const heart = stageRow(container, "심장 초기");
    expect(heart.after).toBe(heart.before);
    expect(heart.after).not.toBe("0원");

    // ★BOHUMFIT-298: 암 계열 17키 표시 — 암 수술은 서버 값 3,000만이 [전]=[후]로 그대로.
    const cancerSurgery = stageRow(container, "암 수술(레보아이 포함)");
    expect(cancerSurgery.before).toBe("3,000만원");
    expect(cancerSurgery.after).toBe(cancerSurgery.before);
    // 회귀 때 비고행 1,410만이 [후] 암 체인에 들어왔었다 — 이제 암 체인 어느 행에도 1,410만은 없다.
    for (const key of ["항암 약물 치료", "표적 약물 치료", "방사선 치료"]) {
      const row = stageRow(container, key);
      expect(row.after).not.toBe("1,410만원");
    }

    // Y/N — 실손 2항목이 [전]=[후]=Y(비대칭 배선이면 [후]=N).
    for (const item of ["상해실손의료비", "질병실손의료비"]) {
      const yn = ynRow(container, item);
      expect(yn.before).toBe("Y");
      expect(yn.after).toBe("Y");
    }
  });

  it("★해지가 있으면 [후]가 [전]의 복사가 아니다(stale 판정 — 담보가 바뀌면 파생값을 버린다)", async () => {
    stubAnalyze(v2Analysis());
    const { container } = await renderUploaded();
    // 계약 1을 해지 → afterCoverages가 [전]과 달라져 stale 판정이 파생값을 버린다.
    fireEvent.click(cancelCheckboxes(container)[0]);

    const brain = stageRow(container, "뇌 초기");
    expect(brain.before).toBe("4,000만원"); // [전]은 서버 값 유지
    // [후]는 stale 판정으로 파생값이 버려져 구 미러 폴백(V2 이름 미스) → 0원. [전]의 복사가 아니다.
    expect(brain.after).not.toBe(brain.before);
    expect(brain.after).toBe("0원");
  });
});
