// BOHUMFIT-163: 로그인 대시보드 홈 — 최근 분석·사용량·저장 리포트·바로가기·Pro 업셀.
//   ★신규 백엔드 API 0 — 기존 3개 엔드포인트 조합만:
//     GET /history?track=recent&limit=5 (최근 분석) · GET /history?track=saved&limit=1 (total=저장 수)
//     GET /billing/status (used/limit·trial_used/trial_limit·role/quota_scope — 159 업셀 톤 재사용)
//   위젯별 독립 상태·독립 fetch — 한 위젯 실패가 페이지 전체를 깨지 않는다(graceful).
//   진입: Layout UserArea "대시보드"(로그인 시). 로그인 후 기본 진입(/disclosure)은 무변경(A안).
import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, FileSearch, Link2, CreditCard } from "lucide-react";
import { useAuth } from "../lib/auth-context";

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

type RecentItem = { id: string; label: string; mode: string; created_at: string };
type Billing = {
  status: string;
  plan: string | null;
  used: number;
  limit: number | null;
  trial_used?: number;
  trial_limit?: number;
  is_internal: boolean;
  is_admin?: boolean;
  quota_scope?: "unlimited" | "monthly" | "subscription" | "lifetime";
  enabled?: boolean;
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function modeLabel(mode: string): string {
  return mode === "easy" ? "간편심사" : "건강체/표준체";
}

/** 위젯 공통 카드 셸 — heading 위계(h2)·실패 캡션 일원화. tone으로 면 색 분기(클래스 충돌 방지). */
function Widget({
  title,
  children,
  className = "",
  tone = "default",
}: {
  title: string;
  children: ReactNode;
  className?: string;
  tone?: "default" | "accent";
}) {
  const surface = tone === "accent" ? "border-accent-200 bg-accent-50" : "border-line bg-white";
  return (
    <section className={`rounded-[8px] border p-5 ${surface} ${className}`}>
      <h2 className="text-sm font-extrabold text-ink-900">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function WidgetFallback({ loading }: { loading: boolean }) {
  return <p className="text-[13px] text-ink-soft">{loading ? "불러오는 중…" : "불러오지 못했어요. 잠시 후 새로고침해 주세요."}</p>;
}

export default function Dashboard() {
  const { user, session } = useAuth();
  const token = session?.access_token;

  // 위젯별 독립 상태: null=로딩, false=실패, 값=성공 (graceful 격리)
  const [recent, setRecent] = useState<{ items: RecentItem[]; total: number } | null | false>(null);
  const [saved, setSaved] = useState<{ total: number; max: number | null } | null | false>(null);
  const [billing, setBilling] = useState<Billing | null | false>(null);

  useEffect(() => {
    if (!token) return;
    const headers = { Authorization: `Bearer ${token}` };
    let alive = true;

    fetch(`${API_BASE}/history?track=recent&limit=5`, { headers })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d) => alive && setRecent({ items: d.items ?? [], total: d.total ?? 0 }))
      .catch(() => alive && setRecent(false));

    fetch(`${API_BASE}/history?track=saved&limit=1`, { headers })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d) => alive && setSaved({ total: d.total ?? 0, max: d.quota?.max ?? null }))
      .catch(() => alive && setSaved(false));

    fetch(`${API_BASE}/billing/status`, { headers })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d) => alive && setBilling(d))
      .catch(() => alive && setBilling(false));

    return () => {
      alive = false;
    };
  }, [token]);

  // 사용량 계산 — 서버 권위 quota_scope 표시: admin=무제한 / internal=월100 / active=플랜 / 그 외=최초 무료 분석
  const isActive = billing && billing.status === "active";
  const isAdmin = !!(billing && (billing.is_admin || billing.quota_scope === "unlimited"));
  const isInternal = !!(billing && billing.is_internal);
  const usageUsed = billing ? (isInternal || isActive ? billing.used : billing.trial_used ?? 0) : 0;
  const usageLimit = billing ? (isAdmin ? null : isInternal || isActive ? billing.limit ?? 0 : billing.trial_limit ?? 5) : 0;
  const usageLeft = usageLimit == null ? null : Math.max(0, usageLimit - usageUsed);
  const usageRatio = usageLimit && usageLimit > 0 ? Math.min(1, usageUsed / usageLimit) : 0;
  const usageWarn = billing && usageLimit != null && usageLeft != null && usageLeft <= Math.max(1, Math.ceil(usageLimit * 0.1));
  // Pro 업셀: 무료 유저 한정(비구독·비admin·비internal) + 소진 근접(잔여 ≤1) 또는 소진
  const showUpsell = !!(billing && !isAdmin && !isInternal && !isActive && usageLeft != null && usageLeft <= 1);

  return (
    <div className="mx-auto max-w-5xl">
      <header>
        <h1 className="text-xl font-extrabold text-ink-900">대시보드</h1>
        <p className="mt-1 text-[13px] text-ink-soft">
          {user?.email ? `${user.email} · ` : ""}최근 분석과 사용량을 한눈에 확인하세요.
        </p>
      </header>

      {/* 데스크톱 3열 → 모바일 1단 (Tailwind 반응형만 사용) */}
      <div className="mt-5 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* ── 1. 최근 분석 (recent 트랙 상위 5) ── */}
        <Widget title="최근 분석" className="md:col-span-2">
          {recent === null || recent === false ? (
            <WidgetFallback loading={recent === null} />
          ) : recent.items.length === 0 ? (
            <div className="py-4 text-center">
              <p className="text-[13px] text-ink-soft">아직 분석 기록이 없어요.</p>
              <Link
                to="/disclosure?mode=agent"
                className="mt-3 inline-block rounded-[8px] bg-accent-600 px-4 py-2 text-sm font-bold text-white hover:bg-accent-700"
              >
                첫 분석 시작하기
              </Link>
            </div>
          ) : (
            <>
              <ul className="divide-y divide-line">
                {recent.items.map((item) => (
                  <li key={item.id}>
                    <Link to="/history" className="flex items-center gap-2 py-2 hover:bg-ink-50" aria-label={`${item.label} 재열람`}>
                      <span className="min-w-0 flex-1 truncate text-[13px] font-semibold text-ink">{item.label}</span>
                      <span className={`shrink-0 rounded-[4px] px-1.5 py-0.5 text-[11px] font-semibold ${
                        item.mode === "easy" ? "bg-accent-50 text-accent-700" : "bg-ink-100 text-ink-soft"
                      }`}>
                        {modeLabel(item.mode)}
                      </span>
                      <span className="shrink-0 text-[12px] text-ink-400">{formatDate(item.created_at)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
              <Link to="/history" className="mt-2 inline-flex items-center gap-1 text-[12px] font-semibold text-accent-700 hover:text-accent-600">
                히스토리 전체 보기 <ArrowRight aria-hidden className="h-3.5 w-3.5" />
              </Link>
            </>
          )}
        </Widget>

        {/* ── 2. 분석 사용량 (billing_status — 159/212 톤) ── */}
        <Widget title={isAdmin ? "분석 사용량" : isInternal || isActive ? "이번 달 사용량" : "무료 분석 사용량"}>
          {billing === null || billing === false ? (
            <WidgetFallback loading={billing === null} />
          ) : billing.enabled === false ? (
            <p className="text-[13px] text-ink-soft">사용량 집계가 비활성 상태예요.</p>
          ) : isAdmin ? (
            <>
              <p className="text-2xl font-extrabold tabular-nums text-ink-900">무제한</p>
              <p className="mt-0.5 text-[12px] text-ink-soft">관리자 계정 · 분석 횟수 제한 없음</p>
            </>
          ) : (
            <>
              <p className="text-2xl font-extrabold tabular-nums text-ink-900">
                {usageUsed}
                <span className="text-sm font-semibold text-ink-soft"> / {usageLimit ?? "-"}회</span>
              </p>
              <p className="mt-0.5 text-[12px] text-ink-soft">
                {isInternal ? "내부 계정 · 월 100회" : isActive ? `${billing.plan === "pro" ? "프로" : "베이직"} 플랜` : "최초 무료 분석"}
                {` · 남은 ${usageLeft ?? 0}회`}
              </p>
              <div
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={usageLimit ?? 0}
                aria-valuenow={usageUsed}
                aria-label={isInternal || isActive ? "이번 달 분석 사용량" : "무료 분석 누적 사용량"}
                className="mt-3 h-2 overflow-hidden rounded-full bg-ink-100"
              >
                <div
                  className={`h-full rounded-full ${usageWarn ? "bg-amber-500" : "bg-accent-600"}`}
                  style={{ width: `${Math.round(usageRatio * 100)}%` }}
                />
              </div>
            </>
          )}
        </Widget>

        {/* ── 3. 저장된 리포트 (saved 트랙 total — 목록 API 재사용, 신규 count API 없음) ── */}
        <Widget title="저장된 리포트">
          {saved === null || saved === false ? (
            <WidgetFallback loading={saved === null} />
          ) : (
            <>
              <p className="text-2xl font-extrabold tabular-nums text-ink-900">
                {saved.total}
                <span className="text-sm font-semibold text-ink-soft">{saved.max === null ? "건 · 무제한" : ` / ${saved.max}건`}</span>
              </p>
              <p className="mt-0.5 text-[12px] text-ink-soft">저장 90일 보관 · PDF 다운로드 가능</p>
              <Link to="/history" className="mt-3 inline-flex items-center gap-1 text-[12px] font-semibold text-accent-700 hover:text-accent-600">
                히스토리 관리 <ArrowRight aria-hidden className="h-3.5 w-3.5" />
              </Link>
            </>
          )}
        </Widget>

        {/* ── 4. 바로가기 ── */}
        <Widget title="바로가기" className={showUpsell ? "" : "lg:col-span-2"}>
          <ul className="grid gap-2 sm:grid-cols-3">
            {[
              { to: "/disclosure?mode=agent", label: "분석 시작", Icon: FileSearch },
              { to: "/insurance-links", label: "보험사 링크", Icon: Link2 },
              { to: "/subscription", label: "요금제", Icon: CreditCard },
            ].map(({ to, label, Icon }) => (
              <li key={to}>
                <Link
                  to={to}
                  className="flex items-center gap-2 rounded-[8px] border border-line bg-white px-3 py-2.5 text-[13px] font-bold text-ink hover:border-accent-600 hover:text-accent-700"
                >
                  <Icon aria-hidden className="h-4 w-4 shrink-0 text-accent-600" />
                  {label}
                </Link>
              </li>
            ))}
          </ul>
        </Widget>

        {/* ── 5. Pro 업셀 (무료 유저 한정·internal 미노출 — 159 카드 톤 재사용) ── */}
        {showUpsell && (
          <Widget title="더 많은 분석이 필요하다면" tone="accent">
            <p className="ko-text text-[13px] leading-6 text-ink-soft break-keep">
              {usageLeft === 0
                ? `무료 분석 ${usageLimit}회를 모두 사용했어요. `
                : `무료 분석이 ${usageLeft}회 남았어요. `}
              구독하면 매월 30회(베이직)~100회(프로) 분석과 고객용 PDF 저장을 이용할 수 있어요.
            </p>
            <Link
              to="/subscription"
              className="mt-3 inline-block rounded-[8px] bg-accent-600 px-4 py-2 text-sm font-bold text-white hover:bg-accent-700"
            >
              요금제 보기
            </Link>
          </Widget>
        )}
      </div>
    </div>
  );
}
