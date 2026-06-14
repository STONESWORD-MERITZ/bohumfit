// BOHUMFIT-043: 컨설팅 후(後) 상태 입력 + 후 비분표.
// - 산식은 041 lib 호출만(applyConsultingPlan/buildCoverageTable/sumColumns/applyManualAssignments) — 재구현 금지.
// - 후 = 유지 계약(담보 단위 감액 override 반영) + 신규 제안 계약. 전과 같은 순수 함수로 계산한다(후 전용 로직 없음).
// - 신규 제안 입력은 042 업로드 흐름(parseSourceMatrix) + 수동 배정(applyManualAssignments)을 그대로 재사용한다.
// - 모든 입력은 이 세션(메모리) 안에서만 유지된다 — 서버 전송·저장 없음.
import { useMemo, useRef, useState } from "react";
import {
  CATEGORY_BY_ID,
  GENERAL_SURGERY_GROUP,
  applyConsultingPlan,
  buildCoverageTable,
  mapCoverageName,
  normalizeCoverageName,
  sumColumns,
  type Contract,
  type ContractColumn,
  type ContractCoverage,
  type ContractStatus,
} from "../../lib/coverageMapping";
import {
  MANUAL_EXCLUDE,
  SourceFormatError,
  applyManualAssignments,
  listAssignableTargets,
  parseSourceMatrix,
  type SourceCell,
  type SourceParseResult,
} from "../../lib/coverageParse";
import CoverageTableView from "./CoverageTableView";
import FinalComparison from "./FinalComparison";
import Badge from "../ui/Badge";
import Button from "../ui/Button";
import { exportCoverageXlsx } from "../../lib/coverageExport";

function parseManwonInput(s: string): number {
  return Math.max(0, parseInt((s || "").replace(/[^\d]/g, "") || "0", 10));
}

export interface CoverageAfterSectionProps {
  /** 전 비분표에 쓰인 계약(수동 배정 반영본). 후 = 이 계약들의 유지/감액 + 신규 제안. */
  contracts: Contract[];
  /** 전 비분표 합계(041 sumColumns 결과, 제안셀 수정 반영) — 최종표 좌측 '전' 열·엑셀 전 시트에 사용. */
  beforeTotals: Record<string, number | boolean>;
  /** 전 비분표 계약 열(제안셀 수정 반영) — 엑셀 '비교분석표'(전) 시트에 사용. */
  beforeColumns: ContractColumn[];
}

