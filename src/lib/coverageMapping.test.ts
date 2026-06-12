// BOHUMFIT-041: 보장분석 매핑 엔진 단위테스트.
// 케이스는 업로드된 '원천자료 샘플.xlsx' 실데이터를 그대로 옮겼다(교보/신한/AIA/흥국/삼성 + 하나).
import { describe, expect, it } from "vitest";

import {
  COVERAGE_CATEGORIES,
  applyConsultingPlan,
  buildAfterTable,
  buildContractColumn,
  buildCoverageTable,
  decomposeDeath,
  mapCoverageName,
  normalizeCoverageName,
  parseSourceRows,
  suggestSurgeryTiers,
  type Contract,
} from "./coverageMapping";

function mkContract(
  id: string,
  insurer: string,
  premiumWon: number,
  coverages: Array<[string, number]>,
  extra?: Partial<Contract>,
): Contract {
  return {
    id,
    insurer,
    premiumWon,
    coverages: coverages.map(([name, amountManwon]) => ({ name, amountManwon })),
    ...extra,
  };
}

// ── 원천자료 샘플 계약 (가입금액: 만원, 보험료: 원) ──────────────────────────
const KYOBO_1 = mkContract("kyobo-1", "교보생명", 66200, [
  ["질병사망", 500],
  ["암사망", 750],
  ["암사망", 750],
  ["상해사망", 1000],
  ["암진단", 500],
  ["특정암진단", 333],
  ["특정상해입원일당", 10],
  ["특정상해입원일당", 30],
]);

const KYOBO_2 = mkContract("kyobo-2", "교보생명", 112000, [
  ["질병사망", 10000],
  ["상해사망", 10000],
]);

const SHINHAN = mkContract("shinhan-1", "신한생명", 80960, [
  ["질병사망", 10000],
  ["상해사망", 30000],
  ["상해후유장해", 10000],
  ["뇌졸중진단", 3000],
  ["급성심근경색진단", 3000],
  ["암진단", 2000],
  ["질병종수술", 240],
  ["암수술", 400],
  ["상해종수술", 240],
  ["질병입원일당", 4],
  ["암입원일당", 20],
  ["상해입원일당", 4],
]);

const AIA = mkContract("aia-1", "AIA생명", 28650, [
  ["암진단", 5000],
  ["고액암진단", 5000],
  ["소액암진단", 500],
  ["특정암진단", 1000],
  ["표적항암약물치료비", 5000],
]);

const HANA = mkContract("hana-1", "하나생명", 1510, [
  ["특정질병사망", 1000],
  ["특정질병사망", 1000],
  ["특정상해진단", 100],
  ["특정질병수술", 10],
]);

const HEUNGKUK = mkContract("heungkuk-1", "흥국화재", 50000, [
  ["상해사망", 1000],
  ["상해후유장해", 1000],
  ["상해80%이상후유장해", 1000],
]);

const SAMSUNG = mkContract("samsung-1", "삼성화재", 20000, [
  ["상해사망", 1000],
  ["상해후유장해", 1000],
  ["상해80%이상후유장해", 1000],
  ["골절진단", 30],
  ["중대골절진단", 30],
  ["특정상해수술", 50],
  ["자동차사고부상위로금", 10],
  ["깁스치료", 10],
]);

// ── 카테고리 정의 ────────────────────────────────────────────────────────────
describe("표준 카테고리 36행", () => {
  it("비분표 순서 그대로 36행이 정의된다", () => {
    expect(COVERAGE_CATEGORIES).toHaveLength(36);
    expect(COVERAGE_CATEGORIES.map((c) => c.label)).toEqual([
      "일반사망", "재해사망", "상해사망", "질병사망",
      "상해후유장해", "질병후유장해",
      "암진단금", "유사암 진단금", "표적항암치료", "차세대암치료", "암수술",
      "뇌혈관(초기)", "뇌졸중(중기)", "뇌출혈(말기)", "뇌혈관수술",
      "허혈심질환(초기)", "급성심근경색(말기)", "심혈관수술",
      "일반종수술 1종", "일반종수술 2종", "일반종수술 3종", "일반종수술 4종", "일반종수술 5종",
      "상해수술", "질병수술", "질병입원", "상해입원",
      "응급실 내원비", "골절진단비", "화상진단비",
      "운전자특약", "자동차부상치료비", "가족일상배상책임", "상해실손의료비", "질병실손의료비",
      "보험료 합계",
    ]);
  });

  it("Y/N형 5행 + 보험료 1행의 kind 가 구분된다", () => {
    const kinds = Object.fromEntries(COVERAGE_CATEGORIES.map((c) => [c.id, c.kind]));
    expect(kinds.driver_rider).toBe("flag");
    expect(kinds.disease_medical_indemnity).toBe("flag");
    expect(kinds.premium).toBe("premium");
    expect(kinds.general_death).toBe("amount");
  });
});

