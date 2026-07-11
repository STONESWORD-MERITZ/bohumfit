import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { isHCaptchaEnabled } from "../lib/hcaptcha";
import HCaptcha from "./HCaptcha";

afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
  delete window.hcaptcha;
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
});
