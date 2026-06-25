// BOHUMFIT-131: 토스트 알림(시각) — 4종 타입, 3초 자동 사라짐(fade out), 닫기 버튼.
import { useEffect, useState } from "react";

export type ToastType = "success" | "error" | "warning" | "info";
export type ToastData = { id: number; type: ToastType; message: string };

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
    const fadeAt = window.setTimeout(() => setLeaving(true), 2700);
    const closeAt = window.setTimeout(() => onClose(toast.id), 3000);
    return () => {
      window.clearTimeout(fadeAt);
      window.clearTimeout(closeAt);
    };
  }, [toast.id, onClose]);

  const s = STYLE[toast.type];
  return (
    <div
      role="status"
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
