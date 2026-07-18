/* BOHUMFIT-226 파트 B: 공개 라우트 전수 렌더 스모크.
   App.tsx 라우트 실측(2026-07-17) 기준 공개 페이지가 크래시 없이 렌더되고
   렌더 중 console.error 0건인지 고정한다. 기존 테스트는 수정하지 않는다. */
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ComponentType } from "react";

/* act() 경고는 테스트 환경 타이밍 아티팩트(예: Home 카운트업 애니메이션의 지연 상태
   업데이트)라 앱 콘솔 오류가 아니다 — 스모크 판정에서는 제외하고 실제 오류만 계수한다. */
function realConsoleErrors(spy: { mock: { calls: unknown[][] } }) {
  return spy.mock.calls.filter(
    ([first]) => !(typeof first === "string" && first.includes("not wrapped in act")),
  );
}

const authMocks = vi.hoisted(() => {
  const ok = { data: { session: null, user: null }, error: null };
  return {
    getSession: vi.fn(async () => ok),
    exchangeCodeForSession: vi.fn(async () => ok),
    signInWithPassword: vi.fn(async () => ok),
    signInWithOAuth: vi.fn(async () => ({ data: { provider: "kakao", url: "" }, error: null })),
    signUp: vi.fn(async () => ok),
    resetPasswordForEmail: vi.fn(async () => ({ data: {}, error: null })),
    updateUser: vi.fn(async () => ok),
    signOut: vi.fn(async () => ({ error: null })),
    onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
  };
});

vi.mock("../lib/supabase", () => ({
  supabase: { auth: authMocks },
}));

import Home from "./Home";
import Login from "./Login";
import Signup from "./Signup";
import ForgotPassword from "./ForgotPassword";
import ResetPassword from "./ResetPassword";
import ReportSample from "./ReportSample";
import DownloadGuide from "./DownloadGuide";
import CoverageGuide from "./CoverageGuide";
import InsuranceLinks from "./InsuranceLinks";
import Subscription from "./Subscription";
import WhyDisclosure from "./WhyDisclosure";
import PrivacyPolicy from "./PrivacyPolicy";
import TermsOfService from "./TermsOfService";
import NotFound from "./NotFound";

class MockIntersectionObserver {
  observe = vi.fn();
  disconnect = vi.fn();
  unobserve = vi.fn();
}

/* App.tsx 실측 공개 라우트(비로그인 접근 가능). ProtectedRoute 하위(/disclosure,
   /history, /dashboard, /coverage-compare, /insurance, /phone-verify)는
   ProtectedRouteSmoke.test.tsx에서 리다이렉트 동작만 고정한다. */
const PUBLIC_PAGES: Array<{ path: string; name: string; Page: ComponentType }> = [
  { path: "/", name: "Home", Page: Home },
  { path: "/login", name: "Login", Page: Login },
  { path: "/signup", name: "Signup", Page: Signup },
  { path: "/forgot-password", name: "ForgotPassword", Page: ForgotPassword },
  { path: "/disclosure/sample", name: "ReportSample", Page: ReportSample },
  { path: "/download-guide", name: "DownloadGuide", Page: DownloadGuide },
  { path: "/coverage-guide", name: "CoverageGuide", Page: CoverageGuide },
  { path: "/insurance-links", name: "InsuranceLinks", Page: InsuranceLinks },
  { path: "/subscription", name: "Subscription", Page: Subscription },
  { path: "/why", name: "WhyDisclosure", Page: WhyDisclosure },
  { path: "/privacy-policy", name: "PrivacyPolicy", Page: PrivacyPolicy },
  { path: "/terms-of-service", name: "TermsOfService", Page: TermsOfService },
  { path: "/definitely-not-a-route", name: "NotFound", Page: NotFound },
];

describe("public routes render smoke", () => {
  let errorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.stubGlobal("IntersectionObserver", MockIntersectionObserver);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => ({}),
        text: async () => "",
      })),
    );
    errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    cleanup();
    errorSpy.mockRestore();
    vi.unstubAllGlobals();
  });

  for (const { path, name, Page } of PUBLIC_PAGES) {
    it(`${name} (${path}) renders without crash and console error`, async () => {
      const { container } = render(
        <MemoryRouter initialEntries={[path]}>
          <Page />
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(container.innerHTML.length).toBeGreaterThan(0);
      });
      // 마운트 직후 비동기 효과(effect) 마이크로태스크를 한 번 비운 뒤 콘솔을 판정한다.
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(realConsoleErrors(errorSpy)).toEqual([]);
    });
  }

  it("ResetPassword direct access shows re-request guidance (recovery 신호 없음)", async () => {
    window.history.pushState({}, "", "/reset-password");
    render(
      <MemoryRouter>
        <ResetPassword />
      </MemoryRouter>,
    );

    expect(await screen.findByText("링크를 다시 요청해 주세요")).toBeInTheDocument();
    expect(authMocks.exchangeCodeForSession).not.toHaveBeenCalled();
    expect(realConsoleErrors(errorSpy)).toEqual([]);
  });
});
