// BOHUMFIT-044 디자인 시스템 — PageHeader (페이지 타이틀 + 액션 영역)
import { type ReactNode } from "react";

export interface PageHeaderProps {
  title: ReactNode;
  /** 타이틀 위 작은 뱃지/라벨 (Badge 등) */
  badge?: ReactNode;
  description?: ReactNode;
  /** 우측 액션 영역 (버튼 등) */
  actions?: ReactNode;
}

export default function PageHeader({ title, badge, description, actions }: PageHeaderProps) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        {badge && <div className="mb-1.5">{badge}</div>}
        <h1 className="text-display text-navy-900">{title}</h1>
        {description && (
          <p className="mt-1.5 max-w-3xl text-body text-ink-soft break-keep">{description}</p>
        )}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}
