// BOHUMFIT-044/045: 최종비교분석표 — 전/후 요약 비교 (표시 전용) + 엑셀 다운로드 트리거.
// - 값은 043에서 계산된 041 집계값(beforeTotals/afterTotals)을 그대로 매핑·표시한다 — 재계산 금지.
// - 행 정의(FINAL_ROWS/KEY_DISEASES)·매핑 헬퍼는 coverageExport.ts(단일 소스)에서 import → 엑셀과 양식 일치.
// - 특이사항 메모·엑셀 트리거는 상위(CoverageAfterSection)가 소유한다(엑셀에 memo 포함 위해 prop 화).
import Card from "../ui/Card";
import Badge from "../ui/Badge";
import Button from "../ui/Button";
import {
  FINAL_ROWS,
  KEY_DISEASES,
  dir,
  flagOf,
  numOf,
  type Totals,
} from "../../lib/coverageExport";

function fmtAmount(v: number): string {
  return v > 0 ? v.toLocaleString() : "-";
}
function fmtPremium(v: number): string {
  return v > 0 ? `${v.toLocaleString()}원` : "-";
}

function DirArrow({ d, premium = false }: { d: -1 | 0 | 1; premium?: boolean }) {
  // 보장은 증가=강조(페리윙클), 감소=경고. 보험료는 중립(증감 자체가 좋고 나쁨이 아님).
  if (d === 0) return <span className="text-ink-400">—</span>;
  if (premium) return <span className="text-ink-500">{d === 1 ? "▲" : "▼"}</span>;
  return d === 1 ? (
    <span className="font-bold text-accent-700">▲</span>
  ) : (
    <span className="font-bold text-danger-600">▼</span>
  );
}

function rowToneClass(d: -1 | 0 | 1, premium: boolean): string {
  if (d === 0 || premium) return "";
  return d === 1 ? "bg-accent-50" : "bg-danger-50";
}

export interface FinalComparisonProps {
  beforeTotals: Totals;
  afterTotals: Totals;
  /** 특이사항 메모 (상위 소유 — 엑셀 내보내기에 포함) */
  memo: string;
  onMemoChange: (v: string) => void;
  /** 엑셀(.xlsx) 다운로드 트리거 */
  onExport: () => void;
  exporting?: boolean;
}

