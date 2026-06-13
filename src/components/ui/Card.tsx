// BOHUMFIT-045 디자인 시스템 v2(Mercury) — Card. API 불변, 내부 스타일만 교체.
// 카드 = 화이트 + 1px 헤어라인 + 큰 라운드. 기본 그림자 없음(구조는 보더가 만든다).
import { type ReactNode } from "react";

export interface CardProps {
  /** 카드 헤더 타이틀 (없으면 헤더 미표시) */
  title?: ReactNode;
  subtitle?: ReactNode;
  /** 헤더 우측 액션 영역 (버튼 등) */
  actions?: ReactNode;
  /** 본문 패딩 제거 (표 등 풀블리드 콘텐츠) */
  flush?: boolean;
  className?: string;
  children: ReactNode;
}

export default function Card({ title, subtitle, actions, flush = false, className = "", children }: CardProps) {
  return (
    <section className={`overflow-hidden rounded-card border border-line bg-white ${className}`}>
      {(title || actions) && (
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4">
          <div className="min-w-0">
            {title && <h2 className="text-title text-ink-900">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-caption text-ink-soft break-keep">{subtitle}</p>}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </div>
      )}
      <div className={flush ? "" : "p-5"}>{children}</div>
    </section>
  );
}
