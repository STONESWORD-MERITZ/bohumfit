// BOHUMFIT-045 디자인 시스템 v2(Mercury) — Button. API 불변(044과 동일 props), 내부 스타일만 교체.
import { type ButtonHTMLAttributes, type ReactNode } from "react";

export type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** 로딩 중 — 스피너 표시 + 클릭 차단(aria-busy) */
  loading?: boolean;
  /** 가로 100% */
  full?: boolean;
  children: ReactNode;
}

const VARIANT_CLS: Record<ButtonVariant, string> = {
  // 보라 솔리드 — 브랜드 CTA (BOHUMFIT-046: 잉크→보라)
  primary: "bg-accent-600 text-white hover:bg-accent-700 active:bg-accent-800",
  // 고스트 1px 헤어라인
  secondary: "border border-line-strong bg-white text-ink-800 hover:bg-ink-50 active:bg-ink-100",
  danger: "bg-danger-600 text-white hover:bg-danger-700",
  ghost: "text-ink-700 hover:bg-ink-50",
};

const SIZE_CLS: Record<ButtonSize, string> = {
  // BOHUMFIT-048 모바일 탭 타깃 44px+: md/lg 에 min-h-[2.75rem] 보장(데스크탑 무해).
  sm: "px-3 py-1.5 text-caption",
  md: "min-h-[2.75rem] px-4 py-2.5 text-sm",
  lg: "min-h-[2.75rem] px-6 py-3 text-body",
};

export default function Button({
  variant = "primary",
  size = "md",
  loading = false,
  full = false,
  disabled,
  className = "",
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={[
        "inline-flex items-center justify-center gap-2 rounded-btn font-semibold transition-colors",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-600",
        "disabled:cursor-not-allowed disabled:opacity-50",
        VARIANT_CLS[variant],
        SIZE_CLS[size],
        full ? "w-full" : "",
        className,
      ].join(" ")}
      {...rest}
    >
      {loading && (
        <span
          aria-hidden
          className={`inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 ${
            variant === "secondary" || variant === "ghost"
              ? "border-ink-300 border-t-ink-700"
              : "border-white/40 border-t-white"
          }`}
        />
      )}
      {children}
    </button>
  );
}
