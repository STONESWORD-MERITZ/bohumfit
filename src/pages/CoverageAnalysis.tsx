// BOHUMFIT-042: /coverage 보장분석 페이지 — 업로드 → 매핑 확인 → 전(前) 비분표.
// - 원천자료 엑셀은 SheetJS 로 브라우저 안에서만 파싱한다(서버 전송·저장 없음).
// - 사망분해·종수술 자동셋팅·합계는 BOHUMFIT-041 lib 결과 그대로 — 재구현 금지.
// - 수동 배정/제안값 수정은 이 화면(세션) 안에서만 유지된다.
import { useMemo, useRef, useState } from "react";
import {
  CATEGORY_BY_ID,
  COVERAGE_CATEGORIES,
  GENERAL_SURGERY_GROUP,
  buildCoverageTable,
  mapCoverageName,
  normalizeCoverageName,
  sumColumns,
  type Contract,
  type ContractColumn,
} from "../lib/coverageMapping";
import {
  MANUAL_EXCLUDE,
  SourceFormatError,
  applyManualAssignments,
  listAssignableTargets,
  parseSourceMatrix,
  type SourceCell,
  type SourceParseResult,
} from "../lib/coverageParse";

const SURGERY_EDITABLE_IDS = [
  "general_surgery_type1",
  "general_surgery_type2",
  "general_surgery_type3",
  "general_surgery_type4",
] as const;

const DISCLAIMER =
  "본 비교분석표는 업로드한 원천자료를 기준으로 정리한 참고용 자료입니다. 실제 보장 내용·보험금 지급 여부는 " +
  "각 보험사 약관과 증권을 따르며, 본 화면은 보험 모집·중개·상품추천·가입권유를 목적으로 하지 않습니다.";

function won(v: number): string {
  return v > 0 ? v.toLocaleString() : "-";
}

function parseManwonInput(s: string): number {
  const n = parseInt((s || "").replace(/[^\d]/g, "") || "0", 10);
  return Math.max(0, n);
}

/** 납만기 표시: 납입기간(년) 우선, 없으면 보험종기(9999 = 종신) */
function payEndLabel(payYears?: string, endDate?: string): string {
  if (payYears && payYears !== "00") return `${parseInt(payYears, 10) || payYears}년`;
  if (endDate?.startsWith("9999")) return "종신";
  return endDate || "-";
}

