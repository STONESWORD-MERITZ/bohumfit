// BOHUMFIT-045 디자인 시스템 v2(Mercury) — DataTable. API 불변, 내부 스타일만 교체.
// 네이비 헤더 제거 → 캔버스색 헤더 + 그레이 캡션. 행 구분은 헤어라인만(줄무늬 제거),
// 호버 행만 옅은 하이라이트. 숫자 tabular-nums 우정렬.
import { type ReactNode } from "react";

export type DataTableAlign = "left" | "center" | "right";

export interface DataTableColumn<T> {
  key: string;
  header: ReactNode;
  align?: DataTableAlign;
  /** 셀 렌더러 — 행 데이터를 받아 내용 반환 */
  render: (row: T, rowIndex: number) => ReactNode;
  /** 열 최소 너비 (px) */
  minWidth?: number;
}

export interface DataTableProps<T> {
  columns: ReadonlyArray<DataTableColumn<T>>;
  rows: ReadonlyArray<T>;
  rowKey: (row: T, rowIndex: number) => string;
  /** 표 전체 최소 너비(px) — 가로 스크롤 기준 (기본 640) */
  minWidth?: number;
  /** 첫 열 고정 (가로 스크롤 시) */
  stickyFirst?: boolean;
  /** (v2: Mercury 문법으로 줄무늬 미사용 — API 호환 위해 prop 유지, 시각 효과 없음) */
  striped?: boolean;
  /** 합계 등 푸터 행 — <tr> 반환 */
  footer?: ReactNode;
  /** rows 가 비었을 때 표시할 내용 */
  empty?: ReactNode;
  /** 행 강조 클래스 (선택) */
  rowClassName?: (row: T, rowIndex: number) => string;
}

const ALIGN_CLS: Record<DataTableAlign, string> = {
  left: "text-left",
  center: "text-center",
  right: "text-right",
};

// striped prop 은 v2(Mercury)에서 시각 효과가 없다 — API 호환을 위해 타입에는 유지하고
// 구조분해에서 제외해 무시한다(이 줄의 의도 변경 시 045 handoff 참조).
export default function DataTable<T>({
  columns,
  rows,
  rowKey,
  minWidth = 640,
  stickyFirst = false,
  footer,
  empty,
  rowClassName,
}: DataTableProps<T>) {
  if (rows.length === 0 && empty) {
    return <div className="rounded-card border border-line bg-white p-6">{empty}</div>;
  }
  return (
    <div className="overflow-x-auto rounded-card border border-line bg-white">
      <table className="w-full border-collapse text-table tabular-nums" style={{ minWidth }}>
        <thead>
          <tr className="bg-canvas">
            {columns.map((c, i) => (
              <th
                key={c.key}
                scope="col"
                className={`border-b border-line-strong px-3 py-2.5 text-caption font-semibold tracking-wide text-ink-soft ${
                  ALIGN_CLS[c.align ?? "left"]
                } ${stickyFirst && i === 0 ? "sticky left-0 z-10 bg-canvas" : ""}`}
                style={c.minWidth ? { minWidth: c.minWidth } : undefined}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr
              key={rowKey(row, ri)}
              className={`group border-b border-line bg-white transition-colors last:border-b-0 hover:bg-ink-50/60 ${
                rowClassName ? rowClassName(row, ri) : ""
              }`}
            >
              {columns.map((c, ci) => (
                <td
                  key={c.key}
                  className={`px-3 py-2.5 text-ink ${ALIGN_CLS[c.align ?? "left"]} ${
                    stickyFirst && ci === 0
                      ? "sticky left-0 z-10 bg-white font-semibold text-ink-900 group-hover:bg-ink-50/60"
                      : ""
                  }`}
                >
                  {c.render(row, ri)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
        {footer && <tfoot className="border-t border-line-strong bg-white font-semibold">{footer}</tfoot>}
      </table>
    </div>
  );
}
