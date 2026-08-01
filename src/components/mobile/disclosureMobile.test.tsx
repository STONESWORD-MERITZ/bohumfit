/// <reference types="node" />
// BOHUMFIT-267 — 고지 결과 모바일 셸 + P2 표 가독성.
//
//   ★핵심 계약: ①질병 카드는 **기존 컴포넌트를 그대로** 통과시킨다(정보 누락 0) ②카톡 문안 문자열은
//   호출부가 만든 값 그대로다(재구성 0) ③P2 리스트는 데스크톱 표와 같은 값·순서를 15px·가로 스크롤 0으로 편다.
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { YnFlag } from "../../lib/coverageAfterDisplayCache";
import { formatCoverageAmount, formatCoverageDeltaAmount } from "../../lib/coverageFormat";
import DisclosureMobileShell, { DisclosureMobileSummary } from "./DisclosureMobileShell";
import { StageComparisonMobile, YnFlagMobile } from "./CoverageInsightMobile";
import { ToastProvider } from "../ToastContext";
import { UNDO_TOAST_ALLOWED_SCOPES } from "./tokens";

afterEach(() => cleanup());

const GROUPS = [
  { qNum: "Q1", title: "1번 질문: 3개월 이내", count: 2 },
  { qNum: "Q3", title: "3번 질문: 5년 이내", count: 3 },
];

const withToast = (node: React.ReactNode) => <ToastProvider>{node}</ToastProvider>;

describe("헤더 요약", () => {
  it("총 건수·질문별 집계·기준일·조회기간을 보여준다", () => {
    render(
      <DisclosureMobileSummary
        groups={GROUPS}
        referenceDate="2026-08-01"
        windowYears={10}
        productLabel="건강체"
        customerName="홍길동"
        fileCount={3}
      />,
    );
    const summary = screen.getByTestId("d-summary");
    expect(summary.textContent).toContain("5건"); // 2 + 3
    expect(summary.textContent).toContain("홍길동 고객");
    expect(summary.textContent).toContain("건강체");
    expect(summary.textContent).toContain("서류 3건");
    expect(summary.textContent).toContain("기준일 2026-08-01");
    expect(summary.textContent).toContain("조회기간 10년");

    // ★질문별 기간 의미를 접지 않는다 — Q 번호가 그대로 나온다.
    const badges = within(screen.getByTestId("d-summary-groups")).getAllByRole("listitem");
    expect(badges.map((b) => b.getAttribute("data-q"))).toEqual(["Q1", "Q3"]);
    expect(badges[0].textContent).toContain("2건");
    expect(badges[1].textContent).toContain("3건");
  });

  it("선택 항목이 없으면 해당 문구만 생략한다(고객명·서류 건수 optional)", () => {
    render(<DisclosureMobileSummary groups={GROUPS} windowYears={5} />);
    const summary = screen.getByTestId("d-summary");
    expect(summary.textContent).toContain("조회기간 5년");
    expect(summary.textContent).not.toContain("고객");
    expect(summary.textContent).not.toContain("서류");
  });

  it("고지 대상이 없으면 안내 문구를 보여준다", () => {
    render(<DisclosureMobileSummary groups={[]} windowYears={10} />);
    expect(screen.getByTestId("d-summary").textContent).toContain("고지 대상 기록이 없습니다");
  });
});

describe("★질병 카드는 그대로 통과한다(정보 누락 0)", () => {
  it("children으로 받은 기존 카드 마크업이 손상 없이 렌더된다", () => {
    const card = (
      <article data-testid="legacy-card">
        <span>등통증(경추 및 요추)</span>
        <span>수술 2건 · 2022-08-09 · 원문코드 M54 · 관절경하수술</span>
      </article>
    );
    render(
      withToast(
        <DisclosureMobileShell groups={GROUPS} windowYears={10} memo="문안" memoLabel="카카오 전송용 메시지">
          {card}
        </DisclosureMobileShell>,
      ),
    );
    const legacy = screen.getByTestId("legacy-card");
    expect(legacy.textContent).toContain("등통증(경추 및 요추)");
    // 251 수술 건별 상세가 그대로 남아 있다.
    expect(legacy.textContent).toContain("원문코드 M54");
    expect(legacy.textContent).toContain("관절경하수술");
  });
});

