// BOHUMFIT-131: 토스트 알림(시각) — 4종 타입, 3초 자동 사라짐(fade out), 닫기 버튼.
import { useEffect, useState } from "react";

export type ToastType = "success" | "error" | "warning" | "info";
/**
 * BOHUMFIT-265: 되돌리기 액션·지속시간 additive.
 *  ★기본값은 기존과 동일(3초·액션 없음) — 기존 호출부 동작 불변.
 *  ★되돌리기 토스트(6초)는 해지 확정·복사 완료·분석 완료 3곳에서만 쓴다(남용 금지 — tokens.ts 참조).
 */
export type ToastAction = { label: string; onAct: () => void };
export type ToastData = {
  id: number;
  type: ToastType;
  message: string;
  durationMs?: number;
  action?: ToastAction;
};

const STYLE: Record<ToastType, { bar: string; icon: string; tone: string }> = {
  success: { bar: "border-l-emerald-500", icon: "✓", tone: "text-emerald-600" },
  error: { bar: "border-l-red-500", icon: "!", tone: "text-red-600" },
  warning: { bar: "border-l-amber-500", icon: "▲", tone: "text-amber-600" },
  info: { bar: "border-l-sky-500", icon: "i", tone: "text-sky-600" },
};

export function ToastItem({
  toast,
  onClose,
}: {
  toast: ToastData;
  onClose: (id: number) => void;
}) {
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    // BOHUMFIT-265: 지속시간은 토스트별로 지정 가능(미지정 = 기존 3초 그대로).
    const total = toast.durationMs ?? 3000;
    const fadeAt = window.setTimeout(() => setLeaving(true), Math.max(0, total - 300));
    const closeAt = window.setTimeout(() => onClose(toast.id), total);
    return () => {
      window.clearTimeout(fadeAt);
      window.clearTimeout(closeAt);
    };
  }, [toast.id, toast.durationMs, onClose]);

  const s = STYLE[toast.type];
  // BOHUMFIT-137: 오류·경고는 role="alert"(스크린리더 즉시), 그 외 정보성은 status.
  const isUrgent = toast.type === "error" || toast.type === "warning";
  return (
    <div
      role={isUrgent ? "alert" : "status"}
      aria-live={isUrgent ? "assertive" : "polite"}
      className={`pointer-events-auto flex items-start gap-3 rounded-[10px] border border-gray-100 border-l-4 ${s.bar} bg-white px-4 py-3 shadow-[0_6px_24px_rgba(0,0,0,0.12)] transition-all duration-300 ${
        leaving ? "translate-y-2 opacity-0" : "translate-y-0 opacity-100"
      }`}
    >
      <span
        className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gray-50 text-[12px] font-bold ${s.tone}`}
      >
        {s.icon}
      </span>
      <p className="flex-1 text-[13px] font-medium leading-5 text-gray-800">{toast.message}</p>
      {/* BOHUMFIT-265: 되돌리기 — 누르면 즉시 실행하고 토스트를 닫는다. */}
      {toast.action && (
        <button
          type="button"
          onClick={() => {
            toast.action?.onAct();
            onClose(toast.id);
          }}
          className="m-tap shrink-0 px-2 text-[13px] font-bold text-accent-600 underline"
        >
          {toast.action.label}
        </button>
      )}
      <button
        type="button"
        onClick={() => onClose(toast.id)}
        aria-label="알림 닫기"
        className="shrink-0 text-gray-300 transition-colors hover:text-gray-500"
      >
        ✕
      </button>
    </div>
  );
}
