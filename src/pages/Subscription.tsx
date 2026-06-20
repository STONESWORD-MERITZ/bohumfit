// BOHUMFIT-071: 구독 관리 페이지. 상태 조회 + 토스페이먼츠 카드 등록(빌링) 플로우.
import { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../lib/auth-context";

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");
const TOSS_CLIENT_KEY = import.meta.env.VITE_TOSS_CLIENT_KEY || "";
// BOHUMFIT-071-hotfix2: 결제위젯(v2/standard·사업자 신청 필요) → 빌링키(v1/payment·테스트 즉시) 방식.
const TOSS_SCRIPT_SRC = "https://js.tosspayments.com/v1/payment";

type BillingStatus = {
  status: string;
  plan: string | null;
  period_end: string | null;
  used: number;
  limit: number;
  trial_used?: number;   // BOHUMFIT-072: 이번 달 무료 체험 사용량
  trial_limit?: number;
  is_internal: boolean;
  enabled?: boolean;
};

type PlanKey = "basic" | "pro";
const PLAN_LABEL: Record<PlanKey, string> = { basic: "베이직", pro: "프로" };

declare global {
  interface Window {
    // v1 빌링키 인스턴스. 메서드 시그니처는 (window as any)로 호출하므로 느슨하게 둔다.
    TossPayments?: (clientKey: string) => unknown;
  }
}

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
  const [tossReady, setTossReady] = useState(false);
  const [toast, setToast] = useState<{ kind: "ok" | "err"; msg: string } | null>(null);

  useEffect(() => {
    if (window.TossPayments) {
      const timer = window.setTimeout(() => setTossReady(true), 0);
      return () => window.clearTimeout(timer);
    }

    const script = document.createElement("script");
    script.src = TOSS_SCRIPT_SRC;
    script.async = true;
    script.onload = () => setTossReady(true);
    script.onerror = () => {
      setTossReady(false);
      setToast({ kind: "err", msg: "결제 모듈을 불러오지 못했어요. 잠시 후 다시 시도해 주세요." });
    };
    document.head.appendChild(script);
    return () => {
      document.head.removeChild(script);
    };
  }, []);

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
    const plan = params.get("plan") || "basic";   // BOHUMFIT-072/073: 선택 플랜 전달
    const token = session?.access_token;
    const timer = window.setTimeout(() => {
      const clear = () => setParams({}, { replace: true });
      if (result === "success" && authKey && token) {
        setBusy(true);
        fetch(`${API_BASE}/billing/issue-key`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify({ authKey, customerKey: customerKey || user?.id, plan }),
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

  const handleSubscribe = async (plan: PlanKey) => {
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
      if (!tossReady || !window.TossPayments) {
        throw new Error("결제 모듈을 아직 불러오는 중입니다. 잠시 후 다시 시도해 주세요.");
      }
      // BOHUMFIT-073: v1 빌링키 — 인스턴스에서 직접 카드 등록(메서드 문자열 '카드'). 라이브 키 교체 시 실결제.
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const toss = (window as any).TossPayments(TOSS_CLIENT_KEY);
      await toss.requestBillingAuth("카드", {
        customerKey: user.id,
        successUrl: `${window.location.origin}/subscription?result=success&plan=${plan}`,
        failUrl: `${window.location.origin}/subscription?result=fail`,
      });
    } catch (e: unknown) {
      setToast({ kind: "err", msg: e instanceof Error ? e.message : "결제 창을 여는 데 실패했어요." });
      setBusy(false);
    }
  };

  const isActive = status?.status === "active";
  const trialUsed = status?.trial_used ?? 0;
  const trialLimit = status?.trial_limit ?? 5;
  const trialLeft = Math.max(0, trialLimit - trialUsed);
  const planLabel = (status?.plan && PLAN_LABEL[status.plan as PlanKey]) || "베이직";

  return (
    <section className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-extrabold text-gray-950">구독 관리</h1>
      <p className="mt-2 text-sm text-gray-600 break-keep">
        보험핏 고지 분석은 구독제로 운영됩니다. 가입 후 매월 무료 체험 {trialLimit}회, 구독 시 플랜별 분석을 제공합니다.
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
          <h2 className="mt-2 text-xl font-extrabold text-gray-950">{planLabel} 플랜</h2>
          <dl className="mt-4 grid gap-2 text-sm">
            <div className="flex justify-between"><dt className="text-gray-500">다음 결제일</dt><dd className="font-medium text-gray-900">{fmtDate(status?.period_end ?? null)}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">이번 달 사용량</dt><dd className="font-medium text-gray-900">{status?.used ?? 0} / {status?.limit ?? 30}회</dd></div>
          </dl>
          <p className="mt-4 text-[12px] text-gray-400">해지를 원하시면 고객센터로 문의해 주세요.</p>
          <button onClick={() => navigate("/disclosure?mode=customer")} className="mt-4 rounded-[8px] bg-accent-600 px-4 py-2 text-sm font-bold text-white">분석하러 가기</button>
        </div>
      ) : (
        <>
          {/* BOHUMFIT-072: 무료 체험 상태(미구독) */}
          <div className={`mt-6 rounded-[8px] px-4 py-3 text-sm ${trialLeft > 0 ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
            {trialLeft > 0
              ? <>무료 체험 <b>{trialLeft}회</b> 남음 (이번 달 {trialUsed}/{trialLimit}회 사용). 더 분석하려면 구독해 주세요.</>
              : <>이번 달 무료 체험 횟수를 모두 사용했습니다. 구독하고 계속 이용하세요.</>}
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {/* 베이직 */}
            <div className="rounded-2xl border border-accent-200 bg-white p-6 shadow-sm">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent-600">베이직 플랜</p>
              <div className="mt-2">
                <span className="inline-block rounded-full bg-accent-50 px-2 py-0.5 text-[11px] font-bold text-accent-700">오픈 이벤트 · 첫 3개월</span>
                <h2 className="mt-1.5 text-2xl font-extrabold text-gray-950">월 9,900원</h2>
                <p className="text-[12px] text-gray-400">이벤트 후 월 14,900원 · 매월 30회</p>
              </div>
              <ul className="mt-4 space-y-1.5 text-sm text-gray-600">
                <li>· 건강체·간편심사 고지 검토</li>
                <li>· 고객용 PDF 저장</li>
                <li>· 매월 30회 분석</li>
              </ul>
              <button
                onClick={() => handleSubscribe("basic")}
                disabled={busy}
                className="mt-5 w-full rounded-[8px] bg-accent-600 px-5 py-3 text-sm font-bold text-white disabled:opacity-60"
              >
                {busy ? "결제 진행 중…" : "베이직 구독 시작"}
              </button>
            </div>

            {/* 프로 */}
            <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-gray-500">프로 플랜</p>
              <div className="mt-2">
                <h2 className="mt-1.5 text-2xl font-extrabold text-gray-950">월 24,900원</h2>
                <p className="text-[12px] text-gray-400">매월 100회</p>
              </div>
              <ul className="mt-4 space-y-1.5 text-sm text-gray-600">
                <li>· 베이직 모든 기능</li>
                <li>· 매월 100회 분석</li>
                <li>· 보장분석 기능 포함</li>
              </ul>
              <button
                onClick={() => handleSubscribe("pro")}
                disabled={busy}
                className="mt-5 w-full rounded-[8px] bg-gray-900 px-5 py-3 text-sm font-bold text-white disabled:opacity-60"
              >
                {busy ? "결제 진행 중…" : "프로 구독 시작"}
              </button>
            </div>
          </div>
          <p className="mt-3 text-[11px] text-gray-400">결제는 토스페이먼츠로 안전하게 처리되며, 카드 등록 후 매월 자동 결제됩니다.</p>
        </>
      )}
    </section>
  );
}
