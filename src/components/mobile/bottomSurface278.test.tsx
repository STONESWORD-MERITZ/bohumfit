/// <reference types="node" />
// BOHUMFIT-278 — 하단 표면 단일화(A-F1 구형 CTA 제거 · A-F2 z층위 계약).
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PrimaryAction from "./PrimaryAction";
import { BANNER_BELOW, BOTTOM_SURFACE_Z, ACTION_BAR_BELOW } from "./bottomSurface";

const ROOT = process.cwd();
const src = (p: string) => readFileSync(resolve(ROOT, p), "utf8");
/** ★주석을 제거한 실행 코드만 검사한다(265 가드 선례) — 설명 문구가 가드를 오탐시키지 않도록. */
const codeOf = (p: string) =>
  src(p)
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "")
    .replace(/\{\/\*[\s\S]*?\*\/\}/g, "");

function mountBar(testid: string, height: number) {
  const el = document.createElement("div");
  el.setAttribute("data-testid", testid);
  Object.defineProperty(el, "offsetHeight", { configurable: true, value: height });
  document.body.appendChild(el);
  return el;
}

beforeEach(() => { document.body.innerHTML = ""; });
afterEach(() => { cleanup(); document.body.innerHTML = ""; vi.restoreAllMocks(); });

// ── A-F1 ────────────────────────────────────────────────────────────────
describe("★A-F1 — 구형 분석 CTA 제거", () => {
  const page = codeOf("src/pages/Disclosure.tsx");

  it("z-50 하단 고정 CTA가 사라졌다", () => {
    expect(page).not.toContain("fixed inset-x-0 bottom-0 z-50");
    expect(page).not.toContain("showSticky");   // 상태·스크롤 리스너까지 제거
  });

  it("★CSS 숨김 분기(md:hidden) 하단 고정 요소가 없다(266 제1원칙)", () => {
    expect(page).not.toMatch(/bottom-0[^"]*md:hidden/);
  });

  it("★모바일 분석 진입이 268a 시트 하나로 단일화됐다", () => {
    expect(page).toContain('data-testid="open-upload-sheet"');
    expect(page).toContain("onSubmit={() => void analyze()}");
    // 데스크톱 분석 버튼은 그대로 남는다.
    expect(page).toContain("onClick={analyze}");
  });

  it("★시트 게이트가 파일 선택까지 요구한다(구형 CTA보다 강하다)", () => {
    expect(page).toContain("selectedFiles.names.length > 0");
  });
});

// ── A-F2 ────────────────────────────────────────────────────────────────
describe("★A-F2 — z 층위 계약", () => {
  it("층위 순서가 정의돼 있다: 네비 < 액션 바 < 배너 < 오버레이 < 토스트", () => {
    expect(BOTTOM_SURFACE_Z.nav).toBeLessThan(BOTTOM_SURFACE_Z.action);
    expect(BOTTOM_SURFACE_Z.action).toBeLessThan(BOTTOM_SURFACE_Z.banner);
    expect(BOTTOM_SURFACE_Z.banner).toBeLessThan(BOTTOM_SURFACE_Z.overlay);
    expect(BOTTOM_SURFACE_Z.overlay).toBeLessThan(BOTTOM_SURFACE_Z.toast);
  });

  it("★업데이트 안내가 더 이상 모달·전체표 위를 덮지 않는다", () => {
    const update = codeOf("src/components/mobile/UpdatePrompt.tsx");
    expect(update).not.toContain("z-[9997]");
    expect(update).toContain("BOTTOM_SURFACE_Z.banner");
    expect(BOTTOM_SURFACE_Z.banner).toBeLessThan(9990); // 전체표
  });

  it("★설치 안내가 토큰과 오프셋을 쓴다", () => {
    const install = codeOf("src/components/InstallPrompt.tsx");
    expect(install).not.toContain("bottom-3 z-50");
    expect(install).toContain("BOTTOM_SURFACE_Z.banner");
    expect(install).toContain("useBottomSurfaceOffset(BANNER_BELOW)");
  });

  it("배너는 네비+액션 바 **둘 다** 피한다", () => {
    expect([...BANNER_BELOW]).toEqual([
      '[data-testid="mobile-bottom-nav"]',
      '[data-testid="primary-action-bar"]',
    ]);
    expect([...ACTION_BAR_BELOW]).toEqual(['[data-testid="mobile-bottom-nav"]']);
  });
});

// ── 273 무회귀 + 조합 ───────────────────────────────────────────────────
describe("★273 계약 무회귀 · 동시 출현 조합", () => {
  it("액션 바가 네비 실측 높이만큼 올라간다(57↔91 추종)", async () => {
    const nav = mountBar("mobile-bottom-nav", 57);
    render(<PrimaryAction label="문안" onPress={() => {}} />);
    const bar = screen.getByTestId("primary-action-bar");
    expect(bar.style.bottom).toBe("57px");
    await act(async () => {
      Object.defineProperty(nav, "offsetHeight", { configurable: true, value: 91 });
      window.dispatchEvent(new Event("resize"));
      await Promise.resolve();
    });
    expect(bar.style.bottom).toBe("91px");
  });

  it("★네비 + 액션 바 + 배너 3단 — 배너 오프셋이 둘의 합이다(겹침 0)", () => {
    mountBar("mobile-bottom-nav", 57);
    mountBar("primary-action-bar", 81);
    const Probe = () => {
      const offset = useOffset();
      return <div data-testid="probe" style={{ bottom: offset }} />;
    };
    render(<Probe />);
    expect(screen.getByTestId("probe").style.bottom).toBe("138px"); // 57 + 81
  });

  it("네비가 사라지면(시트 열림) 오프셋도 줄어든다", async () => {
    const nav = mountBar("mobile-bottom-nav", 57);
    render(<PrimaryAction label="문안" onPress={() => {}} />);
    expect(screen.getByTestId("primary-action-bar").style.bottom).toBe("57px");
    await act(async () => { nav.remove(); await Promise.resolve(); });
    expect(screen.getByTestId("primary-action-bar").style.bottom).toBe("");
  });

  it("★269b 네비 구조·감지 조건 무변경", () => {
    const nav = src("src/components/mobile/MobileBottomNav.tsx");
    expect(nav).toContain(`[role="dialog"][aria-modal="true"]`);
    expect(nav).toContain("data-analysis-busy");
    expect(nav).toContain('style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}');
  });
});

// 훅을 테스트 안에서 쓰기 위한 래퍼(파일 상단 import 순환 방지용 지역 선언)
import { useBottomSurfaceOffset } from "./bottomSurface";
function useOffset() { return useBottomSurfaceOffset(BANNER_BELOW); }
