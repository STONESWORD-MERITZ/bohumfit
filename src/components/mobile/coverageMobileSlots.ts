// BOHUMFIT-266 — 모바일 2단 "주요 담보 8행" 선정 규칙.
//
//   ★S0 실측으로 드러난 사실: 시안의 8개 담보명을 그대로 상수화하면 문서에 따라 3~4칸이 빈다.
//     실 PDF 2건 대조 — 시안 "뇌혈관질환진단비"는 한 문서엔 `뇌혈관질환`, 다른 문서엔 `뇌졸중`/`뇌출혈`로
//     들어오고, "허혈성심장질환진단비"는 `허혈성심장질환` 또는 `급성심근경색`, "실손의료비"는 **양쪽 다 없다**.
//   그래서 8개를 **고정 이름이 아니라 슬롯(의미 단위) + 후보 이름 배열**로 정의한다.
//     · 문서에 실재하는 첫 후보를 채택하고, 못 채운 슬롯은 [후] 금액이 큰 담보로 보충해 항상 8행을 채운다.
//     · 화면에 쓰는 이름은 **실제 kb_name** — 설계사가 원문서와 대조하는 화면이라 임의 라벨은 오히려 방해다.
//   슬롯·후보를 바꿀 일이 생기면 이 파일 한 곳만 고치면 된다(명세의 "상수화" 취지).

/** 2단에 노출할 담보 행 수(시안 고정). */
export const KEY_COVERAGE_COUNT = 8;

export type CoverageSlot = {
  /** 슬롯 식별자(테스트·디버깅용). */
  slot: string;
  /** 우선순위가 높은 순서의 후보 kb_name. 문서에 있는 첫 후보를 쓴다. */
  candidates: string[];
};

/**
 * 슬롯 8종 — 시안 `coverDefs` 순서를 유지하되 후보를 실측 kb_name으로 채웠다.
 *   ★고객이 먼저 묻는 순서(암 → 뇌 → 심장 → 수술 → 실손 → 입원 → 후유장해 → 사망)를 그대로 둔다.
 */
export const COVERAGE_SLOTS: CoverageSlot[] = [
  { slot: "cancer", candidates: ["암진단금", "유사암진단금"] },
  { slot: "brain", candidates: ["뇌혈관질환", "뇌졸중", "뇌출혈"] },
  { slot: "heart", candidates: ["허혈성심장질환", "급성심근경색"] },
  { slot: "surgery", candidates: ["질병수술", "종수술비", "상해수술"] },
  { slot: "indemnity", candidates: ["실손의료비", "실손"] },
  { slot: "hospital", candidates: ["질병입원", "상해입원"] },
  { slot: "disability", candidates: ["질병후유장해", "상해후유장해", "80%이상 후유장해"] },
  { slot: "death", candidates: ["질병사망", "상해사망"] },
];

/** 선정 결과 한 행 — 어느 슬롯에서 왔는지(또는 금액 보충인지)를 남긴다. */
export type KeyCoverage<T> = {
  slot: string;
  row: T;
};

type RowLike = { kb_name: string; after_value: number | null; before_value: number | null };

/** 값이 있는 행인지 — 전·후 모두 비어 있으면 보여줄 것이 없다. */
function hasValue(row: RowLike): boolean {
  return row.after_value != null || row.before_value != null;
}

/**
 * 주요 담보 8행 선정.
 *   ①슬롯 순서대로 후보를 찾아 채우고(중복 담보는 한 번만) ②남은 자리는 [후] 금액이 큰 순으로 보충한다.
 *   ★보충까지 해도 8개가 안 되면 있는 만큼만 돌려준다(빈 행을 만들지 않는다).
 */
export function pickKeyCoverages<T extends RowLike>(rows: T[], limit: number = KEY_COVERAGE_COUNT): KeyCoverage<T>[] {
  const byName = new Map<string, T>();
  for (const row of rows) if (!byName.has(row.kb_name)) byName.set(row.kb_name, row);

  const picked: KeyCoverage<T>[] = [];
  const used = new Set<string>();

  for (const { slot, candidates } of COVERAGE_SLOTS) {
    if (picked.length >= limit) break;
    for (const name of candidates) {
      const row = byName.get(name);
      if (!row || used.has(name) || !hasValue(row)) continue;
      picked.push({ slot, row });
      used.add(name);
      break;
    }
  }

  if (picked.length < limit) {
    // 보충 — [후] 금액이 큰 순. 금액이 같으면 원래 순서를 지켜 렌더가 흔들리지 않게 한다.
    const rest = rows
      .filter((row) => !used.has(row.kb_name) && hasValue(row))
      .map((row, index) => ({ row, index }))
      .sort((a, b) => (b.row.after_value ?? 0) - (a.row.after_value ?? 0) || a.index - b.index);
    for (const { row } of rest) {
      if (picked.length >= limit) break;
      if (used.has(row.kb_name)) continue;
      picked.push({ slot: "extra", row });
      used.add(row.kb_name);
    }
  }

  return picked;
}

/** 증액·감액 담보 수(1단 요약) — 값이 있는 행만 센다. */
export function countChanges(rows: { delta_value: number | null }[]): { up: number; down: number } {
  let up = 0;
  let down = 0;
  for (const row of rows) {
    const delta = row.delta_value ?? 0;
    if (delta > 0) up += 1;
    else if (delta < 0) down += 1;
  }
  return { up, down };
}

/** BOHUMFIT-261과 같은 산식 — 20년 = 240개월. 엑셀 표지·시트3과 값이 어긋나지 않게 한 곳에 둔다. */
export const MONTHS_20Y = 240;

/** 20년 총납입 차액(후−전) — 월납 차액 × 240. */
export function paidTotal20Y(deltaMonthly: number | null | undefined): number {
  return (deltaMonthly ?? 0) * MONTHS_20Y;
}
