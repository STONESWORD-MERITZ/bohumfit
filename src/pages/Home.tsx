// BOHUMFIT-078: 메인 페이지 설계사 중심 전면 개편(다크 히어로 + 라이트 본문).
//   기존 일반 소비자 카피("KNOW BEFORE YOU SIGN") 제거. 그린 포인트 1색 유지.
// BOHUMFIT-080: 하단 "만든 이야기"(메리츠 지점장) 신뢰 섹션 추가(가격 CTA 위).
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

function StatCard({ value, label, detail }: { value: string; label: string; detail: string }) {
  return (
    <div className="flex items-center justify-between gap-4 py-4 md:block md:px-6 md:py-1">
      <dt className="text-[11px] font-semibold uppercase tracking-[0.18em] text-ink-500">{label}</dt>
      <dd className="flex items-baseline gap-2 md:mt-1 md:block">
        <span className="text-2xl font-extrabold tracking-tight text-ink-900 md:text-3xl">{value}</span>
        <span className="ko-text text-[12px] leading-5 text-ink-soft md:mt-1 md:block">{detail}</span>
      </dd>
    </div>
  );
}

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

// ── 데이터 ────────────────────────────────────────────────────
const STATS = [
  { value: "1분", label: "분석 완료", detail: "PDF 업로드부터 결과까지" },
  { value: "99%", label: "핵심 검출", detail: "고지의무 리스크 자동 정리" },
  { value: "30초", label: "리포트 생성", detail: "상담용 PDF 준비 시간" },
];

const STEPS = [
  {
    no: "①",
    title: "심평원 PDF 업로드",
    body: "기본진료·세부진료·처방조제 3종을 올리면 정확도가 더욱 올라갑니다.",
  },
  {
    no: "②",
    title: "AI 고지 리스크 분석",
    body: "상병코드·수술명·투약내역을 자동 분석해 보험사별 알릴의무 항목을 추출합니다.",
  },
  {
    no: "③",
    title: "리포트 완성",
    body: "고객용 PDF 리포트를 즉시 다운로드. 상담 신뢰도가 올라갑니다.",
  },
];

const FEATURES = [
  {
    icon: "🔍",
    title: "고지의무 자동 분석",
    body: "건강체·간편심사 기준으로 고지해야 할 항목을 자동으로 추출합니다. 실수로 인한 계약 해지 리스크를 줄여드립니다.",
  },
  {
    icon: "📊",
    title: "보장 비교분석",
    body: "가입 전·후 보장을 파일만 올리면 자동으로 비교합니다. 수작업 비교표 작성 시간을 절약하세요.",
  },
  {
    icon: "📄",
    title: "고객용 리포트",
    body: "분석 결과를 고객에게 바로 전달할 수 있는 PDF 리포트로 자동 생성됩니다.",
  },
];

const PRICING = [
  { name: "무료 체험", price: "5회", sub: "카드 불필요" },
  { name: "베이직", price: "월 14,900원", sub: "월 30회 분석" },
  { name: "프로", price: "월 24,900원", sub: "월 100회 분석" },
];

