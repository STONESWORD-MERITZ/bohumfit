// BOHUMFIT-044 디자인 시스템 — Button (주/보조/위험/고스트 · 로딩 상태)
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
  primary: "bg-navy-800 text-white shadow-card hover:bg-navy-700 active:bg-navy-900",
  secondary: "border border-navy-200 bg-white text-navy-800 hover:bg-navy-50 active:bg-navy-100",
  danger: "bg-danger-600 text-white hover:bg-danger-700",
  ghost: "text-navy-700 hover:bg-navy-50",
};

const SIZE_CLS: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-caption",
  md: "px-4 py-2.5 text-sm",
  lg: "px-6 py-3 text-body",
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
        "inline-flex items-center justify-center gap-2 rounded-lg font-bold transition-colors",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-navy-500",
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
              ? "border-navy-300 border-t-navy-700"
              : "border-white/40 border-t-white"
          }`}
        />
      )}
      {children}
    </button>
  );
}
