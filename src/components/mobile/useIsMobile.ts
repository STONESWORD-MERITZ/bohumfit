// BOHUMFIT-266 — 모바일 뷰 분기 훅.
//
//   ★CSS 분기(`md:hidden` / `hidden md:block`)를 쓰지 않는 이유: 그러면 데스크톱·모바일 마크업이
//     **둘 다 DOM에 남아** 데스크톱 노드 수가 늘어난다. 266의 제1원칙은 "데스크톱 렌더 회귀 0"이므로
//     JS로 판정해 **한쪽만 렌더**한다.
//   ★matchMedia가 없는 환경(테스트·구형 브라우저)에서는 **데스크톱으로 폴백**한다 —
//     기존 경로가 언제나 기본값이어야 안전하다.
import { useEffect, useState } from "react";

/** Tailwind `md` 브레이크포인트 미만을 모바일로 본다(≤767px). */
export const MOBILE_QUERY = "(max-width: 767px)";

function matches(query: string): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  try {
    return window.matchMedia(query).matches;
  } catch {
    return false; // 폴백 = 데스크톱
  }
}

export function useIsMobile(query: string = MOBILE_QUERY): boolean {
  // 초기값도 동기적으로 판정한다 — 첫 페인트에서 데스크톱 표가 잠깐 보였다 사라지는 깜빡임을 막는다.
  const [isMobile, setIsMobile] = useState(() => matches(query));

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    let mql: MediaQueryList;
    try {
      mql = window.matchMedia(query);
    } catch {
      return;
    }
    const onChange = () => setIsMobile(mql.matches);
    onChange(); // 마운트 시점의 실제 폭을 반영(초기값 계산 이후 회전·리사이즈 대비)
    // Safari 13 이하는 addEventListener를 지원하지 않아 addListener로 폴백한다.
    if (typeof mql.addEventListener === "function") {
      mql.addEventListener("change", onChange);
      return () => mql.removeEventListener("change", onChange);
    }
    mql.addListener(onChange);
    return () => mql.removeListener(onChange);
  }, [query]);

  return isMobile;
}
