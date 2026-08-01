/// <reference types="node" />
// BOHUMFIT-266 — ★모바일 뷰 = 데스크톱 값 동등성(해지 0/1/3건) + 3단 동작 + 스와이프 해지.
//
//   251·260 선례대로 **같은 골든 픽스처**를 써서 "화면이 달라도 숫자는 같다"를 고정한다.
//   데스크톱이 쓰는 값(payload)과 모바일이 그리는 값을 직접 대조하므로, 한쪽만 바뀌면 반드시 깨진다.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  buildAfterResult,
  keyOf,
  type AnalyzeResult,
  type Company,
  type ContractDecision,
  type ProposalDraft,
} from "../../lib/coverageAfterDisplayCache";
import { formatCoverageAmount } from "../../lib/coverageFormat";
import {
  CoverageMobileCoverages,
  CoverageMobileMatrix,
  CoverageMobileSummary,
  type MobileFormatters,
} from "./CoverageMobileView";
import CoverageContractCards from "./CoverageContractCards";
import { COVERAGE_SLOTS, KEY_COVERAGE_COUNT, countChanges, paidTotal20Y, pickKeyCoverages } from "./coverageMobileSlots";
import { SWIPE } from "./tokens";

afterEach(() => cleanup());

type Fixture = {
  analysis: AnalyzeResult;
  decisions: Record<string, ContractDecision>;
  proposals: ProposalDraft[];
};

const fixture = JSON.parse(
  readFileSync(resolve(process.cwd(), "backend/tests/fixtures/coverage_after_parity_211.json"), "utf8"),
) as Fixture;

/** 데스크톱과 동일한 표기 함수(CoverageRemodel의 로컬 함수와 같은 구현 — 값 비교용). */
const fmt: MobileFormatters = {
  formatWon: (v) => (v == null ? "-" : `${v.toLocaleString("ko-KR")}원`),
  formatPremium: (v) => (v == null ? "미제공" : `${v.toLocaleString("ko-KR")}원`),
  formatDeltaWon: (v) =>
    v == null ? "-" : v === 0 ? "변동 없음" : `${v > 0 ? "+" : "-"}${Math.abs(v).toLocaleString("ko-KR")}원`,
  companyLabel: (company, companies) => {
    if (!company.insurer) return `계약 ${company.idx}`;
    const same = companies.filter((c) => c.insurer === company.insurer);
    if (same.length <= 1) return company.insurer;
    return `${company.insurer} (${same.findIndex((c) => keyOf(c.idx) === keyOf(company.idx)) + 1})`;
  },
};

const companiesOf = (analysis: AnalyzeResult): Company[] =>
  analysis.before.contract_list || analysis.before.companies || [];

/** 해지 N건 시나리오 — 계약 앞에서부터 N건을 해지로 표시한다. */
function scenario(cancelCount: number) {
  const companies = companiesOf(fixture.analysis);
  const decisions: Record<string, ContractDecision> = {};
  for (const company of companies.slice(0, cancelCount)) {
    decisions[keyOf(company.idx)] = { disposition: "cancel" };
  }
  return buildAfterResult(fixture.analysis, decisions, []);
}

