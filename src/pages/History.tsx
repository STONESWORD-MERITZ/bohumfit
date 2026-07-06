// BOHUMFIT-156b: 분석 히스토리 — 저장된 분석 결과의 목록·재열람·삭제.
//   백엔드 156a(/history)와 페어. 목록은 별칭(label)·모드·저장일만 노출(result 제외),
//   재열람은 단건 result를 Disclosure의 ResultView에 주입(historyView)해 동일 화면으로 렌더.
//   보관 90일(서버 lazy 삭제) — 화면에도 1줄 고지. 별칭은 실명 금지(저장 모달에서 안내).
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../lib/auth-context";
import { useToast } from "../components/ToastContext";
import { ResultView, type AnalyzeResult } from "./Disclosure";

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");
const PAGE_SIZE = 20;

type HistoryItem = {
  id: string;
  label: string;
  mode: string; // "standard" | "easy"
  created_at: string;
};

type HistoryList = {
  items: HistoryItem[];
  total: number;
  limit: number;
  offset: number;
  retention_days?: number;
  quota?: { used: number; max: number | null };
};

// 저장 시 reference_date를 동봉(Disclosure 저장 로직) — 재열람 복원용.
type StoredResult = AnalyzeResult & { reference_date?: string };

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function modeLabel(mode: string): string {
  return mode === "easy" ? "간편심사" : "건강체/표준체";
}

