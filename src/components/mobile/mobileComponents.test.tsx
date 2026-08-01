// BOHUMFIT-265 — P2 공통 컴포넌트 동작 테스트(시트 개폐·배지 4단·주 액션·스와이프 임계·업데이트 안내).
//   ★적용은 266~ — 여기서는 컴포넌트 자체 계약만 검증한다.
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { fireEvent, render, screen, cleanup } from "@testing-library/react";
import BottomSheet from "./BottomSheet";
import PrimaryAction from "./PrimaryAction";
import DisclosureBadge from "./DisclosureBadge";
import SwipeActionCard from "./SwipeActionCard";
import UpdatePrompt from "./UpdatePrompt";
import { MOBILE_TOUCH, SWIPE } from "./tokens";

afterEach(() => cleanup());

describe("BottomSheet", () => {
  it("open=false면 렌더하지 않는다", () => {
    render(
      <BottomSheet open={false} onClose={() => {}} title="파일 선택">
        <p>내용</p>
      </BottomSheet>
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("배경 탭·핸들·Esc로 닫힌다(맥락 유지 — 패널 클릭은 닫지 않음)", () => {
    const onClose = vi.fn();
    render(
      <BottomSheet open onClose={onClose} title="카톡 문안" description="복사해서 보내세요">
        <p>본문</p>
      </BottomSheet>
    );
    // 패널 내부 클릭 → 닫히지 않는다
    fireEvent.click(screen.getByText("본문"));
    expect(onClose).not.toHaveBeenCalled();
    // 배경 탭 → 닫힘
    fireEvent.click(screen.getByTestId("bottom-sheet-backdrop"));
    expect(onClose).toHaveBeenCalledTimes(1);
    // 핸들 → 닫힘
    fireEvent.click(screen.getByTestId("bottom-sheet-handle"));
    expect(onClose).toHaveBeenCalledTimes(2);
    // Esc → 닫힘
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(3);
  });

  it("제목·설명이 접근성 라벨로 연결된다", () => {
    render(
      <BottomSheet open onClose={() => {}} title="내보내기" description="PDF 또는 엑셀">
        <p>x</p>
      </BottomSheet>
    );
    const dialog = screen.getByRole("dialog");
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    expect(dialog.getAttribute("aria-label")).toBe("내보내기");
    expect(screen.getByText("PDF 또는 엑셀")).toBeTruthy();
  });
});

describe("PrimaryAction", () => {
  it("주 액션 높이가 56px이고 하단 고정 바로 렌더된다", () => {
    render(<PrimaryAction label="분석 시작" onPress={() => {}} />);
    const button = screen.getByRole("button", { name: "분석 시작" });
    expect(button.style.minHeight).toBe(`${MOBILE_TOUCH.action}px`);
    expect(screen.getByTestId("primary-action-bar")).toBeTruthy();
  });

  it("진행 중에는 라벨을 바꾸고 중복 탭을 막는다(전체 화면 스피너 없음)", () => {
    const onPress = vi.fn();
    render(<PrimaryAction label="분석 시작" onPress={onPress} pending />);
    const button = screen.getByRole("button", { name: "처리 중…" });
    expect(button.getAttribute("aria-busy")).toBe("true");
    fireEvent.click(button);
    expect(onPress).not.toHaveBeenCalled();
  });
});

describe("DisclosureBadge 4단", () => {
  it("네 라벨이 확정값(10년)으로 렌더된다", () => {
    render(
      <>
        <DisclosureBadge kind="major10y" />
        <DisclosureBadge kind="minor3m" />
        <DisclosureBadge kind="review1y" />
        <DisclosureBadge kind="none" />
      </>
    );
    expect(screen.getByText("고지대상 · 10년")).toBeTruthy();
    expect(screen.getByText("고지대상 · 3개월")).toBeTruthy();
    expect(screen.getByText("검토 · 1년 재검사")).toBeTruthy();
    expect(screen.getByText("해당없음")).toBeTruthy();
  });

  it("색만으로 구분하지 않는다 — 라벨 텍스트가 항상 함께 나온다", () => {
    render(<DisclosureBadge kind="major10y" />);
    const badge = screen.getByText("고지대상 · 10년");
    expect(badge.getAttribute("data-badge")).toBe("major10y");
    expect(badge.textContent?.trim().length).toBeGreaterThan(0);
  });
});

describe("SwipeActionCard", () => {
  const swipe = (el: HTMLElement, delta: number) => {
    fireEvent.touchStart(el, { touches: [{ clientX: 200 }] });
    fireEvent.touchMove(el, { touches: [{ clientX: 200 + delta }] });
    fireEvent.touchEnd(el);
  };

  it("★임계값 미만이면 해지되지 않는다", () => {
    const onCancel = vi.fn();
    render(
      <SwipeActionCard onCancel={onCancel}>
        <p>계약 A</p>
      </SwipeActionCard>
    );
    swipe(screen.getByTestId("swipe-card"), -(SWIPE.threshold - 10));
    expect(onCancel).not.toHaveBeenCalled();
  });

  it("좌 스와이프가 임계값을 넘으면 해지된다", () => {
    const onCancel = vi.fn();
    render(
      <SwipeActionCard onCancel={onCancel}>
        <p>계약 A</p>
      </SwipeActionCard>
    );
    swipe(screen.getByTestId("swipe-card"), -(SWIPE.threshold + 10));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("해지 상태에서 우 스와이프하면 복원되고, 회색·취소선 상태로 표시된다", () => {
    const onRestore = vi.fn();
    render(
      <SwipeActionCard onCancel={() => {}} onRestore={onRestore} cancelled>
        <p>계약 A</p>
      </SwipeActionCard>
    );
    const card = screen.getByTestId("swipe-card");
    expect(card.getAttribute("data-cancelled")).toBe("true");
    expect(card.className).toContain("line-through");
    swipe(card, SWIPE.threshold + 10);
    expect(onRestore).toHaveBeenCalledTimes(1);
  });
});

describe("UpdatePrompt (SW 업데이트 안내)", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("대기 중인 새 버전이 없으면 아무것도 렌더하지 않는다", () => {
    render(<UpdatePrompt />);
    expect(screen.queryByTestId("sw-update-prompt")).toBeNull();
  });

  it("★자동 새로고침을 하지 않는다 — 사용자가 누를 때만 적용한다", async () => {
    const reload = vi.fn();
    const postMessage = vi.fn();
    const listeners: Record<string, EventListener[]> = {};
    // 대기 중인 SW가 있는 등록 객체를 흉내낸다.
    const registration = {
      waiting: { postMessage },
      installing: null,
      addEventListener: () => {},
      removeEventListener: () => {},
    };
    Object.defineProperty(navigator, "serviceWorker", {
      configurable: true,
      value: {
        controller: {},
        getRegistration: () => Promise.resolve(registration),
        addEventListener: (type: string, fn: EventListener) => {
          (listeners[type] ??= []).push(fn);
        },
      },
    });

    const pwa = await import("../../lib/pwa");
    // 감지 훅은 "대기 중"만 알린다 — 이 시점에 reload가 호출되면 안 된다.
    const stop = pwa.watchServiceWorkerUpdate(() => {});
    await Promise.resolve();
    expect(reload).not.toHaveBeenCalled();

    // 사용자가 눌렀을 때만 SKIP_WAITING을 보낸다.
    pwa.applyServiceWorkerUpdate(reload);
    await Promise.resolve();
    await Promise.resolve();
    expect(postMessage).toHaveBeenCalledWith("SKIP_WAITING");
    // 제어권이 넘어온 뒤에야 새로고침한다.
    expect(reload).not.toHaveBeenCalled();
    listeners.controllerchange?.forEach((fn) => fn(new Event("controllerchange")));
    expect(reload).toHaveBeenCalledTimes(1);
    stop();
  });
});
