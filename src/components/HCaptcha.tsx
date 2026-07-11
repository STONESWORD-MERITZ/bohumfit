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
  className?: string;
};

const SCRIPT_SELECTOR = 'script[data-bohumfit-hcaptcha="true"]';
let hCaptchaLoader: Promise<HCaptchaApi> | null = null;

function loadHCaptcha(): Promise<HCaptchaApi> {
  if (window.hcaptcha) return Promise.resolve(window.hcaptcha);
  if (hCaptchaLoader) return hCaptchaLoader;

  hCaptchaLoader = new Promise<HCaptchaApi>((resolve, reject) => {
    const complete = () => {
      if (window.hcaptcha) {
        resolve(window.hcaptcha);
      } else {
        reject(new Error("hCaptcha 위젯을 초기화하지 못했습니다."));
      }
    };
    const fail = () => reject(new Error("hCaptcha 위젯을 불러오지 못했습니다."));
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

export default function HCaptcha({ onTokenChange, className }: HCaptchaProps) {
  const siteKey = hCaptchaSiteKey();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const onTokenChangeRef = useRef(onTokenChange);
  const widgetIdRef = useRef<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    onTokenChangeRef.current = onTokenChange;
  }, [onTokenChange]);

  useEffect(() => {
    if (!siteKey || !containerRef.current) return;
    let disposed = false;

    void loadHCaptcha()
      .then((hcaptcha) => {
        if (disposed || !containerRef.current) return;
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
            if (!disposed) {
              onTokenChangeRef.current("");
              setError("보안 확인을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.");
            }
          },
        });
      })
      .catch(() => {
        if (!disposed) setError("보안 확인을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.");
      });

    return () => {
      disposed = true;
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
