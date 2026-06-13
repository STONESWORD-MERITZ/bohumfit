// BOHUMFIT-045: Home Mercury 전환 — 카피·링크·훅 로직 불변(시각 계층만).
// 다크 섹션 → 라이트(섹션 구분은 여백), 장식 오버레이 제거, 히어로 scroll-scrub 1곳 적용.
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import HomeMission from "./HomeMission";

// ── 카운트업 훅 ───────────────────────────────────────────────
function useCountUp(target: number, duration = 1800, active = false) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!active) return;
    const start = performance.now();
    const tick = (now: number) => {
      const elapsed = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - elapsed, 3);
      setCount(Math.round(eased * target));
      if (elapsed < 1) requestAnimationFrame(tick);
    };
    const raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration, active]);
  return count;
}

function StatCard({ value, suffix, label, delay }: { value: number; suffix: string; label: string; delay: number }) {
  const [active, setActive] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const count = useCountUp(value, 1800, active);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { setActive(true); obs.disconnect(); } },
      { threshold: 0.4 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <div ref={ref} className="text-center" style={{ transitionDelay: `${delay}ms` }}>
      <p className="text-5xl font-extrabold tabular-nums tracking-tight text-ink-900 md:text-6xl">
        {count}<span className="text-accent-600">{suffix}</span>
      </p>
      <p className="mt-3 text-sm leading-relaxed text-ink-soft break-keep">{label}</p>
    </div>
  );
}

// ── 데이터 ────────────────────────────────────────────────────
const STATS = [
  { value: 9,   suffix: "차", label: "최신 KCD 질병분류 기준 반영" },
  { value: 7,   suffix: "개", label: "건강체·간편 알릴의무 자동 분류" },
  { value: 3,   suffix: "종", label: "기본·세부·처방 PDF 교차 분석" },
  { value: 1,   suffix: "회", label: "민감정보 동의 후 분석 시작" },
];

const ROADMAP = [
  {
    phase: "STEP 01", status: "현재 운영",
    title: "알릴의무 점검",
    body: "심평원 PDF를 분석해 보험 가입 전 고지 리스크를 자동 정리.",
    active: true,
  },
  {
    phase: "STEP 02", status: "개발 예정",
    title: "보장분석 필터",
    body: "기존 보장과 신규 제안서를 비교해 중복·공백을 한눈에.",
    active: false,
  },
  {
    phase: "STEP 03", status: "로드맵",
    title: "권리 보호 서비스 통합",
    body: "보험 소비자·설계사 권리 증진을 위한 서비스를 단계적으로 통합.",
    active: false,
  },
];

const VALUES = [
  { k: "정확성", e: "Accuracy",     body: "KCD 코드 단위 결정론적 룰 + AI 보조 판단으로 고지 검토 항목을 분류." },
  { k: "중립성", e: "Neutrality",   body: "특정 보험사·상품을 권유하지 않습니다. 사실만 정리합니다." },
  { k: "투명성", e: "Transparency", body: "왜 이 항목이 고지 대상인지 근거를 함께 보여줍니다." },
  { k: "안전성", e: "Privacy",      body: "업로드한 자료는 분석 직후 폐기되며 서버에 저장하지 않습니다." },
];

// ── 페이드인 공통 래퍼 ─────────────────────────────────────────
function FadeIn({ children, className = "", delay = 0 }: { children: React.ReactNode; className?: string; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [vis, setVis] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { setVis(true); obs.disconnect(); } },
      { threshold: 0.1 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: vis ? 1 : 0,
        transform: vis ? "translateY(0)" : "translateY(24px)",
        transition: `opacity 0.7s ease ${delay}ms, transform 0.7s ease ${delay}ms`,
      }}
    >
      {children}
    </div>
  );
}