export default function Home() {
  // BOHUMFIT-133b: 히어로 헤드라인 fade-in-up(페이지 로드 시 아래→위 등장).
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    const raf = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(raf);
  }, []);
  return (
    <div className="bf-home-snap -mx-5 -mt-8">

      {/* BOHUMFIT-176: 라이트 통일 서피스 — 히어로도 bg-canvas 위에 얹어 첫 화면 다크 밴드 제거.
          (174까지 히어로는 bg-ink-900 별도 섹션 → 176에서 라이트로 흡수 통합) */}
      <div className="relative z-10 bg-canvas">

        {/* ── 1. HERO + 지표 1화면 묶음 (BOHUMFIT-176) ─────────────────
            174의 min-h-[calc(100svh-3.5rem)]를 히어로 단독 → 히어로+지표 묶음 기준으로 이전(부분 롤백).
            묶음=flex-col·높이 100svh-헤더(h-14=3.5rem). 히어로 flex-1(잔여 흡수·세로 중앙), 지표 shrink-0 하단.
            → 노트북에서 히어로+지표(1분/99%/30초)가 한 화면(fold) 안. min-h라 모바일은 자연 확장(스크롤 허용·잘림 0). */}
        <div className="bf-home-section flex min-h-[calc(100svh-3.5rem)] flex-col">

          {/* ── HERO (BOHUMFIT-176 다크→라이트 전환) ──────────────────
              다크(bg-ink-900·흰 텍스트·accent-400 포인트) → 라이트(canvas·잉크/본문그레이·accent-600 강조).
              대비 AA: 잉크#0A0A0A/흰 19.8:1 · 에메랄드#084734/흰 10.7:1 · 본문#1E293B/흰 14.6:1. */}
          <section className="relative flex flex-1 items-center overflow-hidden">
            {/* BOHUMFIT-133b dot → BOHUMFIT-176: 라이트 배경용 잉크 극연점(흰 점은 라이트서 불가시). 알파 0.04로 과하지 않게. */}
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0"
              style={{
                backgroundImage: "radial-gradient(rgba(10,10,10,0.04) 1px, transparent 1px)",
                backgroundSize: "22px 22px",
              }}
            />
            {/* BOHUMFIT-175: 와이드(2xl 1536+)에서만 컨테이너 축소·중앙(대칭 여백) — 1440 이하 완전 현행(회귀 0). 텍스트 좌정렬 유지, 블록만 중앙.
                BOHUMFIT-176: 히어로 콘텐츠 패딩 pt-clamp(56~80)·pb-clamp(64~96) → py-clamp(24~44)로 압축.
                근거: 묶음이 flex-1 items-center로 세로 중앙을 담당 → 기존 단독 히어로용 큰 패딩(≈80/96px)은 중복이며
                768px 노트북에서 히어로+지표 합산이 fold를 초과시킴. 압축 후 합산 ≈656<712(768-헤더56)로 1화면 진입.
                ※173 유동 타이포 토큰(text-fluid-*)은 무변경 — 여기서 조정한 것은 이 묶음 구간의 여백뿐(Step2 지시 범위). */}
            <div
              className={`relative z-10 mx-auto w-full max-w-6xl px-6 py-[clamp(1.5rem,1rem+2.2vw,2.75rem)] transition-all duration-700 2xl:max-w-4xl ${
                mounted ? "translate-y-0 opacity-100" : "translate-y-3 opacity-0"
              }`}
            >
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-accent-600">
                For Insurance Planners
              </p>
              {/* BOHUMFIT-173: 히어로 h1 유동 스케일(36→60px clamp) 유지 — BOHUMFIT-176: text-white→text-ink-900(잉크). */}
              <h1 className="ko-heading mt-6 text-fluid-hero font-extrabold leading-[1.15] tracking-tight text-ink-900 break-keep">
                고지의무 검토,
                <br />
                이제 <span className="text-accent-600">1분</span>이면 끝납니다
              </h1>
              <p className="ko-text mobile-copy mt-7 max-w-2xl text-lg leading-8 text-ink break-keep">
                설계사님이 매번 수작업으로 하던 병력 분석을
                심평원 PDF 한 장으로 AI가 자동 완성합니다.
              </p>
              <div className="mt-9 flex flex-wrap gap-3">
                <Link
                  to="/signup"
                  className="button-text bf-shimmer rounded-btn bg-accent-600 px-6 py-3.5 text-sm font-semibold text-white transition hover:bg-accent-700"
                >
                  무료로 시작하기 →
                </Link>
                {/* BOHUMFIT-176: 다크 아웃라인(border-ink-700·text-ink-100·hover:bg-ink-800) → 라이트 아웃라인. */}
                <a
                  href="#features"
                  className="button-text rounded-btn border border-line-strong bg-white px-6 py-3.5 text-sm font-semibold text-ink-900 transition hover:bg-ink-50"
                >
                  기능 둘러보기
                </a>
                {/* BOHUMFIT-112: 비로그인 리포트 샘플 미리보기 진입 (BOHUMFIT-176 라이트 아웃라인) */}
                <Link
                  to="/disclosure/sample"
                  className="button-text rounded-btn border border-line-strong bg-white px-6 py-3.5 text-sm font-semibold text-ink-900 transition hover:bg-ink-50"
                >
                  리포트 샘플 미리보기
                </Link>
              </div>
              <p className="ko-text mt-5 text-caption text-ink-soft">
                가입 후 5회 무료 체험 · 신용카드 불필요
              </p>
            </div>
          </section>

          {/* BOHUMFIT-201: 하단 지표는 히어로보다 무겁지 않게 얇은 요약 바로 정리. */}
          <section className="shrink-0 border-y border-line bg-white/70 py-4">
            <div className="mx-auto max-w-6xl px-6">
              <div className="grid gap-4 md:grid-cols-[10rem_1fr] md:items-center">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-accent-700">BohumFit</p>
                  <p className="ko-text mt-1 text-sm font-semibold text-ink-900">상담 준비 요약</p>
                </div>
                <dl className="grid divide-y divide-line md:grid-cols-3 md:divide-x md:divide-y-0">
                  {STATS.map((s) => (
                    <StatCard key={s.label} value={s.value} label={s.label} detail={s.detail} />
                  ))}
                </dl>
              </div>
            </div>
          </section>

        </div>

        {/* ── 3. 3단계 사용 흐름 ─────────────────────────────────── */}
        <section className="bf-home-section bf-home-panel py-24">
          <div className="mx-auto max-w-6xl px-6">
            <FadeIn className="mb-14">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">How it works</p>
              <h2 className="ko-heading mt-4 text-3xl font-extrabold tracking-tight text-ink-900 md:text-4xl break-keep">
                업로드 한 번, 3단계로 끝
              </h2>
            </FadeIn>
            <div className="grid gap-6 md:grid-cols-3">
              {STEPS.map((s, i) => (
                <FadeIn key={s.no} delay={i * 120}>
                  <div className="h-full rounded-card border border-line bg-white p-7">
                    <span className="text-3xl font-extrabold text-accent-600">{s.no}</span>
                    <h3 className="card-title mt-4 text-lg font-bold tracking-tight text-ink-900">{s.title}</h3>
                    <p className="card-desc mt-2 text-[13px] leading-6 text-ink-soft break-keep">{s.body}</p>
                  </div>
                </FadeIn>
              ))}
            </div>
          </div>
        </section>

        {/* ── 4. 핵심 기능 3가지 ─────────────────────────────────── */}
        <section id="features" className="bf-home-section bf-home-panel scroll-mt-20 py-24">
          <div className="mx-auto max-w-6xl px-6">
            <FadeIn className="mb-14">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">Features</p>
              <h2 className="ko-heading mt-4 text-3xl font-extrabold tracking-tight text-ink-900 md:text-4xl break-keep">
                설계사 업무를 줄여주는 3가지
              </h2>
            </FadeIn>
            <div className="grid gap-6 md:grid-cols-3">
              {FEATURES.map((f, i) => (
                <FadeIn key={f.title} delay={i * 100}>
                  <div className="h-full rounded-card border border-line bg-white p-7 transition-all duration-200 hover:-translate-y-0.5 hover:border-green-200 hover:shadow-lg">
                    <span className="text-3xl" aria-hidden>{f.icon}</span>
                    <h3 className="card-title mt-4 text-lg font-bold tracking-tight text-ink-900">{f.title}</h3>
                    <p className="card-desc mt-3 text-[13px] leading-6 text-ink-soft break-keep">{f.body}</p>
                  </div>
                </FadeIn>
              ))}
            </div>
          </div>
        </section>

        {/* ── 5. 만든 이야기 (BOHUMFIT-080 신뢰 스토리) ──────────── */}
        <section className="bf-home-section bf-home-panel bg-accent-50 py-24">
          <div className="mx-auto max-w-6xl px-6">
            <div className="grid items-center gap-10 md:grid-cols-[1fr_auto]">
              <FadeIn>
                <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-700">Our Story</p>
                <h2 className="ko-heading mt-4 text-2xl font-extrabold leading-snug tracking-tight text-ink-900 md:text-3xl break-keep">
                  "현장에서 느낀 불편함이 보험핏을 만들었습니다"
                </h2>
                <div className="ko-text mt-6 space-y-4 text-[15px] leading-8 text-ink-soft break-keep">
                  <p>
                    메리츠화재 지점장으로 근무하며 설계사들이 매번 고객 병력을
                    수작업으로 검토하는 모습을 봐왔습니다.
                  </p>
                  <p>
                    상병코드 하나를 놓쳐 계약이 해지되거나, 고지를 잘못해 고객과의
                    신뢰가 무너지는 경우도 있었습니다.
                  </p>
                  <p>
                    "이 과정이 자동화되면 설계사도, 고객도 모두 편해진다"는 확신에서
                    보험핏을 시작했습니다.
                  </p>
                </div>
              </FadeIn>
              <FadeIn delay={120} className="flex flex-col items-center text-center md:w-56">
                <div className="flex h-36 w-36 items-center justify-center rounded-full border border-line-strong bg-ink-100">
                  <span className="text-caption font-medium text-ink-400">사진 준비 중</span>
                </div>
                <p className="mt-4 text-sm font-bold text-ink-900">이민규</p>
                <p className="mt-1 text-[13px] leading-5 text-ink-soft break-keep">
                  전 메리츠화재 지점장 · 보험핏 대표
                </p>
              </FadeIn>
            </div>
          </div>
        </section>

        {/* ── 6. 가격 CTA ────────────────────────────────────────── */}
        <section className="bf-home-section bf-home-panel py-28">
          <div className="mx-auto max-w-5xl px-6 text-center">
            <FadeIn>
              <h2 className="ko-heading text-3xl font-extrabold tracking-tight text-ink-900 md:text-4xl break-keep">
                지금 바로 시작해보세요
              </h2>
              <div className="mt-12 grid gap-5 sm:grid-cols-3">
                {PRICING.map((p) => (
                  <div key={p.name} className="rounded-card border border-line bg-white px-6 py-8">
                    <p className="card-title text-sm font-semibold text-accent-700">{p.name}</p>
                    <p className="mt-3 text-2xl font-extrabold tracking-tight text-ink-900">{p.price}</p>
                    <p className="card-desc mt-2 text-[13px] text-ink-soft">{p.sub}</p>
                  </div>
                ))}
              </div>
              <p className="ko-text mt-6 text-caption text-ink-400">
                오픈이벤트 — 베이직 첫 3개월 월 9,900원
              </p>
              <Link
                to="/signup"
                className="button-text mt-8 inline-flex rounded-btn bg-accent-600 px-8 py-4 text-base font-semibold text-white transition hover:bg-accent-700"
              >
                무료로 시작하기 →
              </Link>
              <p className="ko-text mt-4 text-xs text-ink-400">
                본 결과는 AI 보조 도구가 제공하는 참고 자료입니다. 가입·인수·보험금 지급을 보장하지 않습니다.
              </p>
            </FadeIn>
          </div>
        </section>

      </div>
    </div>
  );
}
