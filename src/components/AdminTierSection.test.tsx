/* BOHUMFIT-233: 직원 관리 섹션 — 목록 렌더·지정 성공·미가입 404 안내와
   Dashboard의 admin 전용 노출 분기(비admin 미노출)를 고정한다. */
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Session } from "@supabase/supabase-js";
import AdminTierSection from "./AdminTierSection";
import { AuthContext } from "../lib/auth-context";
import Dashboard from "../pages/Dashboard";

const MEMBERS = {
  members: [
    { email: "boss@bohumfit.ai", tier: "admin" },
    { email: "staff1@bohumfit.ai", tier: "internal" },
  ],
};

function jsonResponse(body: unknown, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

/** URL별 응답 라우팅 fetch 스텁 — 위젯별 독립 fetch(163)와 233 API를 함께 흡수한다. */
function stubFetch(overrides: { billing?: unknown; set?: { status: number; body?: unknown } } = {}) {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    calls.push({ url, init });
    if (url.includes("/admin/tier/list")) return jsonResponse(MEMBERS);
    if (url.includes("/admin/tier/set")) {
      const o = overrides.set ?? { status: 200, body: { ok: true } };
      return jsonResponse(o.body ?? { detail: "err" }, o.status);
    }
    if (url.includes("/billing/status")) {
      return jsonResponse(
        overrides.billing ?? {
          status: "admin", plan: "admin", used: 0, limit: null,
          is_internal: false, is_admin: true, quota_scope: "unlimited", enabled: true,
        },
      );
    }
    if (url.includes("/history")) return jsonResponse({ items: [], total: 0 });
    return jsonResponse({});
  });
  vi.stubGlobal("fetch", fn);
  return calls;
}

describe("AdminTierSection", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("현재 admin/internal 목록을 렌더한다", async () => {
    stubFetch();
    render(<AdminTierSection apiBase="http://api.test" token="t" />);
    expect(await screen.findByText("boss@bohumfit.ai")).toBeInTheDocument();
    expect(screen.getByText("staff1@bohumfit.ai")).toBeInTheDocument();
    expect(screen.getByText("직원 관리")).toBeInTheDocument();
  });

  it("이메일 입력 후 internal 지정 성공 피드백을 보여준다", async () => {
    const calls = stubFetch();
    const user = userEvent.setup();
    render(<AdminTierSection apiBase="http://api.test" token="t" />);

    await user.type(screen.getByPlaceholderText("직원 이메일"), "new@bohumfit.ai");
    await user.click(screen.getByRole("button", { name: "internal 지정" }));

    expect(await screen.findByText("new@bohumfit.ai — 내부 직원(월 100회)으로 지정했어요.")).toBeInTheDocument();
    const setCall = calls.find((c) => c.url.includes("/admin/tier/set"));
    expect(setCall).toBeTruthy();
    expect(JSON.parse(String(setCall?.init?.body))).toEqual({ email: "new@bohumfit.ai", tier: "internal" });
  });

  it("미가입 이메일(404)은 가입 후 재시도 안내를 보여준다", async () => {
    stubFetch({ set: { status: 404, body: { detail: "없음" } } });
    const user = userEvent.setup();
    render(<AdminTierSection apiBase="http://api.test" token="t" />);

    await user.type(screen.getByPlaceholderText("직원 이메일"), "ghost@example.com");
    await user.click(screen.getByRole("button", { name: "internal 지정" }));

    expect(await screen.findByText("해당 이메일 가입 이력 없음 — 가입 후 다시 시도해 주세요.")).toBeInTheDocument();
  });
});

describe("Dashboard admin 분기", () => {
  const session = { access_token: "t" } as unknown as Session;
  const baseAuth = { user: null, session, loading: false, signOut: async () => {} };

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("admin이면 직원 관리 섹션이 보인다", async () => {
    stubFetch();
    render(
      <MemoryRouter>
        <AuthContext.Provider value={baseAuth}>
          <Dashboard />
        </AuthContext.Provider>
      </MemoryRouter>,
    );
    expect(await screen.findByText("직원 관리")).toBeInTheDocument();
  });

  it("비admin이면 직원 관리 섹션이 없다", async () => {
    stubFetch({
      billing: {
        status: "inactive", plan: null, used: 1, limit: 5, trial_used: 1, trial_limit: 5,
        is_internal: false, is_admin: false, quota_scope: "lifetime", enabled: true,
      },
    });
    render(
      <MemoryRouter>
        <AuthContext.Provider value={baseAuth}>
          <Dashboard />
        </AuthContext.Provider>
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("무료 분석 사용량")).toBeInTheDocument();
    });
    expect(screen.queryByText("직원 관리")).not.toBeInTheDocument();
  });
});