export default function Home() {
  useEffect(() => {
    if (window.location.hash !== "#mission") return;
    const raf = requestAnimationFrame(() => {
      document.getElementById("mission")?.scrollIntoView({ block: "start" });
    });
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <div className="-mx-5 -mt-8">

      {/* ── 1. HERO (Mercury 라이트 · scroll-scrub — 히어로 1곳만) ───────── */}
      <div className="bf-hero-wrap">
        <section className="bf-hero flex min-h-[88vh] items-center overflow-hidden bg-canvas">
          <div className="mx-auto w-full max-w-6xl px-6 py-20">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-accent-600">
              Insurance Disclosure Intelligence
            </p>
            <h1 className="mt-6 text-5xl font-extrabold leading-[1.05] tracking-tight text-ink-900 md:text-7xl">
              KNOW BEFORE
              <br />
              YOU SIGN
            </h1>
            <p className="mt-7 max-w-xl text-lg leading-8 text-ink-soft break-keep">
              보험은 가입하는 순간이 아니라 보험금을 청구하는 순간 진실이 드러납니다.
              BOHUMFIT은 건강보험심평원 원자료를 분석해 고객과 설계사가 확인해야 할
              고지 리스크를 한 화면에 정리합니다.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link
                to="/check"
                className="rounded-btn bg-accent-600 px-6 py-3.5 text-sm font-semibold text-white transition hover:bg-accent-700"
              >
                고지 리스크 점검 시작 →
              </Link>
              <Link
                to="/why"
                className="rounded-btn border border-line-strong bg-white px-6 py-3.5 text-sm font-semibold text-ink-800 transition hover:bg-ink-50"
              >
                왜 중요한가요?
              </Link>
            </div>
          </div>
        </section>
      </div>

      {/* 이하 섹션은 히어로 위로 자연스럽게 올라와 덮는다 (z-index + 불투명 배경) */}
      <div className="relative z-10 bg-canvas">

        {/* ── 2. MISSION (BOHUMFIT-049: 창업 스토리 — id="mission" 앵커) ─── */}
        <HomeMission />

        {/* ── 3. STATS (라이트 · 카운트업) ───────────────────── */}
        <section className="py-24">
          <div className="mx-auto max-w-6xl px-6">
            <FadeIn className="mb-14 text-center">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">By the numbers</p>
            </FadeIn>
            <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
              {STATS.map((s, i) => (
                <StatCard key={s.label} value={s.value} suffix={s.suffix} label={s.label} delay={i * 100} />
              ))}
            </div>
          </div>
        </section>

        {/* ── 4. SERVICE ROADMAP ─────────────────────────────── */}
        <section className="py-24">
          <div className="mx-auto max-w-6xl px-6">
            <FadeIn className="mb-14">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">Service Roadmap</p>
              <h2 className="mt-4 text-3xl font-extrabold tracking-tight text-ink-900 md:text-4xl break-keep">
                지금의 BOHUMFIT과 앞으로의 BOHUMFIT
              </h2>
            </FadeIn>
            <div className="grid gap-6 md:grid-cols-3">
              {ROADMAP.map((r, i) => (
                <FadeIn key={r.phase} delay={i * 120}>
                  <div
                    className={`rounded-card border bg-white p-7 h-full ${
                      r.active ? "border-accent-300" : "border-line"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-4">
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
                          r.active
                            ? "bg-accent-600 text-white"
                            : "bg-ink-100 text-ink-soft"
                        }`}
                      >
                        {r.phase}
                      </span>
                      <span
                        className={`text-[11px] font-semibold ${
                          r.active ? "text-accent-700" : "text-ink-400"
                        }`}
                      >
                        {r.status}
                      </span>
                    </div>
                    <h3
                      className={`text-lg font-bold tracking-tight ${
                        r.active ? "text-ink-900" : "text-ink-soft"
                      }`}
                    >
                      {r.title}
                    </h3>
                    <p className="mt-2 text-[13px] leading-6 text-ink-soft break-keep">{r.body}</p>
                  </div>
                </FadeIn>
              ))}
            </div>
          </div>
        </section>

        {/* ── 5. CORE VALUES ─────────────────────────────────── */}
        <section className="py-24">
          <div className="mx-auto max-w-6xl px-6">
            <FadeIn className="mb-14">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">Core Values</p>
              <h2 className="mt-4 text-3xl font-extrabold tracking-tight text-ink-900 md:text-4xl">
                우리가 지키는 원칙
              </h2>
            </FadeIn>
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {VALUES.map((v, i) => (
                <FadeIn key={v.k} delay={i * 80}>
                  <div className="rounded-card border border-line bg-white px-6 py-7 h-full">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-accent-600">{v.e}</p>
                    <h3 className="mt-2 text-xl font-extrabold tracking-tight text-ink-900">{v.k}</h3>
                    <p className="mt-3 text-[13px] leading-6 text-ink-soft break-keep">{v.body}</p>
                  </div>
                </FadeIn>
              ))}
            </div>
          </div>
        </section>

        {/* ── 6. WHY 진입 ────────────────────────────────────── */}
        <section className="py-24">
          <div className="mx-auto max-w-4xl px-6 text-center">
            <FadeIn>
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">Why It Matters</p>
              <h2 className="mt-5 text-3xl font-extrabold leading-snug tracking-tight text-ink-900 md:text-4xl break-keep">
                고지 누락은 작은 실수가 아닙니다
              </h2>
              <p className="mt-6 text-[15px] leading-8 text-ink-soft break-keep">
                생명보험 보험금 부지급 사유의{" "}
                <strong className="text-ink-900">41.8%</strong> 가 고지의무 위반입니다.
                손해보험 피해구제 신청의{" "}
                <strong className="text-ink-900">88%</strong> 가 보험금 분쟁입니다.
                실제 분쟁 사례와 통계로 그 위험을 확인하세요.
              </p>
              <Link
                to="/why"
                className="mt-8 inline-flex rounded-btn bg-ink-900 px-6 py-3.5 text-sm font-semibold text-white transition hover:bg-ink-700"
              >
                고지 누락 피해 사례 보기 →
              </Link>
            </FadeIn>
          </div>
        </section>

        {/* ── 7. TWO PATHS ───────────────────────────────────── */}
        <section className="py-24">
          <div className="mx-auto max-w-6xl px-6">
            <FadeIn className="mb-14">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">Use cases</p>
              <h2 className="mt-4 text-3xl font-extrabold tracking-tight text-ink-900 md:text-4xl break-keep">
                누구를 위한 도구인가요
              </h2>
            </FadeIn>
            <div className="grid gap-6 md:grid-cols-2">
              <FadeIn delay={0}>
                <Link
                  to="/check"
                  className="group block rounded-card border border-line bg-white p-8 transition hover:-translate-y-0.5 hover:border-line-strong hover:shadow-hover h-full"
                >
                  <span className="inline-flex rounded-full border border-success-100 bg-success-50 px-2.5 py-0.5 text-[11px] font-semibold text-success-700">
                    고객용
                  </span>
                  <h3 className="mt-4 text-xl font-bold tracking-tight text-ink-900">내 보험 고지 점검</h3>
                  <p className="mt-3 text-[14px] leading-6 text-ink-soft break-keep">
                    이미 가입한 보험이 청약 당시 병력 고지를 빠뜨리지 않았는지 참고용으로 확인합니다.
                  </p>
                  <ul className="mt-4 space-y-1.5">
                    {["보험금 청구 때 분쟁이 될 만한 병력·입원·투약 기록을 미리 점검", "로그인 후 안전하게 이용"].map(b => (
                      <li key={b} className="flex items-start gap-2 text-[13px] text-ink-soft">
                        <span className="mt-1.5 inline-block h-1 w-1 shrink-0 rounded-full bg-ink-300" />
                        <span className="break-keep">{b}</span>
                      </li>
                    ))}
                  </ul>
                  <span className="mt-6 inline-flex items-center text-sm font-semibold text-accent-700">
                    고지 리스크 점검 시작
                    <span aria-hidden className="ml-2 transition group-hover:translate-x-1">→</span>
                  </span>
                </Link>
              </FadeIn>
              <FadeIn delay={120}>
                <Link
                  to="/disclosure?mode=agent"
                  className="group block rounded-card border border-line bg-white p-8 transition hover:-translate-y-0.5 hover:border-line-strong hover:shadow-hover h-full"
                >
                  <span className="inline-flex rounded-full border border-accent-200 bg-accent-50 px-2.5 py-0.5 text-[11px] font-semibold text-accent-800">
                    설계사용
                  </span>
                  <h3 className="mt-4 text-xl font-bold tracking-tight text-ink-900">알릴의무 필터</h3>
                  <p className="mt-3 text-[14px] leading-6 text-ink-soft break-keep">
                    심평원 PDF 기준으로 건강체·간편심사 가입 전 고지 대상 병력을 자동 정리합니다.
                  </p>
                  <ul className="mt-4 space-y-1.5">
                    {["고객 상담용 카카오톡 메시지 자동 생성", "건강체·간편심사 고지 검토 항목 정리"].map(b => (
                      <li key={b} className="flex items-start gap-2 text-[13px] text-ink-soft">
                        <span className="mt-1.5 inline-block h-1 w-1 shrink-0 rounded-full bg-ink-300" />
                        <span className="break-keep">{b}</span>
                      </li>
                    ))}
                  </ul>
                  <span className="mt-6 inline-flex items-center text-sm font-semibold text-ink-700">
                    설계사용 시작
                    <span aria-hidden className="ml-2 transition group-hover:translate-x-1">→</span>
                  </span>
                </Link>
              </FadeIn>
            </div>
          </div>
        </section>

        {/* ── 8. CTA ─────────────────────────────────────────── */}
        <section className="py-28">
          <div className="mx-auto max-w-4xl px-6 text-center">
            <FadeIn>
              <h2 className="text-3xl font-extrabold tracking-tight text-ink-900 md:text-5xl break-keep">
                지금 바로 확인하세요
              </h2>
              <p className="mt-5 text-[15px] leading-8 text-ink-soft break-keep">
                PDF 3장이면 충분합니다. 가입 전 확인해야 할 고지 리스크를 자료량에 따라 순차적으로 정리합니다.
              </p>
              <Link
                to="/check"
                className="mt-8 inline-flex rounded-btn bg-accent-600 px-8 py-4 text-base font-semibold text-white transition hover:bg-accent-700"
              >
                고지 리스크 점검 시작 →
              </Link>
              <p className="mt-4 text-xs text-ink-400">
                본 결과는 AI 보조 도구가 제공하는 참고 자료입니다. 가입·인수·보험금 지급을 보장하지 않습니다.
              </p>
            </FadeIn>
          </div>
        </section>

      </div>
    </div>
  );
}
