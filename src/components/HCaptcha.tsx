import { useEffect, useRef, useState } from "react";
import { hCaptchaSiteKey } from "../lib/hcaptcha";

type HCaptchaOptions = {
  sitekey: string;
  callback: (token: string) => void;
  "expired-callback": () => void;
  "error-callback": (error?: string) => void;
  hl: string;
};

type HCaptchaApi = {
  render: (container: HTMLElement, options: HCaptchaOptions) => number;
  remove: (widgetId: number) => void;
  getResponse?: (widgetId: number) => string;
};

declare global {
  interface Window {
    hcaptcha?: HCaptchaApi;
    __bohumfitHCaptchaOnload?: () => void;
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
const TOKEN_RECOVERY_INTERVAL_MS = 5_000;
const API_ONLOAD_CALLBACK = "__bohumfitHCaptchaOnload";
const API_SRC = `https://js.hcaptcha.com/1/api.js?render=explicit&onload=${API_ONLOAD_CALLBACK}`;
const UNAVAILABLE_MESSAGE = "보안 확인을 불러오지 못했어요. 기존 인증 흐름으로 진행합니다.";
const EXPIRED_MESSAGE = "보안 확인이 만료되었어요. 기존 인증 흐름으로 진행합니다.";
let hCaptchaLoader: Promise<HCaptchaApi> | null = null;
let hCaptchaReady = false;

function loadHCaptcha(): Promise<HCaptchaApi> {
  if (hCaptchaReady && !window.hcaptcha) {
    hCaptchaReady = false;
    hCaptchaLoader = null;
  }
  if (hCaptchaReady && window.hcaptcha) return Promise.resolve(window.hcaptcha);
  if (hCaptchaLoader) return hCaptchaLoader;

  hCaptchaLoader = new Promise<HCaptchaApi>((resolve, reject) => {
    let script: HTMLScriptElement | null = null;
    let timeoutId: number | null = null;
    let settled = false;

    const cleanup = () => {
      if (timeoutId !== null) window.clearTimeout(timeoutId);
      script?.removeEventListener("error", fail);
      if (window.__bohumfitHCaptchaOnload === complete) {
        delete window.__bohumfitHCaptchaOnload;
      }
    };
    const rejectLoad = (error: Error) => {
      if (settled) return;
      settled = true;
      hCaptchaReady = false;
      cleanup();
      script?.remove();
      hCaptchaLoader = null;
      reject(error);
    };
    const complete = () => {
      if (settled) return;
      const hcaptcha = window.hcaptcha;
      if (!hcaptcha) {
        rejectLoad(new Error("hCaptcha 위젯을 초기화하지 못했습니다."));
        return;
      }
      settled = true;
      hCaptchaReady = true;
      if (script) script.dataset.bohumfitHcaptchaReady = "true";
      cleanup();
      resolve(hcaptcha);
    };
    const fail = () => rejectLoad(new Error("hCaptcha 위젯을 불러오지 못했습니다."));

    window.__bohumfitHCaptchaOnload = complete;
    script = document.querySelector<HTMLScriptElement>(SCRIPT_SELECTOR);
    if (script && new URL(script.src).searchParams.get("onload") !== API_ONLOAD_CALLBACK) {
      script.remove();
      script = null;
    }

    let shouldAppend = false;
    if (!script) {
      shouldAppend = true;
      script = document.createElement("script");
      script.src = API_SRC;
      script.async = true;
      script.defer = true;
      script.dataset.bohumfitHcaptcha = "true";
    }

    script.addEventListener("error", fail, { once: true });

    if (script.dataset.bohumfitHcaptchaReady === "true" && window.hcaptcha) {
      complete();
      return;
    }

    timeoutId = window.setTimeout(
      () => rejectLoad(new Error("hCaptcha API 준비 시간이 초과되었습니다.")),
      LOAD_TIMEOUT_MS,
    );
    if (shouldAppend) document.head.appendChild(script);
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
    let tokenReceived = false;
    let responsePollId: number | null = null;
    const stopResponsePoll = () => {
      if (responsePollId === null) return;
      window.clearInterval(responsePollId);
      responsePollId = null;
    };
    const reportUnavailable = (message = UNAVAILABLE_MESSAGE) => {
      if (disposed || unavailableReported) return;
      unavailableReported = true;
      tokenReceived = false;
      stopResponsePoll();
      onTokenChangeRef.current("");
      onUnavailableRef.current?.();
      setError(message);
    };
    const acceptToken = (token: string) => {
      if (disposed || !token) return;
      unavailableReported = false;
      tokenReceived = true;
      stopResponsePoll();
      setError("");
      onTokenChangeRef.current(token);
      onReadyRef.current?.();
    };

    void loadHCaptcha()
      .then((hcaptcha) => {
        if (disposed || !containerRef.current || widgetIdRef.current !== null) return;
        const widgetId = hcaptcha.render(containerRef.current, {
          sitekey: siteKey,
          hl: "ko",
          callback: (token) => {
            acceptToken(token);
          },
          "expired-callback": () => {
            reportUnavailable(EXPIRED_MESSAGE);
          },
          "error-callback": () => {
            reportUnavailable();
          },
        });
        if (typeof widgetId !== "number") {
          throw new Error("hCaptcha 위젯 ID를 받지 못했습니다.");
        }
        widgetIdRef.current = widgetId;
        unavailableReported = false;
        setError("");
        onReadyRef.current?.();
        if (hcaptcha.getResponse && !tokenReceived) {
          responsePollId = window.setInterval(() => {
            if (disposed || unavailableReported || widgetIdRef.current === null) return;
            try {
              acceptToken(hcaptcha.getResponse?.(widgetIdRef.current) || "");
            } catch {
              reportUnavailable();
            }
          }, TOKEN_RECOVERY_INTERVAL_MS);
        }
      })
      .catch(() => reportUnavailable());

    return () => {
      disposed = true;
      stopResponsePoll();
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
