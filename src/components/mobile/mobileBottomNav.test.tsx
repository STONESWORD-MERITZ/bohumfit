/// <reference types="node" />
// BOHUMFIT-269b — 모바일 하단 네비게이션.
//   ★핵심 계약: ①탭은 **기존 라우트**만 ②세이프에어리어 적용 ③시트·분석 중 미표시(겹침 회피)
//   ④활성 탭 표시 ⑤데스크톱 미표시 ⑥라벨 15px 하한.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { act, cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import MobileBottomNav from "./MobileBottomNav";
import { BOTTOM_NAV_HEIGHT, BOTTOM_NAV_TABS } from "./bottomNavTabs";
import { MOBILE_TOUCH } from "./tokens";

const ROOT = process.cwd();

afterEach(() => cleanup());

const renderNav = (path = "/dashboard") =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <MobileBottomNav />
    </MemoryRouter>,
  );

/** MutationObserver 콜백은 마이크로태스크 이후에 돈다. */
async function flushObserver() {
  await act(async () => {
    await Promise.resolve();
    await new Promise((r) => setTimeout(r, 0));
  });
}

describe("탭 구성 — ★기존 라우트만", () => {
  it("4탭이고 전부 기존 경로다(라우트 신설 0)", () => {
    expect(BOTTOM_NAV_TABS).toHaveLength(4);
    const app = readFileSync(resolve(ROOT, "src/App.tsx"), "utf8");
    for (const { to } of BOTTOM_NAV_TABS) {
      const path = to.split("?")[0].replace(/^\//, "");
      // App.tsx의 라우트 정의(`path="dashboard"` 등)에 실재하는 경로인지 확인한다.
      expect(app).toContain(`path="${path}"`);
    }
  });

  it("모바일 개편이 끝난 화면 + 보험사 링크로 구성된다", () => {
    expect(BOTTOM_NAV_TABS.map((t) => t.to)).toEqual([
      "/dashboard",
      "/disclosure?mode=agent",
      "/coverage-compare",
      "/insurance-links",
    ]);
  });

  it("★덜 다듬어진 화면을 탭에 넣지 않는다(실손 계산·요금제·히스토리·자료 받기 제외)", () => {
    const paths = BOTTOM_NAV_TABS.map((t) => t.to);
    for (const excluded of ["/insurance", "/subscription", "/history", "/download-guide"]) {
      expect(paths.some((p) => p.split("?")[0] === excluded)).toBe(false);
    }
  });

  it("라벨이 짧고 15px 하한을 지킨다", () => {
    renderNav();
    for (const { label } of BOTTOM_NAV_TABS) {
      expect(label.length).toBeLessThanOrEqual(4);
      expect(screen.getByTestId(`bottom-nav-${label}`)).toBeTruthy();
    }
    const src = readFileSync(resolve(ROOT, "src/components/mobile/MobileBottomNav.tsx"), "utf8");
    for (const m of src.matchAll(/text-\[(\d+)px\]/g)) {
      expect(Number(m[1])).toBeGreaterThanOrEqual(15);
    }
  });

  it("터치 타깃이 44px 이상이다", () => {
    renderNav();
    for (const { label } of BOTTOM_NAV_TABS) {
      const tab = screen.getByTestId(`bottom-nav-${label}`) as HTMLElement;
      expect(Number.parseInt(tab.style.minHeight, 10)).toBeGreaterThanOrEqual(MOBILE_TOUCH.tap);
    }
  });
});

describe("★세이프에어리어", () => {
  it("하단 인셋을 패딩으로 흡수한다(인디케이터 없으면 0)", () => {
    // ※jsdom은 `env()`를 파싱하지 못해 인라인 style이 비어 보인다 — 소스에서 확인한다.
    //   실제 적용 여부는 프로덕션 브라우저 실측(Codex)에서 확인한다.
    const src = readFileSync(resolve(ROOT, "src/components/mobile/MobileBottomNav.tsx"), "utf8");
    expect(src).toContain('paddingBottom: "env(safe-area-inset-bottom, 0px)"');
    renderNav();
    expect(screen.getByTestId("mobile-bottom-nav").className).toContain("fixed");
  });

  it("viewport-fit=cover가 설정돼 있다(264 meta는 그대로)", () => {
    const html = readFileSync(resolve(ROOT, "index.html"), "utf8");
    expect(html).toContain("viewport-fit=cover");
    // 264 PWA 셸 구성이 살아 있는지도 함께 확인한다.
    expect(html).toContain("site.webmanifest");
    expect(html).toContain('name="theme-color"');
  });

  it("★푸터까지 네비에 가리지 않도록 Layout 페이지 끝에 하단 여백을 준다", () => {
    const layout = readFileSync(resolve(ROOT, "src/components/Layout.tsx"), "utf8");
    expect(layout).toContain("BOTTOM_NAV_HEIGHT");
    expect(layout).toContain("env(safe-area-inset-bottom");
    // Codex 실브라우저 보정: main에 여백을 두면 그 뒤 Footer 마지막 문장이 네비에 가려진다.
    // 페이지 셸(root div)의 여백이어야 Footer 뒤까지 실제 스크롤 여유가 생긴다.
    const mainBlock = layout.slice(layout.indexOf("<main"), layout.indexOf("</main>"));
    expect(mainBlock).not.toContain("paddingBottom");
    expect(layout).toContain("여백은 main이 아니라 Footer 뒤 페이지 끝에 둔다");
    expect(BOTTOM_NAV_HEIGHT).toBeGreaterThan(0);
  });
});

describe("★겹침 회피 — 시트·분석 중에는 숨는다", () => {
  it("바텀시트(role=dialog)가 열리면 네비가 사라진다", async () => {
    renderNav();
    expect(screen.getByTestId("mobile-bottom-nav")).toBeTruthy();

    const sheet = document.createElement("div");
    sheet.setAttribute("role", "dialog");
    sheet.setAttribute("aria-modal", "true");
    document.body.appendChild(sheet);
    await flushObserver();
    expect(screen.queryByTestId("mobile-bottom-nav")).toBeNull();

    sheet.remove();
    await flushObserver();
    expect(screen.getByTestId("mobile-bottom-nav")).toBeTruthy();
  });

  it("분석 진행 중에는 네비가 사라진다", async () => {
    renderNav();
    const busy = document.createElement("div");
    busy.setAttribute("data-analysis-busy", "");
    document.body.appendChild(busy);
    await flushObserver();
    expect(screen.queryByTestId("mobile-bottom-nav")).toBeNull();
    busy.remove();
    await flushObserver();
  });

  it("AnalysisProgress가 진행 마커를 달고 있다(감지 근거)", () => {
    const src = readFileSync(resolve(ROOT, "src/components/AnalysisProgress.tsx"), "utf8");
    expect(src).toContain("data-analysis-busy");
  });

  it("z-index가 시트(9998)보다 낮다", () => {
    renderNav();
    expect(screen.getByTestId("mobile-bottom-nav").className).toContain("z-40");
    const sheet = readFileSync(resolve(ROOT, "src/components/mobile/BottomSheet.tsx"), "utf8");
    expect(sheet).toContain("z-[9998]");
  });
});

describe("활성 탭 표시", () => {
  it("현재 경로의 탭만 강조된다", () => {
    renderNav("/coverage-compare");
    const active = screen.getByTestId("bottom-nav-보장분석");
    expect(active.className).toContain("text-accent-600");
    expect(screen.getByTestId("bottom-nav-홈").className).toContain("text-ink-soft");
  });

  it("쿼리스트링이 붙는 탭도 경로로 판정한다", () => {
    renderNav("/disclosure?mode=customer");
    expect(screen.getByTestId("bottom-nav-고지의무").className).toContain("text-accent-600");
  });
});

describe("★Layout 배선 — 데스크톱·비로그인 미표시", () => {
  const layout = readFileSync(resolve(ROOT, "src/components/Layout.tsx"), "utf8");

  it("모바일이고 로그인했을 때만 렌더한다", () => {
    expect(layout).toContain("const showBottomNav = isMobile && !!navUser;");
    expect(layout).toContain("{showBottomNav && <MobileBottomNav />}");
  });

  it("기존 데스크톱 NAV를 건드리지 않는다", () => {
    // 데스크톱 가로 메뉴·모바일 드롭다운이 그대로 남아 있다.
    expect(layout).toContain('aria-label="주요 메뉴"');
    expect(layout).toContain('id="bf-top-menu"');
  });

  it("nav 요소가 홈 화면 쪽에 중복 생기지 않는다(소유권 단일)", () => {
    const home = readFileSync(resolve(ROOT, "src/components/mobile/MobileHome.tsx"), "utf8");
    expect(home).not.toMatch(/<nav|BottomNav/);
  });
});

describe("가로 넘침 방지", () => {
  it("탭이 균등 분할되고 고정폭이 없다", () => {
    const { container } = renderNav();
    const list = within(screen.getByTestId("mobile-bottom-nav")).getAllByRole("listitem");
    expect(list).toHaveLength(4);
    for (const li of list) expect(li.className).toContain("flex-1");
    expect(container.querySelector('[class*="min-w-["]')).toBeNull();
    expect(container.querySelector('[class*="overflow-x"]')).toBeNull();
  });
});
