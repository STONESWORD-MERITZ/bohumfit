import { useMemo, useState, type ChangeEvent } from "react";
import { Plus, Trash2, UploadCloud } from "lucide-react";
import { useNavigate } from "react-router-dom";
import ConsentGate from "../components/ConsentGate";
import { useAuth } from "../lib/auth-context";
import {
  buildAfterResult,
  groupKey,
  keyOf,
  toNumberOrNull,
  type AnalyzeResult,
  type Company,
  type ComparisonRow,
  type ContractDecision,
  type CoverageAfterResponse,
  type ProposalCoverageDraft,
  type ProposalDraft,
} from "../lib/coverageAfterDisplayCache";

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

type ReportCoverDraft = {
  customerName: string;
  insuranceAge: string;
  ageChangeDate: string;
  gaName: string;
  plannerName: string;
  writtenDate: string;
};

type ParsedProposalCoverage = {
  kb_name: string;
  amount: number | null;
  kb_group?: string;
  group12?: string;
  agg?: string;
  source?: string;
};

type ParsedProposal = {
  proposal_id: string;
  insurer?: string;
  product?: string;
  monthly_premium: number | null;
  pay_months: number | null;
  maturity?: string | null;
  coverages: ParsedProposalCoverage[];
  filename?: string;
};

type ParsedProposalResponse = {
  proposals: ParsedProposal[];
  warnings?: string[];
  premium?: { monthly_total?: number; currency?: string };
  premium_total?: number;
  count?: number;
};

function makeProposal(): ProposalDraft {
  const id = `P${Date.now().toString(36)}`;
  return {
    id,
    insurer: "",
    product: "",
    monthlyPremium: "",
    payMonths: "",
    maturity: "",
    coverages: [{ id: `${id}-C1`, kbName: "", amount: "" }],
  };
}

function draftFromParsedProposal(proposal: ParsedProposal, index: number): ProposalDraft {
  const id = proposal.proposal_id || `P${index + 1}`;
  const coverages = (proposal.coverages || []).map((coverage, coverageIndex) => ({
    id: `${id}-C${coverageIndex + 1}`,
    kbName: coverage.kb_name || "",
    amount: coverage.amount == null ? "" : String(coverage.amount),
    kbGroup: coverage.kb_group,
    group12: coverage.group12,
    agg: coverage.agg,
  }));
  return {
    id,
    insurer: proposal.insurer || "",
    product: proposal.product || proposal.filename || "",
    monthlyPremium: proposal.monthly_premium == null ? "" : String(proposal.monthly_premium),
    payMonths: proposal.pay_months == null ? "" : String(proposal.pay_months),
    maturity: proposal.maturity || "",
    coverages: coverages.length ? coverages : [{ id: `${id}-C1`, kbName: "", amount: "" }],
  };
}

function todayDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function makeReportCover(): ReportCoverDraft {
  return {
    customerName: "",
    insuranceAge: "",
    ageChangeDate: "",
    gaName: "",
    plannerName: "",
    writtenDate: todayDate(),
  };
}

function maskDisplayName(value: string): string {
  const raw = value.replace(/\s+/g, "");
  if (!raw) return "";
  if (raw.includes("*")) return raw;
  if (raw.length === 1) return raw;
  if (raw.length === 2) return `${raw[0]}*`;
  return `${raw[0]}*${raw[raw.length - 1]}`;
}

function reportCoverPayload(draft: ReportCoverDraft): Record<string, string> {
  const entries = {
    customer_name: draft.customerName.trim(),
    insurance_age: draft.insuranceAge.trim(),
    age_change_date: draft.ageChangeDate.trim(),
    ga_name: draft.gaName.trim(),
    planner_name: draft.plannerName.trim(),
    written_date: draft.writtenDate.trim(),
  };
  return Object.fromEntries(Object.entries(entries).filter(([, value]) => value)) as Record<string, string>;
}

function withReportCover<T extends object>(analysis: T, draft: ReportCoverDraft): T & { report_cover?: Record<string, string> } {
  const reportCover = reportCoverPayload(draft);
  return Object.keys(reportCover).length > 0 ? { ...analysis, report_cover: reportCover } : analysis;
}

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

function formatCoverageDeltaAmount(value: number | null | undefined): string {
  if (value == null) return "-";
  if (value === 0) return "0";
  return `${value > 0 ? "+" : "-"}${formatCoverageAmount(Math.abs(value))}`;
}

function formatWon(value: number | null | undefined): string {
  return value == null ? "-" : `${value.toLocaleString("ko-KR")}원`;
}

function formatPremium(value: number | null | undefined): string {
  return value == null ? "미제공" : `${value.toLocaleString("ko-KR")}원`;
}

function formatDeltaWon(value: number | null | undefined): string {
  if (value == null) return "-";
  if (value === 0) return "변동 없음";
  return `${value > 0 ? "+" : "-"}${Math.abs(value).toLocaleString("ko-KR")}원`;
}