// ── 보장명 매핑 ──────────────────────────────────────────────────────────────
describe("보장명 → 카테고리 매핑", () => {
  it("태스크 시드 매핑이 동작한다", () => {
    expect(mapCoverageName("질병사망")).toBe("disease_death");
    expect(mapCoverageName("상해사망")).toBe("injury_death");
    expect(mapCoverageName("암진단")).toBe("cancer_diagnosis");
    expect(mapCoverageName("고액암진단")).toBe("cancer_diagnosis");
    expect(mapCoverageName("소액암진단")).toBe("minor_cancer_diagnosis");
    expect(mapCoverageName("특정암진단")).toBe("minor_cancer_diagnosis");
    expect(mapCoverageName("표적항암약물치료비")).toBe("targeted_anticancer");
    expect(mapCoverageName("뇌졸중진단")).toBe("stroke_mid");
    expect(mapCoverageName("급성심근경색진단")).toBe("ami_late");
    expect(mapCoverageName("질병종수술")).toBe("general_surgery");
    expect(mapCoverageName("상해종수술")).toBe("general_surgery");
    expect(mapCoverageName("질병입원일당")).toBe("disease_hospitalization");
    expect(mapCoverageName("상해입원일당")).toBe("injury_hospitalization");
    expect(mapCoverageName("골절진단")).toBe("fracture_diagnosis");
    expect(mapCoverageName("중대골절진단")).toBe("fracture_diagnosis");
  });

  it("정규화: 전각·괄호·공백을 흡수한다", () => {
    expect(normalizeCoverageName("암진단（갱신）")).toBe("암진단");
    expect(mapCoverageName("암진단（갱신）")).toBe("cancer_diagnosis");
    expect(mapCoverageName(" 질병 사망 ")).toBe("disease_death");
  });

  it("매핑 불가 보장명은 null (드롭 아님 — unmapped 경로)", () => {
    expect(mapCoverageName("암사망")).toBeNull();
    expect(mapCoverageName("깁스치료")).toBeNull();
    expect(mapCoverageName("")).toBeNull();
  });
});

// ── 사망 분해 3분기 ──────────────────────────────────────────────────────────
describe("사망 분해 룰", () => {
  it("질병=상해 → 일반사망", () => {
    const d = decomposeDeath(10000, 10000);
    expect(d).toMatchObject({ branch: "equal", general: 10000, disaster: 0, injury: 0, disease: 0 });
  });

  it("질병<상해 → 일반=질병, 재해=차액 (검증례: 질병1억+상해3억→일반1억+재해2억)", () => {
    const d = decomposeDeath(10000, 30000);
    expect(d).toMatchObject({ branch: "injury_excess", general: 10000, disaster: 20000, injury: 0, disease: 0 });
  });

  it("질병사망 없음 → 상해사망 행 유지", () => {
    const d = decomposeDeath(0, 1000);
    expect(d).toMatchObject({ branch: "injury_only", general: 0, disaster: 0, injury: 1000, disease: 0 });
  });

  it("(보수적 추가 분기) 상해 없음 → 질병 유지 / 질병>상해 → 일반=상해, 질병 잔여", () => {
    expect(decomposeDeath(500, 0)).toMatchObject({ branch: "disease_only", disease: 500 });
    expect(decomposeDeath(3000, 1000)).toMatchObject({
      branch: "disease_excess", general: 1000, disaster: 0, injury: 0, disease: 2000,
    });
  });
});

// ── 종수술 자동셋팅 ──────────────────────────────────────────────────────────
describe("일반종수술 자동셋팅", () => {
  it("기준표 정확 구간 (500만원)", () => {
    const t = suggestSurgeryTiers(500);
    expect(t).not.toBeNull();
    expect(t!.values).toEqual([10, 30, 50, 100, 500]);
    expect(t!.interpolated).toBe(false);
    expect(t!.suggested).toBe(true);
  });

  it("보간 구간 (800만원 = 600·1000 중간)", () => {
    const t = suggestSurgeryTiers(800);
    expect(t!.values).toEqual([20, 55, 100, 350, 800]); // 1~4종 선형 보간, 5종=가입금액
    expect(t!.interpolated).toBe(true);
  });

  it("보간 구간 (240만원, 100~500 사이 t=0.35)", () => {
    const t = suggestSurgeryTiers(240);
    expect(t!.values).toEqual([7, 20, 34, 68, 240]);
  });

  it("표 범위 밖은 경계 행 비례 외삽, 0 이하는 null", () => {
    expect(suggestSurgeryTiers(6000)!.values).toEqual([100, 200, 400, 2000, 6000]);
    expect(suggestSurgeryTiers(50)!.values).toEqual([3, 8, 13, 25, 50]);
    expect(suggestSurgeryTiers(0)).toBeNull();
  });
});

