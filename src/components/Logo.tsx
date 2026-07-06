// BOHUMFIT-166: FIT 브랜드 v1.0 — ㅍ 브릿지 심볼 + "BohumFit 보험핏" 병기.
//   symbol variant = ㅍ 심볼(흰 fill; 에메랄드 타일·다크 서피스·PWA/파비콘용).
//   윗바 + 두 기둥 + 아랫바(세로획15/가로획13, 코너 라운드3.5), viewBox 82×66.
type LogoVariant = "default" | "light" | "symbol";

type LogoProps = {
  /** 텍스트 크기 기준(px). 18→영 text-lg, 20→text-xl, 24+→text-2xl. */
  size?: number;
  /** default=다크 배경(흰) / light=라이트 배경(에메랄드, 기본) / symbol=ㅍ 심볼만. */
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
  // ㅍ 브릿지 심볼 — 흰 fill(에메랄드 타일/다크 위). 파비콘·PWA 단독 용도.
  if (variant === "symbol") {
    const w = size * 2;
    const h = Math.round((size * 2 * 66) / 82);
    return (
      <svg
        viewBox="0 0 82 66"
        width={w}
        height={h}
        className={className}
        role="img"
        aria-label="보험핏"
        fill="#FFFFFF"
      >
        <rect x="0" y="0" width="82" height="13" rx="3.5" />
        <rect x="0" y="53" width="82" height="13" rx="3.5" />
        <rect x="17" y="8" width="15" height="50" rx="3.5" />
        <rect x="50" y="8" width="15" height="50" rx="3.5" />
      </svg>
    );
  }

  if (!showText) return null;

  const isDark = variant === "default";
  const engColor = isDark ? "text-white" : "text-ink-900"; // BOHUMFIT-170 v1.1: 밝은 바탕 워드마크 = 잉크(#0A0A0A)
  const korColor = isDark ? "text-white/60" : "text-ink-soft";
  const engSize = size >= 24 ? "text-2xl" : size >= 20 ? "text-xl" : "text-lg";
  const korSize = size >= 24 ? "text-lg" : size >= 20 ? "text-base" : "text-sm";
  const markSize = Math.max(26, Math.round(size * 1.7));
  const markBg = isDark ? "bg-white/15 ring-white/25" : "bg-accent-600 ring-accent-700/10";
  const markFill = "#FFFFFF";

  return (
    <span
      className={`inline-flex items-center whitespace-nowrap ${className}`.trim()}
      role="img"
      aria-label="BohumFit 보험핏"
    >
      <span
        className={`mr-2 inline-flex shrink-0 items-center justify-center rounded-[7px] ring-1 ${markBg}`}
        style={{ width: markSize, height: markSize }}
        aria-hidden="true"
      >
        <svg viewBox="0 0 82 66" width={Math.round(markSize * 0.62)} height={Math.round(markSize * 0.5)} fill={markFill}>
          <rect x="0" y="0" width="82" height="13" rx="3.5" />
          <rect x="0" y="53" width="82" height="13" rx="3.5" />
          <rect x="17" y="8" width="15" height="50" rx="3.5" />
          <rect x="50" y="8" width="15" height="50" rx="3.5" />
        </svg>
      </span>
      <span className="inline-flex items-baseline">
        <span className={`font-bold tracking-tight ${engSize} ${engColor}`}>BohumFit</span>
        <span className={`ml-1.5 font-medium ${korSize} ${korColor}`}>보험핏</span>
      </span>
    </span>
  );
}
