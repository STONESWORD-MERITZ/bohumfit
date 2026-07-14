import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { isHCaptchaEnabled } from "../lib/hcaptcha";
import HCaptcha from "./HCaptcha";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllEnvs();
  delete window.hcaptcha;
  document
    .querySelectorAll('script[data-bohumfit-hcaptcha="true"]')
    .forEach((script) => script.remove());
});

describe("HCaptcha", () => {
  it("does not render or load a widget when the site key is unset", () => {
    vi.stubEnv("VITE_HCAPTCHA_SITEKEY", "");
    const onTokenChange = vi.fn();
    const { container } = render(<HCaptcha onTokenChange={onTokenChange} />);

    expect(isHCaptchaEnabled()).toBe(false);
    expect(container).toBeEmptyDOMElement();
    expect(document.querySelector('script[data-bohumfit-hcaptcha="true"]')).not.toBeInTheDocument();
  });

  it("renders a configured widget and forwards its token", async () => {
    vi.stubEnv("VITE_HCAPTCHA_SITEKEY", "test-site-key");
    const onTokenChange = vi.fn();
    const renderWidget = vi.fn((_container, options: { callback: (token: string) => void }) => {
      options.callback("test-token");
      return 7;
    });
    window.hcaptcha = { render: renderWidget, remove: vi.fn() };

    render(<HCaptcha onTokenChange={onTokenChange} />);

    await waitFor(() => expect(onTokenChange).toHaveBeenCalledWith("test-token"));
    expect(isHCaptchaEnabled()).toBe(true);
    expect(renderWidget).toHaveBeenCalledTimes(1);
  });

  it("reports widget load failure so auth screens can fail open", async () => {
    vi.stubEnv("VITE_HCAPTCHA_SITEKEY", "test-site-key");
    const onTokenChange = vi.fn();
    const onUnavailable = vi.fn();

    render(<HCaptcha onTokenChange={onTokenChange} onUnavailable={onUnavailable} />);

    const script = document.querySelector<HTMLScriptElement>('script[data-bohumfit-hcaptcha="true"]');
    expect(script).toBeInTheDocument();
    script?.dispatchEvent(new Event("error"));

    await waitFor(() => expect(onUnavailable).toHaveBeenCalledTimes(1));
    expect(onTokenChange).toHaveBeenCalledWith("");
    expect(screen.getByText("보안 확인을 불러오지 못했어요. 기존 인증 흐름으로 진행합니다.")).toBeInTheDocument();
  });

  it("reports a configured widget that never renders so auth can fail open", async () => {
    vi.useFakeTimers();
    vi.stubEnv("VITE_HCAPTCHA_SITEKEY", "test-site-key");
    const onTokenChange = vi.fn();
    const onUnavailable = vi.fn();

    render(<HCaptcha onTokenChange={onTokenChange} onUnavailable={onUnavailable} />);

    expect(document.querySelector('script[data-bohumfit-hcaptcha="true"]')).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000);
    });

    expect(onUnavailable).toHaveBeenCalledTimes(1);
    expect(onTokenChange).toHaveBeenCalledWith("");
    expect(screen.getByText("보안 확인을 불러오지 못했어요. 기존 인증 흐름으로 진행합니다.")).toBeInTheDocument();
  });
});
