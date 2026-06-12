// BOHUMFIT-044 디자인 시스템 — DataTable (헤더 네이비 · 줄무늬 · 가로 스크롤)
// 숫자는 tabular-nums 고정. 첫 열 고정(stickyFirst)은 비분표류 넓은 표용.
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
  /** 행 줄무늬 (기본 true) */
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

export default function DataTable<T>({
  columns,
  rows,
  rowKey,
  minWidth = 640,
  stickyFirst = false,
  striped = true,
  footer,
  empty,
  rowClassName,
}: DataTableProps<T>) {
  if (rows.length === 0 && empty) {
    return <div className="rounded-card border border-line bg-white p-6">{empty}</div>;
  }
  return (
    <div className="overflow-x-auto rounded-card border border-line bg-white shadow-card">
      <table className="w-full border-collapse text-table tabular-nums" style={{ minWidth }}>
        <thead>
          <tr className="bg-navy-800 text-white">
            {columns.map((c, i) => (
              <th
                key={c.key}
                scope="col"
                className={`px-3 py-2.5 font-semibold ${ALIGN_CLS[c.align ?? "left"]} ${
                  stickyFirst && i === 0 ? "sticky left-0 z-10 bg-navy-800" : ""
                }`}
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
              className={`border-t border-line/70 ${
                striped && ri % 2 === 1 ? "bg-navy-50/40" : "bg-white"
              } ${rowClassName ? rowClassName(row, ri) : ""}`}
            >
              {columns.map((c, ci) => (
                <td
                  key={c.key}
                  className={`px-3 py-2 ${ALIGN_CLS[c.align ?? "left"]} ${
                    stickyFirst && ci === 0 ? "sticky left-0 z-10 bg-inherit font-semibold text-navy-900" : ""
                  }`}
                >
                  {c.render(row, ri)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
        {footer && <tfoot className="border-t-2 border-navy-800 bg-navy-50/60 font-bold">{footer}</tfoot>}
      </table>
    </div>
  );
}
