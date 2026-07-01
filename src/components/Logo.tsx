// BOHUMFIT-144b: 심볼(F·I·T 모노그램) + 워드마크 조합 로고.
//   variant: default(흰 심볼·다크 배경) / light(그린 심볼·라이트 배경) / symbol(심볼만).
type LogoVariant = "default" | "light" | "symbol";

type LogoProps = {
  /** 심볼 크기(px). 기본 24. */
  size?: number;
  variant?: LogoVariant;
  /** 텍스트(워드마크) 표시 여부. 기본 true. variant="symbol"이면 무시(항상 숨김). */
  showText?: boolean;
  className?: string;
};

const GREEN = "#15663D";
const GREEN_DARK = "#0E4A2C";

export default function Logo({ size = 24, variant = "default", showText = true, className }: LogoProps) {
  const strokeColor = variant === "default" ? "#FFFFFF" : GREEN; // light·symbol → 그린
  const withText = showText && variant !== "symbol";
  const isDark = variant === "default";
  const bohum = isDark ? "#FFFFFF" : GREEN_DARK;
  const fit = isDark ? "rgba(255,255,255,0.7)" : GREEN;

  return (
    <span
      className={["inline-flex shrink-0 items-center whitespace-nowrap leading-none", className]
        .filter(Boolean)
        .join(" ")}
      aria-label="BOHUMFIT 보험핏"
      style={{ gap: size * 0.35 }}
    >
      <svg viewBox="0 0 48 48" width={size} height={size} aria-hidden="true">
        <path
          d="M13 13 H35 M24 13 V35 M24 24 H33"
          fill="none"
          stroke={strokeColor}
          strokeWidth={5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {withText && (
        <span
          style={{
            fontFamily: "Arial, 'Helvetica Neue', sans-serif",
            fontWeight: 800,
            fontSize: size * 0.72,
            letterSpacing: 0,
          }}
        >
          <span style={{ color: bohum }}>BOHUM</span>
          <span style={{ color: fit }}>FIT</span>
        </span>
      )}
    </span>
  );
}