describe("★카카오톡 문안 — 문자열 동등성 + 시트", () => {
  const MEMO = "[건강체]\n1번 질문: 3개월 이내\n- 등통증 2022-08-09\n\n※ 미특정 수술 1건";

  it("시트를 열면 문안이 **한 글자도 바뀌지 않고** 그대로 보인다", () => {
    render(
      withToast(
        <DisclosureMobileShell groups={GROUPS} windowYears={10} memo={MEMO} memoLabel="카카오 전송용 메시지">
          <div />
        </DisclosureMobileShell>,
      ),
    );
    expect(screen.queryByTestId("d-memo-text")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "카카오톡 문안 보기" }));
    expect(screen.getByTestId("d-memo-text").textContent).toBe(MEMO);
  });

  it("복사하면 클립보드에 같은 문자열이 들어가고 되돌리기 토스트가 뜬다", async () => {
    const writeText = vi.fn(async () => {});
    const readText = vi.fn(async () => "이전 클립보드");
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText, readText },
    });

    render(
      withToast(
        <DisclosureMobileShell groups={GROUPS} windowYears={10} memo={MEMO} memoLabel="카카오 전송용 메시지">
          <div />
        </DisclosureMobileShell>,
      ),
    );
    fireEvent.click(screen.getByRole("button", { name: "카카오톡 문안 보기" }));
    fireEvent.click(screen.getByRole("button", { name: "문안 복사" }));

    await waitFor(() => expect(writeText).toHaveBeenCalledWith(MEMO));
    await waitFor(() => expect(screen.getByText("카카오톡 문안을 복사했습니다.")).toBeTruthy());
    // ★되돌리기는 265 허용 범위(copy-done)에 해당한다.
    expect([...UNDO_TOAST_ALLOWED_SCOPES]).toContain("copy-done");

    // 되돌리기를 누르면 이전 클립보드로 복원한다.
    fireEvent.click(screen.getByRole("button", { name: "되돌리기" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith("이전 클립보드"));
  });

  it("문안이 비어 있으면 하단 액션을 만들지 않는다", () => {
    render(
      withToast(
        <DisclosureMobileShell groups={GROUPS} windowYears={10} memo="" memoLabel="카카오 전송용 메시지">
          <div />
        </DisclosureMobileShell>,
      ),
    );
    expect(screen.queryByRole("button", { name: "카카오톡 문안 보기" })).toBeNull();
  });
});

describe("P2 — 종합비교 모바일 리스트", () => {
  const ROWS = [
    { key: "암", label: "암" },
    { key: "뇌초기", label: "뇌 초기" },
  ];
  const BEFORE = { 암: 30_000_000, 뇌초기: 10_000_000 };
  const AFTER = { 암: 70_000_000, 뇌초기: 5_000_000 };

  it("데스크톱 표와 같은 값·순서·증감을 보여준다", () => {
    render(<StageComparisonMobile rows={ROWS} before={BEFORE} after={AFTER} />);
    const items = within(screen.getByTestId("stage-comparison-mobile")).getAllByRole("listitem");
    expect(items.map((i) => i.getAttribute("data-stage"))).toEqual(["암", "뇌초기"]);

    expect(items[0].textContent).toContain(formatCoverageAmount(BEFORE["암"]));
    expect(items[0].textContent).toContain(formatCoverageAmount(AFTER["암"]));
    expect(items[0].textContent).toContain(formatCoverageDeltaAmount(AFTER["암"] - BEFORE["암"]));
    // 감액도 같은 산식(후−전)
    expect(items[1].textContent).toContain(formatCoverageDeltaAmount(AFTER["뇌초기"] - BEFORE["뇌초기"]));
  });

  it("after가 없으면 '-'로 두고 증감은 비운다", () => {
    render(<StageComparisonMobile rows={ROWS} before={BEFORE} after={null} />);
    const items = within(screen.getByTestId("stage-comparison-mobile")).getAllByRole("listitem");
    expect(items[0].textContent).toContain("-");
  });

  it("★가로 스크롤·표·고정폭이 없고 15px 미만 폰트가 없다", () => {
    const { container } = render(<StageComparisonMobile rows={ROWS} before={BEFORE} after={AFTER} />);
    expect(container.querySelector("table")).toBeNull();
    expect(container.querySelector('[class*="overflow-x"]')).toBeNull();
    expect(container.querySelector('[class*="min-w-["]')).toBeNull();
    for (const el of Array.from(container.querySelectorAll<HTMLElement>('[class*="text-["]'))) {
      const size = /text-\[(\d+(?:\.\d+)?)px\]/.exec(el.className)?.[1];
      if (size) expect(Number(size)).toBeGreaterThanOrEqual(15);
    }
  });
});

describe("P2 — Y/N 모바일 배지 리스트", () => {
  const BEFORE: YnFlag[] = [
    { item: "운전자", value: "Y", sources: [] },
    { item: "상해실손", value: "N", sources: [] },
  ];
  const AFTER: YnFlag[] = [
    { item: "운전자", value: "Y", sources: [] },
    { item: "상해실손", value: "Y", sources: [] },
  ];

  it("항목별 전/후 Y·N을 그대로 보여준다", () => {
    render(<YnFlagMobile before={BEFORE} after={AFTER} />);
    const items = within(screen.getByTestId("yn-flags-mobile")).getAllByRole("listitem");
    expect(items.map((i) => i.getAttribute("data-yn-item"))).toEqual(["운전자", "상해실손"]);
    expect(items[1].textContent).toContain("전");
    expect(items[1].textContent).toContain("후");
    // 전 N → 후 Y 가 모두 보인다
    expect(items[1].textContent?.replace(/\s/g, "")).toContain("전N");
    expect(items[1].textContent?.replace(/\s/g, "")).toContain("후Y");
  });

  it("after가 없으면 후를 '-'로 둔다", () => {
    render(<YnFlagMobile before={BEFORE} after={null} />);
    const items = within(screen.getByTestId("yn-flags-mobile")).getAllByRole("listitem");
    expect(items[0].textContent).toContain("후 -");
  });

  it("★가로 스크롤·표·고정폭 0", () => {
    const { container } = render(<YnFlagMobile before={BEFORE} after={AFTER} />);
    expect(container.querySelector("table")).toBeNull();
    expect(container.querySelector('[class*="overflow-x"]')).toBeNull();
    expect(container.querySelector('[class*="min-w-["]')).toBeNull();
  });
});
