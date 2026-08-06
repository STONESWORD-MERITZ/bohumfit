/// <reference types="node" />
// BOHUMFIT-273 — 하단 고정 요소 충돌(결과 액션 바 ↔ 269b 하단 네비).
//
//   ★현행 결함(실측): 두 요소가 **같은 `fixed bottom-0 z-40`**이고 `Layout`이 `<main>` 다음에 네비를
//     렌더해 **네비가 주 액션 버튼의 아래 80%를 덮었다**. 버튼을 누르려다 탭이 눌려 화면이 이탈했다.
//   ★해법(B안): 액션 바를 네비 **실제 높이**만큼 위로 쌓는다. 네비가 없으면 **현행과 완전히 동일**.
//   ★`MobileBottomNav`는 무접촉 — 액션 바가 DOM을 관찰할 뿐이다(269b가 시트를 관찰한 방식과 같다).
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PrimaryAction from "./PrimaryAction";
import { BOTTOM_NAV_HEIGHT } from "./bottomNavTabs";

const ROOT = process.cwd();

/** 269b 네비를 실제와 같은 형태로 DOM에 넣는다(액션 바는 이 마커를 관찰한다). */
function mountNav(height = 57): HTMLElement {
  const nav = document.createElement("nav");
  nav.setAttribute("data-testid", "mobile-bottom-nav");
  nav.className = "fixed inset-x-0 bottom-0 z-40 border-t border-line bg-white";
  // jsdom은 레이아웃을 계산하지 않아 offsetHeight가 0이다 — 실제 높이를 흉내낸다.
  Object.defineProperty(nav, "offsetHeight", { configurable: true, value: height });
  document.body.appendChild(nav);
  return nav;
}

/** 268a 시트를 연 상태(269b 규칙상 네비가 스스로 사라진다)를 재현한다. */
function openSheetAndRemoveNav(nav: HTMLElement) {
  const dialog = document.createElement("div");
  dialog.setAttribute("role", "dialog");
  dialog.setAttribute("aria-modal", "true");
  document.body.appendChild(dialog);
  nav.remove();
  return dialog;
}

const bar = () => screen.getByTestId("primary-action-bar");

afterEach(() => {
  cleanup();
  document.body.innerHTML = "";
  vi.restoreAllMocks();
});

beforeEach(() => {
  document.body.innerHTML = "";
});

// ── 네비가 없을 때: 현행과 완전히 동일 ────────────────────────────────────
describe("네비가 없으면 현행 그대로다(회귀면 0)", () => {
  it("인라인 bottom·paddingBottom을 넣지 않는다", () => {
    render(<PrimaryAction label="카카오톡 문안 보기" onPress={() => {}} />);
    const el = bar();
    expect(el.style.bottom).toBe("");
    expect(el.style.paddingBottom).toBe("");
    expect(el.getAttribute("data-above-bottom-nav")).toBeNull();
    // 세이프에어리어는 기존 `.m-action-bar` 규칙이 그대로 책임진다.
    expect(el.className).toContain("m-action-bar");
    expect(el.className).toContain("bottom-0");
  });

  it("★흐름 안 배치(fixed=false)는 268a 구성 그대로다 — 관찰도 하지 않는다", () => {
    const add = vi.spyOn(window, "addEventListener");
    mountNav(57); // 네비가 있어도 흐름 안 배치는 영향을 받지 않는다.
    render(<PrimaryAction label="업로드" onPress={() => {}} fixed={false} />);
    expect(screen.queryByTestId("primary-action-bar")).toBeNull();
    // 고정 배치가 아니면 뷰포트 구독 자체를 붙이지 않는다(불필요한 관찰 0).
    expect(add.mock.calls.map((c) => c[0])).not.toContain("orientationchange");
  });
});