// ── 원천자료 샘플 기반 변환 ──────────────────────────────────────────────────
describe("계약 → 비분표 열 (원천자료 샘플)", () => {
  it("교보1: 사망분해(500<1000) + 유사암 + 입원일당 합산 + 암사망 unmapped 보존", () => {
    const col = buildContractColumn(KYOBO_1);
    expect(col.cells.general_death).toBe(500);
    expect(col.cells.disaster_death).toBe(500);
    expect(col.cells.injury_death).toBe(0);
    expect(col.cells.disease_death).toBe(0);
    expect(col.cells.cancer_diagnosis).toBe(500);
    expect(col.cells.minor_cancer_diagnosis).toBe(333);
    expect(col.cells.injury_hospitalization).toBe(40); // 10 + 30
    expect(col.cells.premium).toBe(66200);
    expect(col.unmapped).toEqual([
      { name: "암사망", amountManwon: 750, contractId: "kyobo-1" },
      { name: "암사망", amountManwon: 750, contractId: "kyobo-1" },
    ]);
  });

  it("교보2: 질병=상해 → 일반사망 1억", () => {
    const col = buildContractColumn(KYOBO_2);
    expect(col.cells.general_death).toBe(10000);
    expect(col.cells.disaster_death).toBe(0);
    expect(col.cells.injury_death).toBe(0);
    expect(col.cells.disease_death).toBe(0);
  });

  it("신한: 검증례 사망분해 + 종수술 480 보간 + 암입원일당→질병입원", () => {
    const col = buildContractColumn(SHINHAN);
    // 질병 1억 + 상해 3억 → 일반 1억 + 재해 2억
    expect(col.cells.general_death).toBe(10000);
    expect(col.cells.disaster_death).toBe(20000);
    // 종수술: 질병 240 + 상해 240 = 480 (5종 기준) → 보간 제안
    expect(col.cells.general_surgery_type1).toBe(10);
    expect(col.cells.general_surgery_type2).toBe(29);
    expect(col.cells.general_surgery_type3).toBe(49);
    expect(col.cells.general_surgery_type4).toBe(98);
    expect(col.cells.general_surgery_type5).toBe(480);
    expect(col.suggested.general_surgery_type1).toBe(true);
    expect(col.suggested.general_surgery_type5).toBe(true);
    // 진단·수술·입원
    expect(col.cells.stroke_mid).toBe(3000);
    expect(col.cells.ami_late).toBe(3000);
    expect(col.cells.cancer_diagnosis).toBe(2000);
    expect(col.cells.cancer_surgery).toBe(400);
    expect(col.cells.disease_hospitalization).toBe(24); // 질병입원일당 4 + 암입원일당 20
    expect(col.cells.injury_hospitalization).toBe(4);
    expect(col.unmapped).toEqual([]);
  });

  it("AIA: 암 계열 합산(암+고액암→암진단금, 소액·특정→유사암) + 표적항암", () => {
    const col = buildContractColumn(AIA);
    expect(col.cells.cancer_diagnosis).toBe(10000);
    expect(col.cells.minor_cancer_diagnosis).toBe(1500);
    expect(col.cells.targeted_anticancer).toBe(5000);
    expect(col.cells.general_death).toBe(0);
  });

  it("흥국: 질병사망 없음 → 상해사망 유지, 80%이상후유장해 합산", () => {
    const col = buildContractColumn(HEUNGKUK);
    expect(col.cells.injury_death).toBe(1000);
    expect(col.cells.general_death).toBe(0);
    expect(col.cells.disaster_death).toBe(0);
    expect(col.cells.injury_disability).toBe(2000);
  });

  it("삼성: 골절 합산 + 자부상 Y/N + 깁스치료 unmapped", () => {
    const col = buildContractColumn(SAMSUNG);
    expect(col.cells.injury_death).toBe(1000);
    expect(col.cells.fracture_diagnosis).toBe(60); // 골절 30 + 중대골절 30
    expect(col.cells.injury_surgery).toBe(50);
    expect(col.cells.car_injury_treatment).toBe(true); // Y/N형 — 금액 아닌 존재 여부
    expect(col.unmapped).toEqual([{ name: "깁스치료", amountManwon: 10, contractId: "samsung-1" }]);
  });

  it("하나: 특정질병사망/특정상해진단은 unmapped 보존(드롭 금지)", () => {
    const col = buildContractColumn(HANA);
    expect(col.cells.disease_death).toBe(0); // '특정'질병사망은 임의 합산하지 않는다
    expect(col.cells.disease_surgery).toBe(10);
    expect(col.unmapped.map((u) => u.name)).toEqual(["특정질병사망", "특정질병사망", "특정상해진단"]);
  });
});

