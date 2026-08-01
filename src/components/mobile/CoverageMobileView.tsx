// BOHUMFIT-266 — 보장분석 모바일 3단 점진 공개(1단 요약 / 2단 주요 담보 8행 / 3단 전체 표).
//
//   ★값 동등성 설계: 포맷터를 **props로 주입**받는다. 모바일에서 숫자를 다시 계산하거나 표기를 복제하면
//     데스크톱과 어긋날 수 있어, 같은 함수·같은 payload를 그대로 쓴다(266 검증 항목).
//   ★가로 스크롤은 3단에만 존재한다 — 1·2단은 세로로만 편다(263이 지적한 1,680px 표 문제의 해법).
import { useMemo, useState } from "react";
import type { BeforeCoverage, Company, ComparisonRow } from "../../lib/coverageAfterDisplayCache";
import { keyOf } from "../../lib/coverageAfterDisplayCache";
import { formatCoverageAmount, formatCoverageDeltaAmount } from "../../lib/coverageFormat";
import { countChanges, paidTotal20Y, pickKeyCoverages, KEY_COVERAGE_COUNT } from "./coverageMobileSlots";
import { MOBILE_LAYOUT, MOBILE_TOUCH } from "./tokens";

/** 데스크톱과 동일한 표기를 쓰기 위해 호출부(CoverageRemodel)에서 그대로 넘겨받는다. */
export type MobileFormatters = {
  formatWon: (value: number | null | undefined) => string;
  formatPremium: (value: number | null | undefined) => string;
  formatDeltaWon: (value: number | null | undefined) => string;
  companyLabel: (company: Company, companies: Company[]) => string;
};

type PremiumBlock = {
  before_monthly: number;
  after_monthly: number;
  delta_monthly: number;
  delta_paid_total: number | null;
};

/* ────────────────────────────── 1단 — 요약 ────────────────────────────── */

export function CoverageMobileSummary({
  premium,
  rows,
  fmt,
}: {
  premium: PremiumBlock;
  rows: ComparisonRow[];
  fmt: MobileFormatters;
}) {
  const changes = useMemo(() => countChanges(rows), [rows]);
  const saving = premium.delta_monthly < 0;

  return (
    <section data-testid="m-summary" className="border border-line bg-white" style={{ borderRadius: MOBILE_LAYOUT.radiusCard, padding: MOBILE_LAYOUT.gutter }}>
      <h2 className="text-[20px] font-bold leading-[1.35] text-ink-900">한눈에 보기</h2>

      {/* 고객이 먼저 묻는 숫자 — 월납 차액을 가장 크게. */}
      <div className="mt-4">
        <p className="text-[15px] leading-[1.55] text-ink-soft">월납 보험료</p>
        <p className={`mt-1 text-[28px] font-extrabold leading-[1.25] ${saving ? "text-accent-600" : "text-ink-900"}`}>
          {fmt.formatDeltaWon(premium.delta_monthly)}
        </p>
        <p className="mt-1 text-[15px] leading-[1.55] text-ink-soft">
          {fmt.formatWon(premium.before_monthly)} → <b className="font-bold text-ink-900">{fmt.formatWon(premium.after_monthly)}</b>
        </p>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3">
        <div className="bg-canvas p-3" style={{ borderRadius: MOBILE_LAYOUT.radiusBadge }}>
          <dt className="text-[15px] leading-[1.55] text-ink-soft">총납입 차액</dt>
          <dd className="mt-1 text-[16px] font-bold leading-[1.4] text-ink-900">
            {fmt.formatDeltaWon(premium.delta_paid_total)}
          </dd>
        </div>
        {/* BOHUMFIT-261과 같은 산식(240개월) — 엑셀 표지·시트3과 값이 어긋나지 않게 한 곳에서 계산한다. */}
        <div className="bg-canvas p-3" style={{ borderRadius: MOBILE_LAYOUT.radiusBadge }}>
          <dt className="text-[15px] leading-[1.55] text-ink-soft">20년 총납입 차액</dt>
          <dd className="mt-1 text-[16px] font-bold leading-[1.4] text-ink-900" data-testid="m-summary-20y">
            {fmt.formatDeltaWon(paidTotal20Y(premium.delta_monthly))}
          </dd>
        </div>
      </dl>

      <p className="mt-3 text-[15px] leading-[1.55] text-ink-soft" data-testid="m-summary-changes">
        보장 <b className="font-bold text-accent-700">{changes.up}개 증액</b> ·{" "}
        <b className="font-bold text-warning-700">{changes.down}개 감액</b>
      </p>
    </section>
  );
}

