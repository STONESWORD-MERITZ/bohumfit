/* BOHUMFIT-226 파트 B: ProtectedRoute 게이트 리다이렉트 스모크.
   비로그인 → /login, 미인증 → /phone-verify(state.from 유지), 인증 → children,
   로딩 → 로딩 표시를 고정한다. 판정 로직 자체는 phoneGate.test.ts가 담당한다. */
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

const gateMock = vi.hoisted(() => ({
  status: "loading" as "loading" | "anonymous" | "unverified" | "verified",
}));

vi.mock("../lib/usePhoneGate", () => ({
  usePhoneGateStatus: () => gateMock.status,
}));

import ProtectedRoute from "./ProtectedRoute";

function VerifyProbe() {
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "";
  return <div>VERIFY-PAGE from={from}</div>;
}

function renderGate(initialEntry = "/secret?tab=a") {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route
          path="/secret"
          element={
            <ProtectedRoute>
              <div>SECRET-CONTENT</div>
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<div>LOGIN-PAGE</div>} />
        <Route path="/phone-verify" element={<VerifyProbe />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ProtectedRoute gate redirects", () => {
  afterEach(() => {
    cleanup();
  });

  it("비로그인(anonymous)은 /login 으로 보낸다", () => {
    gateMock.status = "anonymous";
    renderGate();
    expect(screen.getByText("LOGIN-PAGE")).toBeInTheDocument();
    expect(screen.queryByText("SECRET-CONTENT")).not.toBeInTheDocument();
  });

  it("미인증(unverified)은 /phone-verify 로 보내고 원래 경로를 state.from 으로 넘긴다", () => {
    gateMock.status = "unverified";
    renderGate();
    expect(screen.getByText("VERIFY-PAGE from=/secret?tab=a")).toBeInTheDocument();
    expect(screen.queryByText("SECRET-CONTENT")).not.toBeInTheDocument();
  });

  it("인증(verified)은 children 을 그대로 렌더한다", () => {
    gateMock.status = "verified";
    renderGate();
    expect(screen.getByText("SECRET-CONTENT")).toBeInTheDocument();
  });

  it("판정 전(loading)은 로딩 표시만 보여준다", () => {
    gateMock.status = "loading";
    renderGate();
    expect(screen.getByText("로딩 중...")).toBeInTheDocument();
    expect(screen.queryByText("SECRET-CONTENT")).not.toBeInTheDocument();
  });
});
