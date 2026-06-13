// BOHUMFIT-045 디자인 시스템 v2(Mercury) — Callout. API 불변, 내부 스타일만 교체.
// 파스텔 배경 + 진한 동계열 텍스트, 좌측 강조선 제거(미니멀). 면책(legal)=옅은 그레이 박스.
import { type ReactNode } from "react";

export type CalloutVariant = "info" | "success" | "warning" | "danger" | "legal";

export interface CalloutProps {
  variant?: CalloutVariant;
  title?: ReactNode;
  className?: string;
  children: ReactNode;
}

const VARIANT_CLS: Record<CalloutVariant, { box: string; title: string; body: string }> = {
  info: {
    box: "border-accent-100 bg-accent-50",
    title: "text-accent-800",
    body: "text-accent-900/85",
  },
  success: {
    box: "border-success-100 bg-success-50",
    title: "text-success-700",
    body: "text-success-700/90",
  },
  warning: {
    box: "border-warning-100 bg-warning-50",
    title: "text-warning-700",
    body: "text-warning-700/90",
  },
  danger: {
    box: "border-danger-100 bg-danger-50",
    title: "text-danger-700",
    body: "text-danger-700/90",
  },
  // 면책·법적 고지 — 옅은 그레이 박스
  legal: {
    box: "border-line bg-ink-50",
    title: "text-ink-700",
    body: "text-ink-soft",
  },
};

export default function Callout({ variant = "info", title, className = "", children }: CalloutProps) {
  const cls = VARIANT_CLS[variant];
  return (
    <div
      role={variant === "warning" || variant === "danger" ? "alert" : "note"}
      className={`rounded-xl border px-4 py-3.5 ${cls.box} ${className}`}
    >
      {title && <p className={`mb-1 text-caption font-bold ${cls.title}`}>{title}</p>}
      <div className={`text-caption leading-relaxed break-keep ${cls.body}`}>{children}</div>
    </div>
  );
}