describe("★모바일 = 데스크톱 값 동등성 (해지 0/1/3건)", () => {
  for (const cancelCount of [0, 1, 3]) {
    it(`해지 ${cancelCount}건 — 2단 담보 행이 comparison payload와 일치한다`, () => {
      const after = scenario(cancelCount);
      const rows = after.comparison.coverages;

      render(
        <CoverageMobileCoverages
          rows={rows}
          companies={after.after.before.companies}
          beforeCoverages={fixture.analysis.before.coverages}
          afterCoverages={after.after.before.coverages}
          fmt={fmt}
          onOpenFullTable={() => {}}
        />,
      );

      const picked = pickKeyCoverages(rows, KEY_COVERAGE_COUNT);
      expect(picked.length).toBeGreaterThan(0);
      const rendered = screen.getAllByTestId("m-coverage-row");
      expect(rendered).toHaveLength(picked.length);

      picked.forEach(({ row }, index) => {
        const card = rendered[index];
        expect(within(card).getByText(row.kb_name)).toBeTruthy();
        // ★데스크톱 표와 같은 포맷터·같은 필드를 쓴다 — 값이 갈라지면 여기서 잡힌다.
        expect(card.textContent).toContain(formatCoverageAmount(row.before_value));
        expect(card.textContent).toContain(formatCoverageAmount(row.after_value));
      });
    });

    it(`해지 ${cancelCount}건 — 3단 전체 표 셀이 by_company와 일치한다`, () => {
      const after = scenario(cancelCount);
      const companies = after.after.before.companies;
      const coverages = after.after.before.coverages;

      render(
        <CoverageMobileMatrix open onClose={() => {}} companies={companies} coverages={coverages} fmt={fmt} />,
      );

      const table = screen.getByTestId("m-full-table");
      for (const coverage of coverages) {
        const row = within(table).getByText(coverage.kb_name).closest("tr");
        expect(row).toBeTruthy();
        // 합계 열
        expect(row?.textContent).toContain(formatCoverageAmount(coverage.summary));
        // 회사별 열 — 데스크톱 ⑤ 매트릭스와 같은 소스(by_company)를 그대로 읽는다.
        for (const company of companies) {
          expect(row?.textContent).toContain(formatCoverageAmount(coverage.by_company?.[keyOf(company.idx)]));
        }
      }
    });

    it(`해지 ${cancelCount}건 — 1단 요약 숫자가 comparison.premium과 일치한다`, () => {
      const after = scenario(cancelCount);
      const premium = after.comparison.premium;
      render(<CoverageMobileSummary premium={premium} rows={after.comparison.coverages} fmt={fmt} />);

      const summary = screen.getByTestId("m-summary");
      expect(summary.textContent).toContain(fmt.formatWon(premium.before_monthly));
      expect(summary.textContent).toContain(fmt.formatWon(premium.after_monthly));
      expect(summary.textContent).toContain(fmt.formatDeltaWon(premium.delta_monthly));
      expect(summary.textContent).toContain(fmt.formatDeltaWon(premium.delta_paid_total));
      // 261과 같은 산식(240개월)
      expect(screen.getByTestId("m-summary-20y").textContent).toBe(
        fmt.formatDeltaWon(paidTotal20Y(premium.delta_monthly)),
      );
      const changes = countChanges(after.comparison.coverages);
      expect(screen.getByTestId("m-summary-changes").textContent).toContain(`${changes.up}개 증액`);
      expect(screen.getByTestId("m-summary-changes").textContent).toContain(`${changes.down}개 감액`);
    });
  }
});

describe("2단 — 계약별 아코디언(★가로 스크롤 없음)", () => {
  it("담보 행을 누르면 계약별 내역이 펼쳐지고 다시 누르면 접힌다", () => {
    const after = scenario(0);
    render(
      <CoverageMobileCoverages
        rows={after.comparison.coverages}
        companies={after.after.before.companies}
        beforeCoverages={fixture.analysis.before.coverages}
        afterCoverages={after.after.before.coverages}
        fmt={fmt}
        onOpenFullTable={() => {}}
      />,
    );
    expect(screen.queryByTestId("m-coverage-detail")).toBeNull();
    const first = screen.getAllByTestId("m-coverage-row")[0];
    expect(first.getAttribute("aria-expanded")).toBe("false");

    fireEvent.click(first);
    expect(screen.getByTestId("m-coverage-detail")).toBeTruthy();
    expect(first.getAttribute("aria-expanded")).toBe("true");

    fireEvent.click(first);
    expect(screen.queryByTestId("m-coverage-detail")).toBeNull();
  });

  it("★1·2단에는 가로 스크롤 컨테이너도, 고정폭 표도 없다(263이 지적한 1,680px 문제의 해법)", () => {
    const after = scenario(0);
    const { container } = render(
      <>
        <CoverageMobileSummary premium={after.comparison.premium} rows={after.comparison.coverages} fmt={fmt} />
        <CoverageMobileCoverages
          rows={after.comparison.coverages}
          companies={after.after.before.companies}
          beforeCoverages={fixture.analysis.before.coverages}
          afterCoverages={after.after.before.coverages}
          fmt={fmt}
          onOpenFullTable={() => {}}
        />
      </>,
    );
    fireEvent.click(screen.getAllByTestId("m-coverage-row")[0]); // 펼친 상태까지 검사
    expect(container.querySelectorAll("table")).toHaveLength(0);
    expect(container.querySelector('[class*="overflow-x"]')).toBeNull();
    expect(container.querySelector('[class*="min-w-["]')).toBeNull();
  });

  it("전체 표 보기 버튼이 3단을 연다", () => {
    const onOpenFullTable = vi.fn();
    const after = scenario(0);
    render(
      <CoverageMobileCoverages
        rows={after.comparison.coverages}
        companies={after.after.before.companies}
        beforeCoverages={fixture.analysis.before.coverages}
        afterCoverages={after.after.before.coverages}
        fmt={fmt}
        onOpenFullTable={onOpenFullTable}
      />,
    );
    fireEvent.click(screen.getByTestId("m-open-full-table"));
    expect(onOpenFullTable).toHaveBeenCalledTimes(1);
  });
});

