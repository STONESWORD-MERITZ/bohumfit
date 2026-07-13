import { cleanup, fireEvent, render, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ForgotPassword from "./ForgotPassword";
import Login from "./Login";

const authMocks = vi.hoisted(() => ({
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

describe("forgot password SMS reset", () => {
  beforeEach(() => {
    authMocks.signInWithOAuth.mockClear();
    authMocks.signInWithPassword.mockClear();
    vi.stubEnv("VITE_HCAPTCHA_SITEKEY", "");
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

  it("runs request, verify, and confirm through server APIs", async () => {
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

    const { container } = render(
      <MemoryRouter>
        <ForgotPassword />
      </MemoryRouter>,
    );

    const phoneInput = container.querySelector<HTMLInputElement>('input[type="tel"]');
    expect(phoneInput).toBeInTheDocument();
    await user.type(phoneInput!, "010-1234-5678");
    fireEvent.submit(container.querySelector("form")!);

    await waitFor(() => {
      expect(calls[0]).toEqual({
        path: "/auth/password-reset/request",
        body: { phone: "01012345678" },
      });
    });

    const codeInput = await waitFor(() => container.querySelector<HTMLInputElement>('input[type="text"]'));
    expect(codeInput).toBeInTheDocument();
    await user.type(codeInput!, "123456");
    fireEvent.submit(container.querySelector("form")!);

    await waitFor(() => {
      expect(calls[1]).toEqual({
        path: "/auth/password-reset/verify",
        body: { phone: "01012345678", code: "123456" },
      });
    });

    const passwordInput = await waitFor(() => container.querySelector<HTMLInputElement>('input[type="password"]'));
    expect(passwordInput).toBeInTheDocument();
    await user.type(passwordInput!, "new-password-216");
    fireEvent.submit(container.querySelector("form")!);

    await waitFor(() => {
      expect(calls[2]).toEqual({
        path: "/auth/password-reset/confirm",
        body: { reset_token: "reset-token-216", password: "new-password-216" },
      });
    });
    expect(container.querySelector('a[href="/login"]')).toBeInTheDocument();
  });

  it("shows server guidance when NHN SMS is not ready", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ detail: "NHN SMS module is not ready" }, 503)),
    );
    const user = userEvent.setup();
    const { container, findByText } = render(
      <MemoryRouter>
        <ForgotPassword />
      </MemoryRouter>,
    );

    await user.type(container.querySelector<HTMLInputElement>('input[type="tel"]')!, "01012345678");
    fireEvent.submit(container.querySelector("form")!);

    expect(await findByText("NHN SMS module is not ready")).toBeInTheDocument();
  });
});
