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

  it("renders a natural-scroll home with a combined guide section", () => {
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

    const guideSection = container.querySelector("#features");
    expect(guideSection).toHaveTextContent("How it works");
    expect(guideSection).toHaveTextContent("Features");
    expect(guideSection).toHaveTextContent("업로드 한 번, 3단계로 끝");
    expect(guideSection).toHaveTextContent("설계사 업무를 줄여주는 3가지");

    expect(container.querySelector(".bf-home-snap")).not.toBeInTheDocument();
    expect(container.querySelector(".bf-home-panel")).not.toBeInTheDocument();
  });
});