function formatPeriod(company: Company): string {
  const pay = company.pay_years ? `${company.pay_years}년납` : "납입기간 미제공";
  const maturity = company.maturity ? `${company.maturity} 만기` : "만기 미제공";
  return `${pay} · ${maturity}`;
}

function groupComparisonRows(rows: ComparisonRow[]) {
  const grouped = new Map<string, ComparisonRow[]>();
  for (const row of rows) {
    const items = grouped.get(row.group12) || [];
    items.push(row);
    grouped.set(row.group12, items);
  }
  return Array.from(grouped.entries())
    .sort(([left], [right]) => groupKey(left) - groupKey(right))
    .map(([group, groupedRows]) => ({ group, rows: groupedRows }));
}

function groupComparisonValues(rows: ComparisonRow[]) {
  const grouped = new Map<string, { group: string; beforeValue: number; afterValue: number; improvedCount: number }>();
  for (const row of rows) {
    const item = grouped.get(row.group12) || { group: row.group12, beforeValue: 0, afterValue: 0, improvedCount: 0 };
    item.beforeValue += row.before_value || 0;
    item.afterValue += row.after_value || 0;
    if (row.improved) item.improvedCount += 1;
    grouped.set(row.group12, item);
  }
  return Array.from(grouped.values())
    .map((item) => ({ ...item, deltaValue: item.afterValue - item.beforeValue }))
    .filter((item) => item.deltaValue !== 0 || item.improvedCount > 0)
    .sort((left, right) => groupKey(left.group) - groupKey(right.group));
}

function MetricCard({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "default" | "good" | "warn";
}) {
  const toneClass = tone === "good" ? "text-accent-700" : tone === "warn" ? "text-amber-700" : "text-ink-900";
  return (
    <div className="rounded-card border border-line bg-canvas px-4 py-3">
      <p className="text-[12px] text-ink-soft">{label}</p>
      <p className={`mt-1 text-xl font-extrabold ${toneClass}`}>{value}</p>
    </div>
  );
}

