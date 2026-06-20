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
  const symbolSize = size * 1.38;

  return (
    <span
      className={["inline-flex shrink-0 items-center whitespace-nowrap leading-none", className]
        .filter(Boolean)
        .join(" ")}
      aria-label="BOHUMFIT 보험핏"
      style={{
        gap: size * 0.42,
      }}
    >
      <svg
        width={symbolSize}
        height={symbolSize}
        viewBox="0 0 130 130"
        aria-hidden="true"
        focusable="false"
        style={{ display: "block", flex: "0 0 auto" }}
      >
        <g
          fill="none"
          stroke={color}
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="7.4"
        >
          <path d="M45 14 L116 14 L116 116 L14 116 L14 45" />
          <path d="M58 42 L58 92" />
          <path d="M58 42 L88 42" />
          <path d="M58 65 L82 65" />
        </g>
      </svg>
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
    </span>
  );
}
