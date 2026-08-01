// BOHUMFIT-265 — 고지 배지 4단. ★장기 고지 배지는 **10년** 기준으로 Human 확정(초기 검토안의 더 짧은
//   기간에서 상향). 라벨은 tokens.ts의 DISCLOSURE_BADGES가 유일 정본이다.
//   고지대상·10년 / 고지대상·3개월 / 검토·1년 재검사 / 해당없음.
//   ★면(경고·검토·중립)만 상태색을 쓰고 글자는 대비가 확보된 잉크 계열을 쓴다.
//   ★색만으로 구분하지 않는다 — 라벨 텍스트가 항상 함께 나온다.
//   ★적용은 266~ — 265에서는 정의만 한다.
import { DISCLOSURE_BADGES, MOBILE_LAYOUT, STATE_SURFACES, type DisclosureBadgeKey } from "./tokens";

const TEXT_TONE: Record<DisclosureBadgeKey, string> = {
  major10y: "text-warning-700",
  minor3m: "text-warning-700",
  review1y: "text-ink-700",
  none: "text-ink-soft",
};

export interface DisclosureBadgeProps {
  kind: DisclosureBadgeKey;
  className?: string;
}

export default function DisclosureBadge({ kind, className = "" }: DisclosureBadgeProps) {
  const spec = DISCLOSURE_BADGES[kind];
  return (
    <span
      data-badge={kind}
      className={`inline-flex items-center whitespace-nowrap px-2.5 py-1 text-[15px] font-semibold leading-[1.35] ${TEXT_TONE[kind]} ${className}`}
      style={{
        background: STATE_SURFACES[spec.surface],
        borderRadius: MOBILE_LAYOUT.radiusBadge,
      }}
    >
      {spec.label}
    </span>
  );
}
