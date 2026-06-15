type LogoProps = {
  /** Wordmark base size in px. */
  size?: number;
  /** Use white text on dark backgrounds. */
  inverted?: boolean;
  className?: string;
};

const GREEN = "#15663D";
const INK = "#16213b";

export default function Logo({ size = 28, inverted = false, className }: LogoProps) {
  const en = inverted ? "#FFFFFF" : GREEN;
  const ko = inverted ? "#FFFFFF" : INK;

  return (
    <span
      className={className}
      aria-label="보험핏"
      style={{
        display: "inline-flex",
        alignItems: "baseline",
        gap: size * 0.34,
        lineHeight: 1,
      }}
    >
      <span
        style={{
          fontFamily: "'Cormorant Garamond','Noto Serif KR',serif",
          fontWeight: 700,
          fontSize: size * 1.18,
          letterSpacing: 0,
          color: en,
        }}
      >
        BohumFit
      </span>
      <span
        style={{
          fontFamily: "'IBM Plex Sans KR','Apple SD Gothic Neo','Noto Sans KR',sans-serif",
          fontWeight: 700,
          fontSize: size,
          letterSpacing: 0,
          color: ko,
        }}
      >
        보험핏
      </span>
    </span>
  );
}
