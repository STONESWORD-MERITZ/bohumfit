/// <reference types="node" />
// BOHUMFIT-182 — D-11 해지 즉시 미리보기 · D-12 합계형 문서 전용 배너.
//
//   ★핵심 가드: ①즉시 반영 결과가 **버튼 경유 결과와 완전히 동일**할 것(산식 무변경 증명)
//   ②배너 조건·문구는 246/247·259 확정분 그대로일 것 ③표준형 문서에서는 배너가 없을 것.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  buildAfterResult,
  keyOf,
  OVERVIEW_CANCEL_CAUTION,
  type AnalyzeResult,
  type ContractDecision,
} from "../lib/coverageAfterDisplayCache";

vi.mock("../lib/auth-context", () => ({
  useAuth: () => ({ session: { access_token: "test-token" }, loading: false }),
}));

import CoverageRemodel from "./CoverageRemodel";

const fixture = JSON.parse(
  readFileSync(resolve(process.cwd(), "backend/tests/fixtures/coverage_after_parity_211.json"), "utf8"),
) as { analysis: AnalyzeResult };

/** 골든 픽스처는 표준형이라, overview 시나리오는 **테스트 안에서만** 파생한다(원본 불변). */
function withOverviewRow(attributed: boolean): AnalyzeResult {
  const clone = JSON.parse(JSON.stringify(fixture.analysis)) as AnalyzeResult;
  clone.before.coverages = clone.before.coverages.map((coverage, index) =>
    index === 0
      ? {
          ...coverage,
          overview: true,
          // ★259 조건: by_company가 채워졌으면(귀속) 경고 대상이 아니다.
          by_company: attributed ? coverage.by_company : { "1": null, "2": null, "3": null },
        }
      : coverage,
  );
  return clone;
}

function setDesktop() {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

function stubAnalyze(analysis: AnalyzeResult) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, json: async () => analysis })) as unknown as typeof fetch,
  );
}

beforeEach(() => setDesktop());
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

/** 동의 → 업로드까지 태워 결과 화면 직전 상태를 만든다. */
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

/** 계약 카드의 해지 체크박스들(업로드 동의 체크박스는 제외). */
function cancelCheckboxes(container: HTMLElement): HTMLInputElement[] {
  return Array.from(container.querySelectorAll<HTMLInputElement>('input[type="checkbox"]')).filter(
    (box) => box.className.includes("accent-accent-700"),
  );
}

