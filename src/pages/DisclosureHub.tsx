// BOHUMFIT-046: 알릴의무 필터 통합 진입(허브) — 고객용/설계사용 세그먼트 탭.
// 기존 Disclosure 컴포넌트를 그대로 렌더(무수정·리마운트 없음). 탭은 ?mode= 만 변경하며,
// Disclosure 가 파라미터를 라이브 해석하므로 단일 라우트 안에서 입력 상태가 보존된다
// (기존 /check↔/disclosure 라우트 분리 시절의 상태 손실 개선).
import { useSearchParams } from "react-router-dom";
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

  const switchMode = (next: AudienceMode) => {
    if (next === mode) return;
    const params = new URLSearchParams(searchParams);
    params.set("mode", next);
    setSearchParams(params, { replace: true });
  };

  return (
    <div>
      {/* 모드 세그먼트 — Mercury 톤(파스텔 활성) */}
      <div
        role="tablist"
        aria-label="알릴의무 필터 모드"
        className="mb-5 inline-flex rounded-btn border border-line bg-white p-1"
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

      {/* 기존 페이지 그대로 — ?mode= 파라미터가 모드를 결정 */}
      <Disclosure />
    </div>
  );
}
