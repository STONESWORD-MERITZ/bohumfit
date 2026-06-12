// BOHUMFIT-044 디자인 시스템 — Field (라벨+입력+도움말) · TextInput · SelectInput
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
    <label className={`block text-caption font-semibold text-ink-soft ${className}`}>
      <span>
        {label}
        {required && (
          <span aria-hidden className="ml-0.5 text-danger-600">
            *
          </span>
        )}
      </span>
      <div className="mt-1">{children}</div>
      {error ? (
        <p className="mt-1 font-semibold text-danger-600">{error}</p>
      ) : (
        help && <p className="mt-1 font-normal text-ink-soft/80">{help}</p>
      )}
    </label>
  );
}

const INPUT_CLS =
  "w-full rounded-lg border border-line bg-white px-3.5 py-2.5 text-body text-ink " +
  "placeholder:text-ink-soft/50 focus:border-navy-400 focus:outline-2 focus:outline-offset-0 " +
  "focus:outline-navy-500/30 disabled:bg-canvas disabled:text-ink-soft";

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
