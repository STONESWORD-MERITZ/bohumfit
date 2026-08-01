// BOHUMFIT-265 — 스와이프 액션 카드(좌=해지, 우=복원).
//   해지 확정 시 회색 면 + 취소선 상태로 남기고, 6초 되돌리기 토스트로 복구한다(★266에서 적용).
//   ★임계값(72px)을 넘겨야 확정 — 스크롤 중 오조작을 막는다.
//   ★적용은 266~ — 265에서는 정의만 한다.
import { useRef, useState, type ReactNode } from "react";
import { MOBILE_LAYOUT, SWIPE } from "./tokens";

export interface SwipeActionCardProps {
  children: ReactNode;
  /** 좌 스와이프 — 해지. */
  onCancel: () => void;
  /** 우 스와이프 — 복원(해지 상태에서만 동작). */
  onRestore?: () => void;
  /** 해지된 상태(회색 면 + 취소선). */
  cancelled?: boolean;
  className?: string;
}

export default function SwipeActionCard({
  children,
  onCancel,
  onRestore,
  cancelled = false,
  className = "",
}: SwipeActionCardProps) {
  const startX = useRef<number | null>(null);
  const [dx, setDx] = useState(0);

  const finish = (delta: number) => {
    // ★임계값 미만이면 아무 일도 일어나지 않는다(제자리 복귀).
    if (delta <= -SWIPE.threshold && !cancelled) onCancel();
    else if (delta >= SWIPE.threshold && cancelled) onRestore?.();
    setDx(0);
    startX.current = null;
  };

  return (
    <div
      data-testid="swipe-card"
      data-cancelled={cancelled ? "true" : "false"}
      className={`m-swipe-card border border-line ${cancelled ? "bg-ink-50 text-ink-400 line-through" : "bg-white"} ${className}`}
      style={{
        borderRadius: MOBILE_LAYOUT.radiusCard,
        padding: MOBILE_LAYOUT.gutter,
        transform: `translateX(${dx}px)`,
        transition: dx === 0 ? "transform 160ms ease-out" : undefined,
      }}
      onTouchStart={(e) => {
        startX.current = e.touches[0]?.clientX ?? null;
      }}
      onTouchMove={(e) => {
        if (startX.current === null) return;
        const delta = (e.touches[0]?.clientX ?? 0) - startX.current;
        // 과도한 이동을 막아 화면이 흔들리지 않게 한다.
        setDx(Math.max(-SWIPE.maxTravel, Math.min(SWIPE.maxTravel, delta)));
      }}
      onTouchEnd={() => finish(dx)}
      onTouchCancel={() => finish(0)}
    >
      {children}
    </div>
  );
}