export default function FinalComparison({
  beforeTotals,
  afterTotals,
  memo,
  onMemoChange,
  onExport,
  exporting = false,
}: FinalComparisonProps) {
  return (
    <Card
      title="7단계 — 최종비교분석표"
      subtitle="전 비분표와 후 비분표(유지·감액·신규 반영)의 041 집계값을 그대로 비교합니다. 재계산 없음 · 금액 단위: 만원(보험료만 원)."
      flush
    >
      <div className="grid gap-0 lg:grid-cols-3">
        {/* A. 주요보장 전/후 비교 (좌측 2/3) */}
        <div className="lg:col-span-2 lg:border-r lg:border-line">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[420px] border-collapse text-xs">
              <thead>
                <tr className="bg-ink-900 text-white">
                  <th className="px-3 py-2 text-right font-bold">리모델링 전</th>
                  <th className="px-3 py-2 text-center font-bold">주요보장</th>
                  <th className="px-3 py-2 text-right font-bold">리모델링 후</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {FINAL_ROWS.map((row) => {
                  const premium = row.kind === "premium";
                  if (row.kind === "flag") {
                    const b = flagOf(beforeTotals, row.ids);
                    const a = flagOf(afterTotals, row.ids);
                    const d: -1 | 0 | 1 = a === b ? 0 : a ? 1 : -1;
                    return (
                      <tr key={row.label} className={rowToneClass(d, false)}>
                        <td className="px-3 py-1.5 text-right text-ink-700">{b ? "Y" : "–"}</td>
                        <td className="px-3 py-1.5 text-center font-semibold text-ink-800">{row.label}</td>
                        <td className="px-3 py-1.5 text-right">
                          <span className="inline-flex items-center gap-1">
                            <DirArrow d={d} />
                            <span className={a ? "font-bold text-ink-900" : "text-ink-400"}>{a ? "Y" : "–"}</span>
                          </span>
                        </td>
                      </tr>
                    );
                  }
                  if (row.kind === "none") {
                    return (
                      <tr key={row.label}>
                        <td className="px-3 py-1.5 text-right text-ink-300">-</td>
                        <td className="px-3 py-1.5 text-center font-semibold text-ink-700">
                          {row.label}
                          {row.note && <span className="ml-1 text-[10px] font-normal text-ink-400">({row.note})</span>}
                        </td>
                        <td className="px-3 py-1.5 text-right text-ink-300">-</td>
                      </tr>
                    );
                  }
                  const b = numOf(beforeTotals, row.ids);
                  const a = numOf(afterTotals, row.ids);
                  const d = dir(b, a);
                  const fmt = premium ? fmtPremium : fmtAmount;
                  return (
                    <tr key={row.label} className={rowToneClass(d, premium) + (premium ? " border-t-2 border-ink-900 bg-ink-50" : "")}>
                      <td className="px-3 py-1.5 text-right text-ink-600">{fmt(b)}</td>
                      <td className="px-3 py-1.5 text-center font-semibold text-ink-800">
                        {row.label}
                        {row.note && <span className="ml-1 text-[10px] font-normal text-ink-400">({row.note})</span>}
                      </td>
                      <td className="px-3 py-1.5 text-right">
                        <span className="inline-flex items-center gap-1">
                          <DirArrow d={d} premium={premium} />
                          <span className={`font-bold ${d === 1 && !premium ? "text-accent-700" : d === -1 && !premium ? "text-danger-700" : "text-ink-900"}`}>
                            {fmt(a)}
                          </span>
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* C. 핵심 질병 전→후 요약 (우측 1/3) */}
        <div className="border-t border-line p-4 lg:border-t-0">
          <h3 className="mb-2 text-caption font-bold text-ink-700">핵심 질병 전 → 후</h3>
          <div className="space-y-1.5">
            {KEY_DISEASES.map((k) => {
              const b = numOf(beforeTotals, [k.id]);
              const a = numOf(afterTotals, [k.id]);
              const d = dir(b, a);
              return (
                <div key={k.id} className="flex items-center justify-between rounded-btn border border-line px-3 py-2 text-xs">
                  <span className="font-bold text-ink-800">{k.label}</span>
                  <span className="flex items-center gap-1.5">
                    <span className="text-ink-500">{fmtAmount(b)}</span>
                    <span className="text-ink-400">→</span>
                    <span className={`font-bold ${d === 1 ? "text-accent-700" : d === -1 ? "text-danger-700" : "text-ink-900"}`}>
                      {fmtAmount(a)}
                    </span>
                    <DirArrow d={d} />
                  </span>
                </div>
              );
            })}
          </div>

          {/* 특이사항 (세션 내 비저장) */}
          <div className="mt-4">
            <label className="block text-caption font-bold text-ink-700">
              특이사항 (설계사 메모)
              <textarea
                value={memo}
                onChange={(e) => onMemoChange(e.target.value)}
                rows={4}
                placeholder="리모델링 사유·고객 요청·후속 안내 등 (저장되지 않음)"
                className="mt-1.5 w-full rounded-btn border border-line-strong bg-white px-3 py-2 text-xs text-ink placeholder:text-ink-400 focus:border-accent-500 focus:outline-2 focus:outline-offset-0 focus:outline-accent-200"
              />
            </label>
            <p className="mt-1 text-[10px] text-ink-400">메모는 이 화면에서만 사용되며 저장되지 않습니다.</p>
          </div>
        </div>
      </div>

      {/* 범례 */}
      <div className="flex flex-wrap items-center gap-2 border-t border-line px-4 py-3">
        <Badge tone="gold">▲ 증가·신규</Badge>
        <Badge tone="danger">▼ 감소·해지</Badge>
        <Badge tone="neutral">— 변동 없음</Badge>
        <span className="ml-auto text-[10px] text-ink-400">전/후 모두 041 집계값 표시 — 재계산 없음</span>
      </div>

      {/* 엑셀 다운로드 (045 — 045 예고 자리 대체) */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-4 py-3">
        <p className="text-[11px] text-ink-400">엑셀(.xlsx)은 브라우저에서 생성되며 저장되지 않습니다 — 전·후 비분표 + 최종표 3시트.</p>
        <Button onClick={onExport} loading={exporting}>
          엑셀 다운로드 (.xlsx)
        </Button>
      </div>
    </Card>
  );
}
