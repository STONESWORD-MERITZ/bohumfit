import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ForgotPassword from "./ForgotPassword";
import Login from "./Login";

const authMocks = vi.hoisted(() => ({
  resetPasswordForEmail: vi.fn(async () => ({ data: {}, error: null })),
  signInWithOAuth: vi.fn(async () => ({ error: null })),
  signInWithPassword: vi.fn(async () => ({ error: null })),
}));

vi.mock("../lib/supabase", () => ({
  supabase: {
    auth: authMocks,
  },
}));

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("forgot password reset", () => {
  beforeEach(() => {
    authMocks.resetPasswordForEmail.mockClear();
    authMocks.signInWithOAuth.mockClear();
    authMocks.signInWithPassword.mockClear();
    vi.stubEnv("VITE_HCAPTCHA_SITEKEY", "");
    vi.stubEnv("VITE_ENABLE_SMS_PASSWORD_RESET", "");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it("adds a password reset link to the login screen without changing OAuth", async () => {
    const user = userEvent.setup();
    const { container } = render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );

    expect(container.querySelector('a[href="/forgot-password"]')).toBeInTheDocument();

    const oauthButtons = container.querySelectorAll("button");
    await user.click(oauthButtons[0]);

    expect(authMocks.signInWithOAuth).toHaveBeenCalledWith({
      provider: "kakao",
      options: { redirectTo: window.location.origin },
    });
  });

  it("requests a Supabase email reset link without exposing account existence", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ForgotPassword />
      </MemoryRouter>,
    );

    await user.type(screen.getByPlaceholderText("가입 이메일"), "user@example.com");
    await user.click(screen.getByRole("button", { name: "재설정 메일 받기" }));

    await waitFor(() => {
      expect(authMocks.resetPasswordForEmail).toHaveBeenCalledWith("user@example.com", {
        redirectTo: `${window.location.origin}/reset-password`,
      });
    });
    expect(screen.getByText("입력한 이메일로 비밀번호 재설정 안내를 보냈습니다. 메일함에서 링크를 확인해 주세요.")).toBeInTheDocument();

    authMocks.resetPasswordForEmail.mockRejectedValueOnce(new Error("User not found"));
    await user.clear(screen.getByPlaceholderText("가입 이메일"));
    await user.type(screen.getByPlaceholderText("가입 이메일"), "missing@example.com");
    await user.click(screen.getByRole("button", { name: "재설정 메일 받기" }));

    expect(await screen.findByText("입력한 이메일로 비밀번호 재설정 안내를 보냈습니다. 메일함에서 링크를 확인해 주세요.")).toBeInTheDocument();
  });

  it("hides the SMS path unless it is explicitly enabled", () => {
    render(
      <MemoryRouter>
        <ForgotPassword />
      </MemoryRouter>,
    );

    expect(screen.queryByRole("button", { name: "SMS" })).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText("등록 휴대폰 번호 (- 없이)")).not.toBeInTheDocument();
  });

  it("keeps the BOHUMFIT-216 SMS flow behind the environment flag", async () => {
    vi.stubEnv("VITE_ENABLE_SMS_PASSWORD_RESET", "true");
    const calls: Array<{ path: string; body: unknown }> = [];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      calls.push({ path: new URL(url).pathname, body });
      if (url.endsWith("/auth/password-reset/request")) {
        return jsonResponse({ sent: true, message: "sent" });
      }
      if (url.endsWith("/auth/password-reset/verify")) {
        return jsonResponse({ verified: true, reset_token: "reset-token-216", message: "verified" });
      }
      if (url.endsWith("/auth/password-reset/confirm")) {
        return jsonResponse({ updated: true, message: "updated" });
      }
      return jsonResponse({ detail: "unexpected" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <ForgotPassword />
      </MemoryRouter>,
    );

    await user.click(screen.getByRole("button", { name: "SMS" }));
    await user.type(screen.getByPlaceholderText("등록 휴대폰 번호 (- 없이)"), "010-1234-5678");
    fireEvent.submit(screen.getByPlaceholderText("등록 휴대폰 번호 (- 없이)").closest("form")!);

    await waitFor(() => {
      expect(calls[0]).toEqual({
        path: "/auth/password-reset/request",
        body: { phone: "01012345678" },
      });
    });

    await user.type(await screen.findByPlaceholderText("인증번호 6자리"), "123456");
    fireEvent.submit(screen.getByPlaceholderText("인증번호 6자리").closest("form")!);

    await waitFor(() => {
      expect(calls[1]).toEqual({
        path: "/auth/password-reset/verify",
        body: { phone: "01012345678", code: "123456" },
      });
    });

    await user.type(await screen.findByPlaceholderText("새 비밀번호 10자 이상"), "new-password-216");
    fireEvent.submit(screen.getByPlaceholderText("새 비밀번호 10자 이상").closest("form")!);

    await waitFor(() => {
      expect(calls[2]).toEqual({
        path: "/auth/password-reset/confirm",
        body: { reset_token: "reset-token-216", password: "new-password-216" },
      });
    });
    expect(screen.getByText("로그인으로 돌아가기")).toBeInTheDocument();
  });

  it("shows server guidance when the optional SMS path is enabled but NHN is not ready", async () => {
    vi.stubEnv("VITE_ENABLE_SMS_PASSWORD_RESET", "true");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ detail: "NHN SMS module is not ready" }, 503)),
    );
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <ForgotPassword />
      </MemoryRouter>,
    );

    await user.click(screen.getByRole("button", { name: "SMS" }));
    await user.type(screen.getByPlaceholderText("등록 휴대폰 번호 (- 없이)"), "01012345678");
    fireEvent.submit(screen.getByPlaceholderText("등록 휴대폰 번호 (- 없이)").closest("form")!);

    expect(await screen.findByText("NHN SMS module is not ready")).toBeInTheDocument();
  });
});
