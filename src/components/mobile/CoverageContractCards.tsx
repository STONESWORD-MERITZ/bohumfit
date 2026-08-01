// BOHUMFIT-266 — 모바일 계약 카드(좌 스와이프=해지 / 우=복원).
//
//   ★기존 해지 로직을 그대로 쓴다: `updateContractDecision(idx, { disposition })` 하나만 호출하고
//     payload·재계산 흐름(`buildAfterResult`)에는 손대지 않는다 — UI만 교체한다(260 미러 규칙 무변경).
//   ★되돌리기: 265 `showUndoToast`(6초). 허용 범위 상수 `cancel-confirm`에 해당한다.
//   ★해지 상태는 색만으로 표시하지 않는다 — 회색 면 + 취소선 + "해지" 배지를 함께 쓴다.
import { useToast } from "../ToastContext";
import type { Company } from "../../lib/coverageAfterDisplayCache";
import { keyOf } from "../../lib/coverageAfterDisplayCache";
import SwipeActionCard from "./SwipeActionCard";
import { MOBILE_LAYOUT } from "./tokens";
import type { MobileFormatters } from "./CoverageMobileView";

export type ContractDisposition = "keep" | "cancel";

export default function CoverageContractCards({
  companies,
  dispositionOf,
  onChange,
  formatPeriod,
  fmt,
}: {
  companies: Company[];
  /** 현재 처리 상태(데스크톱과 같은 `decisions` 맵에서 읽는다). */
  dispositionOf: (idx: number | string) => ContractDisposition;
  /** 기존 진입점 그대로 — 여기서 새로운 상태를 만들지 않는다. */
  onChange: (idx: number | string, disposition: ContractDisposition) => void;
  formatPeriod: (company: Company) => string;
  fmt: MobileFormatters;
}) {
  const { showUndoToast } = useToast();

  const apply = (company: Company, next: ContractDisposition) => {
    const previous = dispositionOf(company.idx);
    if (previous === next) return;
    onChange(company.idx, next);
    // 해지 확정만 되돌리기를 붙인다(복원은 이미 되돌리는 동작이라 토스트가 겹치면 소음이 된다).
    if (next === "cancel") {
      showUndoToast({
        scope: "cancel-confirm",
        message: `${company.insurer || `계약 ${company.idx}`} 해지로 표시했습니다.`,
        onUndo: () => onChange(company.idx, previous),
      });
    }
  };

  return (
    <ul className="mt-4 space-y-3" data-testid="m-contract-cards">
      {companies.map((company) => {
        const cancelled = dispositionOf(company.idx) === "cancel";
        return (
          <li key={keyOf(company.idx)}>
            <SwipeActionCard
              cancelled={cancelled}
              onCancel={() => apply(company, "cancel")}
              onRestore={() => apply(company, "keep")}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="break-keep text-[16px] font-bold leading-[1.4] text-ink-900">
                    {company.insurer || "보험사 미제공"}
                  </p>
                  <p className="mt-1 break-keep text-[15px] leading-[1.55] text-ink-soft">
                    {company.product || "상품명 확인 필요"}
                  </p>
                  <p className="mt-1 text-[15px] leading-[1.55] text-ink-soft">{formatPeriod(company)}</p>
                  {company.remark && (
                    <p className="mt-1 text-[15px] leading-[1.55] font-semibold text-ink-soft">{company.remark}</p>
                  )}
                </div>
                <div className="flex shrink-0 flex-col items-end gap-2">
                  {cancelled && (
                    <span
                      className="bg-surface-warning px-2 py-0.5 text-[15px] font-bold text-warning-700"
                      style={{ borderRadius: MOBILE_LAYOUT.radiusBadge }}
                    >
                      해지
                    </span>
                  )}
                  {company.paid_up && (
                    <span
                      className="bg-surface-muted px-2 py-0.5 text-[15px] font-bold text-ink-soft"
                      style={{ borderRadius: MOBILE_LAYOUT.radiusBadge }}
                    >
                      납입완료
                    </span>
                  )}
                  <p className="text-[16px] font-extrabold leading-[1.4] text-ink-900">
                    {fmt.formatPremium(company.monthly_premium)}
                  </p>
                </div>
              </div>

              {/* ★스와이프를 모르는 사용자를 막지 않는다 — 같은 동작을 하는 버튼을 항상 함께 둔다. */}
              <div className="mt-3 flex items-center justify-between gap-3 border-t border-line pt-3">
                <span className="text-[15px] leading-[1.55] text-ink-soft">
                  {cancelled ? "← 밀어서 해지 · 밀어서 복원 →" : "← 밀면 해지"}
                </span>
                <button
                  type="button"
                  data-testid="m-contract-toggle"
                  onClick={() => apply(company, cancelled ? "keep" : "cancel")}
                  className="m-tap shrink-0 px-3 text-[15px] font-bold text-accent-700 underline"
                >
                  {cancelled ? "복원" : "해지"}
                </button>
              </div>
            </SwipeActionCard>
          </li>
        );
      })}
    </ul>
  );
}
