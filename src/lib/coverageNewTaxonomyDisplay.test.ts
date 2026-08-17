// BOHUMFIT-247: 신 체계 표시 미러 회귀 — 익명 합성 픽스처만 사용.
// 단계·Y/N 수식은 backend/coverage/constants.py(정본)의 미러다(값 동일성은 246 백엔드
// 테스트가 고정 — 여기서는 클라이언트 이월·정렬·overview 패리티를 고정한다).
import { describe, expect, it } from "vitest";
import {
  buildAfterResult,
  computeStageTotals,
  displayStageTotals,
  displayYnFlags,
  computeYnFlags,
  itemOrderKey,
  ITEM_ORDER,
  type AnalyzeResult,
  type BeforeCoverage,
} from "./coverageAfterDisplayCache";

const MAN = 10_000;

function coverage(partial: Partial<BeforeCoverage> & { kb_name: string }): BeforeCoverage {
  return {
    kb_group: partial.group12 || "기타",
    group12: "기타",
    agg: "sum",
    summary: null,
    by_company: {},
    enrolled: false,
    ...partial,
  };
}

function analysisWith(coverages: BeforeCoverage[]): AnalyzeResult {
  return {
    before: {
      customer: { name: "홍길동", age: 50, sex: "남" },
      premium: { monthly_total: 80_000, monthly_total_active: 80_000, paid_total: 0, currency: "KRW" },
      companies: [
        {
          idx: 1, insurer: "가나손보", product: "합성1", contract_date: "2024-01-01", pay_cycle: "월납",
          pay_years: 20, pay_months: 240, maturity: "100세", monthly_premium: 50_000, paid_total: null, remark: null,
        },
        {
          idx: 2, insurer: "다라생명", product: "합성2", contract_date: "2024-01-01", pay_cycle: "월납",
          pay_years: 20, pay_months: 240, maturity: "100세", monthly_premium: 30_000, paid_total: null, remark: null,
        },
      ],
      coverages,
    },
    final: { premium: { monthly_total: 80_000, paid_total: 0 }, coverages: [], rollup_by_group12: [] },
    warnings: [],
  };
}