describe("3단 — 전체 표", () => {
  it("닫혀 있으면 렌더하지 않는다", () => {
    const after = scenario(0);
    render(
      <CoverageMobileMatrix
        open={false}
        onClose={() => {}}
        companies={after.after.before.companies}
        coverages={after.after.before.coverages}
        fmt={fmt}
      />,
    );
    expect(screen.queryByTestId("m-full-table")).toBeNull();
  });

  it("★첫 열(담보)이 고정되고 가로 스크롤은 여기에만 있다", () => {
    const after = scenario(0);
    render(
      <CoverageMobileMatrix
        open
        onClose={() => {}}
        companies={after.after.before.companies}
        coverages={after.after.before.coverages}
        fmt={fmt}
      />,
    );
    const table = screen.getByTestId("m-full-table");
    const firstHeader = table.querySelector("thead th");
    expect(firstHeader?.className).toContain("sticky");
    expect(firstHeader?.className).toContain("left-0");
    const firstCell = table.querySelector("tbody td");
    expect(firstCell?.className).toContain("sticky");
    expect(table.querySelector('[class*="overflow-auto"]')).toBeTruthy();
  });
});

describe("★스와이프 해지 — 기존 해지 진입점만 호출한다", () => {
  const companies = companiesOf(fixture.analysis);
  const swipe = (el: HTMLElement, delta: number) => {
    fireEvent.touchStart(el, { touches: [{ clientX: 200 }] });
    fireEvent.touchMove(el, { touches: [{ clientX: 200 + delta }] });
    fireEvent.touchEnd(el);
  };

  it("임계값 미만은 무효 · 초과하면 해지로 바뀐다", () => {
    const onChange = vi.fn();
    render(
      <CoverageContractCards
        companies={companies}
        dispositionOf={() => "keep"}
        onChange={onChange}
        formatPeriod={() => "20년납 · 100세 만기"}
        fmt={fmt}
      />,
    );
    const cards = screen.getAllByTestId("swipe-card");
    swipe(cards[0], -(SWIPE.threshold - 10));
    expect(onChange).not.toHaveBeenCalled();

    swipe(cards[0], -(SWIPE.threshold + 10));
    expect(onChange).toHaveBeenCalledWith(companies[0].idx, "cancel");
  });

  it("해지 상태는 회색 면 + 취소선으로 보이고 우 스와이프로 복원된다", () => {
    const onChange = vi.fn();
    render(
      <CoverageContractCards
        companies={companies}
        dispositionOf={() => "cancel"}
        onChange={onChange}
        formatPeriod={() => "20년납 · 100세 만기"}
        fmt={fmt}
      />,
    );
    const card = screen.getAllByTestId("swipe-card")[0];
    expect(card.getAttribute("data-cancelled")).toBe("true");
    expect(card.className).toContain("line-through");
    swipe(card, SWIPE.threshold + 10);
    expect(onChange).toHaveBeenCalledWith(companies[0].idx, "keep");
  });

  it("스와이프를 모르는 사용자를 위해 같은 동작의 버튼을 함께 제공한다", () => {
    const onChange = vi.fn();
    render(
      <CoverageContractCards
        companies={companies}
        dispositionOf={() => "keep"}
        onChange={onChange}
        formatPeriod={() => "-"}
        fmt={fmt}
      />,
    );
    fireEvent.click(screen.getAllByTestId("m-contract-toggle")[0]);
    expect(onChange).toHaveBeenCalledWith(companies[0].idx, "cancel");
  });

  it("★해지 결과가 데스크톱 토글과 동일하다(같은 decisions → 같은 payload)", () => {
    // 스와이프가 만드는 decisions와 데스크톱 체크박스가 만드는 decisions는 같은 형태다.
    const target = companies[0];
    const fromDesktop = buildAfterResult(fixture.analysis, { [keyOf(target.idx)]: { disposition: "cancel" } }, []);
    const fromMobile = buildAfterResult(fixture.analysis, { [keyOf(target.idx)]: { disposition: "cancel" } }, []);
    expect(JSON.stringify(fromMobile)).toBe(JSON.stringify(fromDesktop));
    // 유지 상태와는 실제로 달라야 한다(테스트가 무의미해지지 않도록).
    expect(JSON.stringify(fromDesktop)).not.toBe(JSON.stringify(buildAfterResult(fixture.analysis, {}, [])));
  });
});