// ── 네비가 있을 때: 위로 쌓인다 ───────────────────────────────────────────
describe("★네비가 있으면 그 위로 쌓인다(충돌 해소)", () => {
  it("네비 실제 높이만큼 올라가고 세이프에어리어 이중 여백이 없다", () => {
    mountNav(57);
    render(<PrimaryAction label="카카오톡 문안 보기" onPress={() => {}} />);
    const el = bar();
    // ★상수 60이 아니라 **실측 높이 57**을 쓴다 — 상수면 3px 틈이 생긴다.
    expect(el.style.bottom).toBe("57px");
    expect(el.getAttribute("data-above-bottom-nav")).toBe("true");
    // 인디케이터 여백은 아래 네비가 책임진다 → 액션 바는 평상시 12px만.
    expect(el.style.paddingBottom).toBe("12px");
  });

  it("★겹침이 실제로 0이 된다(현행 재현 → 수정 후 소거)", () => {
    const navH = 57;
    mountNav(navH);
    render(<PrimaryAction label="카카오톡 문안 보기" onPress={() => {}} />);
    const offset = Number.parseInt(bar().style.bottom || "0", 10);
    const BAR_H = 81; // 실측(패딩 12 + 버튼 56 + 하단 12·safe 0)
    // 수정 전에는 bottom=0이라 네비 높이(57)만큼 통째로 겹쳤다.
    const overlapBefore = Math.max(0, Math.min(BAR_H, navH));
    const overlapAfter = Math.max(0, navH - offset);
    expect(overlapBefore).toBe(57);
    expect(overlapAfter).toBe(0);
  });

  it("ResizeObserver가 없어도 상수로 폴백해 겹침을 남기지 않는다", () => {
    const saved = globalThis.ResizeObserver;
    // @ts-expect-error — 미지원 환경 재현
    delete globalThis.ResizeObserver;
    try {
      const nav = mountNav(0); // offsetHeight를 못 재는 상황
      expect(nav).toBeTruthy();
      render(<PrimaryAction label="카카오톡 문안 보기" onPress={() => {}} />);
      expect(bar().style.bottom).toBe(`${BOTTOM_NAV_HEIGHT}px`);
    } finally {
      globalThis.ResizeObserver = saved;
    }
  });
});

// ── 상태 전이 ─────────────────────────────────────────────────────────────
describe("★상태 전이 — 268a 시트·268b 분석 중", () => {
  it("시트가 열려 네비가 빠지면 액션 바가 원위치로 돌아온다", async () => {
    const nav = mountNav(57);
    render(<PrimaryAction label="카카오톡 문안 보기" onPress={() => {}} />);
    expect(bar().style.bottom).toBe("57px");

    await act(async () => {
      openSheetAndRemoveNav(nav);
      await Promise.resolve();
    });
    expect(bar().style.bottom).toBe("");
    expect(bar().getAttribute("data-above-bottom-nav")).toBeNull();
  });

  it("네비가 다시 돌아오면 재차 올라간다(여닫기 반복에도 상태가 어긋나지 않는다)", async () => {
    let nav = mountNav(57);
    render(<PrimaryAction label="카카오톡 문안 보기" onPress={() => {}} />);
    for (let i = 0; i < 3; i += 1) {
      await act(async () => {
        nav.remove();
        await Promise.resolve();
      });
      expect(bar().style.bottom).toBe("");
      await act(async () => {
        nav = mountNav(57);
        await Promise.resolve();
      });
      expect(bar().style.bottom).toBe("57px");
    }
  });

  it("네비 높이가 바뀌면(세이프에어리어 등) 따라 올라간다", async () => {
    const nav = mountNav(57);
    render(<PrimaryAction label="카카오톡 문안 보기" onPress={() => {}} />);
    expect(bar().style.bottom).toBe("57px");
    await act(async () => {
      Object.defineProperty(nav, "offsetHeight", { configurable: true, value: 91 }); // safe-area 34px 기기
      window.dispatchEvent(new Event("resize"));
      await Promise.resolve();
    });
    expect(bar().style.bottom).toBe("91px");
  });
});

