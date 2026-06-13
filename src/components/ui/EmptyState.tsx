// BOHUMFIT-045 디자인 시스템 v2(Mercury) — EmptyState. API 불변, 내부 스타일만 교체.
import { type ReactNode } from "react";

export interface EmptyStateProps {
  title: ReactNode;
  description?: ReactNode;
  /** 행동 유도 영역 (Button 등) */
  action?: ReactNode;
  className?: string;
}

export default function EmptyState({ title, description, action, className = "" }: EmptyStateProps) {
  return (
    <div className={`rounded-card border border-line bg-white px-6 py-14 text-center ${className}`}>
      <div
        aria-hidden
        className="mx-auto mb-4 flex h-10 w-10 items-center justify-center rounded-full border border-line bg-canvas text-ink-400"
      >
        <span className="text-lg font-bold">·</span>
      </div>
      <p className="text-body font-bold text-ink-900">{title}</p>
      {description && <p className="mx-auto mt-1.5 max-w-md text-caption text-ink-soft break-keep">{description}</p>}
      {action && <div className="mt-5 flex justify-center">{action}</div>}
    </div>
  );
}