export default function CoverageAfterSection({ contracts, beforeTotals, beforeColumns }: CoverageAfterSectionProps) {
  // A. 기존 계약 처리 (세션 내만)
  const [statusById, setStatusById] = useState<Record<string, ContractStatus>>({});
  const [covOverrides, setCovOverrides] = useState<Record<string, Record<number, number>>>({});
  const [premiumOverrideById, setPremiumOverrideById] = useState<Record<string, number>>({});
  // B. 신규 제안 계약 (업로드 + 수기)
  const [proposalResult, setProposalResult] = useState<SourceParseResult | null>(null);
  const [proposalFileName, setProposalFileName] = useState("");
  const [proposalParsing, setProposalParsing] = useState(false);
  const [proposalError, setProposalError] = useState("");
  const [manualProposals, setManualProposals] = useState<Contract[]>([]);
  const [proposalAssignments, setProposalAssignments] = useState<Record<string, string>>({});
  // C. 후 비분표 종수술 제안 셀 수정 (contractId → catId → 만원)
  const [afterCellEdits, setAfterCellEdits] = useState<Record<string, Record<string, number>>>({});
  // 045. 특이사항 메모(엑셀 포함) + 엑셀 생성 중 표시 — 세션 내만
  const [memo, setMemo] = useState("");
  const [exporting, setExporting] = useState(false);

  const proposalFileRef = useRef<HTMLInputElement>(null);
  const targets = useMemo(() => listAssignableTargets(), []);

  // ── A. 유지/해지 + 감액 override 가 반영된 기존 계약 ───────────────────────
  const decoratedKept: Contract[] = useMemo(
    () =>
      contracts.map((ct) => ({
        ...ct,
        status: statusById[ct.id] ?? "유지",
        overridePremiumWon: premiumOverrideById[ct.id] ?? null,
        coverages: ct.coverages.map((cov, i) => ({
          ...cov,
          overrideAmountManwon: covOverrides[ct.id]?.[i] ?? null,
        })),
      })),
    [contracts, statusById, premiumOverrideById, covOverrides],
  );

  // ── B. 신규 제안 계약 (업로드 + 수기) — id 충돌 방지 위해 prefix 부여 ───────
  const proposalContracts: Contract[] = useMemo(() => {
    const uploaded = (proposalResult?.contracts ?? []).map((ct) => ({ ...ct, id: `prop-${ct.id}` }));
    return [...uploaded, ...manualProposals];
  }, [proposalResult, manualProposals]);

  // 042 수동 배정 재사용 — 제안 계약의 미매핑 보장명 처리
  const mappedProposals: Contract[] = useMemo(
    () => applyManualAssignments(proposalContracts, proposalAssignments),
    [proposalContracts, proposalAssignments],
  );
  const proposalIdSet = useMemo(() => new Set(mappedProposals.map((c) => c.id)), [mappedProposals]);

  // ── C. 후 비분표 = applyConsultingPlan(유지+제안) → buildCoverageTable (041 공용 함수) ──
  const planned: Contract[] = useMemo(
    () => applyConsultingPlan([...decoratedKept, ...mappedProposals]),
    [decoratedKept, mappedProposals],
  );
  const afterTableRaw = useMemo(() => buildCoverageTable(planned), [planned]);

  // 종수술 제안 셀 수정 반영 → 합계도 lib(sumColumns)로 재계산 (전 비분표와 동일 처리)
  const afterColumns: ContractColumn[] = useMemo(
    () =>
      afterTableRaw.columns.map((col) => {
        const edits = afterCellEdits[col.contractId];
        if (!edits) return col;
        const cells = { ...col.cells };
        for (const [catId, v] of Object.entries(edits)) if (col.suggested[catId]) cells[catId] = v;
        return { ...col, cells };
      }),
    [afterTableRaw, afterCellEdits],
  );
  const afterTotals = useMemo(() => sumColumns(afterColumns), [afterColumns]);

  // 제안 계약 매핑 그리드(미배정 표시) — 전 매핑 그리드와 동일 패턴
  const proposalMappingRows = useMemo(() => {
    const seen = new Map<string, { name: string; categoryId: string | null; count: number; totalManwon: number }>();
    for (const ct of proposalContracts) {
      for (const cov of ct.coverages) {
        if (!cov.name) continue;
        const key = normalizeCoverageName(cov.name);
        const cur = seen.get(key);
        if (cur) {
          cur.count += 1;
          cur.totalManwon += cov.amountManwon;
        } else {
          seen.set(key, { name: cov.name, categoryId: mapCoverageName(cov.name), count: 1, totalManwon: cov.amountManwon });
        }
      }
    }
    return [...seen.entries()].map(([key, v]) => ({ key, ...v }));
  }, [proposalContracts]);
  const proposalUnmapped = proposalMappingRows.filter((r) => r.categoryId === null && !proposalAssignments[r.key]).length;

  // ── 핸들러 ─────────────────────────────────────────────────────────────────
  const setStatus = (id: string, s: ContractStatus) => setStatusById((p) => ({ ...p, [id]: s }));

  const setCovOverride = (ctId: string, idx: number, raw: string) =>
    setCovOverrides((prev) => {
      const forCt = { ...(prev[ctId] ?? {}) };
      if (raw.trim() === "") delete forCt[idx];
      else forCt[idx] = parseManwonInput(raw);
      return { ...prev, [ctId]: forCt };
    });

  const setPremiumOverride = (ctId: string, raw: string) =>
    setPremiumOverrideById((prev) => {
      const next = { ...prev };
      if (raw.trim() === "") delete next[ctId];
      else next[ctId] = parseManwonInput(raw);
      return next;
    });

  const setAfterCellEdit = (contractId: string, catId: string, raw: string) =>
    setAfterCellEdits((prev) => ({
      ...prev,
      [contractId]: { ...prev[contractId], [catId]: parseManwonInput(raw) },
    }));

  async function handleProposalFile(file: File | null) {
    if (!file) return;
    setProposalFileName(file.name);
    setProposalParsing(true);
    setProposalError("");
    try {
      const buf = await file.arrayBuffer();
      const XLSX = await import("xlsx");
      const wb = XLSX.read(buf, { type: "array", cellDates: true });
      const ws = wb.Sheets[wb.SheetNames[0]];
      if (!ws) throw new SourceFormatError("엑셀에 시트가 없습니다.");
      const matrix = XLSX.utils.sheet_to_json(ws, { header: 1, raw: true, defval: null }) as SourceCell[][];
      setProposalResult(parseSourceMatrix(matrix));
    } catch (e) {
      setProposalResult(null);
      setProposalError(
        e instanceof SourceFormatError ? e.message : "엑셀을 읽지 못했습니다. 원천자료와 같은 양식(.xlsx)인지 확인해 주세요.",
      );
    } finally {
      setProposalParsing(false);
    }
  }

  function resetProposalUpload() {
    setProposalResult(null);
    setProposalFileName("");
    setProposalError("");
    if (proposalFileRef.current) proposalFileRef.current.value = "";
  }

  // 수기 제안 계약 추가/편집 (읽힘 실패 대비) — 세션 내만
  const addManualProposal = () =>
    setManualProposals((prev) => [
      ...prev,
      {
        id: `manual-${Date.now()}-${prev.length}`,
        insurer: "",
        productName: "",
        premiumWon: 0,
        coverages: [{ name: "", amountManwon: 0 }],
      },
    ]);

  const patchManual = (id: string, patch: Partial<Contract>) =>
    setManualProposals((prev) => prev.map((c) => (c.id === id ? { ...c, ...patch } : c)));

  const patchManualCoverage = (id: string, idx: number, patch: Partial<ContractCoverage>) =>
    setManualProposals((prev) =>
      prev.map((c) =>
        c.id === id ? { ...c, coverages: c.coverages.map((cov, i) => (i === idx ? { ...cov, ...patch } : cov)) } : c,
      ),
    );

  const addManualCoverage = (id: string) =>
    setManualProposals((prev) =>
      prev.map((c) => (c.id === id ? { ...c, coverages: [...c.coverages, { name: "", amountManwon: 0 }] } : c)),
    );

  const removeManualProposal = (id: string) => setManualProposals((prev) => prev.filter((c) => c.id !== id));

  const renderColumnTag = (contractId: string) =>
    proposalIdSet.has(contractId) ? (
      <Badge tone="gold" solid>
        신규
      </Badge>
    ) : (
      <Badge tone="success">유지</Badge>
    );

  const hasAfterData = planned.length > 0;

  // 045. 엑셀(.xlsx) 내보내기 — 화면 집계값 직렬화만(xlsx dynamic import, 브라우저 내·비저장)
  const handleExport = async () => {
    setExporting(true);
    try {
      await exportCoverageXlsx({
        before: { columns: beforeColumns, totals: beforeTotals, contracts },
        after: { columns: afterColumns, totals: afterTotals, contracts: planned },
        memo,
      });
    } catch {
      // 사용자 취소·환경 문제 — 저장하지 않으며 화면 상태도 유지
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* ── A. 기존 계약 처리 (유지/해지 + 감액) ── */}
      <section className="rounded-[8px] border border-gray-100 bg-white p-4">
        <h2 className="mb-1 text-sm font-bold text-gray-800">4단계 — 컨설팅 후 설계 · 기존 계약 처리</h2>
        <p className="mb-3 text-[11px] text-gray-400">
          계약 단위로 유지/해지를 정하고, 유지 계약은 담보별 감액(예: 사망 1억→5천)과 조정 보험료를 입력할 수 있습니다.
          해지 계약은 후 비분표에서 제외됩니다. 모든 입력은 저장되지 않습니다.
        </p>
        <div className="space-y-3">
          {contracts.map((ct) => {
            const status = statusById[ct.id] ?? "유지";
            const terminated = status === "해지";
            return (
              <div
                key={ct.id}
                className={`rounded-[8px] border p-3 ${terminated ? "border-gray-100 bg-gray-50/60" : "border-gray-200 bg-white"}`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`truncate text-sm font-bold ${terminated ? "text-gray-400 line-through" : "text-gray-800"}`}>
                        {ct.insurer}
                      </span>
                      {terminated && <Badge tone="danger">해지</Badge>}
                    </div>
                    <div className="truncate text-[11px] text-gray-400">{ct.productName || "-"}</div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Button size="sm" variant={status === "유지" ? "primary" : "secondary"} onClick={() => setStatus(ct.id, "유지")}>
                      유지
                    </Button>
                    <Button size="sm" variant={status === "해지" ? "danger" : "secondary"} onClick={() => setStatus(ct.id, "해지")}>
                      해지
                    </Button>
                  </div>
                </div>

                {!terminated && (
                  <div className="mt-3 space-y-2">
                    <div className="flex flex-wrap items-center gap-2 text-[11px] text-gray-500">
                      <span>월/회 보험료</span>
                      <span className="font-semibold text-gray-700">{ct.premiumWon.toLocaleString()}원</span>
                      <span className="text-gray-300">→ 조정</span>
                      <input
                        inputMode="numeric"
                        placeholder={`${ct.premiumWon.toLocaleString()}`}
                        value={premiumOverrideById[ct.id] !== undefined ? String(premiumOverrideById[ct.id]) : ""}
                        onChange={(e) => setPremiumOverride(ct.id, e.target.value)}
                        className="w-28 rounded-[4px] border border-gray-200 px-2 py-1 text-right text-xs"
                        aria-label={`${ct.insurer} 조정 보험료(원)`}
                      />
                      <span className="text-gray-400">원</span>
                    </div>
                    {ct.coverages.length > 0 && (
                      <div className="overflow-x-auto">
                        <table className="w-full min-w-[420px] text-[11px]">
                          <thead>
                            <tr className="text-gray-400">
                              <th className="px-2 py-1 text-left font-medium">담보(보장명)</th>
                              <th className="px-2 py-1 text-right font-medium">현재(만원)</th>
                              <th className="px-2 py-1 text-right font-medium">감액 후(만원)</th>
                            </tr>
                          </thead>
                          <tbody>
                            {ct.coverages.map((cov, i) => {
                              const ov = covOverrides[ct.id]?.[i];
                              return (
                                <tr key={i} className="border-t border-gray-50">
                                  <td className="px-2 py-1 text-gray-700">{cov.name}</td>
                                  <td className="px-2 py-1 text-right text-gray-500">{cov.amountManwon.toLocaleString()}</td>
                                  <td className="px-2 py-1 text-right">
                                    <input
                                      inputMode="numeric"
                                      placeholder={cov.amountManwon.toLocaleString()}
                                      value={ov !== undefined ? String(ov) : ""}
                                      onChange={(e) => setCovOverride(ct.id, i, e.target.value)}
                                      className={`w-20 rounded-[4px] border px-1 py-0.5 text-right ${
                                        ov !== undefined ? "border-amber-300 bg-amber-50" : "border-gray-200"
                                      }`}
                                      aria-label={`${ct.insurer} ${cov.name} 감액 후 가입금액(만원)`}
                                    />
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* ── B. 신규 제안 계약 (042 업로드 흐름 재사용 + 수기 보완) ── */}
      <section className="rounded-[8px] border border-gray-100 bg-white p-4">
        <h2 className="mb-1 text-sm font-bold text-gray-800">5단계 — 신규 제안 계약 입력</h2>
        <p className="mb-3 text-[11px] text-gray-400">
          제안 상품을 원천자료와 같은 양식의 엑셀로 올리거나, 직접 행을 추가해 보완할 수 있습니다. 업로드 파일도 서버로
          전송하지 않고 브라우저 안에서만 처리됩니다.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={proposalFileRef}
            type="file"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(e) => void handleProposalFile(e.target.files?.[0] ?? null)}
            className="text-xs text-gray-500"
          />
          {proposalFileName && (
            <button
              type="button"
              onClick={resetProposalUpload}
              className="rounded-[8px] bg-gray-100 px-3 py-1.5 text-xs font-bold text-gray-600 hover:bg-gray-200"
            >
              업로드 비우기
            </button>
          )}
          <Button size="sm" variant="secondary" onClick={addManualProposal}>
            + 직접 계약 추가
          </Button>
        </div>
        {proposalParsing && <p className="mt-2 text-xs font-semibold text-indigo-600">파싱 중…</p>}
        {proposalError && <p className="mt-2 text-xs font-semibold text-amber-700">{proposalError}</p>}
        {proposalResult && (
          <p className="mt-2 text-xs text-emerald-600">
            {proposalFileName} — 제안 계약 {proposalResult.contracts.length}건 · 담보 행 {proposalResult.totalDataRows}행 인식.
          </p>
        )}
        {proposalResult && proposalResult.warnings.length > 0 && (
          <div className="mt-2 rounded-[8px] bg-amber-50 p-2 text-[11px] text-amber-800">
            <p className="mb-1 font-bold">파싱 경고 {proposalResult.warnings.length}건</p>
            <ul className="list-disc space-y-0.5 pl-4">
              {proposalResult.warnings.map((w, i) => (
                <li key={i}>
                  {w.rowNo > 0 ? `${w.rowNo}행` : "행 미상"}
                  {w.coverageName ? ` · ${w.coverageName}` : ""} — {w.reason}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 수기 제안 계약 편집 */}
        {manualProposals.length > 0 && (
          <div className="mt-3 space-y-3">
            {manualProposals.map((mp) => (
              <div key={mp.id} className="rounded-[8px] border border-gray-200 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <input
                    placeholder="회사명"
                    value={mp.insurer}
                    onChange={(e) => patchManual(mp.id, { insurer: e.target.value })}
                    className="w-28 rounded-[4px] border border-gray-200 px-2 py-1 text-xs"
                    aria-label="제안 계약 회사명"
                  />
                  <input
                    placeholder="상품명"
                    value={mp.productName ?? ""}
                    onChange={(e) => patchManual(mp.id, { productName: e.target.value })}
                    className="w-40 rounded-[4px] border border-gray-200 px-2 py-1 text-xs"
                    aria-label="제안 계약 상품명"
                  />
                  <input
                    inputMode="numeric"
                    placeholder="보험료(원)"
                    value={mp.premiumWon ? String(mp.premiumWon) : ""}
                    onChange={(e) => patchManual(mp.id, { premiumWon: parseManwonInput(e.target.value) })}
                    className="w-28 rounded-[4px] border border-gray-200 px-2 py-1 text-right text-xs"
                    aria-label="제안 계약 보험료(원)"
                  />
                  <button
                    type="button"
                    onClick={() => removeManualProposal(mp.id)}
                    className="ml-auto rounded-[6px] px-2 py-1 text-xs font-bold text-danger-600 hover:bg-danger-50"
                  >
                    삭제
                  </button>
                </div>
                <table className="mt-2 w-full min-w-[420px] text-[11px]">
                  <thead>
                    <tr className="text-gray-400">
                      <th className="px-2 py-1 text-left font-medium">보장명</th>
                      <th className="px-2 py-1 text-right font-medium">가입금액(만원)</th>
                      <th className="px-2 py-1 text-left font-medium">자동 카테고리</th>
                    </tr>
                  </thead>
                  <tbody>
                    {mp.coverages.map((cov, i) => {
                      const mapped = cov.name ? mapCoverageName(cov.name) : null;
                      return (
                        <tr key={i} className="border-t border-gray-50">
                          <td className="px-2 py-1">
                            <input
                              placeholder="예: 암진단금"
                              value={cov.name}
                              onChange={(e) => patchManualCoverage(mp.id, i, { name: e.target.value })}
                              className="w-44 rounded-[4px] border border-gray-200 px-2 py-0.5 text-xs"
                              aria-label="제안 담보 보장명"
                            />
                          </td>
                          <td className="px-2 py-1 text-right">
                            <input
                              inputMode="numeric"
                              value={cov.amountManwon ? String(cov.amountManwon) : ""}
                              onChange={(e) => patchManualCoverage(mp.id, i, { amountManwon: parseManwonInput(e.target.value) })}
                              className="w-24 rounded-[4px] border border-gray-200 px-1 py-0.5 text-right text-xs"
                              aria-label="제안 담보 가입금액(만원)"
                            />
                          </td>
                          <td className="px-2 py-1 text-[11px]">
                            {!cov.name ? (
                              <span className="text-gray-300">-</span>
                            ) : mapped === GENERAL_SURGERY_GROUP ? (
                              <span className="text-emerald-700">일반종수술</span>
                            ) : mapped ? (
                              <span className="text-emerald-700">{CATEGORY_BY_ID[mapped]?.label ?? mapped}</span>
                            ) : (
                              <span className="text-amber-600">미매핑 — 아래 배정</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                <button
                  type="button"
                  onClick={() => addManualCoverage(mp.id)}
                  className="mt-1 text-[11px] font-semibold text-indigo-600 hover:underline"
                >
                  + 담보 행 추가
                </button>
              </div>
            ))}
          </div>
        )}

        {/* 제안 계약 미매핑 보장명 수동 배정 (042 흐름 재사용) */}
        {proposalMappingRows.some((r) => r.categoryId === null) && (
          <div className="mt-3">
            <h3 className="mb-1 text-xs font-bold text-gray-700">
              제안 보장명 매핑 확인
              {proposalUnmapped > 0 && (
                <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold text-amber-700">
                  수동 배정 필요 {proposalUnmapped}건
                </span>
              )}
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[480px] text-xs">
                <thead>
                  <tr className="bg-gray-50 text-gray-500">
                    <th className="px-3 py-2 text-left">보장명</th>
                    <th className="px-3 py-2 text-center">건수</th>
                    <th className="px-3 py-2 text-left">카테고리</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {proposalMappingRows
                    .filter((r) => r.categoryId === null)
                    .map((r) => (
                      <tr key={r.key} className={!proposalAssignments[r.key] ? "bg-amber-50/60" : ""}>
                        <td className="px-3 py-1.5 font-semibold text-gray-800">{r.name}</td>
                        <td className="px-3 py-1.5 text-center text-gray-500">{r.count}</td>
                        <td className="px-3 py-1.5">
                          <select
                            value={proposalAssignments[r.key] ?? ""}
                            onChange={(e) =>
                              setProposalAssignments((prev) => {
                                const next = { ...prev };
                                if (e.target.value) next[r.key] = e.target.value;
                                else delete next[r.key];
                                return next;
                              })
                            }
                            className="w-full max-w-[240px] rounded-[6px] border border-amber-300 bg-white p-1 text-xs"
                          >
                            <option value="">미배정 (unmapped 유지)</option>
                            {targets.map((t) => (
                              <option key={t.value} value={t.value}>
                                {t.value === MANUAL_EXCLUDE ? t.label : `→ ${t.label}`}
                              </option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      {/* ── C. 후 비분표 ── */}
      {hasAfterData ? (
        <section className="overflow-hidden rounded-[8px] border border-gray-100 bg-white">
          <div className="border-b border-gray-100 px-4 py-3">
            <h2 className="text-sm font-bold text-gray-800">6단계 — 비교분석 후 보장 (비분표)</h2>
            <p className="mt-0.5 text-[11px] text-gray-400">
              유지 계약(감액 반영)과 신규 제안 계약을 합쳐 전(前) 비분표와 같은 36행 양식으로 계산했습니다. 사망 분해·
              일반종수술 제안(✎)은 자동 산출값이며 제안 셀은 수정할 수 있습니다. 금액 단위: 만원(보험료 합계만 원).
            </p>
          </div>
          <CoverageTableView
            columns={afterColumns}
            totals={afterTotals}
            contracts={planned}
            onCellEdit={setAfterCellEdit}
            renderColumnTag={renderColumnTag}
          />
          {afterTableRaw.unmapped.length > 0 && (
            <p className="border-t border-gray-100 px-4 py-2 text-[11px] text-amber-700">
              미배정 담보 {afterTableRaw.unmapped.length}건은 후 비분표에 반영되지 않았습니다 — 위 매핑에서 배정하거나
              제외해 주세요.
            </p>
          )}
        </section>
      ) : (
        <section className="rounded-[8px] border border-dashed border-gray-300 bg-gray-50 p-4 text-center text-xs text-gray-400">
          유지할 계약이 없고 신규 제안도 없습니다 — 위에서 유지 계약을 두거나 제안 계약을 추가하면 후 비분표가 표시됩니다.
        </section>
      )}

      {/* ── BOHUMFIT-044/045: 최종비교분석표 + 엑셀 다운로드 (후 비분표가 있을 때만) ── */}
      {hasAfterData && (
        <FinalComparison
          beforeTotals={beforeTotals}
          afterTotals={afterTotals}
          memo={memo}
          onMemoChange={setMemo}
          onExport={handleExport}
          exporting={exporting}
        />
      )}
    </div>
  );
}
