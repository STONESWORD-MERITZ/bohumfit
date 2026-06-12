// BOHUMFIT-044 디자인 시스템 — EmptyState (빈 결과 표시)
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
    <div className={`rounded-card border border-dashed border-line bg-white px-6 py-12 text-center ${className}`}>
      <div aria-hidden className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-navy-50 text-navy-400">
        <span className="text-lg font-extrabold">·</span>
      </div>
      <p className="text-body font-bold text-navy-900">{title}</p>
      {description && <p className="mx-auto mt-1.5 max-w-md text-caption text-ink-soft break-keep">{description}</p>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}
