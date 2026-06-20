// BOHUMFIT-081: 보장 비교분석 페이지 UI 뼈대.
//   업로드 → "분석 준비 중" 상태까지만. 실제 분석 로직·알림신청 Supabase 저장은 추후 별도 태스크.
import { useState } from "react";

function UploadSlot({ label }: { label: string }) {
  return (
    <div className="flex h-44 flex-col items-center justify-center rounded-card border-2 border-dashed border-line-strong bg-ink-50 text-center opacity-60">
      <span className="text-2xl text-ink-300" aria-hidden>📄</span>
      <p className="mt-3 text-sm font-semibold text-ink-500">{label}</p>
      <p className="mt-1 text-[12px] text-ink-400">(PDF 업로드)</p>
    </div>
  );
}

export default function CoverageCompare() {
  const [email, setEmail] = useState("");
  const [requested, setRequested] = useState(false);
  const [error, setError] = useState("");

  const handleNotify = () => {
    const trimmed = email.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
      setError("이메일 주소를 정확히 입력해 주세요.");
      return;
    }
    setError("");
    // TODO(BOHUMFIT-후속): 알림 신청 이메일을 Supabase에 저장. 현재는 UI 확인만.
    setRequested(true);
  };

  return (
    <div className="mx-auto max-w-4xl">
      {/* 헤더 */}
      <header className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">Coverage Compare</p>
        <h1 className="mt-3 text-3xl font-extrabold tracking-tight text-ink-900 md:text-4xl break-keep">
          보장 비교분석
        </h1>
        <p className="mt-3 text-[15px] leading-7 text-ink-soft break-keep">
          가입 전·후 보험을 비교해 고객에게 최적의 설계를 제안하세요.
        </p>
      </header>

      {/* 준비 중 배너 + 알림 신청 */}
      <section className="mb-8 rounded-card border border-warning-100 bg-warning-50 p-6">
        <h2 className="text-lg font-bold tracking-tight text-warning-700 break-keep">
          🔧 이 기능은 현재 준비 중입니다
        </h2>
        <p className="mt-2 text-[14px] leading-6 text-warning-700 break-keep">
          곧 업데이트될 예정이며, 베타 오픈 시 알림을 보내드립니다.
        </p>
        {requested ? (
          <p className="mt-4 rounded-[8px] bg-white px-4 py-3 text-sm font-semibold text-accent-700">
            ✓ 알림 신청이 완료되었어요. 베타 오픈 시 안내드릴게요.
          </p>
        ) : (
          <div className="mt-4">
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                type="email"
                inputMode="email"
                placeholder="알림 받을 이메일 주소"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="min-w-0 flex-1 rounded-[8px] border border-line-strong bg-white px-3 py-2.5 text-sm text-ink-800 placeholder:text-ink-300 focus:outline-none focus:ring-2 focus:ring-accent-600/30"
              />
              <button
                type="button"
                onClick={handleNotify}
                className="rounded-[8px] bg-accent-600 px-5 py-2.5 text-sm font-bold text-white transition hover:bg-accent-700"
              >
                알림 신청하기
              </button>
            </div>
            {error && <p className="mt-2 text-xs font-semibold text-danger-600">{error}</p>}
          </div>
        )}
      </section>

      {/* 미리보기 UI — 비활성 */}
      <section className="mb-8 rounded-card border border-line bg-white p-6">
        <p className="mb-4 text-sm font-semibold text-ink-700">미리보기</p>
        <div className="grid gap-5 sm:grid-cols-2">
          <UploadSlot label="현재 보험 파일" />
          <UploadSlot label="신규 보험 파일" />
        </div>
        <button
          type="button"
          disabled
          aria-disabled="true"
          className="mt-6 w-full cursor-not-allowed rounded-btn bg-ink-200 px-5 py-3 text-sm font-bold text-ink-400"
        >
          분석 시작 — 준비 중인 기능입니다
        </button>
      </section>
    </div>
  );
}
