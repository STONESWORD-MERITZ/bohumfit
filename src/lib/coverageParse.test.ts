// BOHUMFIT-042: 원천자료 파서 단위테스트.
// ⚠️ 픽스처는 전부 익명 합성 데이터(실명·실보험사·실상품 금지) — 원천자료 '양식 구조'만 재현한다.
import { describe, expect, it } from "vitest";

import { buildCoverageTable } from "./coverageMapping";
import {
  MANUAL_EXCLUDE,
  SourceFormatError,
  applyManualAssignments,
  listAssignableTargets,
  matrixToSourceRows,
  parseSourceMatrix,
  parseSourceRows,
  parseSourceRowsDetailed,
  type SourceCell,
} from "./coverageParse";

const N = null;

/** 원천자료 양식 재현: 그룹 헤더 1행 + 열 헤더 1행 + 병합셀(빈 값) 패턴 데이터 */
function fixtureMatrix(): SourceCell[][] {
  return [
    ["계 약 정 보", N, N, N, N, N, N, N, "담 보 정 보", N, N, N],
    ["회사명", "상품명", "구분", "보험시기", "보험종기", "납입주기", "납입기간(년)", "납입보험료", "담보명", "보장명", "상태", "가입금액(만원)"],
    // ── 계약 1: A생명 테스트상품알파 (Date 인스턴스 / 종신 / 질병=상해) ──
    ["A생명", "테스트상품알파", "피보험자", new Date(2010, 2, 15), "9999-12-31", "월납", "20", 50000, "주계약", "질병사망", "정상", 5000],
    [N, N, "피보험자", new Date(2010, 2, 15), "9999-12-31", "월납", "20", 50000, "주계약", "상해사망", "정상", 5000],
    [N, N, "피보험자", new Date(2010, 2, 15), "9999-12-31", "월납", "20", 50000, "특약", "암진단", "정상", 1000],
    [N, N, N, N, N, N, N, N, N, N, N, N], // 빈 행 — 스킵
    // ── 계약 2: 상품명만으로 경계 (회사명 forward-fill, 엑셀 직렬 날짜) ──
    [N, "테스트상품베타", "피보험자", 44197, "2041-01-01", "월납", "20", 30000, "주계약", "질병사망", "정상", 1000],
    [N, N, "피보험자", 44197, "2041-01-01", "월납", "20", 30000, "주계약", "상해사망", "정상", 3000],
    [N, N, "피보험자", 44197, "2041-01-01", "월납", "20", 30000, "특약", "질병종수술", "정상", 100],
    [N, N, "피보험자", 44197, "2041-01-01", "월납", "20", 30000, "특약", N, "정상", 10],          // 보장명 없음
    [N, N, "피보험자", 44197, "2041-01-01", "월납", "20", 30000, "특약", "암진단", "정상", "abc"], // 금액 해석 불가
    [N, N, "피보험자", 44197, "2041-01-01", "월납", "20", 30000, "특약", "유사암진단", "해지", 500], // 해지 — 제외
    [N, N, "피보험자", 44197, "2041-01-01", "월납", "20", 30000, "특약", "골절진단", "검토중", 30],  // 미상 상태 — 포함+경고
    [N, N, "피보험자", 44197, "2041-01-01", "월납", "20", 30000, "특약", "외계보장", "정상", 50],    // unmapped
    // ── 계약 3: 회사명만으로 경계 (상품명 없음 블록) + 보험료 상이 행 ──
    ["B화재", N, "피보험자", "2022-05-01", "2032-05-01", "월납", "10", 20000, "주계약", "상해사망", "정상", 1000],
    [N, N, "피보험자", "2022-05-01", "2032-05-01", "월납", "10", 25000, "특약", "골절진단", "정상", 30],
  ];
}

