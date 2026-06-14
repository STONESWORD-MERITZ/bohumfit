// BOHUMFIT-043: 비교분석표(비분표) 표시 컴포넌트 — 전(前)/후(後) 공용.
// - BOHUMFIT-042 전 비분표의 표 마크업을 그대로 추출해 전/후가 동일 레이아웃을 쓰도록 한다.
// - 산식·자동셋팅(사망분해·종수술)·합계는 모두 041 lib 결과(props)를 그대로 표시한다 — 재계산 없음.
// - suggested(종수술 1~4종 제안) 셀만 수정 가능. onCellEdit 미전달 시 읽기 전용.
import { type ReactNode } from "react";
import {
  COVERAGE_CATEGORIES,
  type Contract,
  type ContractColumn,
} from "../../lib/coverageMapping";

const SURGERY_EDITABLE_IDS = [
  "general_surgery_type1",
  "general_surgery_type2",
  "general_surgery_type3",
  "general_surgery_type4",
] as const;

function won(v: number): string {
  return v > 0 ? v.toLocaleString() : "-";
}

/** 납만기 표시: 납입기간(년) 우선, 없으면 보험종기(9999 = 종신) */
function payEndLabel(payYears?: string, endDate?: string): string {
  if (payYears && payYears !== "00") return `${parseInt(payYears, 10) || payYears}년`;
  if (endDate?.startsWith("9999")) return "종신";
  return endDate || "-";
}

export interface CoverageTableViewProps {
  /** 표시할 계약 열 (제안값 수정이 이미 반영된 상태로 전달) */
  columns: ContractColumn[];
  /** 합계 (041 sumColumns 결과) */
  totals: Record<string, number | boolean>;
  /** 납만기(보험종기) 조회용 계약 목록 — columns 와 contractId 로 매칭 */
  contracts: readonly Contract[];
  /** 제안 셀 수정 콜백 — 미전달 시 종수술 제안 셀도 읽기 전용 */
  onCellEdit?: (contractId: string, catId: string, raw: string) => void;
  /** 열 헤더(상품명 아래)에 붙일 태그 — 후 비분표의 유지/신규 배지 등 */
  renderColumnTag?: (contractId: string) => ReactNode;
  /** 표 최소 너비 (계약 수에 따라 조정 가능) */
  minWidthClass?: string;
}

export default function CoverageTableView({
  columns,
  totals,
  contracts,
  onCellEdit,
  renderColumnTag,
  minWidthClass = "min-w-[920px]",
}: CoverageTableViewProps) {
  return (
    <div className="overflow-x-auto">
      <table className={`w-full ${minWidthClass} border-collapse text-xs`}>
        <thead>
          <tr className="bg-ink-800 text-white">
            <th className="sticky left-0 z-10 bg-ink-800 px-3 py-2 text-left">구분</th>
            {columns.map((c) => (
              <th key={c.contractId} className="min-w-[96px] px-2 py-2 text-center font-bold">
                <div className="truncate">{c.insurer}</div>
                <div className="max-w-[140px] truncate text-[10px] font-medium text-gray-200">
                  {c.productName || "-"}
                </div>
                {renderColumnTag && <div className="mt-1 flex justify-center">{renderColumnTag(c.contractId)}</div>}
              </th>
            ))}
            <th className="min-w-[90px] bg-ink-900 px-2 py-2 text-center">합계</th>
          </tr>
          <tr className="bg-gray-50 text-gray-500">
            <th className="sticky left-0 z-10 bg-gray-50 px-3 py-1.5 text-left font-semibold">가입일</th>
            {columns.map((c) => (
              <th key={c.contractId} className="px-2 py-1.5 text-center font-medium">
                {c.startDate || "-"}
              </th>
            ))}
            <th className="px-2 py-1.5 text-center">-</th>
          </tr>
          <tr className="border-b border-gray-200 bg-gray-50 text-gray-500">
            <th className="sticky left-0 z-10 bg-gray-50 px-3 py-1.5 text-left font-semibold">납만기</th>
            {columns.map((c) => (
              <th key={c.contractId} className="px-2 py-1.5 text-center font-medium">
                {payEndLabel(c.payYears, contracts.find((ct) => ct.id === c.contractId)?.endDate)}
              </th>
            ))}
            <th className="px-2 py-1.5 text-center">-</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {COVERAGE_CATEGORIES.map((cat) => (
            <tr key={cat.id} className={cat.kind === "premium" ? "border-t-2 border-ink-800 bg-gray-50" : ""}>
              <td className="sticky left-0 z-10 bg-white px-3 py-1.5 font-semibold text-gray-700">{cat.label}</td>
              {columns.map((col) => {
                const v = col.cells[cat.id];
                const editable =
                  !!onCellEdit &&
                  col.suggested[cat.id] &&
                  (SURGERY_EDITABLE_IDS as readonly string[]).includes(cat.id);
                if (cat.kind === "flag") {
                  return (
                    <td key={col.contractId} className="px-2 py-1.5 text-center">
                      {v === true ? (
                        <span className="font-bold text-emerald-600">Y</span>
                      ) : (
                        <span className="text-gray-300">-</span>
                      )}
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
                          onChange={(e) => onCellEdit?.(col.contractId, cat.id, e.target.value)}
                          className="w-16 rounded-[4px] border border-amber-200 bg-white px-1 py-0.5 text-right text-xs"
                          aria-label={`${col.insurer} ${cat.label} 제안값 수정`}
                        />
                      </span>
                    ) : (
                      <span className={(v as number) > 0 ? "text-gray-800" : "text-gray-300"}>{won(v as number)}</span>
                    )}
                  </td>
                );
              })}
              <td className="bg-gray-50 px-2 py-1.5 text-right font-bold text-ink-900">
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
  );
}
