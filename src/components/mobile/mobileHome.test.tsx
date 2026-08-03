/// <reference types="node" />
// BOHUMFIT-269a — 모바일 홈 대시보드.
//   ★핵심 계약: ①진입 카드 2종이 **기존 라우트**로만 간다 ②최근 분석에 환자명·원본 파일명이 없다
//   ③빈 상태·로딩·실패를 방치하지 않는다 ④터치 44px·주 액션 56px ⑤하단 네비 자리를 만들지 않는다(269b 범위).
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import MobileHome, { type MobileHomeRecentItem, type MobileHomeUsage } from "./MobileHome";
import { MOBILE_TOUCH } from "./tokens";

afterEach(() => cleanup());

const ROOT = process.cwd();

const recentItems: MobileHomeRecentItem[] = [
  { id: "1", label: "김OO 고객 점검", mode: "standard", created_at: "2026-08-01T10:00:00Z" },
  { id: "2", label: "간편심사 검토", mode: "easy", created_at: "2026-07-30T09:00:00Z" },
];

const usage: MobileHomeUsage = {
  unlimited: false,
  used: 3,
  limit: 5,
  left: 2,
  warn: false,
  planLabel: "최초 무료 분석",
};

const renderHome = (props: Partial<React.ComponentProps<typeof MobileHome>> = {}) =>
  render(
    <MemoryRouter>
      <MobileHome email="a@b.com" recent={recentItems} usage={usage} {...props} />
    </MemoryRouter>,
  );

describe("진입 카드 2종", () => {
  it("고지의무 분석·보장분석이 ★기존 라우트로 간다(신설 0)", () => {
    renderHome();
    const disclosure = screen.getByTestId("home-entry-disclosure");
    const coverage = screen.getByTestId("home-entry-coverage");
    expect(disclosure.getAttribute("href")).toBe("/disclosure?mode=agent");
    expect(coverage.getAttribute("href")).toBe("/coverage-compare");
    expect(disclosure.textContent).toContain("고지의무 분석");
    expect(coverage.textContent).toContain("보장분석");
  });

  it("카드 높이가 주 액션 규격(56px) 이상이다", () => {
    renderHome();
    for (const id of ["home-entry-disclosure", "home-entry-coverage"]) {
      const el = screen.getByTestId(id) as HTMLElement;
      expect(Number.parseInt(el.style.minHeight, 10)).toBeGreaterThanOrEqual(MOBILE_TOUCH.action);
    }
  });

  it("진입 카드는 정확히 2개다", () => {
    renderHome();
    expect(within(screen.getByTestId("home-entries")).getAllByRole("listitem")).toHaveLength(2);
  });
});

describe("남은 횟수 — ★표시만", () => {
  it("남은 횟수와 플랜 문구를 그대로 보여준다", () => {
    renderHome();
    const box = screen.getByTestId("home-usage");
    expect(box.textContent).toContain("2회");
    expect(box.textContent).toContain("최초 무료 분석");
    expect(box.textContent).toContain("3/5회 사용");
  });

  it("무제한이면 숫자를 만들지 않는다", () => {
    renderHome({ usage: { ...usage, unlimited: true, planLabel: "관리자 계정 · 분석 횟수 제한 없음" } });
    const box = screen.getByTestId("home-usage");
    expect(box.textContent).toContain("무제한");
    expect(box.textContent).not.toContain("회 사용");
  });

  it("로딩·실패를 방치하지 않는다", () => {
    renderHome({ usage: null });
    expect(screen.getByTestId("home-usage").textContent).toContain("불러오는 중");
    cleanup();
    renderHome({ usage: false });
    expect(screen.getByTestId("home-usage").textContent).toContain("불러오지 못했어요");
  });
});

describe("최근 분석", () => {
  it("별칭·분석 종류·시각을 보여주고 전체 보기로 이어진다", () => {
    renderHome();
    const box = screen.getByTestId("home-recent");
    expect(box.textContent).toContain("김OO 고객 점검");
    expect(box.textContent).toContain("건강체/표준체");
    expect(box.textContent).toContain("간편심사");
    expect(within(box).getByText("전체 보기").getAttribute("href")).toBe("/history");
  });

  it("★환자명·원본 파일명을 노출하지 않는다(268b 익명화 기조)", () => {
    renderHome();
    const box = screen.getByTestId("home-recent");
    // 표시 항목은 별칭·종류·시각뿐 — 파일명 확장자나 원본 파일 흔적이 없다.
    expect(box.textContent).not.toMatch(/\.pdf|\.xlsx|기본진료정보|세부진료정보|처방조제/);
  });

  it("기록이 없으면 다음 행동을 준다(빈 화면 방치 금지)", () => {
    renderHome({ recent: [] });
    const box = screen.getByTestId("home-recent");
    expect(box.textContent).toContain("아직 분석 기록이 없어요");
    expect(screen.getByTestId("home-recent-empty-cta").getAttribute("href")).toBe("/disclosure?mode=agent");
  });

  it("로딩·실패를 방치하지 않는다", () => {
    renderHome({ recent: null });
    expect(screen.getByTestId("home-recent").textContent).toContain("불러오는 중");
    cleanup();
    renderHome({ recent: false });
    expect(screen.getByTestId("home-recent").textContent).toContain("불러오지 못했어요");
  });
});

describe("★범위 계약", () => {
  // BOHUMFIT-269a: 하단 네비는 269b 범위이므로 홈 컴포넌트가 먼저 만들지 않는다.
  it("하단 네비를 만들지 않는다(269b 범위)", () => {
    const src = readFileSync(resolve(ROOT, "src/components/mobile/MobileHome.tsx"), "utf8");
    expect(src).not.toMatch(/BottomNav|TabBar|fixed inset-x-0 bottom-0/);
    const { container } = renderHome();
    expect(container.querySelector("nav")).toBeNull();
  });

  it("데이터를 스스로 불러오지 않는다(중복 fetch 0)", () => {
    const src = readFileSync(resolve(ROOT, "src/components/mobile/MobileHome.tsx"), "utf8");
    expect(src).not.toMatch(/fetch\(|useEffect/);
  });

  it("15px 미만 폰트를 쓰지 않는다", () => {
    const src = readFileSync(resolve(ROOT, "src/components/mobile/MobileHome.tsx"), "utf8");
    for (const m of src.matchAll(/text-\[(\d+)px\]/g)) {
      expect(Number(m[1])).toBeGreaterThanOrEqual(15);
    }
  });

  it("가로 스크롤·고정폭이 없다", () => {
    const { container } = renderHome();
    expect(container.querySelector('[class*="overflow-x"]')).toBeNull();
    expect(container.querySelector('[class*="min-w-["]')).toBeNull();
    expect(container.querySelector("table")).toBeNull();
  });
});