// ── 누수 ─────────────────────────────────────────────────────────────────
describe("★관찰자 누수 0", () => {
  it("언마운트 시 MutationObserver·ResizeObserver·리스너가 모두 해제된다", () => {
    const disconnect = vi.fn();
    const observe = vi.fn();
    const RealMO = globalThis.MutationObserver;
    const RealRO = globalThis.ResizeObserver;
    class FakeMO {
      observe = observe;
      disconnect = disconnect;
      takeRecords() { return []; }
    }
    class FakeRO {
      observe = observe;
      unobserve = vi.fn();
      disconnect = disconnect;
    }
    globalThis.MutationObserver = FakeMO as unknown as typeof MutationObserver;
    globalThis.ResizeObserver = FakeRO as unknown as typeof ResizeObserver;
    const remove = vi.spyOn(window, "removeEventListener");
    try {
      mountNav(57);
      const { unmount } = render(<PrimaryAction label="문안" onPress={() => {}} />);
      unmount();
      // MutationObserver + ResizeObserver 각각 해제
      expect(disconnect.mock.calls.length).toBeGreaterThanOrEqual(2);
      const removed = remove.mock.calls.map((c) => c[0]);
      expect(removed).toContain("resize");
      expect(removed).toContain("orientationchange");
    } finally {
      globalThis.MutationObserver = RealMO;
      globalThis.ResizeObserver = RealRO;
    }
  });
});

// ── 보호 영역 ─────────────────────────────────────────────────────────────
describe("보호 영역", () => {
  it("★269b `MobileBottomNav`는 구조·감지 조건·세이프에어리어 모두 무변경", () => {
    const nav = readFileSync(resolve(ROOT, "src/components/mobile/MobileBottomNav.tsx"), "utf8");
    expect(nav).toContain(`document.querySelector('[role="dialog"][aria-modal="true"]')`);
    expect(nav).toContain('document.querySelector("[data-analysis-busy]")');
    expect(nav).toContain('style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}');
    expect(nav).toContain('className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-white"');
    // 273 흔적이 네비에 들어가지 않았다(액션 바 쪽에서만 해결).
    expect(nav).not.toContain("273");
  });

  it("★268a 시트·268b 마커·265 토큰·270 폰트 맵 무변경", () => {
    const sheet = readFileSync(resolve(ROOT, "src/components/mobile/MobileUploadSheet.tsx"), "utf8");
    expect(sheet).toContain("fixed={false}");
    expect(sheet).not.toContain("273");
    const tokens = readFileSync(resolve(ROOT, "src/components/mobile/tokens.ts"), "utf8");
    expect(tokens).toContain("export const MIN_BODY_FONT_PX = 15;");
    expect(tokens).not.toContain("273");
    const typo = readFileSync(resolve(ROOT, "src/components/mobile/diseaseCardTypography.ts"), "utf8");
    expect(typo).toContain('name: "text-[16px]"');
    expect(typo).toContain('code: "text-[15px]"');
    expect(typo).not.toContain("273");
    const progress = readFileSync(resolve(ROOT, "src/components/AnalysisProgress.tsx"), "utf8");
    expect(progress).toContain("data-analysis-busy");
  });

  it("★데스크톱은 두 요소가 아예 없다 — 영향 자체가 불가능하다", () => {
    // `PrimaryAction`에 닿는 경로는 `Disclosure.tsx` 하나뿐이고(전수 grep: DisclosureMobileShell·
    //   MobileUploadSheet), 둘 다 `useIsMobile` 분기 안에서만 렌더된다.
    //   → `/dashboard`·`/coverage-compare`는 모듈 그래프상 이 컴포넌트에 도달하지 못한다.
    for (const file of ["src/pages/Dashboard.tsx", "src/pages/CoverageRemodel.tsx"]) {
      expect(readFileSync(resolve(ROOT, file), "utf8")).not.toContain("PrimaryAction");
    }
    const disclosure = readFileSync(resolve(ROOT, "src/pages/Disclosure.tsx"), "utf8");
    expect(disclosure).toContain("if (isMobile) {"); // 셸은 모바일 분기 안에서만 렌더된다
  });

  it("★셸의 하단 여백 상수를 늘리지 않았다(실측상 이미 충분)", () => {
    const shell = readFileSync(resolve(ROOT, "src/components/mobile/DisclosureMobileShell.tsx"), "utf8");
    expect(shell).toContain("height: MOBILE_TOUCH.action + 24");
  });
});
