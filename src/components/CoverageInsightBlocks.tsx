// BOHUMFIT-247: 신 체계(비분양식) 화면 완성용 표시 블록 — 종합비교(시트3 의미)·Y/N·특이사항.
// 계산 규칙은 backend/coverage(정본)와 lib/coverageAfterDisplayCache 미러를 따르고,
// 이 파일은 표시 전용이다(FIT 브랜드 토큰만 사용).
import { type YnFlag } from "../lib/coverageAfterDisplayCache";
import { formatCoverageAmount, formatCoverageDeltaAmount } from "../lib/coverageFormat";
// BOHUMFIT-267 P2: 모바일에서는 고정폭 표 대신 리스트로 편다(가로 스크롤 0·15px 하한).
//   ★데스크톱 경로는 건드리지 않고 분기만 추가한다(266과 같은 방식 — CSS 숨김이 아니라 JS 판정).
import { useIsMobile } from "./mobile/useIsMobile";
import { StageComparisonMobile, YnFlagMobile } from "./mobile/CoverageInsightMobile";

// 시트3 종합비교 표시 라벨(암/뇌 초·중·말/심장 초·중·말 — H10 심장중기 정정 반영).
// ★BOHUMFIT-298(층위 3): 종합비교 표시 축을 **케스케이드 17키**로 이관(백엔드 `PAYOUT_CASCADE_V2` 1:1).
//   구 7키(암·심장말기 포함)는 폐기됐다 — 서버가 17키를 주는데 화면이 7키만 조회해 `암`·`심장말기`가 [전]에서도
//   0으로 보이고 암 계열 12행이 아예 안 나오던 문제(295 §1-6 ③)를 닫는다. key = 서버 `stage_totals` 키와 정확히 일치.
const STAGE_ROWS: { key: string; label: string; section: string }[] = [
  { key: "뇌초기", label: "뇌 초기", section: "뇌" },
  { key: "뇌중기", label: "뇌 중기", section: "뇌" },
  { key: "뇌말기", label: "뇌 말기", section: "뇌" },
  { key: "심장초기", label: "심장 초기", section: "심장" },
  { key: "심장중기", label: "심장 중기", section: "심장" },
  { key: "암 수 술 (레보아이 포함)", label: "암 수술(레보아이 포함)", section: "암" },
  { key: "유사암 수술", label: "유사암 수술", section: "암" },
  { key: "다빈치(일반암)", label: "다빈치(일반암)", section: "암" },
  { key: "다빈치(전립선)", label: "다빈치(전립선)", section: "암" },
  { key: "다빈치(갑상선)", label: "다빈치(갑상선)", section: "암" },
  { key: "항암 약물 치료", label: "항암 약물 치료", section: "암" },
  { key: "표적 약물 치료", label: "표적 약물 치료", section: "암" },
  { key: "면역 약물 치료", label: "면역 약물 치료", section: "암" },
  { key: "방사선 치료", label: "방사선 치료", section: "암" },
  { key: "세기조절 방사선 치료", label: "세기조절 방사선 치료", section: "암" },
  { key: "양성자 방사선 치료", label: "양성자 방사선 치료", section: "암" },
  { key: "중 입 자 치료", label: "중입자 치료", section: "암" },
];