describe("matrixToSourceRows — 헤더 탐지·forward-fill·날짜 통일", () => {
  it("그룹 헤더를 건너뛰고 열 헤더를 찾는다", () => {
    const { rows, headerRowIndex } = matrixToSourceRows(fixtureMatrix());
    expect(headerRowIndex).toBe(1);
    expect(rows.length).toBe(13); // 빈 행 1개 제외한 데이터 행 (3+8+2)
  });

  it("병합셀 패턴: 회사명·상품명·계약 메타가 아래 행으로 채워진다", () => {
    const { rows } = matrixToSourceRows(fixtureMatrix());
    expect(rows[1].insurer).toBe("A생명");
    expect(rows[1].productName).toBe("테스트상품알파");
    // 계약 2 — 상품명만 새로 시작, 회사명은 직전 값 유지
    expect(rows[3].insurer).toBe("A생명");
    expect(rows[3].productName).toBe("테스트상품베타");
    // 계약 3 — 회사명만 새로 시작, 상품명 없음 블록
    expect(rows[12].insurer).toBe("B화재");
    expect(rows[12].productName).toBeUndefined();
  });

  it("날짜: Date 인스턴스·엑셀 직렬값·문자열 모두 YYYY-MM-DD", () => {
    const { rows } = matrixToSourceRows(fixtureMatrix());
    expect(rows[0].startDate).toBe("2010-03-15"); // Date 인스턴스
    expect(rows[0].endDate).toBe("9999-12-31");   // 문자열 그대로(종신)
    expect(rows[3].startDate).toBe("2021-01-01"); // 엑셀 직렬값 44197
  });

  it("필수 열이 없으면 SourceFormatError", () => {
    expect(() => matrixToSourceRows([["아무거나", "다른것"], ["값1", "값2"]])).toThrow(SourceFormatError);
    expect(() =>
      matrixToSourceRows([["회사명", "보장명"], ["A생명", "질병사망"]]),
    ).toThrow(/가입금액/); // 회사명·보장명은 있어도 가입금액 누락
  });
});

describe("parseSourceRowsDetailed — 계약 그룹핑·경고 보존", () => {
  it("계약 3건으로 묶이고 메타가 유지된다", () => {
    const { contracts } = parseSourceMatrix(fixtureMatrix());
    expect(contracts).toHaveLength(3);
    expect(contracts.map((c) => c.id)).toEqual(["ct1", "ct2", "ct3"]);
    expect(contracts[0]).toMatchObject({
      insurer: "A생명", productName: "테스트상품알파", startDate: "2010-03-15",
      payYears: "20", premiumWon: 50000,
    });
    expect(contracts[1]).toMatchObject({ insurer: "A생명", productName: "테스트상품베타", premiumWon: 30000 });
    expect(contracts[2]).toMatchObject({ insurer: "B화재", premiumWon: 20000 });
    expect(contracts[0].coverages).toHaveLength(3);
    // 계약 2: 정상 3건 + 미상상태 포함 1건 + unmapped 1건 = 5 (보장명없음/금액불가/해지 제외)
    expect(contracts[1].coverages).toHaveLength(5);
    expect(contracts[2].coverages).toHaveLength(2);
  });

  it("실패 행은 버리지 않고 경고 5건으로 보존된다", () => {
    const { warnings } = parseSourceMatrix(fixtureMatrix());
    const reasons = warnings.map((w) => w.reason);
    expect(warnings).toHaveLength(5);
    expect(reasons.some((r) => r.includes("보장명이 비어"))).toBe(true);
    expect(reasons.some((r) => r.includes("가입금액을 해석하지"))).toBe(true);
    expect(reasons.some((r) => r.includes("'해지'"))).toBe(true);
    expect(reasons.some((r) => r.includes("'검토중'") && r.includes("포함"))).toBe(true);
    expect(reasons.some((r) => r.includes("납입보험료가 행마다"))).toBe(true);
    // 경고에 엑셀 행 번호(1-base)가 담긴다
    const noName = warnings.find((w) => w.reason.includes("보장명이 비어"));
    expect(noName?.rowNo).toBe(10);
  });

  it("BOHUMFIT-041 parseSourceRows 시그니처와 연결된다", () => {
    const { rows } = matrixToSourceRows(fixtureMatrix());
    const viaSignature = parseSourceRows(rows);
    const viaDetailed = parseSourceRowsDetailed(rows).contracts;
    expect(viaSignature).toEqual(viaDetailed);
  });
});

