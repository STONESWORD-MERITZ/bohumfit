type LogoProps = {
  /** Wordmark base size in px. */
  size?: number;
  /** Use white text and symbol on dark backgrounds. */
  inverted?: boolean;
  className?: string;
};

const GREEN = "#15663D";

export default function Logo({ size = 28, inverted = false, className }: LogoProps) {
  const color = inverted ? "#FFFFFF" : GREEN;

  return (
    <span
      className={["inline-flex shrink-0 items-center whitespace-nowrap leading-none", className]
        .filter(Boolean)
        .join(" ")}
      aria-label="BOHUMFIT 보험핏"
      style={{
        gap: size * 0.2,
      }}
    >
      <span
        style={{
          color,
          fontFamily: "Arial, 'Helvetica Neue', sans-serif",
          fontSize: size,
          fontWeight: 700,
          letterSpacing: size * 0.12,
        }}
      >
        BOHUMFIT
      </span>
      <span
        style={{
          color,
          fontSize: Math.max(size * 0.58, 12),
          fontWeight: 700,
          letterSpacing: 0,
        }}
      >
        보험핏
      </span>
    </span>
  );
}
