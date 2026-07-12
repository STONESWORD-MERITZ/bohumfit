// BOHUMFIT-071/212: 구독 상태·role별 분석 횟수 배지. Disclosure 결과 상단에 표시.
//   게이트 비활성·조회 실패 시 숨김. admin/internal/customer 주기는 서버 응답을 표시만 한다.
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth-context";

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

type BillingStatus = {
  status: string;
  used: number;
  limit: number | null;
  trial_used?: number;   // BOHUMFIT-212: 미구독 무료 분석 누적 사용량
  trial_limit?: number;
  is_internal: boolean;
  is_admin?: boolean;
  quota_scope?: "unlimited" | "monthly" | "subscription" | "lifetime";
  enabled?: boolean;
  period_end?: string | null;
};

export default function UsageBadge() {
  const { session } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState<BillingStatus | null>(null);
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    const token = session?.access_token;
    if (!token) return;
    let alive = true;
    fetch(`${API_BASE}/billing/status`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => (r.ok ? r.json() : null))
      .then((d: BillingStatus | null) => {
        if (!alive) return;
        if (d) setData(d);
        else setHidden(true);
      })
      .catch(() => alive && setHidden(true));
    return () => {
      alive = false;
    };
  }, [session]);

  if (hidden || !data) return null;
  if (data.enabled === false) return null; // 구독 게이트 비활성(기존 무료 동작)

  if (data.is_admin || data.quota_scope === "unlimited") {
    return (
      <button
        type="button"
        onClick={() => navigate("/subscription")}
        className="inline-flex items-center gap-1.5 rounded-[8px] border border-accent-200 bg-accent-50 px-3 py-1.5 text-[12px] font-semibold text-accent-700 hover:bg-accent-100"
        title="구독 관리"
      >
        관리자 · 분석 무제한
      </button>
    );
  }

  // BOHUMFIT-212: 미구독 → 최초 무료 분석 누적 사용량 표시.
  // BOHUMFIT-159: 과노출 금지 — 잔여 3회 이상이면 숨기고, 잔여 ≤ 2부터 "무료 분석 N회 남음"
  //   (v1.1 캡션 위계 600·12, 그린티 틴트 면). 소진(0회)은 소진 안내 + 요금제 제안.
  if (data.status !== "active") {
    const trialLimit = data.trial_limit ?? 5;
    const trialUsed = data.trial_used ?? 0;
    const trialLeft = Math.max(0, trialLimit - trialUsed);
    if (data.is_internal || data.quota_scope === "monthly") {
      const limit = data.limit ?? 100;
      const remaining = Math.max(0, limit - (data.used ?? 0));
      const tone = remaining <= 10 ? "text-amber-700 border-amber-300 bg-amber-50" : "text-ink-soft border-line bg-ink-50";
      return (
        <button
          type="button"
          onClick={() => navigate("/subscription")}
          className={`inline-flex items-center gap-1.5 rounded-[8px] border px-3 py-1.5 text-[12px] font-medium ${tone}`}
          title="구독 관리"
        >
          내부 계정 · 이번 달 <b className="font-bold">{data.used}</b> / {limit}회
          <span className="text-ink-400">(남은 {remaining}회)</span>
        </button>
      );
    }
    if (trialLeft > 2) return null; // 여유 있을 땐 노출하지 않음(과노출 금지)
    if (trialLeft > 0) {
      return (
        <button
          type="button"
          onClick={() => navigate("/subscription")}
          className="inline-flex items-center gap-1.5 rounded-[8px] bg-greentea px-3 py-1.5 text-[12px] font-semibold text-ink hover:opacity-90"
          title="요금제 보기"
        >
          무료 분석 <b className="font-bold">{trialLeft}회</b> 남음
        </button>
      );
    }
    return (
      <button
        type="button"
        onClick={() => navigate("/subscription")}
        className="inline-flex items-center gap-1.5 rounded-[8px] border border-amber-300 bg-amber-50 px-3 py-1.5 text-[12px] font-semibold text-amber-700 hover:bg-amber-100"
      >
        무료 분석 {trialLimit}회를 모두 사용했어요 · 요금제 보기 →
      </button>
    );
  }

  const limit = data.limit ?? 30;
  const remaining = Math.max(0, limit - (data.used ?? 0));
  // BOHUMFIT-159: raw gray → v1.1 ink 토큰(로직 불변).
  const tone = remaining <= 3 ? "text-amber-700 border-amber-300 bg-amber-50" : "text-ink-soft border-line bg-ink-50";
  return (
    <button
      type="button"
      onClick={() => navigate("/subscription")}
      className={`inline-flex items-center gap-1.5 rounded-[8px] border px-3 py-1.5 text-[12px] font-medium ${tone}`}
      title="구독 관리"
    >
      이번 달 <b className="font-bold">{data.used}</b> / {limit}회 사용
      <span className="text-ink-400">(남은 {remaining}회)</span>
    </button>
  );
}
