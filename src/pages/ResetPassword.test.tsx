import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ResetPassword from "./ResetPassword";

const authMocks = vi.hoisted(() => ({
  exchangeCodeForSession: vi.fn(
    async (): Promise<{ data: { session: { user: { id: string } } | null }; error: { message: string } | null }> => ({
      data: { session: { user: { id: "user-1" } } },
      error: null,
    }),
  ),
  getSession: vi.fn(
    async (): Promise<{ data: { session: { user: { id: string } } | null }; error: { message: string } | null }> => ({
      data: { session: { user: { id: "user-1" } } },
      error: null,
    }),
  ),
  updateUser: vi.fn(async () => ({ data: { user: { id: "user-1" } }, error: null })),
  signOut: vi.fn(async () => ({ error: null })),
}));

vi.mock("../lib/supabase", () => ({
  supabase: {
    auth: authMocks,
  },
}));

function renderPage(url = "/reset-password?code=recovery-code") {
  window.history.pushState({}, "", url);
  return render(
    <MemoryRouter>
      <ResetPassword />
    </MemoryRouter>,
  );
}

describe("reset password recovery page", () => {
  beforeEach(() => {
    authMocks.exchangeCodeForSession.mockClear();
    authMocks.exchangeCodeForSession.mockResolvedValue({ data: { session: { user: { id: "user-1" } } }, error: null });
    authMocks.getSession.mockClear();
    authMocks.getSession.mockResolvedValue({ data: { session: { user: { id: "user-1" } } }, error: null });
    authMocks.updateUser.mockClear();
    authMocks.updateUser.mockResolvedValue({ data: { user: { id: "user-1" } }, error: null });
    authMocks.signOut.mockClear();
  });

  afterEach(() => {
    cleanup();
  });

  it("exchanges a recovery code, updates the password, and signs out for a fresh login", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("새 비밀번호 설정")).toBeInTheDocument();
    expect(authMocks.exchangeCodeForSession).toHaveBeenCalledWith("recovery-code");

    await user.type(screen.getByPlaceholderText("새 비밀번호 10자 이상"), "new-password-222");
    await user.type(screen.getByPlaceholderText("새 비밀번호 확인"), "new-password-222");
    await user.click(screen.getByRole("button", { name: "비밀번호 변경" }));

    await waitFor(() => {
      expect(authMocks.updateUser).toHaveBeenCalledWith({ password: "new-password-222" });
    });
    expect(authMocks.signOut).toHaveBeenCalled();
    expect(await screen.findByText("비밀번호가 변경되었습니다. 새 비밀번호로 다시 로그인해 주세요.")).toBeInTheDocument();
  });

  it("blocks direct access without a recovery link", async () => {
    renderPage("/reset-password");

    expect(await screen.findByText("링크를 다시 요청해 주세요")).toBeInTheDocument();
    expect(authMocks.exchangeCodeForSession).not.toHaveBeenCalled();
    expect(authMocks.updateUser).not.toHaveBeenCalled();
    expect(screen.getByText("재설정 메일 다시 받기")).toBeInTheDocument();
  });

  it("shows the retry path when the recovery link is expired or invalid", async () => {
    authMocks.exchangeCodeForSession.mockResolvedValueOnce({ data: { session: null }, error: { message: "expired" } });

    renderPage("/reset-password?code=expired-code");

    expect(await screen.findByText("링크를 다시 요청해 주세요")).toBeInTheDocument();
    expect(authMocks.updateUser).not.toHaveBeenCalled();
  });

  it("validates password length and confirmation before updating", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("새 비밀번호 설정")).toBeInTheDocument();
    await user.type(screen.getByPlaceholderText("새 비밀번호 10자 이상"), "short");
    await user.type(screen.getByPlaceholderText("새 비밀번호 확인"), "short");
    await user.click(screen.getByRole("button", { name: "비밀번호 변경" }));
    expect(await screen.findByText("새 비밀번호는 10자 이상으로 입력해 주세요.")).toBeInTheDocument();

    await user.clear(screen.getByPlaceholderText("새 비밀번호 10자 이상"));
    await user.clear(screen.getByPlaceholderText("새 비밀번호 확인"));
    await user.type(screen.getByPlaceholderText("새 비밀번호 10자 이상"), "new-password-222");
    await user.type(screen.getByPlaceholderText("새 비밀번호 확인"), "different-password");
    await user.click(screen.getByRole("button", { name: "비밀번호 변경" }));
    expect(await screen.findByText("새 비밀번호가 서로 일치하지 않습니다.")).toBeInTheDocument();
    expect(authMocks.updateUser).not.toHaveBeenCalled();
  });
});
