// BOHUMFIT-156b: 분석 히스토리 — 저장된 분석 결과의 목록·재열람·삭제.
//   백엔드 156a(/history)와 페어. 목록은 별칭(label)·모드·저장일만 노출(result 제외),
//   재열람은 단건 result를 Disclosure의 ResultView에 주입(historyView)해 동일 화면으로 렌더.
//   보관 90일(서버 lazy 삭제) — 화면에도 1줄 고지. 별칭은 실명 금지(저장 모달에서 안내).
// BOHUMFIT-171b: 2트랙 — [최근 분석(기본)] 자동 기록·10건 롤링·7일 / [저장됨] 기존 트랙.
//   최근 항목은 "저장" 버튼(별칭 모달)으로 saved 승격(PATCH /history/{id}/save, 한도 검사).
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
  track?: string; // BOHUMFIT-171b: "recent" | "saved"
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

function filenameFromDisposition(value: string | null): string | null {
  if (!value) return null;
  const encoded = value.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  if (encoded) {
    try {
      return decodeURIComponent(encoded);
    } catch {
      return encoded;
    }
  }
  return value.match(/filename="([^"]+)"/i)?.[1] || null;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function modeLabel(mode: string): string {
  return mode === "easy" ? "간편심사" : "건강체/표준체";
}

type Track = "recent" | "saved";