export function StageComparisonTable({
  before,
  after,
}: {
  before: Record<string, number>;
  after: Record<string, number> | null;
}) {
  // BOHUMFIT-267 P2: 같은 STAGE_ROWS를 넘겨 라벨·순서·값이 데스크톱 표와 어긋날 수 없게 한다.
  const isMobile = useIsMobile();
  if (isMobile) return <StageComparisonMobile rows={STAGE_ROWS} before={before} after={after} />;

  return (
    <div className="overflow-x-auto" data-testid="stage-comparison">
      <table className="w-full min-w-[560px] table-fixed text-[12px]">
        <colgroup>
          <col className="w-[28%]" />
          <col className="w-[24%]" />
          <col className="w-[8%]" />
          <col className="w-[24%]" />
          <col className="w-[16%]" />
        </colgroup>
        <thead>
          <tr className="border-b border-line text-left text-ink-500">
            <th className="py-2 pr-2">종합비교</th>
            <th className="px-2 py-2 text-right">전</th>
            <th className="px-1 py-2 text-center" aria-hidden="true" />
            <th className="px-2 py-2 text-right">후</th>
            <th className="py-2 pl-2 text-right">개선(후−전)</th>
          </tr>
        </thead>
        <tbody>
          {STAGE_ROWS.map((row) => {
            const beforeValue = before[row.key] ?? 0;
            const afterValue = after == null ? null : (after[row.key] ?? 0);
            const delta = afterValue == null ? null : afterValue - beforeValue;
            return (
              <tr key={row.key} className="border-b border-line/60">
                <td className="py-1.5 pr-2 font-semibold text-ink-800">{row.label}</td>
                <td className="px-2 py-1.5 text-right tabular-nums">{formatCoverageAmount(beforeValue)}</td>
                <td className="px-1 py-1.5 text-center text-ink-400" aria-hidden="true">
                  →
                </td>
                <td className="px-2 py-1.5 text-right font-semibold tabular-nums text-ink-900">
                  {afterValue == null ? "-" : formatCoverageAmount(afterValue)}
                </td>
                <td
                  className={`py-1.5 pl-2 text-right font-bold tabular-nums ${
                    delta != null && delta > 0
                      ? "text-accent-700"
                      : delta != null && delta < 0
                        ? "text-amber-700"
                        : "text-ink-soft"
                  }`}
                >
                  {formatCoverageDeltaAmount(delta)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function YnFlagTable({ before, after }: { before: YnFlag[]; after: YnFlag[] | null }) {
  const afterByItem = new Map((after || []).map((flag) => [flag.item, flag.value]));
  // BOHUMFIT-267 P2 — 모바일은 배지 리스트(같은 before/after 배열을 그대로 넘긴다).
  const isMobile = useIsMobile();
  if (isMobile) return <YnFlagMobile before={before} after={after} />;

  return (
    <div className="overflow-x-auto" data-testid="yn-flags">
      <table className="w-full min-w-[420px] table-fixed text-[12px]">
        <colgroup>
          <col className="w-[46%]" />
          <col className="w-[27%]" />
          <col className="w-[27%]" />
        </colgroup>
        <thead>
          <tr className="border-b border-line text-left text-ink-500">
            <th className="py-2 pr-2">가입특약(Y/N)</th>
            <th className="px-2 py-2 text-center">전</th>
            <th className="px-2 py-2 text-center">후</th>
          </tr>
        </thead>
        <tbody>
          {before.map((flag) => {
            const afterValue = after == null ? null : (afterByItem.get(flag.item) ?? "N");
            return (
              <tr key={flag.item} className="border-b border-line/60">
                <td className="py-1.5 pr-2 font-semibold text-ink-800">{flag.item}</td>
                <td className="px-2 py-1.5 text-center">
                  <YnBadge value={flag.value} />
                </td>
                <td className="px-2 py-1.5 text-center">{afterValue == null ? "-" : <YnBadge value={afterValue} />}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function YnBadge({ value }: { value: "Y" | "N" }) {
  return value === "Y" ? (
    <span className="rounded-full bg-accent-100 px-2 py-0.5 text-[11px] font-extrabold text-accent-800">Y</span>
  ) : (
    <span className="rounded-full bg-ink-100 px-2 py-0.5 text-[11px] font-extrabold text-ink-soft">N</span>
  );
}

export function SpecialNotes({ notes }: { notes: string[] }) {
  if (notes.length === 0) return null;
  return (
    <div className="rounded-card border border-amber-200 bg-amber-50/60 p-4" data-testid="special-notes">
      <h3 className="ko-heading text-sm font-bold text-ink-900">특이사항</h3>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-[12px] text-amber-800">
        {notes.map((note, index) => (
          <li key={`${index}-${note.slice(0, 20)}`} className="break-keep">
            {note}
          </li>
        ))}
      </ul>
    </div>
  );
}
