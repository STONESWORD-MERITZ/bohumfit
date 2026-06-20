// BOHUMFIT-077: 심평원 진료 자료 다운로드 가이드(공개 페이지).
//   설계사가 고객 자료를 어디서·어떻게 받는지 단계별 안내. 이미지·유튜브 링크는 플레이스홀더.
import { Link } from "react-router-dom";

const HIRA_URL = "https://www.hira.or.kr";
const YOUTUBE_URL = "https://www.youtube.com/@hira_kr";

type GuideCard = {
  icon: string;
  title: string;
  desc: string;
  path: string;
  placeholder: string;
};

const CARDS: ReadonlyArray<GuideCard> = [
  {
    icon: "📋",
    title: "기본진료내역",
    desc: "진료 기록의 기본 정보 (진료일, 병원명, 상병코드)",
    path: "심평원 홈페이지 > 나의 건강정보 > 진료내역",
    placeholder: "기본진료내역 화면 캡처",
  },
  {
    icon: "🔍",
    title: "세부진료내역",
    desc: "수술명, 처치 내용 등 세부 진료 정보",
    path: "심평원 홈페이지 > 나의 건강정보 > 세부진료내역",
    placeholder: "세부진료내역 화면 캡처",
  },
  {
    icon: "💊",
    title: "처방조제내역",
    desc: "처방받은 약 내역 (약품명, 투약일수)",
    path: "심평원 홈페이지 > 나의 건강정보 > 처방조제내역",
    placeholder: "처방조제내역 화면 캡처",
  },
];

function ImagePlaceholder({ label }: { label: string }) {
  return (
    <div className="mt-4 flex h-40 flex-col items-center justify-center rounded-card border border-dashed border-line-strong bg-ink-50 text-center">
      <span className="text-2xl text-ink-300" aria-hidden>🖼️</span>
      <span className="mt-2 text-caption font-medium text-ink-400">{label}</span>
      <span className="text-[11px] text-ink-300">이미지 준비 중</span>
    </div>
  );
}

export default function DownloadGuide() {
  return (
    <div className="mx-auto max-w-5xl">
      {/* 헤더 */}
      <header className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">Download Guide</p>
        <h1 className="ko-heading mt-3 text-3xl font-extrabold tracking-tight text-ink-900 md:text-4xl break-keep">
          심평원 진료 자료 다운로드 가이드
        </h1>
        <p className="ko-text mobile-copy mt-3 text-[15px] leading-7 text-ink-soft break-keep">
          보험핏 분석을 위해 아래 3가지 자료가 필요합니다.
        </p>
      </header>

      {/* 안내 배너 */}
      <div className="mb-8 rounded-card border border-accent-200 bg-accent-50 p-5">
        <p className="ko-text text-[14px] leading-6 text-accent-800 break-keep">
          💡 자료는 건강보험심사평가원(심평원) 홈페이지에서 무료로 발급받을 수 있습니다.
        </p>
      </div>

      {/* 유튜브 영상 섹션 */}
      <section className="mb-10 rounded-card border border-line bg-white p-6">
        <h2 className="ko-heading text-lg font-bold tracking-tight text-ink-900">📹 영상으로 보기</h2>
        <p className="ko-text mt-2 text-[14px] leading-6 text-ink-soft break-keep">
          영상을 보시면 3분 안에 자료 발급이 가능합니다.
        </p>
        <a
          href={YOUTUBE_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="button-text mt-4 inline-flex items-center gap-2 rounded-btn bg-ink-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-ink-700"
        >
          <span aria-hidden>▶</span> 유튜브에서 영상 보기
        </a>
      </section>

      {/* 3단계 자료 안내 카드 */}
      <section className="mb-12">
        <div className="grid gap-6 md:grid-cols-3">
          {CARDS.map((c, i) => (
            <div key={c.title} className="flex flex-col rounded-card border border-line bg-white p-6">
              <div className="flex items-center gap-2">
                <span className="text-2xl" aria-hidden>{c.icon}</span>
                <span className="rounded-full bg-accent-100 px-2.5 py-0.5 text-[11px] font-semibold text-accent-700">
                  STEP {i + 1}
                </span>
              </div>
              <h3 className="card-title mt-4 text-lg font-bold tracking-tight text-ink-900">{c.title}</h3>
              <p className="card-desc mt-2 text-[13px] leading-6 text-ink-soft break-keep">{c.desc}</p>
              <div className="mt-4 rounded-[8px] bg-ink-50 p-3">
                <p className="text-[11px] font-semibold text-ink-400">발급처</p>
                <p className="ko-text mt-1 text-[12px] leading-5 text-ink-700 break-keep">{c.path}</p>
              </div>
              <ImagePlaceholder label={c.placeholder} />
              <a
                href={HIRA_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="safe-break mt-4 inline-flex items-center text-sm font-semibold text-accent-700 hover:text-accent-800"
              >
                심평원 홈페이지 바로가기 →
              </a>
            </div>
          ))}
        </div>
      </section>

      {/* 하단 CTA */}
      <section className="rounded-card border border-accent-200 bg-accent-50 p-8 text-center">
        <h2 className="ko-heading text-2xl font-extrabold tracking-tight text-ink-900 break-keep">
          자료를 모두 준비하셨나요?
        </h2>
        <Link
          to="/disclosure?mode=agent"
          className="button-text mt-6 inline-flex rounded-btn bg-accent-600 px-8 py-4 text-base font-semibold text-white transition hover:bg-accent-700"
        >
          고지의무 분석 시작하기 →
        </Link>
      </section>
    </div>
  );
}
