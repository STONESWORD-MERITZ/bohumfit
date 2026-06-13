// BOHUMFIT-045 디자인 시스템 v2(Mercury) — Field·TextInput·SelectInput. API 불변, 내부 스타일만 교체.
import {
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
} from "react";

export interface FieldProps {
  label: ReactNode;
  /** 필수 표시(*) */
  required?: boolean;
  /** 입력 아래 도움말 */
  help?: ReactNode;
  /** 오류 메시지 — 있으면 도움말 대신 표시 */
  error?: ReactNode;
  className?: string;
  children: ReactNode;
}

export default function Field({ label, required, help, error, className = "", children }: FieldProps) {
  return (
    <label className={`block text-caption font-semibold text-ink-700 ${className}`}>
      <span>
        {label}
        {required && (
          <span aria-hidden className="ml-0.5 text-danger-600">
            *
          </span>
        )}
      </span>
      <div className="mt-1.5">{children}</div>
      {error ? (
        <p className="mt-1.5 font-semibold text-danger-600">{error}</p>
      ) : (
        help && <p className="mt-1.5 font-normal text-ink-soft">{help}</p>
      )}
    </label>
  );
}

const INPUT_CLS =
  "w-full rounded-btn border border-line-strong bg-white px-3.5 py-2.5 text-body text-ink " +
  "placeholder:text-ink-400 transition-colors hover:border-ink-300 " +
  "focus:border-accent-500 focus:outline-2 focus:outline-offset-0 focus:outline-accent-200 " +
  "disabled:bg-ink-50 disabled:text-ink-soft";

/** 토큰 적용 기본 텍스트 입력 — Field 안/밖 모두 사용 가능 */
export function TextInput({ className = "", ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`${INPUT_CLS} ${className}`} {...rest} />;
}

/** 토큰 적용 기본 셀렉트 */
export function SelectInput({ className = "", children, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={`${INPUT_CLS} ${className}`} {...rest}>
      {children}
    </select>
  );
}
