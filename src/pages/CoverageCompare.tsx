// BOHUMFIT-114: 보장 비교분석 — Step1 현재보험 → Step2 가입제안서 → Step3 비교 리포트.
//   /coverage/parse(백엔드) 결과로 비교표 생성. PII(성명·주민번호)는 서버가 미저장·미반환.
import { useMemo, useState, type ChangeEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth-context";

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

type Coverage = { type: string; name: string; amount: number; coverage_names: string[] };
type Contract = {
  product_name: string; contractor: string; join_date: string; coverage_end: string;
  monthly_premium: number; payment_period: string; coverages: Coverage[];
};
type ParseResult = {
  insurer: string; doc_type: string; contracts: Contract[];
  summary: { total_monthly_premium: number; main_coverages: Record<string, number> };
  parse_warnings: string[];
};

const won = (n: number) => n.toLocaleString("ko-KR");

const STEPS: Array<[1 | 2 | 3, string]> = [
  [1, "현재 보험"],
  [2, "가입 제안서"],
  [3, "비교 리포트"],
];

function Stepper({ step }: { step: 1 | 2 | 3 }) {
  return (
    <div className="mb-6 flex items-center gap-2 text-[13px] font-semibold">
      {STEPS.map(([n, label]) => (
        <span key={n} className={`rounded-full px-3 py-1 ${step === n ? "bg-accent-600 text-white" : "bg-ink-100 text-ink-500"}`}>
          {n}. {label}
        </span>
      ))}
    </div>
  );
}

function Warnings({ ws }: { ws: string[] }) {
  return ws.length ? (
    <p className="mt-2 rounded-[8px] bg-amber-50 px-3 py-2 text-[12px] text-amber-700">
      ⚠️ 일부 항목 수동 확인 필요: {ws.join(" / ")}
    </p>
  ) : null;
}

export default function CoverageCompare() {
  const { session } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [current, setCurrent] = useState<ParseResult | null>(null);
  const [proposals, setProposals] = useState<ParseResult[]>([]);
  const [dropContracts, setDropContracts] = useState<Set<number>>(new Set());   // 해지 계약 idx
  const [dropCoverages, setDropCoverages] = useState<Set<string>>(new Set());   // 삭제 담보 키 ci:covi
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function parsePdf(fileObj: File, doc_type: "current" | "proposal"): Promise<ParseResult> {
    const token = session?.access_token;
    if (!token) {
      navigate("/login");
      throw new Error("로그인이 필요합니다.");
    }
    const fd = new FormData();
    fd.append("file", fileObj);
    fd.append("doc_type", doc_type);
    const r = await fetch(`${API_BASE}/coverage/parse`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
    });
    if (!r.ok) {
      const d = await r.json().catch(() => ({}));
      throw new Error(d.detail || "PDF 분석에 실패했어요.");
    }
    return r.json();
  }

  const onUploadCurrent = async (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setBusy(true); setError("");
    try {
      setCurrent(await parsePdf(f, "current"));
      setDropContracts(new Set()); setDropCoverages(new Set());
    } catch (err) { setError(err instanceof Error ? err.message : "오류"); }
    finally { setBusy(false); e.target.value = ""; }
  };

  const onUploadProposals = async (e: ChangeEvent<HTMLInputElement>) => {
    const fs = Array.from(e.target.files || []);
    if (!fs.length) return;
    setBusy(true); setError("");
    try {
      const out: ParseResult[] = [];
      for (const f of fs) out.push(await parsePdf(f, "proposal"));
      setProposals((prev) => [...prev, ...out]);
    } catch (err) { setError(err instanceof Error ? err.message : "오류"); }
    finally { setBusy(false); e.target.value = ""; }
  };

  function toggle<T>(set: Set<T>, key: T, setter: (s: Set<T>) => void) {
    const n = new Set(set);
    if (n.has(key)) n.delete(key); else n.add(key);
    setter(n);
  }

  // ── 비교 데이터(컨설팅 전/후) ───────────────────────────────────────────────
  const report = useMemo(() => {
    const before = new Map<string, number>();
    const after = new Map<string, number>();
    let beforePrem = 0, afterPrem = 0;
    current?.contracts.forEach((c, ci) => {
      beforePrem += c.monthly_premium || 0;
      const contractDropped = dropContracts.has(ci);
      if (!contractDropped) afterPrem += c.monthly_premium || 0;
      c.coverages.forEach((cov, covi) => {
        before.set(cov.name, (before.get(cov.name) || 0) + cov.amount);
        const covDropped = contractDropped || dropCoverages.has(`${ci}:${covi}`);
        if (!covDropped) after.set(cov.name, (after.get(cov.name) || 0) + cov.amount);
      });
    });
    proposals.forEach((p) => {
      afterPrem += p.summary.total_monthly_premium || 0;
      p.contracts.forEach((c) => c.coverages.forEach((cov) => {
        after.set(cov.name, (after.get(cov.name) || 0) + cov.amount);
      }));
    });
    const names = Array.from(new Set([...before.keys(), ...after.keys()]));
    const rows = names.map((nm) => {
      const b = before.get(nm) || 0, a = after.get(nm) || 0;
      return { name: nm, before: b, after: a, removed: b > 0 && a === 0, added: b === 0 && a > 0, diff: a - b };
    }).sort((x, y) => y.after - x.after || y.before - x.before);
    return { rows, beforePrem, afterPrem };
  }, [current, proposals, dropContracts, dropCoverages]);

  return (
    <div className="mx-auto max-w-4xl">
      <header className="mb-6 print:hidden">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">Coverage Compare</p>
        <h1 className="ko-heading mt-2 text-3xl font-extrabold tracking-tight text-ink-900 md:text-4xl">보장 비교분석</h1>
        <p className="ko-text mt-2 text-[14px] text-ink-soft">현재 보험과 신규 제안을 비교해 컨설팅 전·후를 한눈에.</p>
      </header>

      <div className="print:hidden"><Stepper step={step} /></div>
      {error && <p className="print:hidden mb-4 rounded-[8px] bg-red-50 px-4 py-2.5 text-sm text-red-600">{error}</p>}

      {/* STEP 1 */}
      {step === 1 && (
        <section className="rounded-card border border-line bg-white p-6">
          <h2 className="ko-heading text-lg font-bold text-ink-900">① 현재 보험 업로드</h2>
          <p className="ko-text mt-1 text-[13px] text-ink-soft">보장분석서(PDF)를 올리면 계약·담보를 자동 인식합니다.</p>
          <Link
            to="/coverage-guide"
            className="ko-text mt-4 inline-flex text-[13px] font-semibold text-accent-700 hover:text-accent-800"
          >
            PDF 받는 방법을 모르신다면 → 보험사별 가이드 보기
          </Link>
          <label className="mt-3 flex h-32 cursor-pointer flex-col items-center justify-center rounded-card border-2 border-dashed border-accent-200 bg-accent-50 text-center hover:border-accent-400">
            <span className="text-2xl" aria-hidden>📄</span>
            <span className="mt-2 text-sm font-semibold text-accent-700">{busy ? "분석 중…" : "보장분석서 PDF 선택"}</span>
            <input type="file" accept="application/pdf" className="hidden" onChange={onUploadCurrent} disabled={busy} />
          </label>

          {current && (
            <div className="mt-5">
              <p className="text-sm font-bold text-ink-900">{current.insurer} · 월 {won(current.summary.total_monthly_premium)}원</p>
              <Warnings ws={current.parse_warnings} />
              <div className="mt-3 space-y-3">
                {current.contracts.map((c, ci) => (
                  <details key={ci} className="rounded-[8px] border border-line">
                    <summary className="flex cursor-pointer items-center justify-between gap-2 px-4 py-3">
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-semibold text-ink-900">{c.product_name}</span>
                        <span className="text-[12px] text-ink-soft">{c.join_date} · {c.coverage_end} · 월 {won(c.monthly_premium)}원 · 담보 {c.coverages.length}</span>
                      </span>
                      <label className="flex shrink-0 items-center gap-1.5 text-[12px] font-semibold text-red-600">
                        <input type="checkbox" checked={dropContracts.has(ci)} onChange={() => toggle(dropContracts, ci, setDropContracts)} /> 이 보험 해지
                      </label>
                    </summary>
                    <ul className="divide-y divide-line border-t border-line">
                      {c.coverages.map((cov, covi) => (
                        <li key={covi} className="flex items-center justify-between gap-2 px-4 py-2 text-[13px]">
                          <span className={dropCoverages.has(`${ci}:${covi}`) || dropContracts.has(ci) ? "text-ink-400 line-through" : "text-ink-800"}>
                            {cov.type && <span className="mr-1 text-[11px] text-accent-700">[{cov.type}]</span>}{cov.name} · {won(cov.amount)}만원
                          </span>
                          <label className="flex shrink-0 items-center gap-1 text-[11px] text-ink-400">
                            <input type="checkbox" checked={dropCoverages.has(`${ci}:${covi}`)} onChange={() => toggle(dropCoverages, `${ci}:${covi}`, setDropCoverages)} /> 삭제
                          </label>
                        </li>
                      ))}
                    </ul>
                  </details>
                ))}
              </div>
              <button onClick={() => setStep(2)} className="button-text mt-5 w-full rounded-btn bg-accent-600 py-3 text-sm font-bold text-white hover:bg-accent-700">다음 단계 →</button>
            </div>
          )}
        </section>
      )}

      {/* STEP 2 */}
      {step === 2 && (
        <section className="rounded-card border border-line bg-white p-6">
          <h2 className="ko-heading text-lg font-bold text-ink-900">② 신규 가입 제안서 업로드</h2>
          <p className="ko-text mt-1 text-[13px] text-ink-soft">회사별 제안서를 여러 개 올릴 수 있습니다.</p>
          <label className="mt-4 flex h-28 cursor-pointer flex-col items-center justify-center rounded-card border-2 border-dashed border-accent-200 bg-accent-50 text-center hover:border-accent-400">
            <span className="text-2xl" aria-hidden>📑</span>
            <span className="mt-2 text-sm font-semibold text-accent-700">{busy ? "분석 중…" : "제안서 PDF 선택(다중 가능)"}</span>
            <input type="file" accept="application/pdf" multiple className="hidden" onChange={onUploadProposals} disabled={busy} />
          </label>
          {proposals.map((p, i) => (
            <div key={i} className="mt-3 rounded-[8px] border border-line px-4 py-3">
              <p className="text-sm font-semibold text-ink-900">{p.insurer} · 월 {won(p.summary.total_monthly_premium)}원 · 담보 {p.contracts.reduce((n, c) => n + c.coverages.length, 0)}</p>
              <Warnings ws={p.parse_warnings} />
            </div>
          ))}
          <div className="mt-5 flex gap-2">
            <button onClick={() => setStep(1)} className="button-text rounded-btn border border-line-strong bg-white px-5 py-3 text-sm font-bold text-ink-800 hover:bg-ink-50">← 이전</button>
            <button
              onClick={() => { if (!session) { navigate("/login"); return; } setStep(3); }}
              disabled={!current}
              className="button-text flex-1 rounded-btn bg-accent-600 py-3 text-sm font-bold text-white hover:bg-accent-700 disabled:opacity-50"
            >분석 시작 →</button>
          </div>
        </section>
      )}

      {/* STEP 3 */}
      {step === 3 && (
        <section className="rounded-card border border-line bg-white p-6">
          <div className="flex items-center justify-between gap-3">
            <h2 className="ko-heading text-lg font-bold text-ink-900">③ 비교 리포트</h2>
            <button onClick={() => window.print()} className="print:hidden button-text rounded-btn border border-line-strong bg-white px-4 py-2 text-[13px] font-bold text-ink-800 hover:bg-ink-50">🖨 인쇄 / PDF</button>
          </div>

          {/* 세부 비교 */}
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-line text-left text-ink-500">
                  <th className="py-2">보장 항목</th>
                  <th className="py-2 text-right">컨설팅 전(만원)</th>
                  <th className="py-2 text-right">컨설팅 후(만원)</th>
                </tr>
              </thead>
              <tbody>
                {report.rows.map((r) => (
                  <tr key={r.name} className="border-b border-line/60">
                    <td className={`py-1.5 ${r.removed ? "text-ink-400 line-through" : r.added ? "font-semibold text-emerald-700" : "text-ink-800"}`}>
                      {r.name}{r.added && " (신규)"}
                    </td>
                    <td className={`py-1.5 text-right ${r.removed ? "text-ink-400 line-through" : "text-ink-700"}`}>{r.before ? won(r.before) : "-"}</td>
                    <td className={`py-1.5 text-right ${r.added ? "text-emerald-700" : "text-ink-900"}`}>{r.after ? won(r.after) : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 요약 */}
          <div className="mt-6 rounded-card border border-accent-200 bg-accent-50 p-5">
            <h3 className="ko-heading text-sm font-bold text-ink-900">최종 요약</h3>
            <table className="mt-2 w-full text-[13px]">
              <tbody>
                <tr className="border-b border-accent-100">
                  <td className="py-1.5 text-ink-700">총 월 보험료</td>
                  <td className="py-1.5 text-right text-ink-700">{won(report.beforePrem)}원</td>
                  <td className="py-1.5 text-right font-bold text-ink-900">{won(report.afterPrem)}원</td>
                  <td className={`py-1.5 text-right font-bold ${report.afterPrem > report.beforePrem ? "text-emerald-700" : report.afterPrem < report.beforePrem ? "text-red-600" : "text-ink-400"}`}>
                    {report.afterPrem === report.beforePrem ? "동일" : `${report.afterPrem > report.beforePrem ? "+" : ""}${won(report.afterPrem - report.beforePrem)}원`}
                  </td>
                </tr>
              </tbody>
            </table>
            <p className="ko-text mt-2 text-[11px] text-ink-400">※ 자동 인식 결과로 실제 약관과 차이가 있을 수 있어 발송 전 원본 확인이 필요합니다.</p>
          </div>

          <button onClick={() => setStep(2)} className="print:hidden button-text mt-5 rounded-btn border border-line-strong bg-white px-5 py-3 text-sm font-bold text-ink-800 hover:bg-ink-50">← 이전</button>
        </section>
      )}
    </div>
  );
}