describe("BOHUMFIT-247 신 체계 표시 미러", () => {
  it("itemOrderKey — 시트2 항목 순서(일반사망 최상단·목록 밖은 뒤)", () => {
    expect(itemOrderKey("일반사망")).toBe(0);
    expect(itemOrderKey("질병사망")).toBeLessThan(itemOrderKey("상해사망"));
    expect(itemOrderKey("중입자방사선")).toBeGreaterThan(itemOrderKey("표적항암치료"));
    expect(itemOrderKey("80%이상 후유장해")).toBe(ITEM_ORDER.length); // 기타(목록 밖)
  });

  it("computeStageTotals — 비분양식 시트3 수식(공통 가산 = 5종 + 질병수술)", () => {
    const stages = computeStageTotals([
      coverage({ kb_name: "뇌혈관질환", group12: "뇌", summary: 1000 * MAN, enrolled: true }),
      coverage({ kb_name: "뇌졸중", group12: "뇌", summary: 2000 * MAN, enrolled: true }),
      coverage({ kb_name: "뇌출혈", group12: "뇌", summary: 3000 * MAN, enrolled: true }),
      coverage({ kb_name: "뇌혈관수술", group12: "뇌", summary: 300 * MAN, enrolled: true }),
      coverage({ kb_name: "일반종수술 5종(표준환산)", group12: "종수술", summary: 1000 * MAN, enrolled: true, estimated: true }),
      coverage({ kb_name: "질병수술", group12: "수술", summary: 200 * MAN, enrolled: true }),
    ]);
    const common = (1000 + 200) * MAN;
    expect(stages["뇌초기"]).toBe((1000 + 2000 + 3000 + 300) * MAN + common);
    expect(stages["뇌중기"]).toBe((2000 + 3000 + 300) * MAN + common);
    expect(stages["뇌말기"]).toBe((3000 + 300) * MAN + common);
    expect(stages["암"]).toBe(common); // 암 담보 없음 → 공통 가산만
  });

  it("computeYnFlags — 원천 1건 이상 enrolled면 Y(COUNTA 등가)", () => {
    const flags = computeYnFlags([
      coverage({ kb_name: "교통사고처리지원금", group12: "가입특약(Y/N)", summary: 10000 * MAN, enrolled: true }),
      coverage({ kb_name: "질병입원의료비", group12: "가입특약(Y/N)", summary: null, enrolled: false }),
    ]);
    const byItem = Object.fromEntries(flags.map((flag) => [flag.item, flag.value]));
    expect(byItem["운전자특약"]).toBe("Y");
    expect(byItem["질병실손의료비"]).toBe("N");
    expect(flags).toHaveLength(5);
  });

  it("overview 합계-only 행 — 해지 0이면 [후] 완전 동일(246 회송 보정 패리티)", () => {
    const analysis = analysisWith([
      coverage({ kb_name: "상해사망", group12: "사망", summary: 30000 * MAN, enrolled: true, overview: true }),
      coverage({ kb_name: "암진단금", group12: "암", summary: 10000 * MAN, enrolled: true, overview: true }),
      coverage({ kb_name: "깁스치료비", group12: "골절", summary: 50 * MAN, enrolled: true, by_company: { "2": 50 * MAN } }),
    ]);
    const after = buildAfterResult(analysis, {}, []);
    const rows = Object.fromEntries(after.after.before.coverages.map((row) => [row.kb_name, row]));
    expect(rows["상해사망"].summary).toBe(30000 * MAN);
    expect(rows["상해사망"].enrolled).toBe(true);
    expect(rows["암진단금"].summary).toBe(10000 * MAN);
    expect(after.after.before.coverages).toHaveLength(3); // 행수 소실 0
    // 파생값도 전=후 동일.
    expect(computeStageTotals(after.after.before.coverages)).toEqual(computeStageTotals(analysis.before.coverages));
    expect(computeYnFlags(after.after.before.coverages)).toEqual(computeYnFlags(analysis.before.coverages));
  });

  // ── ★BOHUMFIT-295: 제안서 없음 → [후] == [전] 불변식 (실사용 회귀 재현) ──────────────
  //   payload 담보 이름이 290 이후 **V2 49행 표시명**이라 구 40행 이름 미러(computeStageTotals·
  //   computeYnFlags)로는 전부 0/N이 된다. [전]은 서버 파생값을 쓰고 [후]만 재산출해 비대칭이었다.
  const v2Analysis = () =>
    analysisWith([
      coverage({ kb_name: "뇌 혈 관 질 환", group12: "뇌", summary: 4000 * MAN, enrolled: true, by_company: { "1": 4000 * MAN } }),
      coverage({ kb_name: "상 해/질 병 입 원", group12: "실 비", summary: 5000 * MAN, enrolled: true, by_company: { "1": 5000 * MAN } }),
      // 292 Phase E 결합 담보 — 비고행이라 **구 이름 그대로** 남는다(암 체인 오염의 통로였다)
      coverage({ kb_name: "항암약물방사선", group12: "비고", summary: 1410 * MAN, enrolled: true, by_company: { "2": 1410 * MAN } }),
    ]);

  it("295 — 제안서·해지 0이면 [후] 파생값이 [전]과 같다(서버 값 보존)", () => {
    const analysis = v2Analysis();
    analysis.before.stage_totals = { 뇌초기: 4000 * MAN, 뇌중기: 4000 * MAN, 뇌말기: 4000 * MAN };
    analysis.before.yn_flags = [
      { item: "상해실손의료비", value: "Y", sources: [{ kb_name: "상해입원의료비", summary: 5000 * MAN }] },
    ];
    const after = buildAfterResult(analysis, {}, []);
    expect(after.after.before.stage_totals).toEqual(analysis.before.stage_totals);
    expect(after.after.before.yn_flags).toEqual(analysis.before.yn_flags);
    // ★회귀 재현: 구 이름 미러로 재산출하면 뇌가 0이 되고 암에 비고행 1,410만이 들어온다.
    const legacyMirror = computeStageTotals(after.after.before.coverages);
    expect(legacyMirror["뇌초기"]).toBe(0);
    expect(legacyMirror["암"]).toBe(1410 * MAN);
    // 화면은 파생값을 우선 쓰므로 그 오염이 표시되지 않는다.
    expect(after.after.before.stage_totals!["뇌초기"]).toBe(4000 * MAN);
    expect(Object.keys(after.after.before.stage_totals!)).not.toContain("암");
  });

  it("295 — 해지가 있으면 stale 파생값을 지운다([전] 값을 [후]인 척 보이지 않는다)", () => {
    const analysis = v2Analysis();
    analysis.before.stage_totals = { 뇌초기: 4000 * MAN };
    analysis.before.yn_flags = [{ item: "상해실손의료비", value: "Y", sources: [] }];
    const after = buildAfterResult(analysis, { "1": { disposition: "cancel" } }, []);
    expect(after.after.before.stage_totals).toBeUndefined();
    expect(after.after.before.yn_flags).toBeUndefined();
  });

  it("295 — 표시 선택은 [전]·[후]가 **같은 헬퍼**를 쓴다(비대칭이 재발하면 실패)", () => {
    const analysis = v2Analysis();
    analysis.before.stage_totals = { 뇌초기: 4000 * MAN };
    analysis.before.yn_flags = [{ item: "상해실손의료비", value: "Y", sources: [] }];
    const after = buildAfterResult(analysis, {}, []);
    // 화면이 쓰는 선택 함수 — 제안서 0건이면 전·후가 완전히 같아야 한다(불변식).
    expect(displayStageTotals(after.after.before)).toEqual(displayStageTotals(analysis.before));
    expect(displayYnFlags(after.after.before)).toEqual(displayYnFlags(analysis.before));
    expect(displayStageTotals(after.after.before)!["뇌초기"]).toBe(4000 * MAN);   // 0이 아니다
    expect(displayYnFlags(after.after.before)![0].value).toBe("Y");               // N이 아니다
    expect(displayStageTotals(null)).toBeNull();
  });

  it("295 — stage_totals가 없는 구 payload는 종전대로 클라 미러 폴백(하위호환)", () => {
    const analysis = analysisWith([
      coverage({ kb_name: "뇌혈관질환", group12: "뇌", summary: 1000 * MAN, enrolled: true, by_company: { "1": 1000 * MAN } }),
    ]);
    const after = buildAfterResult(analysis, {}, []);
    expect(after.after.before.stage_totals).toBeUndefined();
    expect(computeStageTotals(after.after.before.coverages)).toEqual(computeStageTotals(analysis.before.coverages));
  });

  it("overview + 해지 — 합계행 보존 + 경고, 계약 키 담보는 정상 해지 반영", () => {
    const analysis = analysisWith([
      coverage({ kb_name: "상해사망", group12: "사망", summary: 30000 * MAN, enrolled: true, overview: true }),
      coverage({ kb_name: "깁스치료비", group12: "골절", summary: 50 * MAN, enrolled: true, by_company: { "2": 50 * MAN } }),
    ]);
    const after = buildAfterResult(analysis, { "2": { disposition: "cancel" } }, []);
    const rows = Object.fromEntries(after.after.before.coverages.map((row) => [row.kb_name, row]));
    expect(rows["상해사망"].summary).toBe(30000 * MAN); // 합계 수준 보존
    expect(rows["깁스치료비"].enrolled).toBe(false); // 계약2 해지 반영
    expect(after.comparison.cautions.some((caution) => caution.message.includes("합계"))).toBe(true);
    expect(after.after.before.premium.monthly_total).toBe(50_000); // 보험료는 유지 계약 기준
  });

  it("계약 미상 키('?')는 해지와 무관하게 이월(246 백엔드 동일 규칙)", () => {
    const analysis = analysisWith([
      coverage({ kb_name: "재해사망(계약 미확인)", group12: "기타", summary: 10000 * MAN, enrolled: true, by_company: { "?": 10000 * MAN } }),
    ]);
    const after = buildAfterResult(analysis, { "1": { disposition: "cancel" } }, []);
    const row = after.after.before.coverages[0];
    expect(row.summary).toBe(10000 * MAN);
    expect(row.by_company["?"]).toBe(10000 * MAN);
  });
});
