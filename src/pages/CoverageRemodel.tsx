import { useMemo, useState, type ChangeEvent } from "react";
import { useNavigate } from "react-router-dom";
import ConsentGate from "../components/ConsentGate";
import { useAuth } from "../lib/auth-context";

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

type Company = {
  idx: number;
  insurer: string | null;
  product: string | null;
  contract_date: string | null;
  pay_cycle: string | null;
  pay_years: number | null;
  pay_months: number | null;
  maturity: string | null;
  monthly_premium: number | null;
  paid_total: number | null;
  remark: string | null;
};

type BeforeCoverage = {
  kb_name: string;
  kb_group: string;
  group12: string;
  agg: string;
  summary: number | null;
  by_company: Record<string, number | null>;
  enrolled: boolean;
};

type FinalCoverage = {
  group12: string;
  kb_name: string;
  agg: string;
  value: number | null;
  recommended: number | null;
  gap: number | null;
  status: string | null;
};

type AnalyzeResult = {
  before: {
    customer: { name: string | null; age: number | null; sex: string | null };
    premium: { monthly_total: number; paid_total: number; currency: string };
    companies: Company[];
    contract_list?: Company[];
    coverages: BeforeCoverage[];
  };
  final: {
    premium: { monthly_total: number; paid_total: number };
    coverages: FinalCoverage[];
    rollup_by_group12: { group12: string; status_counts: Record<string, number> }[];
  };
  warnings: string[];
};

const GROUP_ORDER = [
  "사망",
  "후유장해",
  "암",
  "뇌/심장",
  "수술",
  "입원일당",
  "실손의료비",
  "상해",
  "운전자",
  "배상책임",
  "화재",
  "기타",
];

const STATUS_CLASS: Record<string, string> = {
  충분: "bg-accent-50 text-accent-700",
  부족: "bg-amber-50 text-amber-700",
  미가입: "bg-ink-100 text-ink-500",
};

function formatCoverageAmount(value: number | null | undefined): string {
  if (value == null) return "-";
  if (value === 0) return "0";

  const eok = Math.floor(value / 100_000_000);
  const man = Math.floor((value % 100_000_000) / 10_000);
  const parts: string[] = [];
  if (eok) parts.push(`${eok}억`);
  if (man) parts.push(`${man.toLocaleString("ko-KR")}만`);
  return parts.length > 0 ? parts.join(" ") : value.toLocaleString("ko-KR");
}

function formatWon(value: number | null | undefined): string {
  return value == null ? "-" : `${value.toLocaleString("ko-KR")}원`;
}

function formatPremium(value: number | null | undefined): string {
  return value == null ? "미제공" : `${value.toLocaleString("ko-KR")}원`;
}

function formatPeriod(company: Company): string {
  const pay = company.pay_years ? `${company.pay_years}년납` : "납입기간 미제공";
  const maturity = company.maturity ? `${company.maturity} 만기` : "만기 미제공";
  return `${pay} · ${maturity}`;
}

