// BOHUMFIT-265 — 서비스워커 업데이트 안내(264가 남긴 훅 사용).
//   ★자동 새로고침 금지: 새 버전을 감지해도 사용자가 "새로고침"을 누르기 전에는 아무것도 하지 않는다
//   (작성 중인 입력·분석 결과가 날아가지 않도록 — 264가 install 단계 자동 skipWaiting을 제거해 둔 이유).
//   ★배선 위치: `src/main.tsx`에서 `<App/>` 형제로 둔다(264 InstallPrompt와 동일 패턴).
//   대기 중인 새 버전이 없으면 아무것도 렌더하지 않으므로 기존 화면 레이아웃에 영향이 없다.
import { useEffect, useState } from "react";
import { applyServiceWorkerUpdate, watchServiceWorkerUpdate } from "../../lib/pwa";
// BOHUMFIT-278: 하단 표면 단일 계약 — 시트/모달보다 아래, 네비·액션 바보다 위(275 A-F2:
//   기존 z-[9997]은 전체표(9990)·모달(1000/50) **위를 덮었다**).
import { BANNER_BELOW, BOTTOM_SURFACE_Z, useBottomSurfaceOffset } from "./bottomSurface";
import { MOBILE_LAYOUT, MOBILE_TOUCH } from "./tokens";

export default function UpdatePrompt() {
  const [waiting, setWaiting] = useState(false);
  const [applying, setApplying] = useState(false);

  useEffect(() => watchServiceWorkerUpdate(() => setWaiting(true)), []);

  // BOHUMFIT-278: 네비·액션 바 위로 쌓는다.
  const bottomOffset = useBottomSurfaceOffset(BANNER_BELOW, waiting);

  if (!waiting) return null;

  return (
    <div
      role="status"
      data-testid="sw-update-prompt"
      className="fixed inset-x-0 border-t border-line bg-white"
      style={{
        zIndex: BOTTOM_SURFACE_Z.banner,
        bottom: bottomOffset,
        paddingLeft: MOBILE_LAYOUT.gutter,
        paddingRight: MOBILE_LAYOUT.gutter,
        paddingTop: 12,
        // ★아래에 네비·액션 바가 있으면 그쪽이 인디케이터 여백을 책임진다(이중 적용 방지).
        paddingBottom: bottomOffset > 0 ? 12 : `calc(env(safe-area-inset-bottom, 0px) + 12px)`,
      }}
    >
      <div className="flex items-center gap-3">
        <p className="flex-1 text-[15px] leading-[1.55] text-ink-900">
          새 버전이 준비됐습니다. 새로고침하면 최신 화면으로 바뀝니다.
        </p>
        <button
          type="button"
          onClick={() => {
            setApplying(true);
            applyServiceWorkerUpdate();
          }}
          disabled={applying}
          className="shrink-0 bg-accent-600 px-4 font-bold text-white disabled:opacity-60"
          style={{ minHeight: MOBILE_TOUCH.tap, borderRadius: MOBILE_LAYOUT.radiusBtn, fontSize: 15 }}
        >
          {applying ? "적용 중…" : "새로고침"}
        </button>
        <button
          type="button"
          aria-label="나중에"
          onClick={() => setWaiting(false)}
          className="m-tap shrink-0 px-2 text-[15px] text-ink-soft"
        >
          나중에
        </button>
      </div>
    </div>
  );
}
