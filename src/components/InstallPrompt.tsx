// BOHUMFIT-264 — 홈 화면 설치 안내 배너.
//   ★기존 화면 디자인·레이아웃은 건드리지 않는다: 화면 흐름 밖(fixed 하단)에 얹고,
//   설치됨·최근 닫음이면 렌더 자체를 하지 않는다(중복 노출 방지).
import { X } from "lucide-react";
// BOHUMFIT-278: 하단 표면 단일 계약 — 네비·액션 바 위로 쌓이고 z는 토큰을 쓴다(275 A-F2).
import { BANNER_BELOW, BOTTOM_SURFACE_Z, useBottomSurfaceOffset } from "./mobile/bottomSurface";
import { useEffect, useState } from "react";

import {
  isInstallDismissed,
  isIos,
  isStandalone,
  rememberInstallDismiss,
  shouldShowInstallHint,
  type InstallPromptEvent,
} from "../lib/pwa";

export default function InstallPrompt() {
  const ios = isIos();
  const [promptEvent, setPromptEvent] = useState<InstallPromptEvent | null>(null);
  // iOS Safari는 beforeinstallprompt가 없어 안내 문구로 대체한다(공유 → 홈 화면에 추가).
  //   effect에서 setState 하지 않도록 초기 상태로 계산한다(cascading render 방지).
  const [visible, setVisible] = useState(() => ios && !isStandalone() && !isInstallDismissed());

  useEffect(() => {
    if (isStandalone() || isInstallDismissed()) return;

    // Android·데스크탑 Chrome 계열: 브라우저 기본 배너를 가로채 우리 시점에 안내한다.
    const onBeforeInstall = (event: Event) => {
      event.preventDefault();
      setPromptEvent(event as InstallPromptEvent);
      setVisible(true);
    };
    window.addEventListener("beforeinstallprompt", onBeforeInstall);

    const onInstalled = () => setVisible(false);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstall);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  // BOHUMFIT-278: 하단 네비·액션 바가 차지한 높이만큼 위로 띄운다.
  //   ★훅은 early return **앞**에서 호출한다(rules-of-hooks). `show`가 false면 관찰만 하고 렌더는 없다.
  const bottomOffset = useBottomSurfaceOffset(BANNER_BELOW);

  const show =
    visible &&
    shouldShowInstallHint({
      standalone: isStandalone(),
      dismissed: isInstallDismissed(),
      hasPrompt: !!promptEvent,
      ios,
    });
  if (!show) return null;

  const close = () => {
    rememberInstallDismiss();
    setVisible(false);
  };

  const install = async () => {
    if (!promptEvent) return;
    await promptEvent.prompt();
    await promptEvent.userChoice.catch(() => null);
    setPromptEvent(null);
    setVisible(false);
  };

  return (
    <div
      role="dialog"
      aria-label="앱 설치 안내"
      data-testid="install-prompt"
      className="fixed inset-x-3 rounded-xl border border-accent-100 bg-white p-4 shadow-lg md:left-auto md:right-4 md:w-[360px]"
      style={{
        zIndex: BOTTOM_SURFACE_Z.banner,
        // ★네비·액션 바가 있으면 그 위로 올라간다. `offsetHeight`에 각 요소의 세이프에어리어가
        //   이미 포함돼 있어 이중 적용이 생기지 않는다(273 근거 승계).
        bottom: bottomOffset > 0 ? bottomOffset + 12 : 12,
        ...(bottomOffset > 0 ? null : { marginBottom: "env(safe-area-inset-bottom)" }),
      }}
    >
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[10px] bg-accent-600 text-lg font-extrabold text-white">
          ㅍ
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-ink-900">보험핏을 홈 화면에 추가</p>
          <p className="mt-0.5 text-[13px] leading-relaxed text-ink-soft">
            {ios && !promptEvent
              ? "공유 버튼 → “홈 화면에 추가”를 누르면 앱처럼 쓸 수 있어요."
              : "앱처럼 바로 열고, 연결이 끊겨도 마지막 화면을 볼 수 있어요."}
          </p>
          {!!promptEvent && (
            <button
              type="button"
              onClick={install}
              className="mt-3 min-h-[44px] w-full rounded-[10px] bg-accent-600 px-4 text-sm font-bold text-white hover:bg-accent-700"
            >
              홈 화면에 추가
            </button>
          )}
        </div>
        <button
          type="button"
          onClick={close}
          aria-label="설치 안내 닫기"
          className="-mr-1 -mt-1 flex h-11 w-11 items-center justify-center rounded-lg text-ink-400 hover:bg-ink-50"
        >
          <X size={18} />
        </button>
      </div>
    </div>
  );
}
