import { Link } from "react-router-dom";

const cards = [
  {
    label: "Feature 01",
    title: "알릴의무 필터",
    desc: "심평원 PDF 업로드 시 AI가\n고지 항목을 자동 추출합니다.",
    to: "/disclosure",
  },
  {
    label: "Feature 02",
    title: "보장분석 비포&에프터",
    desc: "기존·신규 보장을 비교해\n리모델링 근거를 제시합니다.",
    to: "/before-after",
  },
];

export default function Home() {
  return (
    <div className="relative flex flex-col items-center justify-center min-h-[calc(100vh-56px)] py-20 px-6 -mx-6 overflow-hidden"
      style={{
        background:
          "radial-gradient(ellipse at 20% 50%, rgba(37,99,235,0.18) 0%, transparent 55%), radial-gradient(ellipse at 80% 20%, rgba(99,102,241,0.14) 0%, transparent 50%), linear-gradient(160deg, #070f1f 0%, #0d1f3c 30%, #112a52 60%, #0a1628 100%)",
      }}
    >
      {/* Dot grid overlay */}
      <div className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: "radial-gradient(circle, rgba(255,255,255,0.045) 1px, transparent 1px)",
          backgroundSize: "36px 36px",
        }}
      />

      <div className="relative z-10 flex flex-col items-center w-full max-w-[860px]">
        {/* Badge */}
        <span className="inline-flex items-center gap-1.5 bg-blue-500/15 text-blue-300 text-[0.72rem] font-bold tracking-widest uppercase px-4 py-1.5 rounded-full border border-blue-400/35 mb-7">
          설계사 전용 AI 플랫폼
        </span>

        {/* Logo */}
        <h1 className="text-3xl font-black text-white tracking-tight mb-5">
          SUR<span className="text-blue-400">IT</span>
        </h1>

        {/* Headline */}
        <h2 className="text-4xl md:text-5xl font-black text-white tracking-tight leading-tight text-center mb-5 break-keep">
          보험의 확신,<br />
          <span className="text-blue-400">슈릿</span>에서 쉽고 간편하게.
        </h2>

        {/* Sub */}
        <p className="text-base text-white/50 text-center leading-relaxed mb-14 break-keep">
          심평원 진료 데이터를 AI가 분석해 알릴의무 항목을 자동 추출하고
          <br />
          기존·신규 보장을 한눈에 비교해 드립니다.
        </p>

        {/* Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 w-full max-w-[720px] mb-14">
          {cards.map((c) => (
            <Link key={c.to} to={c.to} className="no-underline group">
              <div className="bg-white/[0.06] border border-white/[0.14] rounded-2xl p-7 text-left backdrop-blur-sm transition-all duration-200 hover:bg-white/[0.11] hover:border-blue-400/55 hover:-translate-y-0.5 hover:shadow-[0_12px_32px_rgba(0,0,0,0.35)]">
                <div className="text-[0.65rem] font-bold tracking-widest uppercase text-blue-400 mb-2.5">
                  {c.label}
                </div>
                <div className="text-lg font-extrabold text-white mb-2.5 tracking-tight">
                  {c.title}
                </div>
                <div className="text-sm text-white/50 leading-relaxed whitespace-pre-line mb-5 break-keep">
                  {c.desc}
                </div>
                <span className="inline-flex items-center gap-1.5 text-sm font-bold text-blue-400 group-hover:gap-2.5 transition-all">
                  시작하기 <span aria-hidden>→</span>
                </span>
              </div>
            </Link>
          ))}
        </div>

        {/* Footer */}
        <p className="text-[0.72rem] text-white/20 tracking-wide">
          SURIT · 설계사에게 확신을 주다 · Powered by Google Gemini
        </p>
      </div>
    </div>
  );
}
