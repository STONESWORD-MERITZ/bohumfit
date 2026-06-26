// BOHUMFIT-132: useCountUp을 감싼 표시 컴포넌트. 뷰포트 진입 시 0→value 카운트업.
import { useCountUp } from "../hooks/useCountUp";

export default function AnimatedNumber({
  value,
  duration = 800,
  className,
}: {
  value: number;
  duration?: number;
  className?: string;
}) {
  const { value: display, ref } = useCountUp(value, duration);
  // BOHUMFIT-135: ticker 스타일 — 고정폭 숫자(tabular-nums)로 자릿수 흔들림 없이 롤업.
  return (
    <span
      ref={ref}
      className={`inline-block tabular-nums ${className ?? ""}`}
      aria-label={String(value)}
    >
      {display.toLocaleString("ko-KR")}
    </span>
  );
}
