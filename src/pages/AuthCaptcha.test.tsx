import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Login from "./Login";
import Signup from "./Signup";

const authMocks = vi.hoisted(() => ({
  signInWithOAuth: vi.fn(async () => ({ error: null })),
  signInWithPassword: vi.fn(async () => ({ error: null })),
  signUp: vi.fn(async () => ({ error: null })),
}));

vi.mock("../lib/supabase", () => ({
  supabase: {
    auth: authMocks,
  },
}));

function removeCaptchaScripts() {
  document
    .querySelectorAll('script[data-bohumfit-hcaptcha="true"]')
    .forEach((script) => script.remove());
}

function failCaptchaScriptIfPresent() {
  document
    .querySelectorAll('script[data-bohumfit-hcaptcha="true"]')
    .forEach((script) => script.dispatchEvent(new Event("error")));
}

async function submitEmailSignup(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("이메일"), "signup@example.com");
  await user.type(screen.getByLabelText("비밀번호 10자 이상"), "password1234");
  await user.type(screen.getByLabelText("휴대폰 번호"), "01012345678");
  await user.click(screen.getByRole("button", { name: "인증 요청" }));
  for (const checkbox of screen.getAllByRole("checkbox")) {
    await user.click(checkbox);
  }
  await user.click(screen.getByRole("button", { name: "회원가입" }));
}

describe("auth hCaptcha fail-open", () => {
  beforeEach(() => {
    authMocks.signInWithOAuth.mockClear();
    authMocks.signInWithPassword.mockClear();
    authMocks.signUp.mockClear();
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllEnvs();
    removeCaptchaScripts();
    delete window.hcaptcha;
    delete window.__bohumfitHCaptchaOnload;
  });

  it("renders the keyless login path without loading hCaptcha", () => {
    vi.stubEnv("VITE_HCAPTCHA_SITEKEY", "");

    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );

    expect(screen.getByRole("button", { name: "카카오로 시작하기" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Google로 시작하기" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "이메일로 로그인" })).toBeInTheDocument();
    expect(document.querySelector('script[data-bohumfit-hcaptcha="true"]')).not.toBeInTheDocument();
  });

  it("does not require hCaptcha for Kakao or Google login even when a site key exists", async () => {
    vi.stubEnv("VITE_HCAPTCHA_SITEKEY", "test-site-key");
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );

    await user.click(screen.getByRole("button", { name: "카카오로 시작하기" }));
    await user.click(screen.getByRole("button", { name: "Google로 시작하기" }));

    expect(authMocks.signInWithOAuth).toHaveBeenNthCalledWith(1, {
      provider: "kakao",
      options: { redirectTo: window.location.origin },
    });
    expect(authMocks.signInWithOAuth).toHaveBeenNthCalledWith(2, {
      provider: "google",
      options: { redirectTo: window.location.origin },
    });
    expect(screen.queryByText("보안 확인을 완료해 주세요.")).not.toBeInTheDocument();
    failCaptchaScriptIfPresent();
  });

  it("lets email login continue if the hCaptcha widget cannot load", async () => {
    vi.stubEnv("VITE_HCAPTCHA_SITEKEY", "test-site-key");
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );

    const script = document.querySelector<HTMLScriptElement>('script[data-bohumfit-hcaptcha="true"]');
    script?.dispatchEvent(new Event("error"));
    await waitFor(() => {
      expect(screen.getByText("보안 확인을 불러오지 못했어요. 기존 인증 흐름으로 진행합니다.")).toBeInTheDocument();
    });

    await user.type(screen.getByPlaceholderText("이메일"), "test@example.com");
    await user.type(screen.getByPlaceholderText("비밀번호"), "password1234");
    await user.click(screen.getByRole("button", { name: "이메일로 로그인" }));

    await waitFor(() => expect(authMocks.signInWithPassword).toHaveBeenCalledTimes(1));
    expect(authMocks.signInWithPassword).toHaveBeenCalledWith({
      email: "test@example.com",
      password: "password1234",
      options: undefined,
    });
  });

  it("does not require hCaptcha for Kakao or Google signup OAuth", async () => {
    vi.stubEnv("VITE_HCAPTCHA_SITEKEY", "test-site-key");
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <Signup />
      </MemoryRouter>,
    );

    await user.click(screen.getByRole("button", { name: "카카오로 계속하기" }));
    await user.click(screen.getByRole("button", { name: "Google로 계속하기" }));

    expect(authMocks.signInWithOAuth).toHaveBeenNthCalledWith(1, {
      provider: "kakao",
      options: { redirectTo: window.location.origin },
    });
    expect(authMocks.signInWithOAuth).toHaveBeenNthCalledWith(2, {
      provider: "google",
      options: { redirectTo: window.location.origin },
    });
    expect(screen.queryByText("보안 확인을 완료해 주세요.")).not.toBeInTheDocument();
    failCaptchaScriptIfPresent();
  });

  it("lets keyless email signup continue without loading hCaptcha", async () => {
    vi.stubEnv("VITE_HCAPTCHA_SITEKEY", "");
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <Signup />
      </MemoryRouter>,
    );

    await submitEmailSignup(user);

    await waitFor(() => expect(authMocks.signUp).toHaveBeenCalledTimes(1));
    expect(authMocks.signUp).toHaveBeenCalledWith({
      email: "signup@example.com",
      password: "password1234",
      options: undefined,
    });
    expect(document.querySelector('script[data-bohumfit-hcaptcha="true"]')).not.toBeInTheDocument();
  });

  it("lets email signup continue if the hCaptcha widget cannot load", async () => {
    vi.stubEnv("VITE_HCAPTCHA_SITEKEY", "test-site-key");
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <Signup />
      </MemoryRouter>,
    );

    failCaptchaScriptIfPresent();
    await waitFor(() => {
      expect(screen.getByText("보안 확인을 불러오지 못했어요. 기존 인증 흐름으로 진행합니다.")).toBeInTheDocument();
    });
    await submitEmailSignup(user);

    await waitFor(() => expect(authMocks.signUp).toHaveBeenCalledTimes(1));
    expect(authMocks.signUp).toHaveBeenCalledWith({
      email: "signup@example.com",
      password: "password1234",
      options: undefined,
    });
  });

  it("keeps token verification when the signup widget renders normally", async () => {
    vi.stubEnv("VITE_HCAPTCHA_SITEKEY", "test-site-key");
    const renderWidget = vi.fn((_container, options: { callback: (token: string) => void }) => {
      options.callback("signup-captcha-token");
      return 9;
    });
    window.hcaptcha = { render: renderWidget, remove: vi.fn() };
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <Signup />
      </MemoryRouter>,
    );

    expect(window.__bohumfitHCaptchaOnload).toEqual(expect.any(Function));
    act(() => window.__bohumfitHCaptchaOnload?.());
    await waitFor(() => expect(renderWidget).toHaveBeenCalledTimes(1));
    await submitEmailSignup(user);

    await waitFor(() => expect(authMocks.signUp).toHaveBeenCalledTimes(1));
    expect(authMocks.signUp).toHaveBeenCalledWith({
      email: "signup@example.com",
      password: "password1234",
      options: { captchaToken: "signup-captcha-token" },
    });
  });
});
