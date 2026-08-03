// BOHUMFIT-269a — 모바일 홈(진입 카드 2종 · 최근 분석 · 남은 횟수).
//
//   ★데이터를 여기서 다시 불러오지 않는다. `Dashboard`(163)가 이미 가져온 값을 **props로 받는다** —
//     같은 화면에서 같은 API를 두 번 부르지 않기 위해서다(중복 구현 금지).
//   ★라우트를 신설하지 않는다. 진입 카드는 기존 경로(`/disclosure?mode=agent`·`/coverage-compare`)로만 간다.
//   ★PII: 최근 분석 항목은 사용자가 입력한 **별칭**·분석 종류·시각뿐이다(환자명·원본 파일명 없음 — 268b 기조).
//   ※하단 네비는 269b 범위라 여기서 자리도 만들지 않는다.
import { Link } from "react-router-dom";
import { FileSearch, ShieldCheck } from "lucide-react";
import { MOBILE_LAYOUT, MOBILE_TOUCH } from "./tokens";

export type MobileHomeRecentItem = { id: string; label: string; mode: string; created_at: string };

export type MobileHomeUsage = {
  /** 무제한(관리자)일 때 true — 숫자를 만들지 않는다. */
  unlimited: boolean;
  used: number;
  limit: number | null;
  left: number | null;
  /** 남은 횟수가 적을 때 강조(159 톤과 같은 기준을 호출부가 판정해 넘긴다). */
  warn: boolean;
  /** 플랜 설명 한 줄 — 호출부가 만든 문구를 그대로 쓴다. */
  planLabel: string;
};

/** 진입 카드 2종 — 기존 라우트만 쓴다. */
const ENTRIES = [
  {
    to: "/disclosure?mode=agent",
    title: "고지의무 분석",
    description: "심평원·공단 진료자료로 알릴의무 대상을 찾습니다.",
    Icon: FileSearch,
    testId: "home-entry-disclosure",
  },
  {
    to: "/coverage-compare",
    title: "보장분석",
    description: "보장분석표로 컨설팅 전·후 보장을 비교합니다.",
    Icon: ShieldCheck,
    testId: "home-entry-coverage",
  },
] as const;

