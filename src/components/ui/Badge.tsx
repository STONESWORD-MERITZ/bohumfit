// BOHUMFIT-045 디자인 시스템 v2(Mercury) — Badge. API 불변(tone 리터럴 유지), 내부 스타일만 교체.
// 파스텔 배경 + 진한 동계열 텍스트. tone 의미 재매핑: "navy"=뉴트럴 잉크, "gold"=포인트(페리윙클).
import { type ReactNode } from "react";

export type BadgeTone = "navy" | "gold" | "success" | "warning" | "danger" | "neutral";
// BOHUMFIT-131: 의미 기반 variant(21st.dev 참고). 제공 시 tone보다 우선.
export type BadgeVariant = "default" | "success" | "warning" | "danger" | "info" | "outline";

export interface BadgeProps {
  tone?: BadgeTone;
  variant?: BadgeVariant;
  /** 채움형(진한 배경) — 강조용 */
  solid?: boolean;
  className?: string;
  children: ReactNode;
}

const VARIANT_CLS: Record<BadgeVariant, string> = {
  default: "border-ink-200 bg-ink-100 text-ink-700",
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  danger: "border-red-200 bg-red-50 text-red-700",
  info: "border-sky-200 bg-sky-50 text-sky-700",
  outline: "border-ink-300 bg-transparent text-ink-500",
};

const TONE_CLS: Record<BadgeTone, { soft: string; solid: string }> = {
  navy: { soft: "border-ink-200 bg-ink-100 text-ink-800", solid: "border-ink-900 bg-ink-900 text-white" },
  gold: { soft: "border-accent-200 bg-accent-50 text-accent-800", solid: "border-accent-600 bg-accent-600 text-white" },
  success: { soft: "border-success-100 bg-success-50 text-success-700", solid: "border-success-600 bg-success-600 text-white" },
  warning: { soft: "border-warning-100 bg-warning-50 text-warning-700", solid: "border-warning-600 bg-warning-600 text-white" },
  danger: { soft: "border-danger-100 bg-danger-50 text-danger-700", solid: "border-danger-600 bg-danger-600 text-white" },
  neutral: { soft: "border-line bg-ink-50 text-ink-soft", solid: "border-ink-600 bg-ink-600 text-white" },
};

export default function Badge({ tone = "neutral", variant, solid = false, className = "", children }: BadgeProps) {
  const cls = variant ? VARIANT_CLS[variant] : TONE_CLS[tone][solid ? "solid" : "soft"];
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2.5 py-0.5 text-caption font-semibold ${cls} ${className}`}
    >
      {children}
    </span>
  );
}
