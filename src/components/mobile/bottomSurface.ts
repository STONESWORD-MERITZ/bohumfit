// BOHUMFIT-278 — 하단 고정 표면(bottom surface) 단일 계약.
//
//   ★왜 필요했나(275 A-F2): 하단에 붙는 요소들이 z-index를 **각자** 정해 왔다
//     — 네비 40 / 액션 바 40 / 구형 CTA 50 / 설치 안내 50 / 업데이트 안내 9997 / 토스트 9999.
//     서로의 존재를 모르니 조합에 따라 겹침이 **확정적으로** 생겼다.
//   ★273은 이 문제를 결과 화면 한 곳에서만 풀었다(액션 바가 네비 실측 높이를 관찰해 위로 쌓임).
//     278은 그 방식을 **깨지 않고 공용 훅으로 승격**해 설치·업데이트 안내에도 같은 규칙을 준다.
//
//   ★층위 결정(275 실측 반영):
//     시트/모달(9990~9998) > **토스트(9999)** > 안내 배너 > 액션 바 > 하단 네비 > 콘텐츠
//     ─ 토스트만 시트보다 위다. 되돌리기 토스트(265, 6초)는 시트를 닫은 직후에도 떠야 하고,
//       가려지면 되돌릴 기회를 잃는다. 패킷 권장 순서에서 이 한 칸만 의도적으로 다르며 사유를 남긴다.
import { useEffect, useState } from "react";

import { BOTTOM_NAV_HEIGHT } from "./bottomNavTabs";

/** 하단 표면 z 층위 — ★새 하단 요소는 반드시 이 토큰을 쓴다(숫자 직접 기입 금지). */
export const BOTTOM_SURFACE_Z = {
  /** 하단 네비(269b) — 가장 아래. */
  nav: 40,
  /** 결과 주 액션 바(265·273) — 네비 위에 쌓인다. */
  action: 45,
  /** 설치·업데이트 안내 — 네비·액션 바보다 위지만 시트/모달보다는 아래. */
  banner: 60,
  /** 전체표·시트·모달 — 화면을 덮는 표면. */
  overlay: 9990,
  /** 토스트 — ★유일하게 시트보다 위(위 주석의 사유). */
  toast: 9999,
} as const;

/** 관찰 대상 — 하단을 실제로 점유하는 요소의 마커. */
const NAV_SELECTOR = '[data-testid="mobile-bottom-nav"]';
const ACTION_SELECTOR = '[data-testid="primary-action-bar"]';

/**
 * 지정한 하단 요소들이 실제로 차지하는 높이(px)를 합산해 돌려준다.
 *
 *   ★상수가 아니라 `offsetHeight`를 재는 이유(273에서 확정된 근거를 그대로 승계):
 *     ①상수(60)와 실측(57)이 달라 **틈이 생긴다** ②네비는 시트·분석 중 **스스로 사라진다**
 *     ③`offsetHeight`에는 그 요소가 적용한 `env(safe-area-inset-bottom)`가 **이미 포함**돼
 *       세이프에어리어 이중 적용이 구조적으로 생기지 않는다.
 *   ★관찰만 한다 — 대상 컴포넌트는 고치지 않는다(269b가 시트를 관찰한 방식과 같다).
 */
export function useBottomSurfaceOffset(selectors: readonly string[], enabled = true): number {
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    if (!enabled) return;
    if (typeof document === "undefined" || typeof MutationObserver === "undefined") return;

    let resizeObserver: ResizeObserver | null = null;
    let watched: Element[] = [];

    const measure = (elements: Element[]) =>
      setOffset(
        elements.reduce((sum, element) => {
          const height = (element as HTMLElement).offsetHeight;
          // ResizeObserver가 없거나 높이를 못 재면 상수로 폴백한다(겹침을 남기는 것보다 낫다).
          return sum + (height || BOTTOM_NAV_HEIGHT);
        }, 0),
      );

    const check = () => {
      const found = selectors
        .map((selector) => document.querySelector(selector))
        .filter((element): element is Element => element !== null);
      const changed =
        found.length !== watched.length || found.some((element, index) => element !== watched[index]);
      if (changed) {
        resizeObserver?.disconnect();
        watched = found;
        if (found.length && typeof ResizeObserver !== "undefined") {
          resizeObserver = new ResizeObserver(() => measure(found));
          found.forEach((element) => resizeObserver!.observe(element));
        }
      }
      measure(found);
    };

    check();
    const observer = new MutationObserver(check);
    observer.observe(document.body, { childList: true, subtree: true });
    window.addEventListener("resize", check);
    window.addEventListener("orientationchange", check);
    return () => {
      observer.disconnect();
      resizeObserver?.disconnect();
      window.removeEventListener("resize", check);
      window.removeEventListener("orientationchange", check);
    };
  }, [selectors, enabled]);

  return offset;
}

/**
 * ★페이지 하단 여백 계산용 — **하단을 점유하는 표면 전부**.
 *   275 A-F2 실측: 네비+액션 바+배너가 동시에 뜨면 점유가 231~265px까지 커져,
 *   `BOTTOM_NAV_HEIGHT` 상수만 빼두던 기존 여백으로는 **본문 마지막 줄이 가려졌다**(실브라우저 확인).
 *   요소가 더 늘어나도 이 배열에만 추가하면 여백이 자동으로 따라온다.
 */
export const PAGE_BOTTOM_SURFACES = [
  NAV_SELECTOR,
  ACTION_SELECTOR,
  '[data-testid="sw-update-prompt"]',
  '[data-testid="install-prompt"]',
] as const;

/** 액션 바가 피해야 하는 표면 = 하단 네비(273 계약 그대로). */
export const ACTION_BAR_BELOW = [NAV_SELECTOR] as const;
/** 안내 배너가 피해야 하는 표면 = 하단 네비 + 액션 바. */
export const BANNER_BELOW = [NAV_SELECTOR, ACTION_SELECTOR] as const;
