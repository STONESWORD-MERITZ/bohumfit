// BOHUMFIT-132: requestAnimationFrame 기반 숫자 카운트업(외부 라이브러리 없음).
//   easeOut(빠르게 시작→천천히 끝), 기본 800ms, 뷰포트 진입 시 시작, target=0이면 그대로 0.
import { useEffect, useRef, useState, type RefObject } from "react";

const easeOutCubic = (t: number): number => 1 - Math.pow(1 - t, 3);

export function useCountUp(
  target: number,
  duration = 800,
): { value: number; ref: RefObject<HTMLSpanElement | null> } {
  const [value, setValue] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const started = useRef(false);

  useEffect(() => {
    if (target === 0) {
      setValue(0);
      return;
    }
    started.current = false;
    let raf = 0;

    const animate = () => {
      const start = performance.now();
      const step = (now: number) => {
        const p = Math.min(1, (now - start) / duration);
        setValue(Math.round(easeOutCubic(p) * target));
        if (p < 1) raf = requestAnimationFrame(step);
      };
      raf = requestAnimationFrame(step);
    };

    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") {
      started.current = true;
      animate();
      return () => cancelAnimationFrame(raf);
    }

    const obs = new IntersectionObserver(
      (entries) => {
        if (!started.current && entries.some((e) => e.isIntersecting)) {
          started.current = true;
          animate();
          obs.disconnect();
        }
      },
      { threshold: 0.1 },
    );
    obs.observe(el);
    return () => {
      obs.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [target, duration]);

  return { value, ref };
}