function formatWhen(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function modeLabel(mode: string): string {
  return mode === "easy" ? "간편심사" : "건강체/표준체";
}

export default function MobileHome({
  email,
  recent,
  usage,
}: {
  email?: string | null;
  /** null=로딩 · false=실패 · 배열=성공(빈 배열이면 "아직 없음"). */
  recent: MobileHomeRecentItem[] | null | false;
  /** null=로딩 · false=실패. */
  usage: MobileHomeUsage | null | false;
}) {
  return (
    <div data-testid="mobile-home" style={{ paddingBottom: MOBILE_LAYOUT.gutter }}>
      <header>
        <h1 className="text-[20px] font-bold leading-[1.35] text-ink-900">무엇을 도와드릴까요?</h1>
        {email && <p className="mt-1 break-all text-[15px] leading-[1.55] text-ink-soft">{email}</p>}
      </header>

      {/* ── 진입 카드 2종 ── */}
      <ul className="mt-4 space-y-3" data-testid="home-entries">
        {ENTRIES.map(({ to, title, description, Icon, testId }) => (
          <li key={to}>
            <Link
              to={to}
              data-testid={testId}
              className="flex items-center gap-3 border border-line bg-white px-4 text-left"
              style={{
                borderRadius: MOBILE_LAYOUT.radiusCard,
                minHeight: MOBILE_TOUCH.action,
                paddingTop: 14,
                paddingBottom: 14,
              }}
            >
              <Icon aria-hidden className="h-6 w-6 shrink-0 text-accent-600" />
              <span className="min-w-0 flex-1">
                <span className="block text-[16px] font-bold leading-[1.4] text-ink-900">{title}</span>
                <span className="mt-0.5 block break-keep text-[15px] leading-[1.55] text-ink-soft">{description}</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>

      {/* ── 남은 횟수 (표시만 — 요금제·결제 로직 무접촉) ── */}
      <section
        className="mt-4 border border-line bg-white px-4 py-4"
        style={{ borderRadius: MOBILE_LAYOUT.radiusCard }}
        data-testid="home-usage"
      >
        <h2 className="text-[16px] font-bold leading-[1.4] text-ink-900">분석 사용량</h2>
        {usage === null || usage === false ? (
          <p className="mt-2 text-[15px] leading-[1.55] text-ink-soft">
            {usage === null ? "불러오는 중…" : "불러오지 못했어요. 잠시 후 새로고침해 주세요."}
          </p>
        ) : usage.unlimited ? (
          <>
            <p className="mt-2 text-[24px] font-extrabold leading-[1.25] text-ink-900">무제한</p>
            <p className="mt-1 text-[15px] leading-[1.55] text-ink-soft">{usage.planLabel}</p>
          </>
        ) : (
          <>
            <p className={`mt-2 text-[24px] font-extrabold leading-[1.25] ${usage.warn ? "text-warning-700" : "text-ink-900"}`}>
              {usage.left ?? 0}회
              <span className="text-[15px] font-semibold text-ink-soft"> 남음</span>
            </p>
            <p className="mt-1 break-keep text-[15px] leading-[1.55] text-ink-soft">
              {usage.planLabel} · {usage.used}/{usage.limit ?? "-"}회 사용
            </p>
          </>
        )}
      </section>

      {/* ── 최근 분석 (서버 히스토리 — 기기 로컬 24h 캐시와는 성격이 다르다) ── */}
      <section
        className="mt-4 border border-line bg-white px-4 py-4"
        style={{ borderRadius: MOBILE_LAYOUT.radiusCard }}
        data-testid="home-recent"
      >
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="text-[16px] font-bold leading-[1.4] text-ink-900">최근 분석</h2>
          {Array.isArray(recent) && recent.length > 0 && (
            <Link to="/history" className="m-tap shrink-0 text-[15px] font-bold text-accent-700">
              전체 보기
            </Link>
          )}
        </div>

        {recent === null || recent === false ? (
          <p className="mt-2 text-[15px] leading-[1.55] text-ink-soft">
            {recent === null ? "불러오는 중…" : "불러오지 못했어요. 잠시 후 새로고침해 주세요."}
          </p>
        ) : recent.length === 0 ? (
          // 빈 상태를 방치하지 않는다 — 다음에 할 일을 바로 준다.
          <div className="mt-3">
            <p className="text-[15px] leading-[1.55] text-ink-soft">아직 분석 기록이 없어요.</p>
            <Link
              to="/disclosure?mode=agent"
              data-testid="home-recent-empty-cta"
              className="mt-3 flex w-full items-center justify-center bg-accent-600 text-[16px] font-bold text-white"
              style={{ minHeight: MOBILE_TOUCH.action, borderRadius: MOBILE_LAYOUT.radiusBtn }}
            >
              첫 분석 시작하기
            </Link>
          </div>
        ) : (
          <ul className="mt-2 divide-y divide-line">
            {recent.map((item) => (
              <li key={item.id}>
                <Link
                  to="/history"
                  className="flex items-center gap-2 py-3"
                  style={{ minHeight: MOBILE_TOUCH.tap }}
                  aria-label={`${item.label} 재열람`}
                >
                  <span className="min-w-0 flex-1 truncate text-[15px] font-semibold leading-[1.55] text-ink">
                    {item.label}
                  </span>
                  <span className="shrink-0 text-[15px] leading-[1.55] text-ink-soft">{modeLabel(item.mode)}</span>
                  <span className="shrink-0 text-[15px] leading-[1.55] text-ink-400">{formatWhen(item.created_at)}</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