export default function History() {
  const { session } = useAuth();
  const { showToast } = useToast();

  // BOHUMFIT-171b: 2트랙 탭 — 최근 분석(기본) / 저장됨.
  const [track, setTrack] = useState<Track>("recent");
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

  // BOHUMFIT-171b: 최근 → 저장 승격 모달(별칭 입력 — 156 저장 모달과 동일 규칙)
  const [promoteTarget, setPromoteTarget] = useState<HistoryItem | null>(null);
  const [promoteLabel, setPromoteLabel] = useState("");
  const [promoteLoading, setPromoteLoading] = useState(false);
  const [promoteError, setPromoteError] = useState("");
  const [promoteLimited, setPromoteLimited] = useState(false);

  const token = session?.access_token;

  const fetchList = useCallback(
    async (offset: number, append: boolean) => {
      if (append) setMoreLoading(true);
      else setLoading(true);
      setError("");
      try {
        const res = await fetch(`${API_BASE}/history?limit=${PAGE_SIZE}&offset=${offset}&track=${track}`, {
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
    [token, track],
  );

  useEffect(() => {
    if (!token) return;
    const id = window.setTimeout(() => {
      void fetchList(0, false);
    }, 0);
    return () => window.clearTimeout(id);
  }, [token, fetchList]);

  // BOHUMFIT-157: 저장(saved) 항목을 고객 전달용 리포트 PDF 파일로 다운로드(공유 링크 금지 — 파일만).
  //   목록·재열람 화면이 동일 핸들러를 재사용. 파일명은 서버 규칙과 동일하게 클라이언트에서도 지정.
  const [pdfLoadingId, setPdfLoadingId] = useState<string | null>(null);
  async function downloadPdf(item: HistoryItem) {
    setPdfLoadingId(item.id);
    try {
      const res = await fetch(`${API_BASE}/history/${item.id}/report-pdf`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `PDF 생성에 실패했어요 (${res.status})`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const safeLabel = item.label.replace(/[^가-힣A-Za-z0-9]/g, "").slice(0, 20);
      const datePart = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      a.download = filenameFromDisposition(res.headers.get("Content-Disposition"))
        || (safeLabel
          ? `BohumFit_고지의무리포트_${safeLabel}_${datePart}.pdf`
          : `BohumFit_고지의무리포트_${datePart}.pdf`);
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      showToast(e instanceof Error ? e.message : "PDF 생성에 실패했어요. 잠시 후 다시 시도해 주세요.", "error");
    } finally {
      setPdfLoadingId(null);
    }
  }

  // BOHUMFIT-171b: recent → saved 승격 (별칭 필수, 한도 409 시 안내)
  async function confirmPromote() {
    if (!promoteTarget) return;
    const label = promoteLabel.trim();
    if (!label) {
      setPromoteError("별칭을 입력해 주세요.");
      return;
    }
    setPromoteLoading(true);
    setPromoteError("");
    setPromoteLimited(false);
    try {
      const res = await fetch(`${API_BASE}/history/${promoteTarget.id}/save`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ label }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        if (res.status === 409) {
          setPromoteLimited(true);
          throw new Error(d.detail || "히스토리 저장 한도(10건)에 도달했어요. 기존 항목을 삭제해 주세요.");
        }
        throw new Error(d.detail || `저장하지 못했어요 (${res.status})`);
      }
      // 최근 탭에서 항목이 저장됨 탭으로 이동
      setItems((prev) => prev.filter((i) => i.id !== promoteTarget.id));
      setTotal((t) => Math.max(0, t - 1));
      setPromoteTarget(null);
      setPromoteLabel("");
      showToast("저장됨 탭으로 이동했습니다", "success");
    } catch (e: unknown) {
      setPromoteError(e instanceof Error ? e.message : "저장하지 못했어요. 잠시 후 다시 시도해 주세요.");
    } finally {
      setPromoteLoading(false);
    }
  }

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
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-[12px] text-ink-soft">
              <span className="font-bold text-ink">{viewing.item.label}</span>
              {" · "}{modeLabel(viewing.item.mode)}{" · "}{formatDate(viewing.item.created_at)} 저장
            </p>
            {/* BOHUMFIT-157: 재열람에서도 동일 핸들러로 PDF 다운로드(saved) / recent는 저장 유도 안내 */}
            {viewing.item.track === "saved" ? (
              <button
                type="button"
                onClick={() => void downloadPdf(viewing.item)}
                disabled={pdfLoadingId === viewing.item.id}
                className="rounded-[8px] border border-line-strong bg-white px-3.5 py-2 text-[13px] font-bold text-ink hover:border-accent-600 hover:text-accent-700 disabled:opacity-60"
              >
                {pdfLoadingId === viewing.item.id ? "생성 중…" : "PDF 저장"}
              </button>
            ) : (
              <span className="text-[11px] text-ink-soft">저장 후 PDF로 내려받을 수 있어요.</span>
            )}
          </div>
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
            {track === "recent"
              ? "최근 10건이 자동 기록되며 7일 후 삭제됩니다. 남기고 싶은 결과는 저장해 주세요 — 저장 후 PDF로 내려받을 수 있어요."
              : `별칭으로 저장한 분석 결과를 다시 열람하거나 고객 전달용 PDF로 내려받을 수 있습니다. 저장일부터 ${retentionDays}일이 지나면 자동 삭제됩니다.`}
          </p>
        </div>
        {track === "saved" && quota && (
          <span className="rounded-full bg-ink-100 px-3 py-1 text-[12px] font-semibold text-ink-soft">
            {quota.max === null ? `${total}건 저장됨 · 무제한` : `${quota.used}/${quota.max}건 저장됨`}
          </span>
        )}
      </div>

      {/* BOHUMFIT-171b: 트랙 탭 — 최근 분석(기본) / 저장됨 */}
      <div role="tablist" aria-label="히스토리 트랙" className="mt-4 inline-flex rounded-[8px] border border-line bg-white p-1">
        {(["recent", "saved"] as const).map((t) => {
          const active = track === t;
          return (
            <button
              key={t}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setTrack(t)}
              className={`rounded-[6px] px-4 py-1.5 text-sm transition-colors ${
                active ? "bg-accent-50 font-semibold text-accent-700" : "font-medium text-ink-soft hover:text-ink-900"
              }`}
            >
              {t === "recent" ? "최근 분석" : "저장됨"}
            </button>
          );
        })}
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
          {track === "recent" ? (
            <>
              <p className="text-sm font-bold text-ink">아직 자동 기록된 분석이 없어요.</p>
              <p className="mt-2 text-xs leading-6 text-ink-soft break-keep">
                분석을 실행하면 최근 10건이 자동으로 기록됩니다.
              </p>
            </>
          ) : (
            <>
              <p className="text-sm font-bold text-ink">저장된 분석 히스토리가 없어요.</p>
              <p className="mt-2 text-xs leading-6 text-ink-soft break-keep">
                분석 결과 화면 또는 최근 분석 탭에서 <strong className="text-ink">저장</strong>하면 별칭으로 보관해 두고 다시 볼 수 있습니다.
              </p>
            </>
          )}
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
                {/* BOHUMFIT-157: 저장 항목 → 고객 전달용 PDF 다운로드(세컨더리) */}
                {track === "saved" && (
                  <button
                    type="button"
                    onClick={() => void downloadPdf(item)}
                    disabled={pdfLoadingId === item.id}
                    className="rounded-[8px] border border-line-strong bg-white px-3.5 py-2 text-[13px] font-bold text-ink hover:border-accent-600 hover:text-accent-700 disabled:opacity-60"
                  >
                    {pdfLoadingId === item.id ? "생성 중…" : "PDF 저장"}
                  </button>
                )}
                {/* BOHUMFIT-171b: 최근 항목 → 저장 승격(별칭 모달) */}
                {track === "recent" && (
                  <button
                    type="button"
                    onClick={() => {
                      setPromoteTarget(item);
                      setPromoteLabel("");
                      setPromoteError("");
                      setPromoteLimited(false);
                    }}
                    className="rounded-[8px] border border-line-strong bg-white px-3.5 py-2 text-[13px] font-bold text-ink hover:border-accent-600 hover:text-accent-700"
                  >
                    저장
                  </button>
                )}
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
        {track === "recent"
          ? `자동 기록 항목: 분석 결과 요약(고객 실명은 저장되지 않음). 최근 10건 유지·${retentionDays}일 경과 시 자동 파기되며, 언제든지 직접 삭제할 수 있습니다.`
          : `저장 항목: 별칭·분석 결과(고객 실명은 저장되지 않음). 보관 ${retentionDays}일 경과 시 자동 파기되며, 언제든지 직접 삭제할 수 있습니다.`}
      </p>

      {/* BOHUMFIT-171b: 저장 승격 모달 — 별칭(실명 금지) + 90일 고지(156 모달과 동일 규칙) */}
      {promoteTarget && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/40 px-5"
          role="dialog"
          aria-modal="true"
          aria-label="히스토리에 저장"
          onClick={() => !promoteLoading && setPromoteTarget(null)}
        >
          <div
            className="w-full max-w-sm rounded-[8px] bg-white p-5 shadow-[0_8px_32px_rgba(0,0,0,0.18)]"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-sm font-extrabold text-ink-900">저장됨으로 이동</h3>
            <p className="mt-1.5 text-[12px] leading-5 text-ink-soft">
              고객 실명 대신 <strong className="text-ink">별칭</strong>을 입력하세요. (예: 40대 남 · 고혈압)
            </p>
            <input
              type="text"
              value={promoteLabel}
              onChange={(e) => setPromoteLabel(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !promoteLoading) void confirmPromote(); }}
              placeholder="예: 40대 남 · 고혈압"
              maxLength={40}
              autoFocus
              aria-label="히스토리 별칭"
              className="mt-3 w-full rounded-[6px] border border-line-strong px-3 py-2 text-sm focus:border-accent-600 focus:outline-none"
            />
            <p className="mt-2 text-[11px] text-ink-soft">저장된 결과는 90일 뒤 자동 삭제됩니다.</p>
            {promoteError && (
              <p className="mt-2 text-[12px] font-semibold text-red-500">
                {promoteError}
                {promoteLimited && (
                  <>
                    {" "}
                    <Link to="/subscription" className="font-bold text-accent-700 underline">Pro 안내 보기</Link>
                  </>
                )}
              </p>
            )}
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setPromoteTarget(null)}
                disabled={promoteLoading}
                className="rounded-[8px] border border-line px-4 py-2 text-sm font-bold text-ink-soft hover:text-ink disabled:opacity-60"
              >
                취소
              </button>
              <button
                type="button"
                onClick={() => void confirmPromote()}
                disabled={promoteLoading}
                className="rounded-[8px] bg-accent-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-60"
              >
                {promoteLoading ? "저장 중…" : "저장"}
              </button>
            </div>
          </div>
        </div>
      )}

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
