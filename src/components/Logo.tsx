// BOHUMFIT-145: 로고를 "보험핏" 한글 텍스트만으로 단순화(심볼·영문 제거).
//   variant symbol만 F·I·T 모노그램 SVG 유지(PWA/파비콘 등 심볼 단독 용도).
type LogoVariant = "default" | "light" | "symbol";

type LogoProps = {
  /** 텍스트 크기 기준(px). 18→text-lg, 20→text-xl, 24+→text-2xl. */
  size?: number;
  /** default=흰 텍스트(다크 배경) / light=그린 텍스트(라이트 배경, 기본) / symbol=SVG 심볼만. */
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

  const textColor = variant === "default" ? "text-white" : "text-[#15663D]";
  const fontSize = size >= 24 ? "text-2xl" : size >= 20 ? "text-xl" : "text-lg";

  return (
    <span
      className={`font-bold tracking-tight ${fontSize} ${textColor} ${className}`.trim()}
      role="img"
      aria-label="보험핏"
    >
      보험핏
    </span>
  );
}