export default function CoverageAnalysis() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState("");
  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState("");
  const [result, setResult] = useState<SourceParseResult | null>(null);
  // 2단계 수동 배정 (normalizeCoverageName(보장명) → 카테고리 id / 종수술 그룹 / 제외) — 세션 내만 유지
  const [assignments, setAssignments] = useState<Record<string, string>>({});
  // 3단계 종수술 제안값 셀 수정 (contractId → categoryId → 만원) — 세션 내만 유지
  const [cellEdits, setCellEdits] = useState<Record<string, Record<string, number>>>({});

  const reset = () => {
    setFileName("");
    setParseError("");
    setResult(null);
    setAssignments({});
    setCellEdits({});
    if (fileRef.current) fileRef.current.value = "";
  };

  async function handleFile(file: File | null) {
    if (!file) return;
    reset();
    setFileName(file.name);
    setParsing(true);
    try {
      const buf = await file.arrayBuffer();
      const XLSX = await import("xlsx"); // 지연 로딩 — 초기 번들 영향 최소화
      const wb = XLSX.read(buf, { type: "array", cellDates: true });
      const ws = wb.Sheets[wb.SheetNames[0]];
      if (!ws) throw new SourceFormatError("엑셀에 시트가 없습니다.");
      const matrix = XLSX.utils.sheet_to_json(ws, {
        header: 1,
        raw: true,
        defval: null,
      }) as SourceCell[][];
      setResult(parseSourceMatrix(matrix));
    } catch (e) {
      setResult(null);
      setParseError(
        e instanceof SourceFormatError
          ? e.message
          : "엑셀을 읽지 못했습니다. 원천자료 양식(.xlsx)인지 확인해 주세요.",
      );
    } finally {
      setParsing(false);
    }
  }

  // ── 2단계: 매핑 그리드 데이터 (원본 계약 기준) ────────────────────────────
  const mappingRows = useMemo(() => {
    if (!result) return [];
    const seen = new Map<string, { name: string; categoryId: string | null; count: number; totalManwon: number }>();
    for (const ct of result.contracts) {
      for (const cov of ct.coverages) {
        const key = normalizeCoverageName(cov.name);
        const cur = seen.get(key);
        if (cur) {
          cur.count += 1;
          cur.totalManwon += cov.amountManwon;
        } else {
          seen.set(key, {
            name: cov.name,
            categoryId: mapCoverageName(cov.name),
            count: 1,
            totalManwon: cov.amountManwon,
          });
        }
      }
    }
    return [...seen.entries()].map(([key, v]) => ({ key, ...v }));
  }, [result]);

  const unmappedCount = mappingRows.filter((r) => r.categoryId === null && !assignments[r.key]).length;
  const targets = useMemo(() => listAssignableTargets(), []);

  // ── 3단계: 전 비분표 (041 lib — 산식 재구현 없음) ─────────────────────────
  const effectiveContracts: Contract[] = useMemo(
    () => (result ? applyManualAssignments(result.contracts, assignments) : []),
    [result, assignments],
  );
  const table = useMemo(() => buildCoverageTable(effectiveContracts), [effectiveContracts]);

  // 종수술 제안값 셀 수정 반영 → 합계도 lib(sumColumns)로 재계산
  const displayColumns: ContractColumn[] = useMemo(
    () =>
      table.columns.map((col) => {
        const edits = cellEdits[col.contractId];
        if (!edits) return col;
        const cells = { ...col.cells };
        for (const [catId, v] of Object.entries(edits)) {
          if (col.suggested[catId]) cells[catId] = v; // 제안(suggested) 셀만 수정 허용
        }
        return { ...col, cells };
      }),
    [table, cellEdits],
  );
  const totals = useMemo(() => sumColumns(displayColumns), [displayColumns]);

  const setCellEdit = (contractId: string, catId: string, raw: string) => {
    setCellEdits((prev) => ({
      ...prev,
      [contractId]: { ...prev[contractId], [catId]: parseManwonInput(raw) },
    }));
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-extrabold text-gray-950">보장분석 — 비교분석표(전)</h1>
        <p className="mt-1 text-sm text-gray-600 break-keep">
          원천자료 엑셀을 올리면 계약·담보를 표준 비교분석표 36행으로 정리합니다. 업로드한 파일은{" "}
          <b>서버로 전송하지 않으며 브라우저 안에서만 처리</b>되고, 화면을 벗어나면 사라집니다(저장 없음).
        </p>
      </div>

      {/* ── 1단계: 업로드 ── */}
      <section className="rounded-[8px] border border-gray-100 bg-white p-4">
        <h2 className="mb-2 text-sm font-bold text-gray-800">1단계 — 원천자료 업로드</h2>
        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={fileRef}
            type="file"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(e) => void handleFile(e.target.files?.[0] ?? null)}
            className="text-xs text-gray-500"
          />
          {fileName && (
            <button
              type="button"
              onClick={reset}
              className="rounded-[8px] bg-gray-100 px-3 py-1.5 text-xs font-bold text-gray-600 hover:bg-gray-200"
            >
              다시 업로드
            </button>
          )}
        </div>
        <p className="mt-2 text-[11px] text-gray-400">
          헤더 2행(계약정보/담보정보) 양식의 .xlsx — 회사명·상품명 병합셀은 자동으로 계약 단위로 묶습니다.
          고객 계약정보는 민감정보이므로 이 화면에서만 사용하고 저장하지 않습니다.
        </p>
        {parsing && <p className="mt-2 text-xs font-semibold text-indigo-600">파싱 중…</p>}
        {parseError && <p className="mt-2 text-xs font-semibold text-amber-700">{parseError}</p>}
        {result && (
          <p className="mt-2 text-xs text-emerald-600">
            {fileName} — 계약 {result.contracts.length}건 · 담보 행 {result.totalDataRows}행 인식 완료.
          </p>
        )}
      </section>

      {/* 파싱 경고 — 실패 행도 버리지 않고 표시 */}
      {result && result.warnings.length > 0 && (
        <section className="rounded-[8px] bg-amber-50 p-3 text-xs text-amber-800">
          <p className="mb-1 font-bold">파싱 경고 {result.warnings.length}건 — 원천자료를 확인해 주세요.</p>
          <ul className="list-disc space-y-0.5 pl-4">
            {result.warnings.map((w, i) => (
              <li key={i}>
                {w.rowNo > 0 ? `${w.rowNo}행` : "행 미상"}
                {w.insurer ? ` · ${w.insurer}` : ""}
                {w.coverageName ? ` · ${w.coverageName}` : ""} — {w.reason}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* ── 2단계: 매핑 확인 ── */}
      {result && (
        <section className="rounded-[8px] border border-gray-100 bg-white p-4">
          <h2 className="mb-1 text-sm font-bold text-gray-800">
            2단계 — 보장명 매핑 확인
            {unmappedCount > 0 && (
              <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-bold text-amber-700">
                수동 배정 필요 {unmappedCount}건
              </span>
            )}
          </h2>
          <p className="mb-3 text-[11px] text-gray-400">
            자동 매핑되지 않은 보장명은 드롭다운으로 카테고리에 배정하거나 제외할 수 있습니다. 배정 결과는
            저장되지 않고 이 화면에서만 사용됩니다.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-xs">
              <thead>
                <tr className="bg-gray-50 text-gray-500">
                  <th className="px-3 py-2 text-left">보장명</th>
                  <th className="px-3 py-2 text-center">건수</th>
                  <th className="px-3 py-2 text-right">가입금액 합(만원)</th>
                  <th className="px-3 py-2 text-left">카테고리</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {mappingRows.map((r) => (
                  <tr key={r.key} className={r.categoryId === null && !assignments[r.key] ? "bg-amber-50/60" : ""}>
                    <td className="px-3 py-1.5 font-semibold text-gray-800">{r.name}</td>
                    <td className="px-3 py-1.5 text-center text-gray-500">{r.count}</td>
                    <td className="px-3 py-1.5 text-right text-gray-500">{r.totalManwon.toLocaleString()}</td>
                    <td className="px-3 py-1.5">
                      {r.categoryId !== null ? (
                        <span className="font-semibold text-emerald-700">
                          {r.categoryId === GENERAL_SURGERY_GROUP
                            ? "일반종수술 (1~5종 자동셋팅)"
                            : CATEGORY_BY_ID[r.categoryId]?.label ?? r.categoryId}
                        </span>
                      ) : (
                        <select
                          value={assignments[r.key] ?? ""}
                          onChange={(e) =>
                            setAssignments((prev) => {
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
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* ── 3단계: 전 비분표 ── */}
      {result && displayColumns.length > 0 && (
        <section className="overflow-hidden rounded-[8px] border border-gray-100 bg-white">
          <div className="border-b border-gray-100 px-4 py-3">
            <h2 className="text-sm font-bold text-gray-800">3단계 — 비교분석 전 보장 (비분표)</h2>
            <p className="mt-0.5 text-[11px] text-gray-400">
              사망 분해·일반종수술 1~4종 제안(✎ 표시 셀)은 자동 산출값입니다. 제안 셀은 수정할 수 있으며
              합계에 즉시 반영됩니다. 금액 단위: 만원(보험료 합계만 원).
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[920px] border-collapse text-xs">
              <thead>
                <tr className="bg-[#1F3A5F] text-white">
                  <th className="sticky left-0 z-10 bg-[#1F3A5F] px-3 py-2 text-left">구분</th>
                  {displayColumns.map((c) => (
                    <th key={c.contractId} className="min-w-[96px] px-2 py-2 text-center font-bold">
                      <div className="truncate">{c.insurer}</div>
                      <div className="max-w-[140px] truncate text-[10px] font-medium text-gray-200">
                        {c.productName || "-"}
                      </div>
                    </th>
                  ))}
                  <th className="min-w-[90px] bg-[#14253D] px-2 py-2 text-center">합계</th>
                </tr>
                <tr className="bg-gray-50 text-gray-500">
                  <th className="sticky left-0 z-10 bg-gray-50 px-3 py-1.5 text-left font-semibold">가입일</th>
                  {displayColumns.map((c) => (
                    <th key={c.contractId} className="px-2 py-1.5 text-center font-medium">
                      {c.startDate || "-"}
                    </th>
                  ))}
                  <th className="px-2 py-1.5 text-center">-</th>
                </tr>
                <tr className="border-b border-gray-200 bg-gray-50 text-gray-500">
                  <th className="sticky left-0 z-10 bg-gray-50 px-3 py-1.5 text-left font-semibold">납만기</th>
                  {displayColumns.map((c) => (
                    <th key={c.contractId} className="px-2 py-1.5 text-center font-medium">
                      {payEndLabel(c.payYears, effectiveContracts.find((ct) => ct.id === c.contractId)?.endDate)}
                    </th>
                  ))}
                  <th className="px-2 py-1.5 text-center">-</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {COVERAGE_CATEGORIES.map((cat) => (
                  <tr key={cat.id} className={cat.kind === "premium" ? "border-t-2 border-[#1F3A5F] bg-gray-50" : ""}>
                    <td className="sticky left-0 z-10 bg-white px-3 py-1.5 font-semibold text-gray-700">
                      {cat.label}
                    </td>
                    {displayColumns.map((col) => {
                      const v = col.cells[cat.id];
                      const editable =
                        col.suggested[cat.id] &&
                        (SURGERY_EDITABLE_IDS as readonly string[]).includes(cat.id);
                      if (cat.kind === "flag") {
                        return (
                          <td key={col.contractId} className="px-2 py-1.5 text-center">
                            {v === true ? <span className="font-bold text-emerald-600">Y</span> : <span className="text-gray-300">-</span>}
                          </td>
                        );
                      }
                      if (cat.kind === "premium") {
                        return (
                          <td key={col.contractId} className="px-2 py-1.5 text-right font-bold text-gray-800">
                            {(v as number) > 0 ? `${(v as number).toLocaleString()}원` : "-"}
                          </td>
                        );
                      }
                      return (
                        <td key={col.contractId} className={`px-2 py-1.5 text-right ${editable ? "bg-amber-50" : ""}`}>
                          {editable ? (
                            <span className="inline-flex items-center gap-1">
                              <span className="text-[10px] text-amber-500">✎</span>
                              <input
                                inputMode="numeric"
                                value={String(v as number)}
                                onChange={(e) => setCellEdit(col.contractId, cat.id, e.target.value)}
                                className="w-16 rounded-[4px] border border-amber-200 bg-white px-1 py-0.5 text-right text-xs"
                                aria-label={`${col.insurer} ${cat.label} 제안값 수정`}
                              />
                            </span>
                          ) : (
                            <span className={(v as number) > 0 ? "text-gray-800" : "text-gray-300"}>
                              {won(v as number)}
                            </span>
                          )}
                        </td>
                      );
                    })}
                    <td className="bg-gray-50 px-2 py-1.5 text-right font-bold text-[#1F3A5F]">
                      {cat.kind === "flag"
                        ? totals[cat.id] === true
                          ? "Y"
                          : "-"
                        : cat.kind === "premium"
                          ? `${(totals[cat.id] as number).toLocaleString()}원`
                          : won(totals[cat.id] as number)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {table.unmapped.length > 0 && (
            <p className="border-t border-gray-100 px-4 py-2 text-[11px] text-amber-700">
              미배정 담보 {table.unmapped.length}건은 비분표에 반영되지 않았습니다 — 2단계에서 배정하거나 제외를
              선택해 주세요.
            </p>
          )}
        </section>
      )}

      {/* 043 예고 — 기능 없음 */}
      {result && (
        <section className="rounded-[8px] border border-dashed border-gray-300 bg-gray-50 p-4 text-center">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-gray-400">Next</p>
          <p className="mt-1 text-sm font-bold text-gray-600">다음 단계: 해지/유지·신규 제안 설계 (준비 중)</p>
          <p className="mt-1 text-[11px] text-gray-400">
            유지/해지 선택, 담보별 감액, 신규 제안 계약을 반영한 후(後) 비분표 비교 기능이 이어집니다.
          </p>
        </section>
      )}

      <p className="text-[11px] leading-relaxed text-gray-400 break-keep">{DISCLAIMER}</p>
    </div>
  );
}