/* ──────────────────────── 2단 — 주요 담보 8행 + 계약별 아코디언 ──────────────────────── */

/** 담보 한 줄의 계약별 내역(전·후) — ★가로 스크롤 없이 세로로 편다. */
function ContractBreakdown({
  companies,
  before,
  after,
  fmt,
}: {
  companies: Company[];
  before: BeforeCoverage | undefined;
  after: BeforeCoverage | undefined;
  fmt: MobileFormatters;
}) {
  // 전·후 어느 쪽이든 값이 있는 계약만 노출한다(빈 줄로 화면을 채우지 않는다).
  const lines = companies
    .map((company) => {
      const key = keyOf(company.idx);
      return {
        company,
        beforeValue: before?.by_company?.[key] ?? null,
        afterValue: after?.by_company?.[key] ?? null,
      };
    })
    .filter((line) => line.beforeValue != null || line.afterValue != null);

  if (lines.length === 0) {
    return (
      <p className="px-1 py-2 text-[15px] leading-[1.55] text-ink-soft">
        계약별 내역이 없습니다 — 합계로만 제공된 담보입니다.
      </p>
    );
  }

  return (
    <ul className="mt-1 space-y-2">
      {lines.map(({ company, beforeValue, afterValue }) => {
        const removed = beforeValue != null && afterValue == null;
        return (
          <li
            key={keyOf(company.idx)}
            className={`flex items-baseline justify-between gap-3 bg-canvas px-3 py-2 ${removed ? "text-ink-400" : ""}`}
            style={{ borderRadius: MOBILE_LAYOUT.radiusBadge }}
          >
            <span className="min-w-0 flex-1 break-keep text-[15px] leading-[1.55] font-semibold text-ink-800">
              {fmt.companyLabel(company, companies)}
            </span>
            <span className={`shrink-0 text-[15px] leading-[1.55] ${removed ? "line-through" : "text-ink-soft"}`}>
              {formatCoverageAmount(beforeValue)}
            </span>
            <span className="shrink-0 text-[15px] leading-[1.55] font-bold text-ink-900">
              {formatCoverageAmount(afterValue)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export function CoverageMobileCoverages({
  rows,
  companies,
  beforeCoverages,
  afterCoverages,
  fmt,
  onOpenFullTable,
}: {
  rows: ComparisonRow[];
  companies: Company[];
  beforeCoverages: BeforeCoverage[];
  afterCoverages: BeforeCoverage[];
  fmt: MobileFormatters;
  onOpenFullTable: () => void;
}) {
  const picked = useMemo(() => pickKeyCoverages(rows, KEY_COVERAGE_COUNT), [rows]);
  const [openName, setOpenName] = useState<string | null>(null);

  const beforeByName = useMemo(() => new Map(beforeCoverages.map((c) => [c.kb_name, c])), [beforeCoverages]);
  const afterByName = useMemo(() => new Map(afterCoverages.map((c) => [c.kb_name, c])), [afterCoverages]);

  return (
    <section
      data-testid="m-coverages"
      className="mt-4 border border-line bg-white"
      style={{ borderRadius: MOBILE_LAYOUT.radiusCard, padding: MOBILE_LAYOUT.gutter }}
    >
      <h2 className="text-[20px] font-bold leading-[1.35] text-ink-900">주요 담보</h2>
      <p className="mt-1 text-[15px] leading-[1.55] text-ink-soft">담보를 누르면 계약별 내역이 펼쳐집니다.</p>

      {/* 2열 헤더 — 담보명 + 전/후. 여기서는 가로 스크롤을 만들지 않는다. */}
      <div className="mt-4 flex items-baseline gap-3 border-b border-line pb-2">
        <span className="min-w-0 flex-1 text-[15px] leading-[1.55] text-ink-soft">담보</span>
        <span className="w-[72px] shrink-0 text-right text-[15px] leading-[1.55] text-ink-soft">현재</span>
        <span className="w-[80px] shrink-0 text-right text-[15px] leading-[1.55] text-ink-soft">리모델링</span>
      </div>

      <ul>
        {picked.map(({ slot, row }) => {
          const open = openName === row.kb_name;
          const delta = row.delta_value ?? 0;
          return (
            <li key={row.kb_name} className="border-b border-line/60">
              <button
                type="button"
                data-testid="m-coverage-row"
                data-slot={slot}
                aria-expanded={open}
                onClick={() => setOpenName(open ? null : row.kb_name)}
                className="flex w-full items-center gap-3 py-3 text-left"
                style={{ minHeight: MOBILE_TOUCH.tap }}
              >
                <span className="min-w-0 flex-1">
                  <span className="block break-keep text-[16px] font-bold leading-[1.4] text-ink-900">{row.kb_name}</span>
                  {delta !== 0 && (
                    <span
                      className={`mt-0.5 block text-[15px] font-bold leading-[1.4] ${
                        delta > 0 ? "text-accent-700" : "text-warning-700"
                      }`}
                    >
                      {formatCoverageDeltaAmount(delta)}
                    </span>
                  )}
                </span>
                <span className="w-[72px] shrink-0 text-right text-[15px] leading-[1.55] text-ink-soft">
                  {formatCoverageAmount(row.before_value)}
                </span>
                <span className="w-[80px] shrink-0 text-right text-[16px] font-bold leading-[1.4] text-ink-900">
                  {formatCoverageAmount(row.after_value)}
                </span>
              </button>
              {open && (
                <div className="pb-3" data-testid="m-coverage-detail">
                  <ContractBreakdown
                    companies={companies}
                    before={beforeByName.get(row.kb_name)}
                    after={afterByName.get(row.kb_name)}
                    fmt={fmt}
                  />
                </div>
              )}
            </li>
          );
        })}
      </ul>

      {/* 3단 진입 — 시안 의도대로 "검증이 필요한 순간에만" 들어가는 단일 버튼. */}
      <button
        type="button"
        data-testid="m-open-full-table"
        onClick={onOpenFullTable}
        className="mt-4 w-full border border-line-strong bg-white text-[16px] font-bold text-ink-800"
        style={{ minHeight: MOBILE_TOUCH.action, borderRadius: MOBILE_LAYOUT.radiusBtn }}
      >
        전체 표 보기
      </button>
    </section>
  );
}

/* ────────────────────────── 3단 — 전체 표(전체화면) ────────────────────────── */

export function CoverageMobileMatrix({
  open,
  onClose,
  companies,
  coverages,
  fmt,
}: {
  open: boolean;
  onClose: () => void;
  companies: Company[];
  coverages: BeforeCoverage[];
  fmt: MobileFormatters;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[9990] flex flex-col bg-white" data-testid="m-full-table" role="dialog" aria-modal="true" aria-label="전체 보장 표">
      <header
        className="flex items-center justify-between gap-3 border-b border-line bg-white"
        style={{ paddingLeft: MOBILE_LAYOUT.gutter, paddingRight: MOBILE_LAYOUT.gutter, paddingTop: 12, paddingBottom: 12 }}
      >
        <h2 className="text-[20px] font-bold leading-[1.35] text-ink-900">전체 보장 표</h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="닫기"
          className="m-tap shrink-0 px-3 text-[16px] font-bold text-ink-700"
          style={{ minHeight: MOBILE_TOUCH.tap }}
        >
          닫기
        </button>
      </header>

      {/* ★여기에만 가로 스크롤이 있다 — 첫 열(담보)은 고정해 어느 계약인지 잃지 않게 한다. */}
      <div className="flex-1 overflow-auto" style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}>
        <table className="w-full min-w-[720px] text-[15px]">
          <thead>
            <tr className="border-b border-line text-ink-soft">
              <th className="sticky left-0 z-10 whitespace-nowrap bg-white py-2 pr-2 pl-3 text-left align-middle">담보</th>
              <th className="whitespace-nowrap px-2 py-2 text-right align-middle">후 보장금액</th>
              {companies.map((company) => (
                <th key={keyOf(company.idx)} className="whitespace-nowrap px-2 py-2 text-right align-middle">
                  {fmt.companyLabel(company, companies)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {coverages.map((coverage) => (
              <tr key={coverage.kb_name} className="border-b border-line/60">
                <td className="sticky left-0 z-10 break-keep bg-white py-2 pr-2 pl-3 font-semibold text-ink-800">
                  {coverage.kb_name}
                </td>
                <td className="px-2 py-2 text-right font-bold text-ink-900">{formatCoverageAmount(coverage.summary)}</td>
                {companies.map((company) => (
                  <td key={keyOf(company.idx)} className="px-2 py-2 text-right text-ink-soft">
                    {formatCoverageAmount(coverage.by_company?.[keyOf(company.idx)])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
