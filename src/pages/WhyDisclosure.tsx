// BOHUMFIT-048: '왜 중요한가' — 알릴의무 중요성 설득 랜딩(5단 서사). Mercury 톤.
// 기능·라우팅 변경 없음(/why 유지). 콘텐츠 데이터는 ./why/whyContent.ts 분리.
import { Link } from "react-router-dom";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Callout from "../components/ui/Callout";
import {
  CONFLICT_SCENES,
  DISCLOSURE_CRITERIA,
  MECHANISM_STEPS,
  QUAL_CARDS,
  STAT_CARDS,
} from "./why/whyContent";

export default function WhyDisclosure() {
  return (
    <div className="-mt-8 overflow-x-hidden md:-mx-5">

      {/* ── 1. HERO (다크 — 이 페이지 유일한 강조 포인트) ──────────── */}
      <section className="bg-ink-900 px-6 py-20 md:py-24">
        <div className="mx-auto max-w-4xl text-center">
          <Link
            to="/"
            className="mb-8 inline-flex items-center gap-1.5 text-caption font-semibold text-ink-300 transition-colors hover:text-white"
          >
            ← 홈으로
          </Link>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-accent-300">Why It Matters</p>
          <h1 className="mt-5 text-3xl font-extrabold leading-tight tracking-tight text-white sm:text-4xl md:text-5xl break-words md:break-keep">
            고지 누락은<br className="hidden md:inline" /> 작은 실수가 아닙니다
          </h1>
          <p className="mx-auto mt-6 max-w-xl text-[15px] leading-8 text-ink-200 break-words md:break-keep">
            수십 년 납입한 보험이 보험금을 청구하는 순간 무너질 수 있습니다.
            왜 그런 일이 반복되는지, 구조부터 짚어 봅니다.
          </p>
        </div>
      </section>

      {/* ── 2. THE NUMBERS (라이트) ──────────────────────────────── */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-5xl">
          <div className="mb-12 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">The numbers</p>
            <h2 className="mt-3 text-2xl font-extrabold tracking-tight text-ink-900 md:text-3xl">숫자로 보는 현실</h2>
          </div>
          <div className="grid gap-5 md:grid-cols-2">
            {STAT_CARDS.map((s) => (
              <div key={s.label} className="rounded-card border border-line bg-white p-7">
                <p className="text-4xl font-extrabold tabular-nums tracking-tight text-ink-900 md:text-5xl">
                  {s.figure}
                  {s.unit && <span className="ml-1 text-xl font-bold text-ink-soft md:text-2xl">{s.unit}</span>}
                </p>
                <p className="mt-4 text-body leading-7 text-ink break-words md:break-keep">{s.label}</p>
                <p className="mt-3 text-caption text-ink-400">출처 · {s.source}</p>
              </div>
            ))}
            {QUAL_CARDS.map((q) => (
              <div key={q.title} className="rounded-card border border-line bg-white p-7">
                <h3 className="text-title text-ink-900">{q.title}</h3>
                <p className="mt-3 text-body leading-7 text-ink-soft break-words md:break-keep">{q.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 3. 핵심 메커니즘 — 왜 가입 후(청구 시점)가 중요한가 (라이트) ── */}
      <section className="px-6 pb-4 pt-8">
        <div className="mx-auto max-w-5xl">
          <div className="mb-10 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">The mechanism</p>
            <h2 className="mt-3 text-2xl font-extrabold tracking-tight text-ink-900 md:text-3xl break-words md:break-keep">
              왜 ‘가입한 뒤’가 더 중요할까요
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-body leading-7 text-ink-soft break-words md:break-keep">
              병력을 알리는 것에서 끝나지 않습니다. 보험금은 ‘청구하는 순간’ 서면 기록으로 확인되기 때문입니다.
            </p>
          </div>
          <ol className="grid list-none gap-5 md:grid-cols-3">
            {MECHANISM_STEPS.map((m) => (
              <li key={m.step} className="flex flex-col rounded-card border border-line bg-white p-7">
                <span className="text-caption font-bold tabular-nums tracking-[0.25em] text-accent-600">{m.step}</span>
                <h3 className="mt-3 text-title text-ink-900 break-words md:break-keep">{m.title}</h3>
                <p className="mt-3 text-body leading-7 text-ink-soft break-words md:break-keep">{m.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ── 4. 알릴의무란 — 청약서 기준 (라이트) ────────────────────── */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-5xl">
          <div className="mb-10 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">How it works</p>
            <h2 className="mt-3 text-2xl font-extrabold tracking-tight text-ink-900 md:text-3xl break-words md:break-keep">
              청약서는 이런 것들을 묻습니다
            </h2>
          </div>
          <div className="mx-auto grid max-w-3xl gap-3 sm:grid-cols-2">
            {DISCLOSURE_CRITERIA.map((c, i) => (
              <div key={c} className="flex items-start gap-3 rounded-card border border-line bg-white px-5 py-4">
                <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-accent-50 text-caption font-bold tabular-nums text-accent-700">
                  {i + 1}
                </span>
                <span className="text-body leading-6 text-ink break-words md:break-keep">{c}</span>
              </div>
            ))}
          </div>
          <p className="mt-8 text-center text-lg font-bold tracking-tight text-ink-900 md:text-xl break-words md:break-keep">
            이걸 우리 기억력으로 다 체크할 수 있을까요?
          </p>
        </div>
      </section>

      {/* ── 5. 이렇게 어긋납니다 — 분쟁 3장면 (라이트) ───────────── */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-5xl">
          <div className="mb-10 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">Where it breaks</p>
            <h2 className="mt-3 text-2xl font-extrabold tracking-tight text-ink-900 md:text-3xl break-words md:break-keep">
              이렇게 어긋납니다
            </h2>
          </div>
          <div className="grid gap-5 md:grid-cols-3">
            {CONFLICT_SCENES.map((c) => (
              <div key={c.title} className="flex flex-col rounded-card border border-line bg-white p-6">
                <Badge tone={c.resultTone}>{c.result}</Badge>
                <h3 className="mt-4 text-title text-ink-900 break-words md:break-keep">{c.title}</h3>
                <p className="mt-3 text-body leading-7 text-ink-soft break-words md:break-keep">{c.body}</p>
              </div>
            ))}
          </div>
          <p className="mt-6 text-center text-caption text-ink-400 break-words md:break-keep">
            ※ 위 3가지는 실제 개별 사건이 아니라 일반적으로 반복되는 분쟁 유형을 재구성한 예시입니다.
          </p>
        </div>
      </section>

      {/* ── 6. 그래서, 점검 — 해결 + CTA (라이트) ────────────────── */}
      <section className="px-6 pb-24 pt-4">
        <div className="mx-auto max-w-3xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">So, check it</p>
          <h2 className="mt-3 text-2xl font-extrabold tracking-tight text-ink-900 md:text-3xl break-words md:break-keep">
            그래서, 점검합니다
          </h2>
          <p className="mx-auto mt-5 text-[15px] leading-8 text-ink-soft break-words md:break-keep">
            보험핏은 심평원 진료기록을 청약서 기준에 대조해 항목마다
            <strong className="text-ink-900"> 고지 필요 · 확인 필요 · 해당 없음</strong>을 정리해 보여 줍니다.
            기억이 아니라 기록으로 확인하는 것이 시작입니다.
          </p>

          <div className="mt-8">
            <Link to="/disclosure">
              <Button size="lg">알릴의무 필터로 점검하기 →</Button>
            </Link>
          </div>

          <Callout variant="legal" className="mx-auto mt-10 max-w-2xl text-left">
            보험핏은 특정 상품의 가입이나 해지를 권유하지 않는 <strong>중립 점검 도구</strong>입니다.
            본 페이지의 통계는 표기된 출처를 인용한 것이며, 분쟁 장면은 일반 유형의 재구성 예시입니다.
            개별 계약의 해석은 약관과 보험회사 심사에 따르며, 보험핏은 보험 가입·인수·보험금 지급을
            보장하지 않습니다.
          </Callout>

          <p className="mt-6 text-caption text-ink-400">
            보험핏을 만든 사람들이 궁금하다면{" "}
            <Link to="/#mission" className="font-semibold text-accent-700 hover:underline">
              회사소개
            </Link>
            에서 확인하세요.
          </p>
        </div>
      </section>

    </div>
  );
}
