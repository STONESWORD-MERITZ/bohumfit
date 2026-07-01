// BOHUMFIT-146: 로고 영한 병기 — "BohumFit 보험핏"(영어 bold + 한국어 muted 작게).
//   variant symbol만 F·I·T 모노그램 SVG 유지(PWA/파비콘 등 심볼 단독 용도).
type LogoVariant = "default" | "light" | "symbol";

type LogoProps = {
  /** 텍스트 크기 기준(px). 18→영 text-lg, 20→text-xl, 24+→text-2xl. */
  size?: number;
  /** default=다크 배경(흰) / light=라이트 배경(그린, 기본) / symbol=SVG 심볼만. */
  variant?: LogoVariant;
  /** 텍스트 표시 여부(기본 true). variant="symbol"이면 무시. */
  showText?: boolean;
  className?: string;
};

export default function Logo({
  size = 18,
  variant = "light",
  showText = true,
  className = "",
}: LogoProps) {
  // 심볼 단독(파비콘/PWA용) — F·I·T 모노그램 유지.
  if (variant === "symbol") {
    return (
      <svg
        viewBox="0 0 48 48"
        width={size * 2}
        height={size * 2}
        className={className}
        role="img"
        aria-label="보험핏"
      >
        <path
          d="M13 13 H35 M24 13 V35 M24 24 H33"
          fill="none"
          stroke="#FFFFFF"
          strokeWidth="5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  }

  if (!showText) return null;

  const isDark = variant === "default";
  const engColor = isDark ? "text-white" : "text-[#15663D]";
  const korColor = isDark ? "text-white/55" : "text-[#64748B]";
  const engSize = size >= 24 ? "text-2xl" : size >= 20 ? "text-xl" : "text-lg";
  const korSize = size >= 24 ? "text-lg" : size >= 20 ? "text-base" : "text-sm";

  return (
    <span
      className={`inline-flex items-baseline whitespace-nowrap ${className}`.trim()}
      role="img"
      aria-label="BohumFit 보험핏"
    >
      <span className={`font-bold tracking-tight ${engSize} ${engColor}`}>BohumFit</span>
      <span className={`ml-1.5 font-medium ${korSize} ${korColor}`}>보험핏</span>
    </span>
  );
}