describe("★D-11 — 해지 체크 즉시 미리보기", () => {
  it("버튼을 누르지 않아도 결과가 바로 나온다", async () => {
    stubAnalyze(fixture.analysis);
    const { container } = await renderUploaded();

    // 업로드 직후에는 결과 섹션이 없다.
    expect(screen.queryByText("④ 최종 전 VS 후 — 특약별 보장 비교")).toBeNull();

    fireEvent.click(cancelCheckboxes(container)[0]);
    // ★버튼 클릭 없이 결과가 나타난다.
    expect(screen.getByText("④ 최종 전 VS 후 — 특약별 보장 비교")).toBeTruthy();
    expect(screen.getByText("⑤ 최종 전 VS 후 — 회사별 보장 세부")).toBeTruthy();
  });

  it("★즉시 반영 결과가 버튼 경유 결과와 완전히 동일하다(마크업 전체 대조)", async () => {
    stubAnalyze(fixture.analysis);

    // (A) 즉시 반영 — 체크만 한다.
    const immediate = await renderUploaded();
    fireEvent.click(cancelCheckboxes(immediate.container)[0]);
    const immediateHtml = immediate.container.innerHTML;
    cleanup();

    // (B) 버튼 경유 — 체크 후 "전후 비교 계산"을 누른다.
    const viaButton = await renderUploaded();
    fireEvent.click(cancelCheckboxes(viaButton.container)[0]);
    await act(async () => {
      fireEvent.click(screen.getByText("전후 비교 계산"));
    });
    expect(viaButton.container.innerHTML).toBe(immediateHtml);
    // 빈 화면 대조로 통과하는 것 방지
    expect(immediateHtml).toContain("④ 최종 전 VS 후 — 특약별 보장 비교");
  });

  it("★payload 자체도 동일하다(같은 함수·같은 인자 — 산식 무변경)", () => {
    const target = (fixture.analysis.before.contract_list || fixture.analysis.before.companies || [])[0];
    const decisions: Record<string, ContractDecision> = {
      [keyOf(target.idx)]: { disposition: "cancel" },
    };
    const a = buildAfterResult(fixture.analysis, decisions, []);
    const b = buildAfterResult(fixture.analysis, decisions, []);
    expect(JSON.stringify(a)).toBe(JSON.stringify(b));
    // 유지 상태와는 실제로 달라야 한다(테스트가 무의미해지지 않도록).
    expect(JSON.stringify(a)).not.toBe(JSON.stringify(buildAfterResult(fixture.analysis, {}, [])));
  });

  it("연속 토글에도 마지막 상태가 정확히 반영된다(해지 → 복원)", async () => {
    stubAnalyze(fixture.analysis);
    const { container } = await renderUploaded();
    const boxes = cancelCheckboxes(container);

    fireEvent.click(boxes[0]);
    const afterCancelHtml = container.innerHTML;
    fireEvent.click(boxes[0]); // 복원
    const afterRestoreHtml = container.innerHTML;
    expect(afterRestoreHtml).not.toBe(afterCancelHtml);

    fireEvent.click(boxes[0]); // 다시 해지 → 첫 해지 상태와 같아야 한다
    expect(container.innerHTML).toBe(afterCancelHtml);
  });

  it("★'전후 비교 계산' 버튼은 그대로 남아 있다(데스크톱 동선 유지)", async () => {
    stubAnalyze(fixture.analysis);
    await renderUploaded();
    expect(screen.getByText("전후 비교 계산")).toBeTruthy();
  });
});

describe("★D-12 — 합계형 문서 전용 배너", () => {
  it("미귀속 overview 행 + 해지면 배너가 뜨고, 나열에서는 빠진다", async () => {
    stubAnalyze(withOverviewRow(false));
    const { container } = await renderUploaded();
    fireEvent.click(cancelCheckboxes(container)[0]);

    const banner = screen.getByTestId("overview-cancel-banner");
    expect(banner.textContent).toContain("합계형 문서");
    // ★문구는 확정본 그대로다.
    expect(banner.textContent).toContain(OVERVIEW_CANCEL_CAUTION);

    // 같은 문장이 특이사항 목록에 중복으로 남아 있지 않다.
    const notes = screen.queryByTestId("special-notes");
    if (notes) expect(notes.textContent).not.toContain(OVERVIEW_CANCEL_CAUTION);
  });

  it("표준형 문서에서는 배너가 뜨지 않는다", async () => {
    stubAnalyze(fixture.analysis);
    const { container } = await renderUploaded();
    fireEvent.click(cancelCheckboxes(container)[0]);
    expect(screen.queryByTestId("overview-cancel-banner")).toBeNull();
  });

  it("★귀속된 overview 행은 배너 대상이 아니다(259 조건 그대로)", async () => {
    stubAnalyze(withOverviewRow(true));
    const { container } = await renderUploaded();
    fireEvent.click(cancelCheckboxes(container)[0]);
    expect(screen.queryByTestId("overview-cancel-banner")).toBeNull();
  });

  it("해지가 없으면 배너가 뜨지 않는다(조건 ①)", async () => {
    stubAnalyze(withOverviewRow(false));
    await renderUploaded();
    await act(async () => {
      fireEvent.click(screen.getByText("전후 비교 계산"));
    });
    expect(screen.queryByTestId("overview-cancel-banner")).toBeNull();
  });

  it("배너는 폭을 고정하지 않는다(가로 넘침 방지)", async () => {
    stubAnalyze(withOverviewRow(false));
    const { container } = await renderUploaded();
    fireEvent.click(cancelCheckboxes(container)[0]);
    const banner = screen.getByTestId("overview-cancel-banner");
    expect(banner.className).not.toMatch(/min-w-\[|w-\[\d+px\]/);
    expect(within(banner).queryByRole("table")).toBeNull();
  });
});
