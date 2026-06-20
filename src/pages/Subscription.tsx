// BOHUMFIT-071: 구독 관리 페이지. 상태 조회 + 토스페이먼츠 카드 등록(빌링) 플로우.
import { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../lib/auth-context";

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");
const TOSS_CLIENT_KEY = import.meta.env.VITE_TOSS_CLIENT_KEY || "";

type BillingStatus = {
  status: string;
  plan: string | null;
  period_end: string | null;
  used: number;
  limit: number;
  is_internal: boolean;
  enabled?: boolean;
};

function fmtDate(iso: string | null): string {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleDateString("ko-KR", { year: "numeric", month: "long", day: "numeric" });
  } catch {
    return iso.slice(0, 10);
  }
}

export default function Subscription() {
  const { session, user } = useAuth();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<{ kind: "ok" | "err"; msg: string } | null>(null);

  const loadStatus = useCallback(async () => {
    const token = session?.access_token;
    if (!token) return;
    setLoading(true);
    try {
      const r = await fetch(`${API_BASE}/billing/status`, { headers: { Authorization: `Bearer ${token}` } });
      setStatus(r.ok ? await r.json() : null);
    } catch {
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, [session]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadStatus();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadStatus]);

  // 토스 빌링 인증 리다이렉트 처리: success → /billing/issue-key, fail → 토스트
  useEffect(() => {
    const result = params.get("result");
    if (!result) return;
    const authKey = params.get("authKey");
    const customerKey = params.get("customerKey");
    const token = session?.access_token;
    const timer = window.setTimeout(() => {
    const clear = () => setParams({}, { replace: true });
    if (result === "success" && authKey && token) {
      setBusy(true);
      fetch(`${API_BASE}/billing/issue-key`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ authKey, customerKey: customerKey || user?.id }),
      })
        .then(async (r) => {
          if (!r.ok) {
            const d = await r.json().catch(() => ({}));
            throw new Error(d.detail || "결제 처리에 실패했어요.");
          }
          setToast({ kind: "ok", msg: "구독이 시작되었습니다. 감사합니다!" });
          await loadStatus();
        })
        .catch((e: unknown) => setToast({ kind: "err", msg: e instanceof Error ? e.message : "결제 실패" }))
        .finally(() => {
          setBusy(false);
          clear();
        });
    } else if (result === "fail") {
      setToast({ kind: "err", msg: "결제가 취소되었거나 실패했어요." });
      clear();
    }
    }, 0);

    return () => window.clearTimeout(timer);
  }, [params, session, user, loadStatus, setParams]);

  const startSubscribe = async () => {
    if (!TOSS_CLIENT_KEY) {
      setToast({ kind: "err", msg: "결제 설정이 준비되지 않았습니다(VITE_TOSS_CLIENT_KEY)." });
      return;
    }
    if (!user?.id) {
      setToast({ kind: "err", msg: "로그인이 필요합니다." });
      return;
    }
    setBusy(true);
    try {
      const { loadTossPayments } = await import("@tosspayments/tosspayments-sdk");
      const tossPayments = await loadTossPayments(TOSS_CLIENT_KEY);
      const payment = tossPayments.payment({ customerKey: user.id });
      await payment.requestBillingAuth({
        method: "CARD",
        successUrl: `${window.location.origin}/subscription?result=success`,
        failUrl: `${window.location.origin}/subscription?result=fail`,
      });
    } catch (e: unknown) {
      setToast({ kind: "err", msg: e instanceof Error ? e.message : "결제 창을 여는 데 실패했어요." });
      setBusy(false);
    }
  };

  const isActive = status?.status === "active";

  return (
    <section className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-extrabold text-gray-950">구독 관리</h1>
      <p className="mt-2 text-sm text-gray-600 break-keep">
        보험핏 고지 분석은 구독제로 운영됩니다. 월 9,900원으로 매월 30회까지 분석할 수 있어요.
      </p>

      {toast && (
        <div
          className={`mt-4 rounded-[8px] px-4 py-2.5 text-sm ${
            toast.kind === "ok" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-600"
          }`}
        >
          {toast.msg}
        </div>
      )}

      {loading ? (
        <div className="mt-6 text-sm text-gray-400">불러오는 중…</div>
      ) : status?.is_internal ? (
        <div className="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50 p-6">
          <p className="text-sm font-bold text-emerald-800">내부 사용자 — 무제한 이용</p>
          <p className="mt-1 text-sm text-emerald-700">별도 구독 없이 분석을 제한 없이 이용할 수 있습니다.</p>
        </div>
      ) : isActive ? (
        <div className="mt-6 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent-600">구독 중</p>
          <h2 className="mt-2 text-xl font-extrabold text-gray-950">베이직 플랜 · 월 9,900원</h2>
          <dl className="mt-4 grid gap-2 text-sm">
            <div className="flex justify-between"><dt className="text-gray-500">다음 결제일</dt><dd className="font-medium text-gray-900">{fmtDate(status?.period_end ?? null)}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">이번 달 사용량</dt><dd className="font-medium text-gray-900">{status?.used ?? 0} / {status?.limit ?? 30}회</dd></div>
          </dl>
          <p className="mt-4 text-[12px] text-gray-400">해지를 원하시면 고객센터로 문의해 주세요.</p>
          <button onClick={() => navigate("/disclosure?mode=customer")} className="mt-4 rounded-[8px] bg-accent-600 px-4 py-2 text-sm font-bold text-white">분석하러 가기</button>
        </div>
      ) : (
        <div className="mt-6 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent-600">베이직 플랜</p>
          <h2 className="mt-2 text-xl font-extrabold text-gray-950">월 9,900원 · 매월 30회 분석</h2>
          <ul className="mt-4 space-y-1.5 text-sm text-gray-600">
            <li>· 건강보험심평원 PDF 기반 고지 리스크 점검</li>
            <li>· 건강체·간편심사 고지 검토 + 고객용 PDF 저장</li>
            <li>· 매월 30회까지 분석(초과 시 다음 결제일에 초기화)</li>
          </ul>
          <button
            onClick={startSubscribe}
            disabled={busy}
            className="mt-5 w-full rounded-[8px] bg-accent-600 px-5 py-3 text-sm font-bold text-white disabled:opacity-60"
          >
            {busy ? "결제 진행 중…" : "구독 시작 (카드 등록)"}
          </button>
          <p className="mt-3 text-[11px] text-gray-400">결제는 토스페이먼츠로 안전하게 처리되며, 카드 등록 후 매월 자동 결제됩니다.</p>
        </div>
      )}
    </section>
  );
}