export default function CoverageRemodel() {
  const { session } = useAuth();
  const navigate = useNavigate();
  const [agreed, setAgreed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [fileName, setFileName] = useState("");
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [afterResult, setAfterResult] = useState<CoverageAfterResponse | null>(null);
  const [decisions, setDecisions] = useState<Record<string, ContractDecision>>({});
  const [proposals, setProposals] = useState<ProposalDraft[]>([]);
  const [expandedProposalIds, setExpandedProposalIds] = useState<Record<string, boolean>>({});
  const [proposalFileNames, setProposalFileNames] = useState<string[]>([]);
  const [proposalParsing, setProposalParsing] = useState(false);
  const [proposalParseNotes, setProposalParseNotes] = useState<string[]>([]);
  const [reportCover, setReportCover] = useState<ReportCoverDraft>(() => makeReportCover());
  const [exporting, setExporting] = useState<"" | "excel" | "pdf">("");

  const companies = useMemo(() => result?.before.contract_list || result?.before.companies || [], [result]);
  const comparisonGroups = useMemo(() => groupComparisonRows(afterResult?.comparison.coverages || []), [afterResult]);
  const comparisonValueGroups = useMemo(() => groupComparisonValues(afterResult?.comparison.coverages || []), [afterResult]);
  const coverageOptions = useMemo(() => {
    const options = [...(result?.before.coverages || [])];
    const seen = new Set(options.map((coverage) => coverage.kb_name));
    for (const proposal of proposals) {
      for (const coverage of proposal.coverages) {
        if (!coverage.kbName || seen.has(coverage.kbName)) continue;
        options.push({
          kb_name: coverage.kbName,
          kb_group: coverage.kbGroup || coverage.group12 || "신규제안",
          group12: coverage.group12 || "기타",
          agg: coverage.agg || "sum",
          summary: null,
          by_company: {},
          enrolled: false,
        });
        seen.add(coverage.kbName);
      }
    }
    return options;
  }, [result, proposals]);

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
    setAfterResult(null);
    setDecisions({});
    setProposals([]);
    setExpandedProposalIds({});
    setProposalFileNames([]);
    setProposalParseNotes([]);
    setReportCover(makeReportCover());
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
        body: JSON.stringify(withReportCover(afterResult || result, reportCover)),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "파일을 생성하지 못했습니다.");
      }
      const blob = await response.blob();
      const disposition = response.headers.get("Content-Disposition") || "";
      const match = /filename\*=UTF-8''([^;]+)/.exec(disposition);
      const fallback = kind === "excel" ? "BohumFit_전후비교.xlsx" : "BohumFit_전후비교.pdf";
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

  function updateContractDecision(idx: number | string, patch: Partial<ContractDecision>) {
    const key = keyOf(idx);
    setDecisions((current) => {
      const previous: ContractDecision = current[key] || {
        disposition: "keep",
      };
      return { ...current, [key]: { ...previous, ...patch } };
    });
    setAfterResult(null);
  }

  function updateReportCover(patch: Partial<ReportCoverDraft>) {
    setReportCover((current) => ({ ...current, ...patch }));
  }

  function addProposal() {
    const proposal = makeProposal();
    setProposals((current) => [...current, proposal]);
    setExpandedProposalIds((current) => ({ ...current, [proposal.id]: true }));
    setAfterResult(null);
  }

  function toggleProposalExpanded(id: string) {
    setExpandedProposalIds((current) => ({ ...current, [id]: !current[id] }));
  }

  function updateProposal(id: string, patch: Partial<ProposalDraft>) {
    setProposals((current) => current.map((proposal) => (proposal.id === id ? { ...proposal, ...patch } : proposal)));
    setAfterResult(null);
  }

  function removeProposal(id: string) {
    setProposals((current) => current.filter((proposal) => proposal.id !== id));
    setExpandedProposalIds((current) => {
      const next = { ...current };
      delete next[id];
      return next;
    });
    setAfterResult(null);
  }

  function updateProposalCoverage(proposalId: string, coverageId: string, patch: Partial<ProposalCoverageDraft>) {
    setProposals((current) =>
      current.map((proposal) =>
        proposal.id === proposalId
          ? {
              ...proposal,
              coverages: proposal.coverages.map((coverage) =>
                coverage.id === coverageId ? { ...coverage, ...patch } : coverage,
              ),
            }
          : proposal,
      ),
    );
    setAfterResult(null);
  }

  function addProposalCoverage(proposalId: string) {
    setProposals((current) =>
      current.map((proposal) =>
        proposal.id === proposalId
          ? {
              ...proposal,
              coverages: [
                ...proposal.coverages,
                { id: `${proposal.id}-C${Date.now().toString(36)}`, kbName: "", amount: "" },
              ],
            }
          : proposal,
      ),
    );
    setAfterResult(null);
  }

  function removeProposalCoverage(proposalId: string, coverageId: string) {
    setProposals((current) =>
      current.map((proposal) =>
        proposal.id === proposalId
          ? {
              ...proposal,
              coverages:
                proposal.coverages.length > 1
                  ? proposal.coverages.filter((coverage) => coverage.id !== coverageId)
                  : proposal.coverages,
            }
          : proposal,
      ),
    );
    setAfterResult(null);
  }

  function recalculateAfter() {
    if (!result) return;
    setError("");
    setAfterResult(buildAfterResult(result, decisions, proposals));
  }

  async function handleProposalSlotUpload(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files || []);
    setProposalFileNames(files.map((file) => file.name));
    setProposalParseNotes([]);
    if (files.length === 0) return;
    const token = session?.access_token;
    if (!token) {
      navigate("/login");
      return;
    }
    setProposalParsing(true);
    setError("");
    try {
      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));
      const response = await fetch(`${API_BASE}/coverage/proposals/parse`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "신규 가입제안서 파싱에 실패했습니다. 수기로 보완해 주세요.");
      }
      const payload = (await response.json()) as ParsedProposalResponse;
      const parsed = (payload.proposals || []).map(draftFromParsedProposal);
      if (parsed.length > 0) {
        setProposals(parsed);
        setExpandedProposalIds(Object.fromEntries(parsed.map((proposal) => [proposal.id, false])));
        if (result) {
          setAfterResult(buildAfterResult(result, decisions, parsed));
        } else {
          setAfterResult(null);
        }
      }
      const notes = [...(payload.warnings || [])];
      const monthlyTotal = payload.premium?.monthly_total ?? payload.premium_total;
      if (monthlyTotal != null) notes.unshift(`파싱된 월보험료 합계 ${monthlyTotal.toLocaleString()}원`);
      setProposalParseNotes(notes);
    } catch (parseError) {
      setProposalParseNotes([parseError instanceof Error ? parseError.message : "신규 가입제안서 파싱 중 오류가 발생했습니다."]);
      if (proposals.length === 0) {
        const proposal = makeProposal();
        setProposals([proposal]);
        setExpandedProposalIds({ [proposal.id]: true });
      }
      setAfterResult(null);
    } finally {
      setProposalParsing(false);
      event.target.value = "";
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 md:px-6">
      <header className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">Coverage Remodeling</p>
        <h1 className="ko-heading mt-2 text-3xl font-extrabold tracking-tight text-ink-900 md:text-4xl">
          컨설팅 전 VS 후 보장 비교
        </h1>
        <p className="ko-text mt-2 break-keep text-[14px] text-ink-soft">
          KB 보장분석의 현재 상태와 유지·해지·신규제안 반영 후 상태를 나란히 비교합니다.
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
          <section className="mt-6">
            <div className="flex flex-col gap-1">
              <h2 className="ko-heading text-lg font-bold text-ink-900">① 표지</h2>
            </div>
            <div className="mt-3 grid gap-4 lg:grid-cols-[1.35fr_0.85fr]">
              <div className="rounded-card border border-line bg-white p-5">
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="text-[12px] font-semibold text-ink-700">
                    고객명
                    <input
                      className="mt-1 w-full rounded-[8px] border border-line bg-white px-3 py-2 text-sm"
                      placeholder="홍길동"
                      value={reportCover.customerName}
                      onChange={(event) => updateReportCover({ customerName: event.target.value })}
                    />
                  </label>
                  <label className="text-[12px] font-semibold text-ink-700">
                    보험나이
                    <input
                      className="mt-1 w-full rounded-[8px] border border-line bg-white px-3 py-2 text-sm"
                      placeholder="40세"
                      value={reportCover.insuranceAge}
                      onChange={(event) => updateReportCover({ insuranceAge: event.target.value })}
                    />
                  </label>
                  <label className="text-[12px] font-semibold text-ink-700">
                    상령일
                    <input
                      className="mt-1 w-full rounded-[8px] border border-line bg-white px-3 py-2 text-sm"
                      type="date"
                      value={reportCover.ageChangeDate}
                      onChange={(event) => updateReportCover({ ageChangeDate: event.target.value })}
                    />
                  </label>
                  <label className="text-[12px] font-semibold text-ink-700">
                    소속(GA)
                    <input
                      className="mt-1 w-full rounded-[8px] border border-line bg-white px-3 py-2 text-sm"
                      placeholder="GA명"
                      value={reportCover.gaName}
                      onChange={(event) => updateReportCover({ gaName: event.target.value })}
                    />
                  </label>
                  <label className="text-[12px] font-semibold text-ink-700">
                    설계사명
                    <input
                      className="mt-1 w-full rounded-[8px] border border-line bg-white px-3 py-2 text-sm"
                      placeholder="설계사명"
                      value={reportCover.plannerName}
                      onChange={(event) => updateReportCover({ plannerName: event.target.value })}
                    />
                  </label>
                  <label className="text-[12px] font-semibold text-ink-700">
                    작성일자
                    <input
                      className="mt-1 w-full rounded-[8px] border border-line bg-white px-3 py-2 text-sm"
                      type="date"
                      value={reportCover.writtenDate}
                      onChange={(event) => updateReportCover({ writtenDate: event.target.value })}
                    />
                  </label>
                </div>
              </div>
              <div className="rounded-card border border-line bg-white p-5">
                <div className="flex items-center gap-2">
                  <span className="inline-flex h-9 w-9 items-center justify-center rounded-[8px] bg-accent-700 text-lg font-extrabold text-white">
                    ㅍ
                  </span>
                  <div>
                    <p className="text-sm font-extrabold text-ink-900">BohumFit</p>
                    <p className="text-[11px] font-semibold text-ink-soft">보험핏</p>
                  </div>
                </div>
                <div className="mt-8">
                  <p className="text-[12px] font-bold text-accent-700">FIT 보장분석</p>
                  <p className="ko-heading mt-1 text-3xl font-extrabold text-ink-900">보장분석 리포트</p>
                </div>
                <div className="mt-8 grid grid-cols-[88px_1fr] gap-4">
                  <div className="flex h-16 items-center justify-center rounded-[8px] border border-dashed border-line text-[10px] font-bold uppercase tracking-[0.18em] text-ink-soft">
                    GA Logo
                  </div>
                  <div className="border-t-2 border-accent-700 text-[12px]">
                    {reportCover.customerName && (
                      <div className="flex justify-between border-b border-line py-2">
                        <span className="font-semibold text-ink-soft">고객명</span>
                        <strong className="text-ink-900">{maskDisplayName(reportCover.customerName)}</strong>
                      </div>
                    )}
                    {reportCover.insuranceAge && (
                      <div className="flex justify-between border-b border-line py-2">
                        <span className="font-semibold text-ink-soft">보험나이</span>
                        <strong className="text-ink-900">{reportCover.insuranceAge}</strong>
                      </div>
                    )}
                    {reportCover.ageChangeDate && (
                      <div className="flex justify-between border-b border-line py-2">
                        <span className="font-semibold text-ink-soft">상령일</span>
                        <strong className="text-ink-900">{reportCover.ageChangeDate}</strong>
                      </div>
                    )}
                    {reportCover.gaName && (
                      <div className="flex justify-between border-b border-line py-2">
                        <span className="font-semibold text-ink-soft">소속(GA)</span>
                        <strong className="text-ink-900">{reportCover.gaName}</strong>
                      </div>
                    )}
                    {reportCover.plannerName && (
                      <div className="flex justify-between border-b border-line py-2">
                        <span className="font-semibold text-ink-soft">설계사명</span>
                        <strong className="text-ink-900">{reportCover.plannerName}</strong>
                      </div>
                    )}
                    {reportCover.writtenDate && (
                      <div className="flex justify-between border-b border-line py-2">
                        <span className="font-semibold text-ink-soft">작성일자</span>
                        <strong className="text-ink-900">{reportCover.writtenDate}</strong>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="mt-6 rounded-card border border-line bg-white p-6">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <h2 className="ko-heading text-lg font-bold text-ink-900">② 컨설팅 전 계약 — 유지/해지</h2>
                <p className="mt-1 text-xs text-ink-soft">
                  기존 계약은 목록에서 바로 유지·해지를 체크합니다.
                </p>
              </div>
            </div>

            <div className="mt-5 grid gap-4 lg:grid-cols-2">
              {companies.map((company) => {
                const decision = decisions[keyOf(company.idx)] || {
                  disposition: "keep",
                };
                const isCanceled = decision.disposition === "cancel";
                return (
                  <article
                    key={company.idx}
                    className={`rounded-card border p-4 ${
                      isCanceled ? "border-amber-200 bg-amber-50/40" : "border-line bg-canvas"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className={isCanceled ? "text-ink-soft line-through decoration-2" : ""}>
                        <p className="font-bold text-ink-900">{company.insurer || `계약 ${company.idx}`}</p>
                        <p className="mt-1 text-xs text-ink-soft">{company.product || "상품명 확인 필요"}</p>
                        <p className="mt-1 text-[11px] font-semibold text-ink-soft">{formatPeriod(company)}</p>
                      </div>
                      <div className="flex shrink-0 flex-col items-end gap-2">
                        {isCanceled && (
                          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-bold text-amber-700">
                            해지
                          </span>
                        )}
                        <p className={`text-sm font-extrabold text-ink-900 ${isCanceled ? "line-through decoration-2" : ""}`}>
                          {formatPremium(company.monthly_premium)}
                        </p>
                      </div>
                    </div>
                    <div className="mt-4 flex items-center justify-between gap-3 rounded-[8px] border border-line bg-white px-3 py-2">
                      <span className="text-[12px] font-semibold text-ink-700">처리</span>
                      <label className="inline-flex items-center gap-2 text-sm font-bold text-ink-800">
                        <input
                          type="checkbox"
                          className="h-4 w-4 accent-accent-700"
                          checked={isCanceled}
                          onChange={(event) =>
                            updateContractDecision(company.idx, {
                              disposition: event.target.checked ? "cancel" : "keep",
                            })
                          }
                        />
                        해지
                      </label>
                    </div>
                  </article>
                );
              })}
            </div>

          </section>

          <section className="mt-6 rounded-card border border-line bg-white p-6">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <h2 className="ko-heading text-lg font-bold text-ink-900">③ 신규가입 제안서</h2>
                <p className="mt-1 text-xs text-ink-soft">
                  회사별 가입제안서 PDF를 자동 파싱해 아래 신규 제안 카드에 채웁니다. 파싱이 부족하면 수기로 보완할 수 있습니다.
                </p>
              </div>
              <button
                type="button"
                onClick={recalculateAfter}
                className="button-text rounded-btn bg-accent-600 px-4 py-2 text-[13px] font-bold text-white hover:bg-accent-700"
              >
                전후 비교 계산
              </button>
            </div>

            <label className="mt-5 flex min-h-28 cursor-pointer flex-col items-center justify-center rounded-card border-2 border-dashed border-accent-200 bg-accent-50 px-4 py-5 text-center hover:border-accent-400">
              <UploadCloud size={26} className="text-accent-700" aria-hidden="true" />
              <span className="mt-2 text-sm font-bold text-accent-800">
                {proposalParsing ? "신규 가입제안서 파싱 중..." : "신규 가입제안서 PDF 업로드"}
              </span>
              <span className="mt-1 text-xs text-ink-soft">파싱 결과는 핵심 보장금액 카드로 들어오며, 전후 비교 계산에 바로 반영됩니다.</span>
              <input
                type="file"
                accept="application/pdf"
                multiple
                className="hidden"
                disabled={proposalParsing}
                onChange={handleProposalSlotUpload}
                aria-label="신규 가입제안서 PDF 업로드"
              />
            </label>
            {proposalParseNotes.length > 0 && (
              <div className="mt-3 rounded-[8px] border border-line bg-canvas px-4 py-3 text-[12px] text-ink-700">
                {proposalParseNotes.slice(0, 4).map((note, index) => (
                  <p key={`${note}-${index}`}>{note}</p>
                ))}
              </div>
            )}
            {proposalFileNames.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {proposalFileNames.map((name) => (
                  <span key={name} className="rounded-full bg-ink-100 px-3 py-1 text-[12px] font-semibold text-ink-700">
                    {name}
                  </span>
                ))}
              </div>
            )}

            <div className="mt-6">
              <div className="flex items-center justify-between gap-3">
                <h3 className="ko-heading text-base font-bold text-ink-900">핵심 보장금액</h3>
                <button
                  type="button"
                  onClick={addProposal}
                  className="inline-flex items-center gap-1 rounded-btn border border-line-strong bg-white px-3 py-2 text-[12px] font-bold text-ink-800 hover:bg-ink-50"
                >
                  <Plus size={14} aria-hidden="true" />
                  추가
                </button>
              </div>

              {proposals.length === 0 ? (
                <p className="mt-3 rounded-[8px] bg-canvas px-4 py-3 text-[13px] text-ink-soft">
                  신규 제안이 없다면 기존 계약 조정만으로 비교할 수 있습니다.
                </p>
              ) : (
                <div className="mt-3 space-y-3">
                  {proposals.map((proposal) => {
                    const expanded = expandedProposalIds[proposal.id] ?? false;
                    const filledCoverages = proposal.coverages.filter((coverage) => coverage.kbName || coverage.amount);
                    const previewCoverages = filledCoverages.slice(0, 3);
                    const hiddenCoverageCount = Math.max(filledCoverages.length - previewCoverages.length, 0);
                    return (
                      <article key={proposal.id} className="rounded-card border border-line bg-canvas p-4">
                        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <p className="font-bold text-ink-900">{proposal.insurer || "보험사 미입력"}</p>
                              <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-bold text-accent-700">
                                {formatPremium(toNumberOrNull(proposal.monthlyPremium))}
                              </span>
                              <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-semibold text-ink-soft">
                                {proposal.maturity || "만기 미입력"}
                              </span>
                            </div>
                            <p className="mt-1 truncate text-sm font-semibold text-ink-800">
                              {proposal.product || "상품명 확인 필요"}
                            </p>
                            <div className="mt-2 flex flex-wrap gap-1.5">
                              {previewCoverages.length > 0 ? (
                                previewCoverages.map((coverage) => (
                                  <span
                                    key={coverage.id}
                                    className="rounded-full bg-white px-2 py-1 text-[11px] font-semibold text-ink-700"
                                  >
                                    {coverage.kbName || "담보 미입력"} {formatCoverageAmount(toNumberOrNull(coverage.amount))}
                                  </span>
                                ))
                              ) : (
                                <span className="text-[12px] text-ink-soft">핵심 보장금액을 입력해 주세요.</span>
                              )}
                              {hiddenCoverageCount > 0 && (
                                <span className="rounded-full bg-white px-2 py-1 text-[11px] font-semibold text-ink-soft">
                                  +{hiddenCoverageCount}
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="flex shrink-0 items-center gap-2">
                            <button
                              type="button"
                              onClick={() => toggleProposalExpanded(proposal.id)}
                              aria-expanded={expanded}
                              className="rounded-btn border border-line-strong bg-white px-3 py-2 text-[12px] font-bold text-accent-700 hover:bg-ink-50"
                            >
                              {expanded ? "접기" : "펼치기"}
                            </button>
                            <button
                              type="button"
                              onClick={() => removeProposal(proposal.id)}
                              className="rounded-btn border border-line-strong bg-white p-2 text-ink-600 hover:bg-ink-50"
                              aria-label="신규 제안 삭제"
                              title="신규 제안 삭제"
                            >
                              <Trash2 size={16} aria-hidden="true" />
                            </button>
                          </div>
                        </div>

                        {expanded && (
                          <div className="mt-4 border-t border-line pt-4">
                            <div className="grid gap-3 md:grid-cols-5">
                              <input
                                className="rounded-[8px] border border-line bg-white px-3 py-2 text-sm"
                                placeholder="보험사"
                                value={proposal.insurer}
                                onChange={(event) => updateProposal(proposal.id, { insurer: event.target.value })}
                              />
                              <input
                                className="rounded-[8px] border border-line bg-white px-3 py-2 text-sm md:col-span-2"
                                placeholder="상품명"
                                value={proposal.product}
                                onChange={(event) => updateProposal(proposal.id, { product: event.target.value })}
                              />
                              <input
                                className="rounded-[8px] border border-line bg-white px-3 py-2 text-sm"
                                inputMode="numeric"
                                placeholder="월납 보험료"
                                value={proposal.monthlyPremium}
                                onChange={(event) => updateProposal(proposal.id, { monthlyPremium: event.target.value })}
                              />
                              <input
                                className="rounded-[8px] border border-line bg-white px-3 py-2 text-sm"
                                inputMode="numeric"
                                placeholder="납입개월"
                                value={proposal.payMonths}
                                onChange={(event) => updateProposal(proposal.id, { payMonths: event.target.value })}
                              />
                            </div>
                            <input
                              className="mt-3 w-full rounded-[8px] border border-line bg-white px-3 py-2 text-sm"
                              placeholder="만기 예: 100세"
                              value={proposal.maturity}
                              onChange={(event) => updateProposal(proposal.id, { maturity: event.target.value })}
                            />
                            <div className="mt-3 space-y-2">
                              {proposal.coverages.map((coverage) => (
                                <div key={coverage.id} className="grid gap-2 sm:grid-cols-[1fr_140px_36px]">
                                  <select
                                    className="rounded-[8px] border border-line bg-white px-3 py-2 text-sm"
                                    value={coverage.kbName}
                                    onChange={(event) =>
                                      updateProposalCoverage(proposal.id, coverage.id, { kbName: event.target.value })
                                    }
                                  >
                                    <option value="">핵심 담보 선택</option>
                                    {coverageOptions.map((option) => (
                                      <option key={option.kb_name} value={option.kb_name}>
                                        {option.group12} · {option.kb_name}
                                      </option>
                                    ))}
                                  </select>
                                  <input
                                    className="rounded-[8px] border border-line bg-white px-3 py-2 text-right text-sm"
                                    inputMode="numeric"
                                    placeholder="가입금액"
                                    value={coverage.amount}
                                    onChange={(event) =>
                                      updateProposalCoverage(proposal.id, coverage.id, { amount: event.target.value })
                                    }
                                  />
                                  <button
                                    type="button"
                                    onClick={() => removeProposalCoverage(proposal.id, coverage.id)}
                                    className="rounded-btn border border-line-strong bg-white p-2 text-ink-600 hover:bg-ink-50"
                                    aria-label="담보 행 삭제"
                                    title="담보 행 삭제"
                                  >
                                    <Trash2 size={15} aria-hidden="true" />
                                  </button>
                                </div>
                              ))}
                              <button
                                type="button"
                                onClick={() => addProposalCoverage(proposal.id)}
                                className="inline-flex items-center gap-1 rounded-btn border border-line-strong bg-white px-3 py-2 text-[12px] font-bold text-ink-800 hover:bg-ink-50"
                              >
                                <Plus size={14} aria-hidden="true" />
                                보장금액 추가
                              </button>
                            </div>
                          </div>
                        )}
                      </article>
                    );
                  })}
                </div>
              )}
            </div>
          </section>

          {afterResult && (
            <>
            <section className="mt-6 rounded-card border border-line bg-white p-6">
              <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
                <div>
                  <h2 className="ko-heading text-lg font-bold text-ink-900">④ 최종 전 VS 후 — 특약별 보장 비교</h2>
                  <p className="mt-1 text-xs text-ink-soft">
                    월납 보험료 절감과 담보 단위 보장 변화를 함께 확인합니다.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => void exportFile("excel")}
                    disabled={exporting !== ""}
                    className="button-text rounded-btn border border-line-strong bg-white px-4 py-2 text-[13px] font-bold text-ink-800 hover:bg-ink-50 disabled:opacity-50"
                  >
                    비교 엑셀 저장
                  </button>
                  <button
                    type="button"
                    onClick={() => void exportFile("pdf")}
                    disabled={exporting !== ""}
                    className="button-text rounded-btn border border-line-strong bg-white px-4 py-2 text-[13px] font-bold text-ink-800 hover:bg-ink-50 disabled:opacity-50"
                  >
                    고객용 PDF 저장
                  </button>
                </div>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <MetricCard label="전 월납" value={formatWon(afterResult.comparison.premium.before_monthly)} />
                <MetricCard label="후 월납" value={formatWon(afterResult.comparison.premium.after_monthly)} />
                <MetricCard
                  label="절감액"
                  value={formatDeltaWon(afterResult.comparison.premium.delta_monthly)}
                  tone={afterResult.comparison.premium.delta_monthly < 0 ? "good" : "warn"}
                />
              </div>

              <div className="mt-4 rounded-[8px] bg-accent-50 px-4 py-3 text-[13px] font-semibold text-accent-800">
                월납 {formatDeltaWon(afterResult.comparison.premium.delta_monthly)} · 총납입{" "}
                {formatDeltaWon(afterResult.comparison.premium.delta_paid_total)}
              </div>

              {comparisonValueGroups.length > 0 && (
                <div className="mt-5">
                  <h3 className="ko-heading mb-2 text-sm font-bold text-ink-900">대분류별 보장 변화 요약</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[680px] table-fixed text-[12px]">
                      <colgroup>
                        <col className="w-[40%]" />
                        <col className="w-[20%]" />
                        <col className="w-[20%]" />
                        <col className="w-[20%]" />
                      </colgroup>
                      <thead>
                        <tr className="border-b border-line text-left text-ink-500">
                          <th className="py-2 pr-2">대분류</th>
                          <th className="px-2 py-2 text-right">전 보장금액</th>
                          <th className="px-2 py-2 text-right">후 보장금액</th>
                          <th className="px-2 py-2 text-right">증감</th>
                        </tr>
                      </thead>
                      <tbody>
                        {comparisonValueGroups.map((group) => (
                          <tr key={group.group} className="border-b border-line/60">
                            <td className="py-1.5 pr-2 font-semibold text-ink-800">{group.group}</td>
                            <td className="px-2 py-1.5 text-right">{formatCoverageAmount(group.beforeValue)}</td>
                            <td className="px-2 py-1.5 text-right font-semibold text-ink-900">
                              {formatCoverageAmount(group.afterValue)}
                            </td>
                            <td
                              className={`px-2 py-1.5 text-right font-semibold ${
                                group.deltaValue > 0
                                  ? "text-accent-700"
                                  : group.deltaValue < 0
                                    ? "text-amber-700"
                                    : "text-ink-soft"
                              }`}
                            >
                              {formatCoverageDeltaAmount(group.deltaValue)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              <div className="mt-5 space-y-5">
                {comparisonGroups.map(({ group, rows }) => (
                  <div key={group}>
                    <h3 className="ko-heading mb-2 text-sm font-bold text-ink-900">{group}</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[680px] table-fixed text-[12px]">
                        <colgroup>
                          <col className="w-[40%]" />
                          <col className="w-[20%]" />
                          <col className="w-[20%]" />
                          <col className="w-[20%]" />
                        </colgroup>
                        <thead>
                          <tr className="border-b border-line text-left text-ink-500">
                            <th className="py-2 pr-2">담보</th>
                            <th className="px-2 py-2 text-right">전 보장금액</th>
                            <th className="px-2 py-2 text-right">후 보장금액</th>
                            <th className="py-2 pl-2 text-right">증감</th>
                          </tr>
                        </thead>
                        <tbody>
                          {rows.map((coverage) => (
                            <tr key={`${coverage.group12}-${coverage.kb_name}`} className="border-b border-line/60">
                              <td className="break-keep py-1.5 pr-2 font-semibold text-ink-800">{coverage.kb_name}</td>
                              <td className="px-2 py-1.5 text-right">{formatCoverageAmount(coverage.before_value)}</td>
                              <td className="px-2 py-1.5 text-right font-semibold text-ink-900">
                                {formatCoverageAmount(coverage.after_value)}
                              </td>
                              <td className="py-1.5 pl-2 text-right">
                                {formatCoverageDeltaAmount(coverage.delta_value)}
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

            <section className="mt-6 rounded-card border border-line bg-white p-6">
              <div>
                <h2 className="ko-heading text-lg font-bold text-ink-900">⑤ 최종 전 VS 후 — 회사별 보장 세부</h2>
                <p className="mt-1 text-xs text-ink-soft">유지 계약과 신규 제안을 합친 후 기준 계약 단위 보장입니다.</p>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {afterResult.after.before.companies.map((company) => (
                  <div key={company.idx} className="rounded-card border border-line bg-canvas px-4 py-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-bold text-ink-900">{company.insurer || `계약 ${company.idx}`}</p>
                        <p className="mt-1 text-xs text-ink-soft">{company.product || "상품명 확인 필요"}</p>
                        <p className="mt-1 text-[11px] font-semibold text-ink-soft">{formatPeriod(company)}</p>
                      </div>
                      <div className="shrink-0 text-right">
                        <span className="rounded-full bg-accent-50 px-2 py-0.5 text-[11px] font-bold text-accent-700">
                          {company.consulting_status || "유지"}
                        </span>
                        <p className="mt-2 text-sm font-extrabold text-ink-900">
                          {formatPremium(company.monthly_premium)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-5 overflow-x-auto">
                <table className="w-full min-w-[720px] text-[12px]">
                  <thead>
                    <tr className="border-b border-line text-ink-500">
                      <th rowSpan={2} className="py-2 pr-2 text-left align-middle">담보</th>
                      <th rowSpan={2} className="px-2 py-2 text-right align-middle">후 보장금액</th>
                      {afterResult.after.before.companies.map((company) => (
                        <th key={company.idx} className="px-2 py-2 text-right">
                          {company.insurer || `계약 ${company.idx}`}
                        </th>
                      ))}
                    </tr>
                    <tr className="border-b border-line text-ink-500">
                      {afterResult.after.before.companies.map((company) => (
                        <th key={company.idx} className="px-2 py-2 text-right text-[11px] font-semibold text-accent-700">
                          {formatPremium(company.monthly_premium)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {afterResult.after.before.coverages.map((coverage) => (
                      <tr key={coverage.kb_name} className="border-b border-line/60">
                        <td className="break-keep py-1.5 pr-2 font-semibold text-ink-800">{coverage.kb_name}</td>
                        <td className="px-2 py-1.5 text-right font-semibold text-ink-900">
                          {formatCoverageAmount(coverage.summary)}
                        </td>
                        {afterResult.after.before.companies.map((company) => (
                          <td key={company.idx} className="px-2 py-1.5 text-right text-ink-soft">
                            {formatCoverageAmount(coverage.by_company[keyOf(company.idx)])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
            </>
          )}

        </>
      )}
    </div>
  );
}
