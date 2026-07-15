import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { isHCaptchaEnabled } from "../lib/hcaptcha";
import HCaptcha from "./HCaptcha";

type CaptchaOptions = {
  sitekey: string;
  callback: (token: string) => void;
  "expired-callback": () => void;
  "error-callback": () => void;
};

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllEnvs();
  delete window.hcaptcha;
  delete window.__bohumfitHCaptchaOnload;
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

  it("reports an API whose official onload callback never fires", async () => {
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

  it("reports a render failure after the API onload callback", async () => {
    vi.stubEnv("VITE_HCAPTCHA_SITEKEY", "test-site-key");
    const onTokenChange = vi.fn();
    const onUnavailable = vi.fn();
    window.hcaptcha = {
      render: vi.fn(() => {
        throw new Error("render failed");
      }),
      remove: vi.fn(),
    };

    render(<HCaptcha onTokenChange={onTokenChange} onUnavailable={onUnavailable} />);

    expect(window.__bohumfitHCaptchaOnload).toEqual(expect.any(Function));
    act(() => window.__bohumfitHCaptchaOnload?.());

    await waitFor(() => expect(onUnavailable).toHaveBeenCalledTimes(1));
    expect(onTokenChange).toHaveBeenCalledWith("");
  });

  it("recovers a response token when the verify callback is missed", async () => {
    vi.useFakeTimers();
    vi.stubEnv("VITE_HCAPTCHA_SITEKEY", "test-site-key");
    const onTokenChange = vi.fn();
    const onUnavailable = vi.fn();
    const getResponse = vi.fn(() => "recovered-token");
    const renderWidget = vi.fn(() => 8);
    window.hcaptcha = { render: renderWidget, remove: vi.fn(), getResponse };

    render(<HCaptcha onTokenChange={onTokenChange} onUnavailable={onUnavailable} />);
    await act(async () => {
      window.__bohumfitHCaptchaOnload?.();
      await Promise.resolve();
    });
    expect(renderWidget).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000);
    });

    expect(getResponse).toHaveBeenCalledWith(8);
    expect(onTokenChange).toHaveBeenLastCalledWith("recovered-token");
    expect(onUnavailable).not.toHaveBeenCalled();
  });

  it("does not fail open merely because a rendered widget has no response yet", async () => {
    vi.useFakeTimers();
    vi.stubEnv("VITE_HCAPTCHA_SITEKEY", "test-site-key");
    const onTokenChange = vi.fn();
    const onUnavailable = vi.fn();
    const getResponse = vi.fn(() => "");
    window.hcaptcha = { render: vi.fn(() => 9), remove: vi.fn(), getResponse };

    render(<HCaptcha onTokenChange={onTokenChange} onUnavailable={onUnavailable} />);
    await act(async () => {
      window.__bohumfitHCaptchaOnload?.();
      await Promise.resolve();
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000);
    });

    expect(getResponse).toHaveBeenCalledTimes(3);
    expect(onTokenChange).not.toHaveBeenCalled();
    expect(onUnavailable).not.toHaveBeenCalled();
  });

  it("waits for API onload, renders once, and wires verify, expire, and error callbacks", async () => {
    vi.stubEnv("VITE_HCAPTCHA_SITEKEY", "env-site-key");
    const onTokenChange = vi.fn();
    const onReady = vi.fn();
    const onUnavailable = vi.fn();
    const removeWidget = vi.fn();
    let options: CaptchaOptions | undefined;
    const renderWidget = vi.fn((_container: HTMLElement, nextOptions: CaptchaOptions) => {
      options = nextOptions;
      return 7;
    });

    const view = render(
      <StrictMode>
        <HCaptcha
          onTokenChange={onTokenChange}
          onReady={onReady}
          onUnavailable={onUnavailable}
        />
      </StrictMode>,
    );

    const scripts = document.querySelectorAll<HTMLScriptElement>('script[data-bohumfit-hcaptcha="true"]');
    expect(scripts).toHaveLength(1);
    const scriptUrl = new URL(scripts[0].src);
    expect(scriptUrl.searchParams.get("render")).toBe("explicit");
    expect(scriptUrl.searchParams.get("onload")).toBe("__bohumfitHCaptchaOnload");

    window.hcaptcha = { render: renderWidget, remove: removeWidget };
    act(() => scripts[0].dispatchEvent(new Event("load")));
    expect(renderWidget).not.toHaveBeenCalled();

    act(() => window.__bohumfitHCaptchaOnload?.());
    await waitFor(() => expect(renderWidget).toHaveBeenCalledTimes(1));
    expect(options?.sitekey).toBe("env-site-key");
    expect(onReady).toHaveBeenCalledTimes(1);

    act(() => options?.callback("verified-token"));
    expect(onTokenChange).toHaveBeenLastCalledWith("verified-token");
    expect(onReady).toHaveBeenCalledTimes(2);

    act(() => options?.["expired-callback"]());
    expect(onTokenChange).toHaveBeenLastCalledWith("");
    expect(onUnavailable).toHaveBeenCalledTimes(1);
    expect(screen.getByText("보안 확인이 만료되었어요. 기존 인증 흐름으로 진행합니다.")).toBeInTheDocument();

    act(() => options?.callback("renewed-token"));
    expect(onTokenChange).toHaveBeenLastCalledWith("renewed-token");
    expect(screen.queryByText("보안 확인이 만료되었어요. 기존 인증 흐름으로 진행합니다.")).not.toBeInTheDocument();

    act(() => options?.["error-callback"]());
    expect(onTokenChange).toHaveBeenLastCalledWith("");
    expect(onUnavailable).toHaveBeenCalledTimes(2);

    view.unmount();
    expect(removeWidget).toHaveBeenCalledWith(7);
  });
});
