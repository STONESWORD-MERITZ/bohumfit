// BOHUMFIT-044 디자인 시스템 — Badge (판정 뱃지: 고지권고/불요/확인필요 등)
import { type ReactNode } from "react";

export type BadgeTone = "navy" | "gold" | "success" | "warning" | "danger" | "neutral";

export interface BadgeProps {
  tone?: BadgeTone;
  /** 채움형(진한 배경) — 표 헤더 위 강조용 */
  solid?: boolean;
  className?: string;
  children: ReactNode;
}

const TONE_CLS: Record<BadgeTone, { soft: string; solid: string }> = {
  navy: { soft: "border-navy-200 bg-navy-50 text-navy-800", solid: "border-navy-800 bg-navy-800 text-white" },
  gold: { soft: "border-gold-300 bg-gold-50 text-gold-700", solid: "border-gold-500 bg-gold-500 text-white" },
  success: { soft: "border-success-100 bg-success-50 text-success-700", solid: "border-success-600 bg-success-600 text-white" },
  warning: { soft: "border-warning-100 bg-warning-50 text-warning-700", solid: "border-warning-600 bg-warning-600 text-white" },
  danger: { soft: "border-danger-100 bg-danger-50 text-danger-700", solid: "border-danger-600 bg-danger-600 text-white" },
  neutral: { soft: "border-line bg-canvas text-ink-soft", solid: "border-ink-soft bg-ink-soft text-white" },
};

export default function Badge({ tone = "neutral", solid = false, className = "", children }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-caption font-bold ${
        TONE_CLS[tone][solid ? "solid" : "soft"]
      } ${className}`}
    >
      {children}
    </span>
  );
}