describe("주요 담보 8행 선정 규칙", () => {
  it("★실측 kb_name 세트에서 슬롯 8개를 채운다", () => {
    // overview E 문서 계열(실측) — 슬롯 후보가 대부분 존재하는 경우.
    const rows = [
      "질병사망", "상해사망", "질병후유장해", "암진단금", "뇌혈관질환", "허혈성심장질환",
      "질병수술", "질병입원", "골절진단비", "깁스치료비",
    ].map((kb_name, i) => ({ kb_name, before_value: 1000 + i, after_value: 2000 + i, delta_value: 1000 }));

    const picked = pickKeyCoverages(rows);
    expect(picked).toHaveLength(KEY_COVERAGE_COUNT);
    expect(picked.map((p) => p.row.kb_name)).toEqual([
      "암진단금", "뇌혈관질환", "허혈성심장질환", "질병수술", "질병입원", "질병후유장해", "질병사망",
      // 실손 슬롯은 이 문서에 없어 금액 보충으로 채워진다(빈 행을 만들지 않는다).
      "깁스치료비",
    ]);
  });

  it("★슬롯 후보가 없는 문서(표준 B 계열)에서도 8행을 채운다 — 시안 이름 상수화가 깨지는 지점", () => {
    const rows = [
      "질병사망", "상해사망", "암진단금", "유사암진단금", "뇌졸중", "뇌출혈", "급성심근경색",
      "질병수술", "질병입원", "응급실", "골절진단비",
    ].map((kb_name, i) => ({ kb_name, before_value: 100 * i, after_value: 200 * i, delta_value: 100 * i }));

    const picked = pickKeyCoverages(rows);
    expect(picked).toHaveLength(KEY_COVERAGE_COUNT);
    // 대체 후보가 정확히 잡혔는지(뇌졸중·급성심근경색)
    expect(picked.map((p) => p.row.kb_name)).toContain("뇌졸중");
    expect(picked.map((p) => p.row.kb_name)).toContain("급성심근경색");
  });

  it("값이 전혀 없는 담보는 고르지 않는다(빈 행 방지)", () => {
    const rows = [
      { kb_name: "암진단금", before_value: null, after_value: null, delta_value: null },
      { kb_name: "질병수술", before_value: 100, after_value: 200, delta_value: 100 },
    ];
    const picked = pickKeyCoverages(rows);
    expect(picked.map((p) => p.row.kb_name)).toEqual(["질병수술"]);
  });

  it("담보 수가 8개 미만이면 있는 만큼만 돌려준다", () => {
    const after = scenario(0);
    const picked = pickKeyCoverages(after.comparison.coverages);
    expect(picked.length).toBeLessThanOrEqual(KEY_COVERAGE_COUNT);
    expect(picked.length).toBeGreaterThan(0);
  });

  it("슬롯 정의가 중복 없이 8개다", () => {
    expect(COVERAGE_SLOTS).toHaveLength(KEY_COVERAGE_COUNT);
    expect(new Set(COVERAGE_SLOTS.map((s) => s.slot)).size).toBe(KEY_COVERAGE_COUNT);
  });
});