export default function History() {
  const { session } = useAuth();
  const { showToast } = useToast();

  const [items, setItems] = useState<HistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [quota, setQuota] = useState<{ used: number; max: number | null } | null>(null);
  const [retentionDays, setRetentionDays] = useState(90);
  const [loading, setLoading] = useState(true);
  const [moreLoading, setMoreLoading] = useState(false);
  const [error, setError] = useState("");

  // 재열람
  const [viewing, setViewing] = useState<{ item: HistoryItem; result: StoredResult } | null>(null);
  const [openLoadingId, setOpenLoadingId] = useState<string | null>(null);

  // 삭제 확인 모달
  const [deleteTarget, setDeleteTarget] = useState<HistoryItem | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const token = session?.access_token;

  const fetchList = useCallback(
    async (offset: number, append: boolean) => {
      if (append) setMoreLoading(true);
      else setLoading(true);
      setError("");
      try {
        const res = await fetch(`${API_BASE}/history?limit=${PAGE_SIZE}&offset=${offset}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) {
          const d = await res.json().catch(() => ({}));
          throw new Error(d.detail || `히스토리를 불러오지 못했어요 (${res.status})`);
        }
        const data = (await res.json()) as HistoryList;
        setItems((prev) => (append ? [...prev, ...data.items] : data.items));
        setTotal(data.total);
        if (data.quota) setQuota(data.quota);
        if (data.retention_days) setRetentionDays(data.retention_days);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "히스토리를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.");
      } finally {
        setLoading(false);
        setMoreLoading(false);
      }
    },
    [token],
  );

  useEffect(() => {
    if (token) void fetchList(0, false);
  }, [token, fetchList]);

  async function openItem(item: HistoryItem) {
    setOpenLoadingId(item.id);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/history/${item.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `히스토리를 열지 못했어요 (${res.status})`);
      }
      const row = (await res.json()) as { result: StoredResult };
      setViewing({ item, result: row.result });
      window.scrollTo({ top: 0 });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "히스토리를 열지 못했어요. 잠시 후 다시 시도해 주세요.";
      setError(msg);
      showToast(msg, "error");
    } finally {
      setOpenLoadingId(null);
    }
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setDeleteLoading(true);
    try {
      const res = await fetch(`${API_BASE}/history/${deleteTarget.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `삭제하지 못했어요 (${res.status})`);
      }
      setItems((prev) => prev.filter((i) => i.id !== deleteTarget.id));
      setTotal((t) => Math.max(0, t - 1));
      setQuota((q) => (q ? { ...q, used: Math.max(0, q.used - 1) } : q));
      showToast("히스토리를 삭제했습니다", "success");
      setDeleteTarget(null);
    } catch (e: unknown) {
      showToast(e instanceof Error ? e.message : "삭제하지 못했어요. 잠시 후 다시 시도해 주세요.", "error");
    } finally {
      setDeleteLoading(false);
    }
  }

  // ── 재열람 화면 ──────────────────────────────────────────────────────────
  if (viewing) {
    return (
      <div>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => setViewing(null)}
            className="rounded-[8px] border border-line bg-white px-3 py-2 text-xs font-bold text-ink-soft hover:border-accent-600/40 hover:text-accent-600"
          >
            ← 히스토리 목록으로
          </button>
          <p className="text-[12px] text-ink-soft">
            <span className="font-bold text-ink">{viewing.item.label}</span>
            {" · "}{modeLabel(viewing.item.mode)}{" · "}{formatDate(viewing.item.created_at)} 저장
          </p>
        </div>
        <div className="mb-4 rounded-[8px] border border-line bg-ink-50 px-4 py-2.5 text-[12px] text-ink-soft">
          저장 시점의 분석 결과입니다. 이후 진료 이력은 반영되어 있지 않으니, 청약 직전에는 새로 분석해 주세요.
        </div>
        <ResultView
          result={viewing.result}
          mode="agent"
          referenceDate={viewing.result.reference_date || ""}
          initialProductTab={viewing.item.mode === "easy" ? "easy" : "standard"}
          historyView
        />
      </div>
    );
  }

  // ── 목록 화면 ────────────────────────────────────────────────────────────
  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-extrabold text-ink-900">분석 히스토리</h1>
          <p className="mt-1.5 text-[13px] leading-6 text-ink-soft">
            별칭으로 저장한 분석 결과를 다시 열람할 수 있습니다. 저장일부터 {retentionDays}일이 지나면 자동 삭제됩니다.
          </p>
        </div>
        {quota && (
          <span className="rounded-full bg-ink-100 px-3 py-1 text-[12px] font-semibold text-ink-soft">
            {quota.max === null ? `${total}건 저장됨 · 무제한` : `${quota.used}/${quota.max}건 저장됨`}
          </span>
        )}
      </div>

      {error && (
        <div className="mt-5 rounded-[8px] bg-red-50 p-4 text-sm font-semibold text-red-600">{error}</div>
      )}

      {loading ? (
        <div className="mt-5 rounded-[8px] bg-white p-8 text-center text-sm text-ink-soft shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
          불러오는 중…
        </div>
      ) : items.length === 0 && !error ? (
        <section className="mt-5 rounded-[8px] bg-white p-8 text-center shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
          <p className="text-sm font-bold text-ink">저장된 분석 히스토리가 없어요.</p>
          <p className="mt-2 text-xs leading-6 text-ink-soft break-keep">
            분석 결과 화면에서 <strong className="text-ink">히스토리에 저장</strong> 버튼을 누르면 별칭으로 저장해 두고 다시 볼 수 있습니다.
          </p>
          <Link
            to="/disclosure?mode=agent"
            className="mt-4 inline-block rounded-[8px] bg-accent-600 px-4 py-2 text-sm font-bold text-white"
          >
            분석하러 가기
          </Link>
        </section>
      ) : (
        <ul className="mt-5 space-y-2.5">
          {items.map((item) => (
            <li
              key={item.id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-[8px] border border-line bg-white px-4 py-3.5"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-ink-900">{item.label}</p>
                <p className="mt-0.5 text-[12px] text-ink-soft">
                  <span className={`mr-1.5 rounded-[4px] px-1.5 py-0.5 text-[11px] font-semibold ${
                    item.mode === "easy" ? "bg-accent-50 text-accent-700" : "bg-ink-100 text-ink-soft"
                  }`}>
                    {modeLabel(item.mode)}
                  </span>
                  {formatDate(item.created_at)} 저장
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                <button
                  type="button"
                  onClick={() => void openItem(item)}
                  disabled={openLoadingId === item.id}
                  className="rounded-[8px] bg-accent-600 px-3.5 py-2 text-[13px] font-bold text-white disabled:opacity-60"
                >
                  {openLoadingId === item.id ? "여는 중…" : "열람"}
                </button>
                <button
                  type="button"
                  onClick={() => setDeleteTarget(item)}
                  className="rounded-[8px] border border-line px-3.5 py-2 text-[13px] font-bold text-ink-soft hover:border-red-300 hover:text-red-500"
                >
                  삭제
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {!loading && items.length < total && (
        <div className="mt-4 text-center">
          <button
            type="button"
            onClick={() => void fetchList(items.length, true)}
            disabled={moreLoading}
            className="rounded-[8px] border border-line bg-white px-4 py-2 text-sm font-bold text-ink-soft hover:text-ink disabled:opacity-60"
          >
            {moreLoading ? "불러오는 중…" : `더 보기 (${items.length}/${total})`}
          </button>
        </div>
      )}

      <p className="mt-6 text-[11px] leading-5 text-ink-soft">
        저장 항목: 별칭·분석 결과(고객 실명은 저장되지 않음). 보관 {retentionDays}일 경과 시 자동 파기되며, 언제든지 직접 삭제할 수 있습니다.
      </p>

      {/* 삭제 확인 모달 */}
      {deleteTarget && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/40 px-5"
          role="dialog"
          aria-modal="true"
          aria-label="히스토리 삭제 확인"
          onClick={() => !deleteLoading && setDeleteTarget(null)}
        >
          <div
            className="w-full max-w-sm rounded-[8px] bg-white p-5 shadow-[0_8px_32px_rgba(0,0,0,0.18)]"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-sm font-extrabold text-ink-900">히스토리를 삭제할까요?</h3>
            <p className="mt-1.5 text-[13px] leading-6 text-ink-soft">
              <strong className="text-ink">{deleteTarget.label}</strong> 항목이 삭제됩니다. 삭제하면 되돌릴 수 없어요.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setDeleteTarget(null)}
                disabled={deleteLoading}
                className="rounded-[8px] border border-line px-4 py-2 text-sm font-bold text-ink-soft hover:text-ink disabled:opacity-60"
              >
                취소
              </button>
              <button
                type="button"
                onClick={() => void confirmDelete()}
                disabled={deleteLoading}
                className="rounded-[8px] bg-red-500 px-4 py-2 text-sm font-bold text-white hover:bg-red-600 disabled:opacity-60"
              >
                {deleteLoading ? "삭제 중…" : "삭제"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
