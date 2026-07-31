// BOHUMFIT-264 — PWA 셸 지원 유틸(서비스워커 등록 · 설치 프롬프트 상태).
//   화면 디자인·기존 로직은 건드리지 않는다. 등록 실패는 조용히 무시해 앱 동작을 막지 않는다.

const DISMISS_KEY = "bohumfit_install_dismissed_v1";
/** 한 번 닫으면 이 기간 동안 다시 띄우지 않는다(중복 노출 방지). */
const DISMISS_DAYS = 30;

export type InstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

/** 서비스워커 등록 — 프로덕션 빌드에서만(개발 중 HMR 간섭 방지). */
export function registerServiceWorker(): void {
  if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;
  if (!import.meta.env.PROD) return;
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // 등록 실패는 기능 저하일 뿐 — 앱은 그대로 동작한다.
    });
  });
}

/** 이미 설치된 앱(스탠드얼론)으로 실행 중인지. */
export function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  const iosStandalone = (window.navigator as Navigator & { standalone?: boolean }).standalone;
  return window.matchMedia?.("(display-mode: standalone)")?.matches === true || iosStandalone === true;
}

/** iOS Safari는 beforeinstallprompt를 지원하지 않아 안내 문구로 대체한다. */
export function isIos(): boolean {
  if (typeof navigator === "undefined") return false;
  return /iphone|ipad|ipod/i.test(navigator.userAgent);
}

export function isInstallDismissed(now: number = Date.now()): boolean {
  try {
    const raw = window.localStorage.getItem(DISMISS_KEY);
    if (!raw) return false;
    const until = Number(raw);
    if (!Number.isFinite(until)) return false;
    return now < until;
  } catch {
    return false; // 저장소 접근 불가(프라이빗 모드 등)면 배너를 막지 않는다.
  }
}

export function rememberInstallDismiss(now: number = Date.now()): void {
  try {
    window.localStorage.setItem(DISMISS_KEY, String(now + DISMISS_DAYS * 24 * 60 * 60 * 1000));
  } catch {
    // 저장 실패는 무시(다음 방문에 다시 보일 뿐).
  }
}

/** 설치 배너를 지금 노출해도 되는지 — 설치됨·최근 닫음이면 숨긴다. */
export function shouldShowInstallHint(options: {
  standalone: boolean;
  dismissed: boolean;
  hasPrompt: boolean;
  ios: boolean;
}): boolean {
  if (options.standalone || options.dismissed) return false;
  return options.hasPrompt || options.ios;
}