function StatusBadge({ status }: { status: string | null }) {
  const className = status ? STATUS_CLASS[status] : undefined;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-bold ${
        className || "bg-ink-100 text-ink-500"
      }`}
    >
      {status || "-"}
    </span>
  );
}

const DISCLAIMER =
  "이 리모델링표는 업로드한 KB 보장분석 제안서 PDF를 기준으로 정리한 참고 자료입니다. 실제 보장 내용, 보험금 지급 여부, 가입 가능 여부는 각 보험사의 약관과 심사 기준에 따라 달라질 수 있습니다.";

export default function CoverageRemodel() {
  const { session } = useAuth();
  const navigate = useNavigate();
  const [agreed, setAgreed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [fileName, setFileName] = useState("");
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [showBefore, setShowBefore] = useState(false);
  const [exporting, setExporting] = useState<"" | "excel" | "pdf">(""); // BOHUMFIT-181

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    const token = session?.access_token;
    if (!token) {
      navigate("/login");
      return;
    }

    setBusy(true);
    setError("");
    setResult(null);
    setFileName(file.name);

    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API_BASE}/coverage/analyze`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "보장분석표를 생성하지 못했습니다.");
      }

      setResult((await response.json()) as AnalyzeResult);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "알 수 없는 오류가 발생했습니다.");
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }

  // BOHUMFIT-181: 분석 결과(result) JSON을 서버로 보내 엑셀/PDF 스트림 수신 → 다운로드. (서버 미저장)
  async function exportFile(kind: "excel" | "pdf") {
    if (!result) return;
    const token = session?.access_token;
    if (!token) {
      navigate("/login");
      return;
    }
    setExporting(kind);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/coverage/export/${kind}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(result),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "파일을 생성하지 못했습니다.");
      }
      const blob = await response.blob();
      const disposition = response.headers.get("Content-Disposition") || "";
      const match = /filename\*=UTF-8''([^;]+)/.exec(disposition);
      const fallback = kind === "excel" ? "BohumFit_보장분석.xlsx" : "BohumFit_보장분석.pdf";
      const downloadName = match ? decodeURIComponent(match[1]) : fallback;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = downloadName;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : "파일 생성 중 오류가 발생했습니다.");
    } finally {
      setExporting("");
    }
  }

  const finalGroups = useMemo(() => {
    if (!result) return [];
    const grouped = new Map<string, FinalCoverage[]>();
    for (const coverage of result.final.coverages) {
      const rows = grouped.get(coverage.group12) || [];
      rows.push(coverage);
      grouped.set(coverage.group12, rows);
    }
    return GROUP_ORDER.filter((group) => grouped.has(group)).map((group) => ({
      group,
      rows: grouped.get(group) || [],
    }));
  }, [result]);

  const statusSummary = useMemo(() => {
    const summary = { 부족: 0, 미가입: 0 };
    if (!result) return summary;
    for (const coverage of result.final.coverages) {
      if (coverage.status === "부족") summary.부족 += 1;
      if (coverage.status === "미가입") summary.미가입 += 1;
    }
    return summary;
  }, [result]);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 md:px-6">
      <header className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">Coverage Remodeling</p>
        <h1 className="ko-heading mt-2 text-3xl font-extrabold tracking-tight text-ink-900 md:text-4xl">
          보장분석 리모델링표
        </h1>
        <p className="ko-text mt-2 break-keep text-[14px] text-ink-soft">
          KB 보장분석 제안서 PDF를 업로드하면 현재 가입 보장과 권장 보장 대비 과부족을 표로 정리합니다.
        </p>
      </header>

      <section className="rounded-card border border-line bg-white p-6">
        <h2 className="ko-heading text-lg font-bold text-ink-900">PDF 업로드</h2>
        <ConsentGate
          agreed={agreed}
          onChange={setAgreed}
          note="보장분석 제안서에는 고객 계약정보가 포함될 수 있습니다. 분석 목적에 필요한 범위에서만 사용해 주세요."
          className="mt-3"
        />
        <label
          className={`mt-4 flex h-32 flex-col items-center justify-center rounded-card border-2 border-dashed text-center transition ${
            agreed
              ? "cursor-pointer border-accent-200 bg-accent-50 hover:border-accent-400"
              : "cursor-not-allowed border-line bg-ink-50 opacity-60"
          }`}
        >
          <span className="text-2xl" aria-hidden="true">
            PDF
          </span>
          <span className="mt-2 text-sm font-semibold text-accent-700">
            {busy ? "분석 중입니다..." : "KB 보장분석 제안서 PDF 선택"}
          </span>
          <span className="mt-1 text-xs text-ink-soft">PDF 1개를 업로드해 주세요.</span>
          <input
            type="file"
            accept="application/pdf"
            className="hidden"
            disabled={!agreed || busy}
            onChange={handleUpload}
            aria-label="KB 보장분석 제안서 PDF 업로드"
          />
        </label>
        {fileName && result && !error && <p className="mt-2 text-xs text-accent-600">{fileName} 분석 완료</p>}
        {error && <p className="mt-2 rounded-[8px] bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}
        {result && result.warnings.length > 0 && (
          <p className="mt-2 rounded-[8px] bg-amber-50 px-3 py-2 text-[12px] text-amber-700">
            확인 필요: {result.warnings.join(" / ")}
          </p>
        )}
      </section>

      {result && (
        <>
          <section className="mt-6 rounded-card border border-line bg-white p-6">
            <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
              <div>
                <h2 className="ko-heading text-lg font-bold text-ink-900">최종 보장 진단</h2>
                <p className="mt-1 text-xs text-ink-soft">{DISCLAIMER}</p>
              </div>
              <div className="flex flex-col items-start gap-2 md:items-end">
                {result.before.customer.name && (
                  <p className="text-sm font-semibold text-ink-700">고객명 {result.before.customer.name}</p>
                )}
                {/* BOHUMFIT-181: 엑셀·PDF 내보내기(세컨더리). 분석 결과 있을 때만 노출. */}
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => void exportFile("excel")}
                    disabled={exporting !== ""}
                    className="button-text rounded-btn border border-line-strong bg-white px-4 py-2 text-[13px] font-bold text-ink-800 hover:bg-ink-50 disabled:opacity-50"
                  >
                    {exporting === "excel" ? "엑셀 생성 중…" : "엑셀 저장"}
                  </button>
                  <button
                    type="button"
                    onClick={() => void exportFile("pdf")}
                    disabled={exporting !== ""}
                    className="button-text rounded-btn border border-line-strong bg-white px-4 py-2 text-[13px] font-bold text-ink-800 hover:bg-ink-50 disabled:opacity-50"
                  >
                    {exporting === "pdf" ? "PDF 생성 중…" : "PDF 저장"}
                  </button>
                </div>
              </div>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <div className="rounded-card border border-line bg-canvas px-4 py-3">
                <p className="text-[12px] text-ink-soft">월납 보험료 합계</p>
                <p className="mt-1 text-xl font-extrabold text-ink-900">{formatWon(result.before.premium.monthly_total)}</p>
              </div>
              <div className="rounded-card border border-line bg-canvas px-4 py-3">
                <p className="text-[12px] text-ink-soft">총 납입 예정액</p>
                <p className="mt-1 text-xl font-extrabold text-ink-900">{formatWon(result.before.premium.paid_total)}</p>
              </div>
              <div className="rounded-card border border-line bg-canvas px-4 py-3">
                <p className="text-[12px] text-ink-soft">부족 / 미가입 담보</p>
                <p className="mt-1 text-xl font-extrabold text-ink-900">
                  <span className="text-amber-700">{statusSummary.부족}</span>
                  <span className="text-sm text-ink-soft"> / </span>
                  <span className="text-ink-500">{statusSummary.미가입}</span>
                </p>
              </div>
            </div>

            <div className="mt-5 space-y-5">
              {finalGroups.map(({ group, rows }) => (
                <div key={group}>
                  <h3 className="ko-heading mb-2 text-sm font-bold text-ink-900">{group}</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[560px] text-[13px]">
                      <thead>
                        <tr className="border-b border-line text-left text-ink-500">
                          <th className="py-2 pr-2">담보</th>
                          <th className="px-2 py-2 text-right">권장</th>
                          <th className="px-2 py-2 text-right">가입</th>
                          <th className="px-2 py-2 text-right">과부족</th>
                          <th className="py-2 pl-2 text-center">준비</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rows.map((coverage) => (
                          <tr key={`${coverage.group12}-${coverage.kb_name}`} className="border-b border-line/60">
                            <td className="break-keep py-1.5 pr-2 font-semibold text-ink-800">{coverage.kb_name}</td>
                            <td className="px-2 py-1.5 text-right text-ink-soft">
                              {formatCoverageAmount(coverage.recommended)}
                            </td>
                            <td className="px-2 py-1.5 text-right text-ink-900">{formatCoverageAmount(coverage.value)}</td>
                            <td
                              className={`px-2 py-1.5 text-right font-semibold ${
                                coverage.gap == null
                                  ? "text-ink-400"
                                  : coverage.gap < 0
                                    ? "text-amber-700"
                                    : coverage.gap > 0
                                      ? "text-accent-700"
                                      : "text-ink-500"
                              }`}
                            >
                              {coverage.gap == null
                                ? "-"
                                : `${coverage.gap > 0 ? "+" : coverage.gap < 0 ? "-" : ""}${formatCoverageAmount(Math.abs(coverage.gap))}`}
                            </td>
                            <td className="py-1.5 pl-2 text-center">
                              <StatusBadge status={coverage.status} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="mt-6 rounded-card border border-line bg-white">
            <button
              type="button"
              onClick={() => setShowBefore((value) => !value)}
              aria-expanded={showBefore}
              className="flex w-full items-center justify-between gap-2 px-6 py-4 text-left"
            >
              <span className="ko-heading text-lg font-bold text-ink-900">회사별 가입 현황 (전)</span>
              <span className="text-sm font-semibold text-accent-700">{showBefore ? "접기" : "펼치기"}</span>
            </button>

            {showBefore && (
              <div className="border-t border-line px-6 py-5">
                <div className="mb-4 grid gap-3 md:grid-cols-2">
                  {(result.before.contract_list || result.before.companies).map((company) => (
                    <div key={company.idx} className="rounded-card border border-line bg-canvas px-4 py-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-bold text-ink-900">{company.insurer || `계약 ${company.idx}`}</p>
                          <p className="mt-1 text-xs text-ink-soft">{company.product || "상품명 확인 필요"}</p>
                          <p className="mt-1 text-[11px] font-semibold text-ink-soft">{formatPeriod(company)}</p>
                        </div>
                        <p className="shrink-0 text-sm font-extrabold text-ink-900">{formatPremium(company.monthly_premium)}</p>
                      </div>
                      {company.remark && <p className="mt-2 text-xs font-semibold text-amber-700">{company.remark}</p>}
                    </div>
                  ))}
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full min-w-[720px] text-[12px]">
                    <thead>
                      <tr className="border-b border-line text-ink-500">
                        <th className="py-2 pr-2 text-left">담보</th>
                        <th className="px-2 py-2 text-right">합산</th>
                        {result.before.companies.map((company) => (
                          <th key={company.idx} className="px-2 py-2 text-right">
                            {company.insurer || `계약 ${company.idx}`}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.before.coverages.map((coverage) => (
                        <tr key={coverage.kb_name} className="border-b border-line/60">
                          <td className="break-keep py-1.5 pr-2 font-semibold text-ink-800">{coverage.kb_name}</td>
                          <td className="px-2 py-1.5 text-right font-semibold text-ink-900">
                            {formatCoverageAmount(coverage.summary)}
                          </td>
                          {result.before.companies.map((company) => (
                            <td key={company.idx} className="px-2 py-1.5 text-right text-ink-soft">
                              {formatCoverageAmount(coverage.by_company[String(company.idx)])}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
