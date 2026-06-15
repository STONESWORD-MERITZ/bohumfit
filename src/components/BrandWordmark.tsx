// BOHUMFIT-051: 텍스트 로고 락업 "BohumFit 보험핏" (워드마크 이미지 대체, 재사용).
// - 영문 메인(굵게·잉크) + 한글 보조(작게·muted). 포인트는 마침표(.)만 그린(accent-600).
// - 사이트 폰트(Pretendard) 그대로 — 별도 웹폰트 추가 없음. 색 토큰(ink/accent) 참조.
// - 핏히어 "FitHere 핏히어" 락업과 같은 결(영문 메인 + 한글 보조).

export interface BrandWordmarkProps {
  /** 영문 크기 — sm(푸터·미션) / md(네비) / lg(로그인) */
  size?: "sm" | "md" | "lg";
  className?: string;
}

const EN_SIZE: Record<NonNullable<BrandWordmarkProps["size"]>, string> = {
  sm: "text-base",
  md: "text-lg",
  lg: "text-2xl",
};
const KO_SIZE: Record<NonNullable<BrandWordmarkProps["size"]>, string> = {
  sm: "text-[10px]",
  md: "text-xs",
  lg: "text-sm",
};

export default function BrandWordmark({ size = "md", className = "" }: BrandWordmarkProps) {
  return (
    <span className={`inline-flex items-baseline gap-1.5 ${className}`}>
      <span className={`font-extrabold tracking-tight text-ink-900 ${EN_SIZE[size]}`}>
        BohumFit<span className="text-accent-600">.</span>
      </span>
      <span className={`font-semibold text-ink-soft ${KO_SIZE[size]}`}>보험핏</span>
    </span>
  );
}