describe("041 lib 통합 — 파싱 결과 그대로 비분표 산출(재구현 없음)", () => {
  it("사망분해·종수술·합계가 lib 결과로 나온다", () => {
    const { contracts } = parseSourceMatrix(fixtureMatrix());
    const table = buildCoverageTable(contracts);
    // 계약1: 질병5000=상해5000 → 일반사망
    expect(table.columns[0].cells.general_death).toBe(5000);
    // 계약2: 질병1000<상해3000 → 일반1000+재해2000, 종수술 100 정확구간
    expect(table.columns[1].cells.general_death).toBe(1000);
    expect(table.columns[1].cells.disaster_death).toBe(2000);
    expect(table.columns[1].cells.general_surgery_type1).toBe(5);
    expect(table.columns[1].cells.general_surgery_type5).toBe(100);
    expect(table.columns[1].suggested.general_surgery_type1).toBe(true);
    // 계약3: 질병 없음 → 상해사망 유지
    expect(table.columns[2].cells.injury_death).toBe(1000);
    // 합계
    expect(table.totals.general_death).toBe(6000);
    expect(table.totals.fracture_diagnosis).toBe(60); // 검토중 포함 30 + 계약3 30
    expect(table.totals.premium).toBe(100000);
    // unmapped 보존
    expect(table.unmapped.map((u) => u.name)).toEqual(["외계보장"]);
  });
});

describe("applyManualAssignments — 수동 배정/제외 (세션 내 한정)", () => {
  function contractsWithUnmapped() {
    return parseSourceMatrix(fixtureMatrix()).contracts;
  }

  it("카테고리 배정 시 대표 보장명으로 재작성돼 lib 사전을 그대로 탄다", () => {
    const assigned = applyManualAssignments(contractsWithUnmapped(), { 외계보장: "er_visit" });
    const table = buildCoverageTable(assigned);
    expect(table.columns[1].cells.er_visit).toBe(50);
    expect(table.unmapped).toHaveLength(0);
  });

  it("일반종수술 그룹 배정 시 자동셋팅을 탄다", () => {
    const assigned = applyManualAssignments(contractsWithUnmapped(), { 외계보장: "general_surgery" });
    const table = buildCoverageTable(assigned);
    // 기존 100 + 배정 50 = 150 (그룹 합산 후 1회 확장 — 041 규칙)
    expect(table.columns[1].cells.general_surgery_type5).toBe(150);
  });

  it("제외 선택 시 비분표에서 빠지고, 미배정은 unmapped 로 유지된다", () => {
    const excluded = applyManualAssignments(contractsWithUnmapped(), { 외계보장: MANUAL_EXCLUDE });
    expect(buildCoverageTable(excluded).unmapped).toHaveLength(0);
    expect(excluded[1].coverages.map((c) => c.name)).not.toContain("외계보장");

    const untouched = applyManualAssignments(contractsWithUnmapped(), {});
    expect(buildCoverageTable(untouched).unmapped.map((u) => u.name)).toEqual(["외계보장"]);
  });

  it("입력 계약 배열을 변경하지 않는다(순수 함수)", () => {
    const contracts = contractsWithUnmapped();
    const snapshot = JSON.parse(JSON.stringify(contracts)) as unknown;
    applyManualAssignments(contracts, { 외계보장: MANUAL_EXCLUDE });
    expect(contracts).toEqual(snapshot);
  });
});

describe("listAssignableTargets — 드롭다운 옵션", () => {
  it("보험료 제외, 종수술은 그룹 1개, 제외 옵션 포함", () => {
    const targets = listAssignableTargets();
    const values = targets.map((t) => t.value);
    expect(values).not.toContain("premium");
    expect(values).not.toContain("general_surgery_type1");
    expect(values.filter((v) => v === "general_surgery")).toHaveLength(1);
    expect(values).toContain(MANUAL_EXCLUDE);
    // 36행 - 종수술 5행 - 보험료 1행 + 그룹 1 + 제외 1 = 32
    expect(targets).toHaveLength(32);
  });
});
