import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Home from "./Home";

class MockIntersectionObserver {
  observe = vi.fn();
  disconnect = vi.fn();
  unobserve = vi.fn();
}

describe("Home landing layout", () => {
  beforeEach(() => {
    vi.stubGlobal("IntersectionObserver", MockIntersectionObserver);
  });

  it("renders compact stat bar and home section snap hooks", () => {
    const { container } = render(
      <MemoryRouter>
        <Home />
      </MemoryRouter>,
    );

    expect(screen.getByText("상담 준비 요약")).toBeInTheDocument();
    expect(screen.getByText("분석 완료")).toBeInTheDocument();
    expect(screen.getByText("핵심 검출")).toBeInTheDocument();
    expect(screen.getByText("리포트 생성")).toBeInTheDocument();
    expect(screen.getByText("고지의무 리스크 자동 정리")).toBeInTheDocument();

    expect(container.querySelector(".bf-home-snap")).toBeInTheDocument();
    expect(container.querySelectorAll(".bf-home-section").length).toBeGreaterThanOrEqual(5);
  });
});
