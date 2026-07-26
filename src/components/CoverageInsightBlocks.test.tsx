// BOHUMFIT-247: 표시 블록 렌더 회귀 — 종합비교(개선 + 강조)·Y/N·특이사항.
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SpecialNotes, StageComparisonTable, YnFlagTable } from "./CoverageInsightBlocks";

const MAN = 10_000;

describe("CoverageInsightBlocks", () => {
  it("StageComparisonTable — 7개 단계 행·H10 정정 라벨(심장 중기)·개선(후−전) 표기", () => {
    const before = {
      암: 5000 * MAN, 뇌초기: 3000 * MAN, 뇌중기: 2000 * MAN, 뇌말기: 1000 * MAN,
      심장초기: 4000 * MAN, 심장중기: 3000 * MAN, 심장말기: 2000 * MAN,
    };
    const after = { ...before, 암: 8000 * MAN, 뇌말기: 500 * MAN };
    render(<StageComparisonTable before={before} after={after} />);
    expect(screen.getByText("심장 중기")).toBeInTheDocument(); // H10 심장중기 정정 반영
    expect(screen.getByText("뇌 초기")).toBeInTheDocument();
    expect(screen.getByText("+3,000만원")).toBeInTheDocument(); // 암 개선 + 표기
    expect(screen.getByText("-500만원")).toBeInTheDocument(); // 감소는 − 표기
  });

  it("StageComparisonTable — [후] 미계산이면 '-' 표시", () => {
    render(<StageComparisonTable before={{ 암: 1000 * MAN }} after={null} />);
    expect(screen.getAllByText("-").length).toBeGreaterThan(0);
  });

  it("YnFlagTable — 전/후 Y·N 배지", () => {
    const before = [
      { item: "운전자특약", value: "Y" as const, sources: [] },
      { item: "질병실손의료비", value: "N" as const, sources: [] },
    ];
    const after = [
      { item: "운전자특약", value: "N" as const, sources: [] },
      { item: "질병실손의료비", value: "N" as const, sources: [] },
    ];
    render(<YnFlagTable before={before} after={after} />);
    expect(screen.getByText("운전자특약")).toBeInTheDocument();
    expect(screen.getAllByText("Y")).toHaveLength(1); // 전 Y 1개
    expect(screen.getAllByText("N")).toHaveLength(3); // 전 1 + 후 2
  });

  it("SpecialNotes — 246 overview 해지 불가 경고 등 노출·빈 목록은 미렌더", () => {
    const { container } = render(<SpecialNotes notes={[]} />);
    expect(container).toBeEmptyDOMElement();
    render(
      <SpecialNotes
        notes={["전체 보장현황(합계형) 문서는 계약별 보장 귀속이 없어 해지를 보장 합계에 반영할 수 없습니다 — 해당 보장행은 [전] 합계 수준으로 유지됩니다."]}
      />,
    );
    expect(screen.getByText(/합계형.*해지/)).toBeInTheDocument();
    expect(screen.getByText("특이사항")).toBeInTheDocument();
  });
});