// ── 합계 (전/후 공용) ────────────────────────────────────────────────────────
describe("비분표 합계", () => {
  it("amount 합산 + flag OR + 보험료 합", () => {
    const table = buildCoverageTable([KYOBO_1, KYOBO_2, SHINHAN, AIA, HANA, HEUNGKUK, SAMSUNG]);
    expect(table.columns).toHaveLength(7);
    // 일반사망: 교보1 500 + 교보2 10000 + 신한 10000
    expect(table.totals.general_death).toBe(20500);
    // 재해사망: 교보1 500 + 신한 20000
    expect(table.totals.disaster_death).toBe(20500);
    // 상해사망 유지분: 흥국 1000 + 삼성 1000
    expect(table.totals.injury_death).toBe(2000);
    // 암진단금: 교보1 500 + 신한 2000 + AIA 10000
    expect(table.totals.cancer_diagnosis).toBe(12500);
    expect(table.totals.car_injury_treatment).toBe(true);
    expect(table.totals.driver_rider).toBe(false);
    expect(table.totals.premium).toBe(66200 + 112000 + 80960 + 28650 + 1510 + 50000 + 20000);
    // unmapped 집계 — 드롭 금지
    expect(table.unmapped.map((u) => u.name).sort()).toEqual(
      ["깁스치료", "암사망", "암사망", "특정상해진단", "특정질병사망", "특정질병사망"].sort(),
    );
  });
});

// ── 컨설팅 후 모델 (유지/해지 + 감액 override + 신규 제안) ───────────────────
describe("컨설팅 후 계산 (전/후 동일 순수 함수)", () => {
  it("해지 계약 제외 + 담보 감액 override + 보험료 수기 조정 반영", () => {
    const kept: Contract = {
      ...KYOBO_2,
      status: "유지",
      overridePremiumWon: 60000, // 감액에 따른 보험료 수기 조정
      coverages: [
        { name: "질병사망", amountManwon: 10000, overrideAmountManwon: 5000 }, // 1억 → 5천 감액
        { name: "상해사망", amountManwon: 10000 },
      ],
    };
    const cancelled: Contract = { ...SHINHAN, status: "해지" };
    const proposal = mkContract("proposal-1", "신규제안", 45000, [
      ["암진단", 3000],
      ["질병실손의료비", 1],
    ]);

    const after = buildAfterTable([kept, cancelled], [proposal]);

    expect(after.columns.map((c) => c.contractId)).toEqual(["kyobo-2", "proposal-1"]); // 해지 제외
    // 감액 반영: 질병 5000 < 상해 10000 → 일반 5000 + 재해 5000
    const keptCol = after.columns[0];
    expect(keptCol.cells.general_death).toBe(5000);
    expect(keptCol.cells.disaster_death).toBe(5000);
    expect(keptCol.cells.premium).toBe(60000);
    // 신규 제안 포함 합계
    expect(after.totals.cancer_diagnosis).toBe(3000);
    expect(after.totals.disease_medical_indemnity).toBe(true);
    expect(after.totals.premium).toBe(60000 + 45000);
  });

  it("후 비분표는 전과 동일한 함수로 계산된다 (별도 후 전용 로직 금지)", () => {
    const contracts = [KYOBO_1, { ...HEUNGKUK, status: "해지" as const }];
    const viaAfter = buildAfterTable(contracts);
    const viaSamePureFn = buildCoverageTable(applyConsultingPlan(contracts));
    expect(viaAfter).toEqual(viaSamePureFn);
  });

  it("applyConsultingPlan 은 순수 함수 — 입력을 변경하지 않는다", () => {
    const original: Contract = {
      ...KYOBO_2,
      coverages: [{ name: "질병사망", amountManwon: 10000, overrideAmountManwon: 5000 }],
    };
    const snapshot = JSON.parse(JSON.stringify(original)) as Contract;
    applyConsultingPlan([original]);
    expect(original).toEqual(snapshot);
  });
});

// ── 042 자리 ────────────────────────────────────────────────────────────────
describe("parseSourceRows (BOHUMFIT-042 예정)", () => {
  it("시그니처만 정의 — 호출 시 명시적 에러", () => {
    expect(() => parseSourceRows([])).toThrowError(/042/);
  });
});
