// BOHUMFIT-044: 최종비교분석표 — 전/후 요약 비교 (표시 전용).
// - 값은 043에서 이미 계산된 041 집계값(beforeTotals/afterTotals)을 그대로 매핑·표시한다 — 재계산 금지.
// - 양식의 일부 행(상해사망 결합/일반입원·암입원 분리)은 lib 변경 없이 렌더 레이어에서만 처리한다.
// - 특이사항 메모는 이 세션(메모리) 안에서만 유지된다 — 저장 없음.
import { useState } from "react";
import Card from "../ui/Card";
import Badge from "../ui/Badge";

type Totals = Record<string, number | boolean>;
type FinalRowKind = "amount" | "flag" | "premium" | "none";

interface FinalRow {
  label: string;
  /** 합산할 041 카테고리 id (빈 배열 = lib 미분류 표시 전용 행) */
  ids: string[];
  kind: FinalRowKind;
  note?: string;
}

// 양식 순서 그대로 (약 37행). ids 는 041 카테고리 id 매핑.
const FINAL_ROWS: FinalRow[] = [
  // 양식에 재해사망 행이 없어 상해사망 = 상해(injury)+재해(disaster) 합산 표시(분해 잔액 손실 방지)
  { label: "일반사망", ids: ["general_death"], kind: "amount" },
  { label: "상해사망", ids: ["injury_death", "disaster_death"], kind: "amount", note: "재해사망 포함" },
  { label: "질병사망", ids: ["disease_death"], kind: "amount" },
  { label: "상해후유장해", ids: ["injury_disability"], kind: "amount" },
  { label: "질병후유장해", ids: ["disease_disability"], kind: "amount" },
  { label: "일반암진단금", ids: ["cancer_diagnosis"], kind: "amount" },
  { label: "유사암진단금", ids: ["minor_cancer_diagnosis"], kind: "amount" },
  { label: "표적항암치료", ids: ["targeted_anticancer"], kind: "amount" },
  { label: "차세대암치료", ids: ["next_gen_anticancer"], kind: "amount" },
  { label: "암수술비", ids: ["cancer_surgery"], kind: "amount" },
  { label: "뇌혈관(초기)", ids: ["cerebrovascular_early"], kind: "amount" },
  { label: "뇌졸중(중기)", ids: ["stroke_mid"], kind: "amount" },
  { label: "뇌출혈(말기)", ids: ["cerebral_hemorrhage_late"], kind: "amount" },
  { label: "뇌혈관수술비", ids: ["cerebrovascular_surgery"], kind: "amount" },
  { label: "허혈성(초기)", ids: ["ischemic_heart_early"], kind: "amount" },
  { label: "급성심(말기)", ids: ["ami_late"], kind: "amount" },
  { label: "심혈관수술비", ids: ["cardiovascular_surgery"], kind: "amount" },
  { label: "일반종수술 1종", ids: ["general_surgery_type1"], kind: "amount" },
  { label: "일반종수술 2종", ids: ["general_surgery_type2"], kind: "amount" },
  { label: "일반종수술 3종", ids: ["general_surgery_type3"], kind: "amount" },
  { label: "일반종수술 4종", ids: ["general_surgery_type4"], kind: "amount" },
  { label: "일반종수술 5종", ids: ["general_surgery_type5"], kind: "amount" },
  { label: "상해수술", ids: ["injury_surgery"], kind: "amount" },
  { label: "질병수술", ids: ["disease_surgery"], kind: "amount" },
  { label: "일반입원", ids: [], kind: "none", note: "표준 카테고리 미분류(원천은 질병/상해입원 매핑)" },
  { label: "상해입원", ids: ["injury_hospitalization"], kind: "amount" },
  { label: "질병입원", ids: ["disease_hospitalization"], kind: "amount", note: "암입원 포함" },
  { label: "암입원", ids: [], kind: "none", note: "질병입원에 포함 — 별도 분리 불가" },
  { label: "골절진단비", ids: ["fracture_diagnosis"], kind: "amount" },
  { label: "화상진단비", ids: ["burn_diagnosis"], kind: "amount" },
  { label: "운전자특약", ids: ["driver_rider"], kind: "flag" },
  { label: "자부상치료비", ids: ["car_injury_treatment"], kind: "flag" },
  { label: "상해의료비", ids: ["injury_medical_indemnity"], kind: "flag" },
  { label: "질병의료비", ids: ["disease_medical_indemnity"], kind: "flag" },
  { label: "가족일상배상", ids: ["family_liability"], kind: "flag" },
  { label: "응급실내원비", ids: ["er_visit"], kind: "amount" },
  { label: "보험료", ids: ["premium"], kind: "premium" },
];

// 우측 핵심 질병 요약 (구분 → 카테고리 id)
const KEY_DISEASES: ReadonlyArray<{ label: string; id: string }> = [
  { label: "암", id: "cancer_diagnosis" },
  { label: "뇌 초기", id: "cerebrovascular_early" },
  { label: "뇌 중기", id: "stroke_mid" },
  { label: "뇌 말기", id: "cerebral_hemorrhage_late" },
  { label: "심장 초기", id: "ischemic_heart_early" },
  { label: "심장 말기", id: "ami_late" },
];

function numOf(totals: Totals, ids: string[]): number {
  return ids.reduce((s, id) => s + (typeof totals[id] === "number" ? (totals[id] as number) : 0), 0);
}
function flagOf(totals: Totals, ids: string[]): boolean {
  return ids.some((id) => totals[id] === true);
}
function fmtAmount(v: number): string {
  return v > 0 ? v.toLocaleString() : "-";
}
function fmtPremium(v: number): string {
  return v > 0 ? `${v.toLocaleString()}원` : "-";
}

/** 방향: 1 증가 / -1 감소 / 0 동일 */
function dir(before: number, after: number): -1 | 0 | 1 {
  return after > before ? 1 : after < before ? -1 : 0;
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
}

export default function FinalComparison({ beforeTotals, afterTotals }: FinalComparisonProps) {
  const [memo, setMemo] = useState("");

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
                onChange={(e) => setMemo(e.target.value)}
                rows={4}
                placeholder="리모델링 사유·고객 요청·후속 안내 등 (저장되지 않음)"
                className="mt-1.5 w-full rounded-btn border border-line-strong bg-white px-3 py-2 text-xs text-ink placeholder:text-ink-400 focus:border-accent-500 focus:outline-2 focus:outline-offset-0 focus:outline-accent-200"
              />
            </label>
            <p className="mt-1 text-[10px] text-ink-400">메모는 이 화면에서만 사용되며 저장되지 않습니다.</p>
          </div>
        </div>
      </div>

      {/* 범례 + 045 예고 */}
      <div className="flex flex-wrap items-center gap-2 border-t border-line px-4 py-3">
        <Badge tone="gold">▲ 증가·신규</Badge>
        <Badge tone="danger">▼ 감소·해지</Badge>
        <Badge tone="neutral">— 변동 없음</Badge>
        <span className="ml-auto text-[10px] text-ink-400">전/후 모두 041 집계값 표시 — 재계산 없음</span>
      </div>
      <div className="border-t border-dashed border-line bg-ink-50 px-4 py-3 text-center">
        <p className="text-caption font-bold uppercase tracking-[0.2em] text-ink-400">Next</p>
        <p className="mt-0.5 text-sm font-bold text-ink-600">다음: 엑셀 출력 (준비 중)</p>
      </div>
    </Card>
  );
}
