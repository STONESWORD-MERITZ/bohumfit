// BOHUMFIT-269b — 모바일 하단 네비게이션.
//
//   ★탭은 **모바일 개편이 끝난 화면**만 담는다(263~269a). 덜 다듬어진 화면으로 유도하지 않기 위해서다.
//     실손 계산·요금제·히스토리·자료 받기를 뺀 사유는 269b 태스크 문서에 적었다.
//   ★라우트를 신설하지 않는다 — 전부 기존 `NAV`에 있던 경로다.
//   ★세이프에어리어: 홈 인디케이터가 있는 기기에선 그만큼 밀어 올리고, 없는 기기에선 여백이 생기지 않는다
//     (`env(safe-area-inset-bottom)`은 인디케이터가 없으면 0이다).
//   ★겹침 회피: 268a 바텀시트가 열려 있거나 분석이 진행 중이면 **네비를 감춘다**.
//     그 상태를 알기 위해 Disclosure를 고치지 않고 **네비가 스스로 DOM을 관찰**한다 —
//     268a·268b 동작에는 손대지 않고 겹침만 피하는 방법이다.
import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { MOBILE_TOUCH } from "./tokens";
import { BOTTOM_NAV_TABS } from "./bottomNavTabs";

/**
 * 시트가 열렸거나 분석이 진행 중인지 관찰한다.
 *   ★다른 컴포넌트를 수정하지 않고 알아내기 위한 방법이다. 대상은 두 가지뿐이라 관찰 비용이 작다.
 */
function useOverlayActive(): boolean {
  const [active, setActive] = useState(false);

  useEffect(() => {
    if (typeof document === "undefined" || typeof MutationObserver === "undefined") return;
    const check = () => {
      const sheetOpen = !!document.querySelector('[role="dialog"][aria-modal="true"]');
      const analyzing = !!document.querySelector("[data-analysis-busy]");
      setActive(sheetOpen || analyzing);
    };
    check();
    const observer = new MutationObserver(check);
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, []);

  return active;
}

export default function MobileBottomNav() {
  const overlayActive = useOverlayActive();
  // 시트·분석 중에는 아예 렌더하지 않는다(z-index 다툼 자체를 만들지 않는다).
  if (overlayActive) return null;

  return (
    <nav
      data-testid="mobile-bottom-nav"
      aria-label="주요 화면"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-white"
      // 홈 인디케이터가 있으면 그만큼만 더 밀어 올린다(없으면 0이라 여백이 생기지 않는다).
      style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
    >
      <ul className="flex">
        {BOTTOM_NAV_TABS.map(({ to, label, Icon, match }) => {
          return (
            <li key={to} className="flex-1">
              <NavLink
                to={to}
                data-testid={`bottom-nav-${label}`}
                // 쿼리스트링이 붙는 탭(`/disclosure?mode=agent`)은 경로로 활성 판정한다.
                className={({ isActive }) => {
                  const active = isActive || window.location.pathname.startsWith(match);
                  return `flex flex-col items-center justify-center gap-0.5 px-1 ${
                    active ? "text-accent-600" : "text-ink-soft"
                  }`;
                }}
                style={{ minHeight: MOBILE_TOUCH.tap, paddingTop: 8, paddingBottom: 8 }}
              >
                {({ isActive }) => {
                  const active = isActive || window.location.pathname.startsWith(match);
                  return (
                    <>
                      <Icon aria-hidden className="h-5 w-5 shrink-0" />
                      {/* ★265 하한(15px) 준수. 375px ÷ 4탭 = 약 93px이라 한글 4글자가 뭉개지지 않는다. */}
                      <span className={`whitespace-nowrap text-[15px] leading-[1.2] ${active ? "font-bold" : "font-medium"}`}>
                        {label}
                      </span>
                    </>
                  );
                }}
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
