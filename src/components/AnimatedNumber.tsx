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
  return (
    <span ref={ref} className={className}>
      {display.toLocaleString("ko-KR")}
    </span>
  );
}
