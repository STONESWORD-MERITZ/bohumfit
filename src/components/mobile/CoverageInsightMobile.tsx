// BOHUMFIT-267 P2 — 266이 남긴 모바일 표 가독성 보정.
//
//   266 잔여: 종합비교(560px)·Y/N(420px) 표가 모바일에서 `overflow-x-auto` 안에 갇혀 가로 스크롤이 생기고
//   폰트도 12px이라 265 하한(15px)에 못 미쳤다. 두 표를 **리스트로 펴서** 가로 스크롤을 없애고 15px로 올린다.
//   ★값·순서·계산은 데스크톱 표와 동일한 소스를 그대로 쓴다 — 표시 형태만 바꾼다.
import type { YnFlag } from "../../lib/coverageAfterDisplayCache";
import { formatCoverageAmount, formatCoverageDeltaAmount } from "../../lib/coverageFormat";
import { MOBILE_LAYOUT } from "./tokens";

/** 데스크톱 `StageComparisonTable`과 동일한 행 정의(라벨·순서 일치). */
export type StageRow = { key: string; label: string };

export function StageComparisonMobile({
  rows,
  before,
  after,
}: {
  rows: StageRow[];
  before: Record<string, number>;
  after: Record<string, number> | null;
}) {
  return (
    <ul className="space-y-2" data-testid="stage-comparison-mobile">
      {rows.map((row) => {
        const beforeValue = before[row.key] ?? 0;
        const afterValue = after == null ? null : (after[row.key] ?? 0);
        const delta = afterValue == null ? null : afterValue - beforeValue;
        return (
          <li
            key={row.key}
            className="bg-canvas px-3 py-2.5"
            style={{ borderRadius: MOBILE_LAYOUT.radiusBadge }}
            data-stage={row.key}
          >
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-[15px] font-bold leading-[1.55] text-ink-800">{row.label}</span>
              <span
                className={`text-[15px] font-bold leading-[1.55] ${
                  delta != null && delta > 0
                    ? "text-accent-700"
                    : delta != null && delta < 0
                      ? "text-warning-700"
                      : "text-ink-soft"
                }`}
              >
                {formatCoverageDeltaAmount(delta)}
              </span>
            </div>
            {/* 전 → 후를 한 줄로 — 열을 나누지 않으니 가로 스크롤이 생기지 않는다. */}
            <p className="mt-1 text-[15px] leading-[1.55] text-ink-soft">
              {formatCoverageAmount(beforeValue)} <span aria-hidden="true">→</span>{" "}
              <b className="font-bold text-ink-900">{afterValue == null ? "-" : formatCoverageAmount(afterValue)}</b>
            </p>
          </li>
        );
      })}
    </ul>
  );
}

function YnPill({ value, label }: { value: "Y" | "N"; label: string }) {
  const on = value === "Y";
  return (
    <span className="inline-flex items-baseline gap-1">
      <span className="text-[15px] leading-[1.55] text-ink-soft">{label}</span>
      <span
        className={`px-2 py-0.5 text-[15px] font-extrabold leading-[1.4] ${
          on ? "bg-accent-100 text-accent-800" : "bg-surface-muted text-ink-soft"
        }`}
        style={{ borderRadius: MOBILE_LAYOUT.radiusBadge }}
      >
        {value}
      </span>
    </span>
  );
}

export function YnFlagMobile({ before, after }: { before: YnFlag[]; after: YnFlag[] | null }) {
  const afterByItem = new Map((after || []).map((flag) => [flag.item, flag.value]));
  return (
    <ul className="space-y-2" data-testid="yn-flags-mobile">
      {before.map((flag) => {
        const afterValue = after == null ? null : (afterByItem.get(flag.item) ?? "N");
        return (
          <li
            key={flag.item}
            className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 bg-canvas px-3 py-2.5"
            style={{ borderRadius: MOBILE_LAYOUT.radiusBadge }}
            data-yn-item={flag.item}
          >
            <span className="min-w-0 break-keep text-[15px] font-bold leading-[1.55] text-ink-800">{flag.item}</span>
            <span className="flex shrink-0 items-baseline gap-3">
              <YnPill value={flag.value} label="전" />
              {afterValue == null ? (
                <span className="text-[15px] leading-[1.55] text-ink-soft">후 -</span>
              ) : (
                <YnPill value={afterValue} label="후" />
              )}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
