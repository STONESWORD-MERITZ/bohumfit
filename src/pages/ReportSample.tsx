// BOHUMFIT-112: 고지의무 분석 리포트 '샘플 미리보기'(비로그인 구독 유도).
//   하드코딩 mock 데이터(실데이터·PII 없음). 실제 분석과 혼동 없도록 상단 샘플 배너·워터마크 문구 표시.
//   실제 분석 화면(Disclosure)과 분리된 자기완결형 페이지 — 표시 구조만 모사한다.
import { Link } from "react-router-dom";
import { useAuth } from "../lib/auth-context"; // BOHUMFIT-159: 하단 전환 섹션 로그인 분기

type SampleItem = { code: string; name: string; first: string; latest: string; visit: number; med: number; surgery?: string };

// ── 가상 데이터(실명·주민번호·실제 진료 없음) ──────────────────────────────
const METRICS = [
  { label: "건강체 고지", value: "3건", tone: "text-amber-600" },
  { label: "간편 고지", value: "1건", tone: "text-amber-600" },
  { label: "전체 병력", value: "5개", tone: "text-ink-900" },
  { label: "총 투약일", value: "84일", tone: "text-ink-900" },
];

const Q_SECTIONS: ReadonlyArray<{ title: string; items: SampleItem[] }> = [
  {
    title: "[3번질문] 5년 이내 입원·수술·통원·투약",
    items: [
      { code: "K29", name: "위염", first: "2023-04-12", latest: "2024-01-08", visit: 6, med: 42 },
      { code: "J30", name: "알레르기비염", first: "2022-09-03", latest: "2023-11-20", visit: 9, med: 30 },
    ],
  },
  {
    title: "[4번질문] 5년 초과 10년 이내 입원·수술",
    items: [
      { code: "S93", name: "발목 인대 손상", first: "2017-06-07", latest: "2017-06-21", visit: 3, med: 12, surgery: "관혈적정복술" },
    ],
  },
];

function Metric({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="rounded-[8px] border border-line bg-white px-4 py-3 text-center">
      <p className={`text-xl font-extrabold ${tone}`}>{value}</p>
      <p className="mt-1 text-[12px] text-ink-soft">{label}</p>
    </div>
  );
}

export default function ReportSample() {
  const { user } = useAuth(); // BOHUMFIT-159: 로그인 여부로 하단 CTA 분기
  return (
    <div className="mx-auto max-w-3xl">
      {/* 샘플 배너 */}
      <div className="rounded-card border border-amber-200 bg-amber-50 p-5">
        <p className="ko-text text-[14px] font-bold text-amber-800">⚠️ 이것은 샘플입니다.</p>
        <p className="ko-text mt-1 text-[13px] leading-6 text-amber-700 break-keep">
          아래 내용은 가상의 예시 데이터로 구성된 미리보기입니다. 실제 분석을 원하시면 구독 후 심평원 PDF를 업로드해 주세요.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Link
            to="/subscription"
            className="button-text rounded-btn bg-accent-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-700"
          >
            구독하고 실제 분석하기 →
          </Link>
          <Link
            to="/download-guide"
            className="button-text rounded-btn border border-line-strong bg-white px-5 py-2.5 text-sm font-semibold text-ink-800 transition hover:bg-ink-50"
          >
            자료 받는 방법
          </Link>
        </div>
      </div>

      {/* 헤더 */}
      <header className="mt-6">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">Sample Report</p>
        <h1 className="ko-heading mt-2 text-2xl font-extrabold tracking-tight text-ink-900 md:text-3xl">
          고지의무 분석 리포트 <span className="text-ink-400">(샘플)</span>
        </h1>
      </header>

      {/* 지표 */}
      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {METRICS.map((m) => (
          <Metric key={m.label} label={m.label} value={m.value} tone={m.tone} />
        ))}
      </div>

      {/* 고지 항목(질문별) */}
      <div className="mt-6 space-y-5">
        {Q_SECTIONS.map((sec) => (
          <section key={sec.title} className="overflow-hidden rounded-card border border-line bg-white">
            <div className="border-b border-line bg-ink-50 px-5 py-3">
              <h2 className="ko-heading text-sm font-bold text-ink-900">{sec.title}</h2>
            </div>
            <ul className="divide-y divide-line">
              {sec.items.map((it, i) => (
                <li key={i} className="px-5 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-accent-50 px-2 py-0.5 text-[11px] font-semibold text-accent-700">{it.code}</span>
                    <span className="text-sm font-bold text-ink-900">{it.name}</span>
                    {it.surgery && (
                      <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700">수술 {it.surgery}</span>
                    )}
                  </div>
                  <p className="ko-text mt-1 text-[13px] text-ink-soft">
                    {it.first} ~ {it.latest} · 통원 {it.visit}회 · 투약 {it.med}일
                  </p>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>

      {/* BOHUMFIT-159: 하단 전환 섹션(딱 1개 — 중간 삽입 없음). 로그인 → 분석, 비로그인 → 가입. */}
      <div className="mt-8 rounded-card border border-accent-200 bg-accent-50 p-6 text-center">
        <h2 className="ko-heading text-lg font-bold text-ink-900">내 PDF로 실제 분석해 보세요</h2>
        <p className="ko-text mt-1 text-[13px] text-ink-soft">
          {user
            ? "샘플은 예시일 뿐, 실제 분석은 업로드한 진료자료를 기준으로 정확히 산출됩니다."
            : "가입하면 최초 무료 분석 5회가 제공됩니다."}
        </p>
        {user ? (
          <Link
            to="/disclosure?mode=agent"
            className="button-text mt-4 inline-flex rounded-btn bg-accent-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-accent-700"
          >
            내 PDF로 분석하기 →
          </Link>
        ) : (
          <Link
            to="/signup"
            className="button-text mt-4 inline-flex rounded-btn bg-accent-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-accent-700"
          >
            가입하고 분석 시작하기 →
          </Link>
        )}
      </div>

      <p className="mt-4 text-center text-[11px] text-ink-400">
        ※ 본 샘플은 가상 데이터이며 실제 진료내역·개인정보를 포함하지 않습니다.
      </p>
    </div>
  );
}
