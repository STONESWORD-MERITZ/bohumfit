// BOHUMFIT-044 디자인 시스템 — Callout (안내·경고·면책 박스 통일)
// 면책·비저장 문구는 variant="legal" 로 통일한다.
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
    box: "border-navy-200 bg-navy-50 border-l-4 border-l-navy-600",
    title: "text-navy-800",
    body: "text-navy-900/80",
  },
  success: {
    box: "border-success-100 bg-success-50 border-l-4 border-l-success-600",
    title: "text-success-700",
    body: "text-success-700/90",
  },
  warning: {
    box: "border-warning-100 bg-warning-50 border-l-4 border-l-warning-600",
    title: "text-warning-700",
    body: "text-warning-700/90",
  },
  danger: {
    box: "border-danger-100 bg-danger-50 border-l-4 border-l-danger-600",
    title: "text-danger-700",
    body: "text-danger-700/90",
  },
  // 면책·법적 고지 — 차분한 회색, 본문보다 작게
  legal: {
    box: "border-line bg-canvas",
    title: "text-ink",
    body: "text-ink-soft",
  },
};

export default function Callout({ variant = "info", title, className = "", children }: CalloutProps) {
  const cls = VARIANT_CLS[variant];
  return (
    <div
      role={variant === "warning" || variant === "danger" ? "alert" : "note"}
      className={`rounded-lg border px-4 py-3 ${cls.box} ${className}`}
    >
      {title && <p className={`mb-1 text-caption font-bold ${cls.title}`}>{title}</p>}
      <div className={`text-caption leading-relaxed break-keep ${cls.body}`}>{children}</div>
    </div>
  );
}
