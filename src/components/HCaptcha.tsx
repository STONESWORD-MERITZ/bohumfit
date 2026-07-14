import { useEffect, useRef, useState } from "react";
import { hCaptchaSiteKey } from "../lib/hcaptcha";

type HCaptchaOptions = {
  sitekey: string;
  callback: (token: string) => void;
  "expired-callback": () => void;
  "error-callback": () => void;
  hl: string;
};

type HCaptchaApi = {
  render: (container: HTMLElement, options: HCaptchaOptions) => number;
  remove: (widgetId: number) => void;
};

declare global {
  interface Window {
    hcaptcha?: HCaptchaApi;
  }
}

type HCaptchaProps = {
  onTokenChange: (token: string) => void;
  onReady?: () => void;
  onUnavailable?: () => void;
  className?: string;
};

const SCRIPT_SELECTOR = 'script[data-bohumfit-hcaptcha="true"]';
const LOAD_TIMEOUT_MS = 5_000;
const UNAVAILABLE_MESSAGE = "보안 확인을 불러오지 못했어요. 기존 인증 흐름으로 진행합니다.";
let hCaptchaLoader: Promise<HCaptchaApi> | null = null;

function loadHCaptcha(): Promise<HCaptchaApi> {
  if (window.hcaptcha) return Promise.resolve(window.hcaptcha);
  if (hCaptchaLoader) return hCaptchaLoader;

  hCaptchaLoader = new Promise<HCaptchaApi>((resolve, reject) => {
    const rejectLoad = (error: Error) => {
      hCaptchaLoader = null;
      reject(error);
    };
    const complete = () => {
      if (window.hcaptcha) {
        resolve(window.hcaptcha);
      } else {
        rejectLoad(new Error("hCaptcha 위젯을 초기화하지 못했습니다."));
      }
    };
    const fail = () => rejectLoad(new Error("hCaptcha 위젯을 불러오지 못했습니다."));
    const existing = document.querySelector<HTMLScriptElement>(SCRIPT_SELECTOR);
    if (existing) {
      existing.addEventListener("load", complete, { once: true });
      existing.addEventListener("error", fail, { once: true });
      return;
    }

    const script = document.createElement("script");
    script.src = "https://js.hcaptcha.com/1/api.js?render=explicit";
    script.async = true;
    script.defer = true;
    script.dataset.bohumfitHcaptcha = "true";
    script.addEventListener("load", complete, { once: true });
    script.addEventListener("error", fail, { once: true });
    document.head.appendChild(script);
  });

  return hCaptchaLoader;
}

export default function HCaptcha({ onTokenChange, onReady, onUnavailable, className }: HCaptchaProps) {
  const siteKey = hCaptchaSiteKey();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const onTokenChangeRef = useRef(onTokenChange);
  const onReadyRef = useRef(onReady);
  const onUnavailableRef = useRef(onUnavailable);
  const widgetIdRef = useRef<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    onTokenChangeRef.current = onTokenChange;
    onReadyRef.current = onReady;
    onUnavailableRef.current = onUnavailable;
  }, [onReady, onTokenChange, onUnavailable]);

  useEffect(() => {
    if (!siteKey || !containerRef.current) return;
    let disposed = false;
    let unavailableReported = false;
    const reportUnavailable = () => {
      if (disposed || unavailableReported) return;
      unavailableReported = true;
      onTokenChangeRef.current("");
      onUnavailableRef.current?.();
      setError(UNAVAILABLE_MESSAGE);
    };
    // A CSP/network failure does not consistently dispatch a script error in
    // every browser. Auth screens that opt into fail-open must not wait forever.
    const loadTimeout = onUnavailableRef.current
      ? window.setTimeout(reportUnavailable, LOAD_TIMEOUT_MS)
      : null;

    void loadHCaptcha()
      .then((hcaptcha) => {
        if (disposed || !containerRef.current) return;
        if (loadTimeout !== null) window.clearTimeout(loadTimeout);
        widgetIdRef.current = hcaptcha.render(containerRef.current, {
          sitekey: siteKey,
          hl: "ko",
          callback: (token) => {
            if (!disposed) onTokenChangeRef.current(token);
          },
          "expired-callback": () => {
            if (!disposed) onTokenChangeRef.current("");
          },
          "error-callback": () => {
            reportUnavailable();
          },
        });
        unavailableReported = false;
        setError("");
        onReadyRef.current?.();
      })
      .catch(reportUnavailable);

    return () => {
      disposed = true;
      if (loadTimeout !== null) window.clearTimeout(loadTimeout);
      if (widgetIdRef.current !== null && window.hcaptcha) {
        window.hcaptcha.remove(widgetIdRef.current);
        widgetIdRef.current = null;
      }
    };
  }, [siteKey]);

  if (!siteKey) return null;

  return (
    <div className={className}>
      <div ref={containerRef} />
      {error && <p className="mt-2 text-xs font-semibold text-red-500">{error}</p>}
    </div>
  );
}
