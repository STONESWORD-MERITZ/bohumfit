// BOHUMFIT-233: 직원 관리(admin 전용) — bohumfit_tier internal 지정/해제.
//   노출 게이트는 Dashboard의 isAdmin 분기(billing_status 서버 권위)이고, 실제 권한은
//   백엔드 /admin/tier/* 가 요청자 tier='admin'을 재검증한다(403). admin 지정은 API 불가(SQL 절차).
import { useCallback, useEffect, useState } from "react";

type Member = { email: string; tier: string };
type Notice = { kind: "ok" | "err"; text: string };

export default function AdminTierSection({ apiBase, token }: { apiBase: string; token: string }) {
  const [members, setMembers] = useState<Member[] | null | false>(null);
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);

  const headers = useCallback(
    () => ({ Authorization: `Bearer ${token}`, "Content-Type": "application/json" }),
    [token],
  );

  const load = useCallback(() => {
    fetch(`${apiBase}/admin/tier/list`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d) => setMembers(d.members ?? []))
      .catch(() => setMembers(false));
  }, [apiBase, token]);

  useEffect(() => {
    load();
  }, [load]);

  const apply = async (tier: "internal" | "customer") => {
    const target = email.trim();
    if (!target) {
      setNotice({ kind: "err", text: "이메일을 입력해 주세요." });
      return;
    }
    setBusy(true);
    setNotice(null);
    try {
      const res = await fetch(`${apiBase}/admin/tier/set`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ email: target, tier }),
      });
      if (res.status === 404) {
        // 기존 미가입 직원 케이스: 가입 유도 후 재시도 안내.
        setNotice({ kind: "err", text: "해당 이메일 가입 이력 없음 — 가입 후 다시 시도해 주세요." });
        return;
      }
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setNotice({ kind: "err", text: body?.detail || "처리에 실패했어요. 잠시 후 다시 시도해 주세요." });
        return;
      }
      setNotice({
        kind: "ok",
        text: tier === "internal" ? `${target} — 내부 직원(월 100회)으로 지정했어요.` : `${target} — 직원 지정을 해제했어요.`,
      });
      setEmail("");
      load();
    } catch {
      setNotice({ kind: "err", text: "네트워크 오류예요. 잠시 후 다시 시도해 주세요." });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="rounded-[8px] border border-line bg-white p-5 md:col-span-2 lg:col-span-3">
      <h2 className="text-sm font-extrabold text-ink-900">직원 관리</h2>
      <p className="mt-1 text-[12px] text-ink-soft">
        관리자 전용 · 이메일로 내부 직원(월 100회 분석)을 지정하거나 해제합니다. admin 등급은 여기서 변경할 수 없어요.
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <label htmlFor="admin-tier-email" className="sr-only">직원 이메일</label>
        <input
          id="admin-tier-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !busy) void apply("internal");
          }}
          placeholder="직원 이메일"
          className="w-full max-w-xs rounded-[8px] border border-line px-3 py-2 text-sm text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-600"
        />
        <button
          type="button"
          disabled={busy}
          onClick={() => void apply("internal")}
          className="rounded-[8px] bg-accent-600 px-4 py-2 text-sm font-bold text-white hover:bg-accent-700 disabled:opacity-50"
        >
          internal 지정
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void apply("customer")}
          className="rounded-[8px] border border-accent-600 px-4 py-2 text-sm font-bold text-accent-700 hover:bg-accent-50 disabled:opacity-50"
        >
          지정 해제
        </button>
      </div>

      {notice && (
        <p
          role="status"
          className={`mt-2 text-[13px] font-semibold ${notice.kind === "ok" ? "text-accent-700" : "text-red-600"}`}
        >
          {notice.text}
        </p>
      )}

      <div className="mt-4">
        <h3 className="text-[12px] font-bold text-ink-soft">현재 등록된 계정</h3>
        {members === null ? (
          <p className="mt-1 text-[13px] text-ink-soft">불러오는 중…</p>
        ) : members === false ? (
          <p className="mt-1 text-[13px] text-ink-soft">목록을 불러오지 못했어요. 새로고침해 주세요.</p>
        ) : members.length === 0 ? (
          <p className="mt-1 text-[13px] text-ink-soft">등록된 admin/internal 계정이 없어요.</p>
        ) : (
          <ul className="mt-1 divide-y divide-line">
            {members.map((m) => (
              <li key={`${m.email}-${m.tier}`} className="flex items-center gap-2 py-1.5">
                <span className="min-w-0 flex-1 truncate text-[13px] font-semibold text-ink">{m.email}</span>
                <span
                  className={`shrink-0 rounded-[4px] px-1.5 py-0.5 text-[11px] font-semibold ${
                    m.tier === "admin" ? "bg-accent-600 text-white" : "bg-accent-50 text-accent-700"
                  }`}
                >
                  {m.tier}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
