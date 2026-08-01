/// <reference types="node" />
// BOHUMFIT-266 — ★데스크톱 회귀 0 / 모바일 분기 검증.
//
//   실제 사용자 동선(동의 → 업로드 → 전후 비교 계산)을 그대로 태워 결과 화면까지 렌더한 뒤,
//   ①데스크톱에서는 모바일 마크업이 **한 노드도 없고** 기존 섹션이 전부 그대로인지
//   ②모바일에서는 1,680px 표 대신 3단 뷰가 나오는지 확인한다.
//   ★matchMedia 폴백이 데스크톱이므로, 별도 조작이 없으면 항상 기존 경로가 렌더된다.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AnalyzeResult, ContractDecision, ProposalDraft } from "../lib/coverageAfterDisplayCache";

vi.mock("../lib/auth-context", () => ({
  useAuth: () => ({ session: { access_token: "test-token" }, loading: false }),
}));

import CoverageRemodel from "./CoverageRemodel";

const fixture = JSON.parse(
  readFileSync(resolve(process.cwd(), "backend/tests/fixtures/coverage_after_parity_211.json"), "utf8"),
) as { analysis: AnalyzeResult; decisions: Record<string, ContractDecision>; proposals: ProposalDraft[] };

/** matchMedia를 원하는 폭으로 고정한다(미정의면 훅이 데스크톱으로 폴백). */
function setViewport(mobile: boolean) {
  Object.defineProperty(window, "matchMedia", {
    configurable: true,
    writable: true,
    value: (query: string) => ({
      matches: mobile,
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

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, json: async () => fixture.analysis })) as unknown as typeof fetch,
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

/** 동의 → 업로드 → 전후 비교 계산까지 태워 결과 화면을 띄운다. */
async function renderWithResult() {
  const utils = render(
    <MemoryRouter>
      <CoverageRemodel />
    </MemoryRouter>,
  );

  fireEvent.click(screen.getByLabelText("고객 본인 동의 확인"));
  const input = screen.getByLabelText("KB 보장분석 제안서 PDF 업로드") as HTMLInputElement;
  const file = new File(["%PDF-1.4"], "test.pdf", { type: "application/pdf" });
  await act(async () => {
    fireEvent.change(input, { target: { files: [file] } });
  });
  await waitFor(() => expect(screen.getByText("전후 비교 계산")).toBeTruthy());
  await act(async () => {
    fireEvent.click(screen.getByText("전후 비교 계산"));
  });
  return utils;
}

describe("★데스크톱 — 기존 화면 그대로(회귀 0)", () => {
  it("모바일 전용 마크업이 하나도 렌더되지 않는다", async () => {
    setViewport(false);
    const { container } = await renderWithResult();

    for (const testId of [
      "m-summary",
      "m-coverages",
      "m-full-table",
      "m-contract-cards",
      "swipe-card",
      "m-coverage-row",
    ]) {
      expect(screen.queryAllByTestId(testId)).toHaveLength(0);
    }
    // 모바일 컴포넌트의 흔적이 DOM 어디에도 없어야 한다.
    expect(container.querySelector("[data-testid^='m-']")).toBeNull();
  });

  it("④·⑤ 기존 섹션과 표가 모두 남아 있다", async () => {
    setViewport(false);
    const { container } = await renderWithResult();

    expect(screen.getByText("④ 최종 전 VS 후 — 특약별 보장 비교")).toBeTruthy();
    expect(screen.getByText("⑤ 최종 전 VS 후 — 회사별 보장 세부")).toBeTruthy();
    // 담보별 비교 표(680px 고정폭) — 모바일에서 2단이 대신하는 대상이다.
    //   ※"대분류별 보장 변화 요약"은 이 픽스처에서 `comparisonValueGroups`가 비어 렌더되지 않으므로
    //     검사하지 않는다(데스크톱에서도 없으니 대조 의미가 없다 — 실측으로 확인).
    expect(container.querySelector("table.min-w-\\[680px\\]")).toBeTruthy();
    // 지표 카드 3종·내보내기 동선 유지
    expect(screen.getByText("전 월납")).toBeTruthy();
    expect(screen.getByText("후 월납")).toBeTruthy();
    expect(screen.getByText("비교 엑셀 저장")).toBeTruthy();
    expect(screen.getByText("고객용 PDF 저장")).toBeTruthy();
    // ⑤ 매트릭스의 고정폭 표(가로 스크롤 UX)가 그대로 있다
    expect(container.querySelector("table.min-w-\\[720px\\]")).toBeTruthy();
    // ② 계약 카드의 해지 체크박스(데스크톱 조작 방식) 유지
    expect(screen.getAllByLabelText(/해지/).length + screen.getAllByText("해지").length).toBeGreaterThan(0);
  });
});

describe("모바일 — 3단 점진 공개로 대체", () => {
  it("1·2단이 나오고 1,680px 매트릭스 섹션은 사라진다", async () => {
    setViewport(true);
    const { container } = await renderWithResult();

    expect(screen.getByTestId("m-summary")).toBeTruthy();
    expect(screen.getByTestId("m-coverages")).toBeTruthy();
    expect(screen.getAllByTestId("m-coverage-row").length).toBeGreaterThan(0);

    // ⑤ 섹션과 데스크톱 고정폭 표가 없다(둘 다 데스크톱에서는 실재함을 위 테스트가 확인한다).
    expect(screen.queryByText("⑤ 최종 전 VS 후 — 회사별 보장 세부")).toBeNull();
    expect(container.querySelector("table.min-w-\\[720px\\]")).toBeNull();
    expect(container.querySelector("table.min-w-\\[680px\\]")).toBeNull();
    // ★모바일에 남는 표는 종합비교(560px)·Y/N(420px) 두 블록뿐이다 — 266 명세 범위 밖이라 그대로 두되,
    //   둘 다 `overflow-x-auto` 안에 있어 **문서 자체는 넘치지 않는다**(263과 같은 판정 기준).
    //   1,680px 매트릭스처럼 화면을 밀어내는 표는 남아 있지 않다.
    for (const table of Array.from(container.querySelectorAll("table"))) {
      expect(table.closest(".overflow-x-auto")).toBeTruthy();
      expect(table.className).not.toMatch(/min-w-\[(6[89]\d|7\d\d|\d{4})px\]/);
    }
  });

  it("② 계약 목록이 스와이프 카드로 바뀐다(기존 체크박스 그리드는 사라짐)", async () => {
    setViewport(true);
    await renderWithResult();
    expect(screen.getByTestId("m-contract-cards")).toBeTruthy();
    expect(screen.getAllByTestId("swipe-card").length).toBeGreaterThan(0);
  });

  it("★내보내기 동선은 모바일에서도 유지된다(268 이전까지 기능 상실 0)", async () => {
    setViewport(true);
    await renderWithResult();
    expect(screen.getByText("비교 엑셀 저장")).toBeTruthy();
    expect(screen.getByText("고객용 PDF 저장")).toBeTruthy();
  });

  it("전체 표 보기로 3단을 열고 닫을 수 있다", async () => {
    setViewport(true);
    await renderWithResult();
    expect(screen.queryByTestId("m-full-table")).toBeNull();
    fireEvent.click(screen.getByTestId("m-open-full-table"));
    expect(screen.getByTestId("m-full-table")).toBeTruthy();
    fireEvent.click(screen.getByLabelText("닫기"));
    expect(screen.queryByTestId("m-full-table")).toBeNull();
  });
});
