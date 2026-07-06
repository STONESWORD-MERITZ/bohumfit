// BOHUMFIT-046: 알릴의무 필터 통합 진입(허브) — 고객용/설계사용 세그먼트 탭.
// 기존 Disclosure 컴포넌트를 그대로 렌더(무수정·리마운트 없음). 탭은 ?mode= 만 변경하며,
// Disclosure 가 파라미터를 라이브 해석하므로 단일 라우트 안에서 입력 상태가 보존된다
// (기존 /check↔/disclosure 라우트 분리 시절의 상태 손실 개선).
import { useCallback, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Disclosure from "./Disclosure";

type AudienceMode = "customer" | "agent";

const MODES: ReadonlyArray<{ value: AudienceMode; label: string; caption: string }> = [
  { value: "agent", label: "설계사용", caption: "청약 전 알릴의무 필터" },
  { value: "customer", label: "고객용", caption: "기존 보험 고지 점검" },
];

export default function DisclosureHub() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requested = searchParams.get("mode");
  // Disclosure 기본값(initialMode="agent")과 동일한 해석 — 허브 탭 활성 표시용
  const mode: AudienceMode = requested === "customer" ? "customer" : "agent";

  // BOHUMFIT-172: Disclosure가 등록한 가이드 투어 replay 함수(진입점 통합 — 버튼은 허브 줄에).
  const [replayFn, setReplayFn] = useState<(() => void) | null>(null);
  const registerReplay = useCallback((fn: () => void) => setReplayFn(() => fn), []);

  const switchMode = (next: AudienceMode) => {
    if (next === mode) return;
    const params = new URLSearchParams(searchParams);
    params.set("mode", next);
    setSearchParams(params, { replace: true });
  };

  return (
    <div>
      {/* 모드 세그먼트 — Mercury 톤(파스텔 활성) + 우측 [분석 히스토리][필터 가이드 다시보기](BOHUMFIT-172 통합, NAV 미편입) */}
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
      <div
        role="tablist"
        aria-label="알릴의무 필터 모드"
        className="inline-flex rounded-btn border border-line bg-white p-1"
      >
        {MODES.map((m) => {
          const active = m.value === mode;
          return (
            <button
              key={m.value}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => switchMode(m.value)}
              className={`rounded-[0.45rem] px-4 py-1.5 text-sm transition-colors ${
                active
                  ? "bg-accent-50 font-semibold text-accent-700"
                  : "font-medium text-ink-soft hover:text-ink-900"
              }`}
            >
              {m.label}
              <span className="ml-1.5 hidden text-caption font-normal text-ink-400 sm:inline">
                {m.caption}
              </span>
            </button>
          );
        })}
      </div>
      {/* BOHUMFIT-172: 히스토리 진입점 단일화 + 가이드 버튼 통합(고스트 스타일 통일).
          flex-wrap이라 좁은 폭에서는 버튼 그룹이 탭 아래로 자연 줄바꿈(겹침·가로 스크롤 없음). */}
      <div className="flex flex-wrap items-center gap-2">
        <Link
          to="/history"
          data-tour="history"
          className="rounded-[8px] border border-line bg-white px-3 py-2 text-xs font-bold text-ink-soft hover:border-accent-600/40 hover:text-accent-600"
        >
          분석 히스토리
        </Link>
        <button
          type="button"
          onClick={() => replayFn?.()}
          disabled={!replayFn}
          className="rounded-[8px] border border-line bg-white px-3 py-2 text-xs font-bold text-ink-soft hover:border-accent-600/40 hover:text-accent-600 disabled:opacity-60"
        >
          필터 가이드 다시보기
        </button>
      </div>
      </div>

      {/* 기존 페이지 그대로 — ?mode= 파라미터가 모드를 결정 */}
      <Disclosure onRegisterReplay={registerReplay} />
    </div>
  );
}
