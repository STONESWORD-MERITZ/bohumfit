// BOHUMFIT-042: /coverage 보장분석 페이지 — 업로드 → 매핑 확인 → 전(前) 비분표.
// - 원천자료 엑셀은 SheetJS 로 브라우저 안에서만 파싱한다(서버 전송·저장 없음).
// - 사망분해·종수술 자동셋팅·합계는 BOHUMFIT-041 lib 결과 그대로 — 재구현 금지.
// - 수동 배정/제안값 수정은 이 화면(세션) 안에서만 유지된다.
import { useMemo, useRef, useState } from "react";
import {
  CATEGORY_BY_ID,
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
import CoverageTableView from "../components/coverage/CoverageTableView";
import CoverageAfterSection from "../components/coverage/CoverageAfterSection";

const DISCLAIMER =
  "본 비교분석표는 업로드한 원천자료를 기준으로 정리한 참고용 자료입니다. 실제 보장 내용·보험금 지급 여부는 " +
  "각 보험사 약관과 증권을 따르며, 본 화면은 보험 모집·중개·상품추천·가입권유를 목적으로 하지 않습니다.";

function parseManwonInput(s: string): number {
  const n = parseInt((s || "").replace(/[^\d]/g, "") || "0", 10);
  return Math.max(0, n);
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
          <CoverageTableView
            columns={displayColumns}
            totals={totals}
            contracts={effectiveContracts}
            onCellEdit={setCellEdit}
          />
          {table.unmapped.length > 0 && (
            <p className="border-t border-gray-100 px-4 py-2 text-[11px] text-amber-700">
              미배정 담보 {table.unmapped.length}건은 비분표에 반영되지 않았습니다 — 2단계에서 배정하거나 제외를
              선택해 주세요.
            </p>
          )}
        </section>
      )}

      {/* BOHUMFIT-043/044: 컨설팅 후 설계 + 후 비분표 + 최종비교분석표 (전 비분표가 준비된 뒤에만 노출) */}
      {result && displayColumns.length > 0 && (
        <CoverageAfterSection contracts={effectiveContracts} beforeTotals={totals} />
      )}

      <p className="text-[11px] leading-relaxed text-gray-400 break-keep">{DISCLAIMER}</p>
    </div>
  );
}
