// BOHUMFIT-215: 화면/복사문 조회기간 필터다. 실제 고지문항별 서버 판정은 바꾸지 않는다.
// 날짜가 전혀 없으면 누락 표시를 피하기 위해 유지하고, 하나라도 창 안이면 표시한다.

/**
 * BOHUMFIT-183: 투약 일수 산식 설명 — ★**표시 전용**이다. 산식(`filters._sum_daily_max_presc`)은 바꾸지 않았다.
 *   현행 산식은 "날짜별 최대 처방일수의 누적 합"이며, 030 진단 이후 031/032에서 **배지와 헤더 판정을 일치시키기
 *   위해 의도적으로 채택**된 설계다. 사용자가 숫자의 의미를 오해하지 않도록 그 사실만 밝힌다.
 *   ★백엔드 `pipeline/report_pdf.py`의 `MED_SUM_FORMULA_NOTE`와 **문자열이 완전히 같아야 한다**
 *   (언어가 달라 한 곳에 둘 수 없어, 동일성을 테스트로 고정한다).
 */
export const MED_SUM_FORMULA_NOTE = "동일 날짜에 여러 처방이 있으면 가장 긴 처방일수 1건만 반영한 합계입니다.";
export type DisclosureWindowItem = {
  first_date?: string;
  latest_date?: string;
  first_diagnosis_date?: string;
  inpatient_periods?: { start?: string; end?: string; days?: number; hospital?: string }[];
  inpatient?: number;
  inpatient_count?: number;
  visit?: number;
  med_days?: number;
  surgery_dates?: string[];
  surgery_events?: { date?: string; hospital?: string }[];
  // BOHUMFIT-251(3차): 수술 건별 record — 창 필터를 통과시키되 날짜로 걸러야 한다
  //   (미통과 시 필터 경로가 옛 합산 폴백으로 떨어져 중복 잔존).
  // BOHUMFIT-303: tier = "confirmed" | "review"(수술 여부 확인). 부재 시 확정으로 폴백(구 payload 호환).
  surgery_records?: { date?: string; code?: string; context?: string; name?: string; surgery_name?: string; hospital?: string; co_diagnoses?: string[]; tier?: string }[];
  surgeries?: string[];
  surgery_count?: number;
  // BOHUMFIT-303: `수술 여부 확인` 티어 이름(표시 전용 — surgeries·surgery_count는 불변).
  surgery_review?: string[];
  surgery_suspected_dates?: string[];
  surgery_suspected?: string[];
  surgery_suspected_grade?: string;
  procedure_dates?: string[];
  detail?: string;
};

// 기준일(ISO)에서 N 달력연도 전 날짜. 백엔드 _subtract_years 와 동일하게 2/29 -> 2/28 보정.
export function subYearsIso(iso: string, years: number): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
  if (!m) return "";
  const y = Number(m[1]) - years;
  const mo = Number(m[2]);
  const lastDay = new Date(y, mo, 0).getDate();
  const d = Math.min(Number(m[3]), lastDay);
  return `${y}-${String(mo).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

export function resultItemInWindow(item: DisclosureWindowItem, cutoffIso: string): boolean {
  const starts = (item.inpatient_periods ?? []).map((p) => p.start).filter(Boolean);
  const surgD = item.surgery_dates ?? [];
  const suspD = item.surgery_suspected_dates ?? [];
  const procD = item.procedure_dates ?? [];
  const all = [
    item.first_date,
    item.latest_date,
    item.first_diagnosis_date,
    ...starts,
    ...surgD,
    ...procD,
    ...suspD,
  ].filter((d): d is string => Boolean(d));
  if (all.length === 0) return true;
  return all.some((d) => d >= cutoffIso);
}

// BOHUMFIT-251(3차): 미특정 수술 블록 등 외부 창 필터에서도 동일 기준을 쓰도록 공개.
export function dateInWindow(date: unknown, cutoffIso: string): boolean {
  return typeof date === "string" && date >= cutoffIso;
}

function sumNumbers(values: unknown[]): number {
  return values.reduce<number>((sum, value) => sum + (Number(value) || 0), 0);
}

function values(value: unknown): string[] {
  if (!value) return [];
  const raw = Array.isArray(value) || value instanceof Set ? Array.from(value) : [value];
  return raw.map((v) => String(v || "").trim()).filter(Boolean);
}

export function currentSurgeryCount(item: DisclosureWindowItem): number {
  if (item.surgery_count != null) return Math.max(0, Number(item.surgery_count) || 0);
  if (Array.isArray(item.surgery_events)) return item.surgery_events.length;
  if (Array.isArray(item.surgery_dates)) return item.surgery_dates.length;
  return values(item.surgeries).length;
}

export function visibleSurgeryNames(item: DisclosureWindowItem): string[] {
  if (currentSurgeryCount(item) <= 0) return [];
  return values(item.surgeries).filter((name) => name !== "수술");
}

// ── BOHUMFIT-303: `수술 여부 확인` 티어(285 C-1) — 프런트 1상수. 서버 main.SURGERY_REVIEW_LABEL과
//   동등성 테스트로 고정(251 4경로). ★카운트(currentSurgeryCount)는 티어와 무관하게 불변이다.
export const SURGERY_REVIEW_LABEL = "수술 여부 확인";

export function surgeryReviewNames(item: DisclosureWindowItem): string[] {
  return values(item.surgery_review);
}

/** 확정 수술명은 그대로, 확인 티어는 `수술 여부 확인: {명칭}`. 티어 정보가 없으면 확정(구 payload 호환). */
export function labeledSurgeryName(item: DisclosureWindowItem, name: string, tier?: string): string {
  const n = String(name || "").trim();
  if (!n) return n;
  const isReview = tier ? tier === "review" : surgeryReviewNames(item).includes(n);
  return isReview ? `${SURGERY_REVIEW_LABEL}: ${n}` : n;
}

/** (확정 N, 확인 M) — 합은 항상 currentSurgeryCount(=헤더 "수술 N건"). 서버 report_pdf._surgery_tier_counts와 동일 규칙. */
export function surgeryTierCounts(item: DisclosureWindowItem): { confirmed: number; review: number } {
  const total = currentSurgeryCount(item);
  if (total <= 0) return { confirmed: 0, review: 0 };
  const records = (item.surgery_records ?? []).filter((r) => r && typeof r === "object");
  let review: number;
  if (records.length) {
    const reviewDates = new Set(records.filter((r) => r.tier === "review").map((r) => String(r.date || "")));
    const confirmedDates = new Set(records.filter((r) => r.tier !== "review").map((r) => String(r.date || "")));
    review = [...reviewDates].filter((d) => !confirmedDates.has(d)).length;
  } else {
    review = surgeryReviewNames(item).length ? total : 0;
  }
  review = Math.max(0, Math.min(total, review));
  return { confirmed: total - review, review };
}

export function inpatientSummary(item: DisclosureWindowItem) {
  const days = Math.max(0, Number(item.inpatient) || 0);
  const periodCount = Array.isArray(item.inpatient_periods) ? item.inpatient_periods.length : 0;
  const explicitCount = Math.max(0, Number(item.inpatient_count) || 0);
  const count = explicitCount || periodCount || (days > 0 ? 1 : 0);
  return { count, days, show: count > 0 || days > 0 };
}

function disclosureWindowPrefix(text: string): string {
  return (
    text.match(/\d+\s*년\s*초과\s*\d+\s*년\s*이내/)?.[0] ||
    text.match(/\d+\s*년\s*이내/)?.[0] ||
    ""
  ).replace(/\s+/g, " ");
}

export function displayJudgmentDetail(item: DisclosureWindowItem): string {
  const text = String(item.detail || "").trim();
  if (!text) return "";

  const surgeryCount = currentSurgeryCount(item);
  const hasSurgery = surgeryCount > 0;
  const hasVisit = (Number(item.visit) || 0) > 0;
  const hasMed = (Number(item.med_days) || 0) > 0;
  const prefix = disclosureWindowPrefix(text);
  const normalized = text.replace(/\s*(또는|및|과|와)\s*/g, "/");
  const segments = normalized.split(/\s*(?:\/|,|·|\n)\s*/).map((part) => part.trim()).filter(Boolean);
  const hadInpatient = text.includes("입원");
  const kept: string[] = [];

  for (const segment of segments.length ? segments : [text]) {
    if (segment.includes("입원")) continue;
    if (segment.includes("수술")) {
      if (hasSurgery) kept.push(segment);
      continue;
    }
    if (segment.includes("통원")) {
      if (hasVisit) kept.push(segment);
      continue;
    }
    if (segment.includes("투약") || segment.includes("처방")) {
      if (hasMed) kept.push(segment);
      continue;
    }
    if (!hadInpatient) kept.push(segment);
  }

  if (!kept.length && hasSurgery) {
    const names = visibleSurgeryNames(item);
    return `${prefix ? `${prefix} ` : ""}${names.length ? `수술: ${names.join(", ")}` : "수술"}`;
  }

  const joined = kept.join(" / ").replace(/\s{2,}/g, " ").trim();
  if (!joined) return "";
  if (prefix && !/\d+\s*년/.test(joined) && /수술|통원|투약|처방/.test(joined)) {
    return `${prefix} ${joined}`;
  }
  return joined;
}

export function filterDisclosureItemEvidenceByWindow<T extends DisclosureWindowItem>(
  item: T,
  cutoffIso: string,
): T | null {
  if (!cutoffIso) return item;
  if (!resultItemInWindow(item, cutoffIso)) return null;

  const next: Record<string, unknown> = { ...item };
  const visibleDates: string[] = [];
  const addDate = (date: unknown) => {
    if (dateInWindow(date, cutoffIso)) visibleDates.push(String(date));
  };

  const inpatientPeriods = (item.inpatient_periods ?? []).filter((p) => dateInWindow(p.start, cutoffIso));
  next.inpatient_periods = inpatientPeriods;
  if (Array.isArray(item.inpatient_periods)) {
    next.inpatient = sumNumbers(inpatientPeriods.map((p) => p.days));
    next.inpatient_count = inpatientPeriods.length;
  }
  inpatientPeriods.forEach((p) => addDate(p.start));

  for (const key of ["surgery_dates", "surgery_suspected_dates", "procedure_dates"] as const) {
    const values = (item[key] ?? []).filter((d) => dateInWindow(d, cutoffIso));
    next[key] = values;
    values.forEach(addDate);
    if (key === "surgery_dates" && Array.isArray(item.surgery_dates) && !Array.isArray(item.surgery_events)) {
      next.surgery_count = values.length;
      if (values.length === 0) next.surgeries = [];
    }
    if (key === "surgery_suspected_dates" && Array.isArray(item.surgery_suspected_dates) && values.length === 0) {
      next.surgery_suspected = [];
      next.surgery_suspected_grade = "";
    }
  }

  const visitRecords = Array.isArray(next.visit_records)
    ? (next.visit_records as Array<Record<string, unknown>>).filter((r) => dateInWindow(r.date, cutoffIso))
    : undefined;
  if (visitRecords) {
    next.visit_records = visitRecords;
    next.visit = sumNumbers(visitRecords.map((r) => r.count || 1));
    visitRecords.forEach((r) => addDate(r.date));
  }

  const medRecords = Array.isArray(next.med_records)
    ? (next.med_records as Array<Record<string, unknown>>).filter((r) => dateInWindow(r.date, cutoffIso))
    : undefined;
  if (medRecords) {
    next.med_records = medRecords;
    next.med_days = sumNumbers(medRecords.map((r) => r.days));
    medRecords.forEach((r) => addDate(r.date));
  }

  // BOHUMFIT-251(3차): 수술 건별 record도 창 필터 통과 — 미통과 시 memoItem이 옛 합산
  //   폴백(surgeries.join)으로 떨어져 건별·합산 중복이 잔존한다.
  const surgeryRecords = Array.isArray(next.surgery_records)
    ? (next.surgery_records as Array<Record<string, unknown>>).filter((r) => dateInWindow(r.date, cutoffIso))
    : undefined;
  if (surgeryRecords) {
    next.surgery_records = surgeryRecords;
    surgeryRecords.forEach((r) => addDate(r.date));
  }

  const surgeryEvents = Array.isArray(next.surgery_events)
    ? (next.surgery_events as Array<Record<string, unknown>>).filter((r) => dateInWindow(r.date, cutoffIso))
    : undefined;
  if (surgeryEvents) {
    next.surgery_events = surgeryEvents;
    next.surgery_count = surgeryEvents.length;
    if (surgeryEvents.length === 0) next.surgeries = [];
    surgeryEvents.forEach((r) => addDate(r.date));
  }

  for (const key of ["first_date", "latest_date", "first_diagnosis_date"] as const) addDate(item[key]);
  if (visibleDates.length) {
    const sorted = [...new Set(visibleDates)].sort();
    if (!dateInWindow(next.first_date, cutoffIso)) next.first_date = sorted[0];
    if (!dateInWindow(next.latest_date, cutoffIso)) next.latest_date = sorted[sorted.length - 1];
    if (!dateInWindow(next.first_diagnosis_date, cutoffIso)) next.first_diagnosis_date = "";
  }

  return next as T;
}

export function filterDisclosureReportsByWindow<T extends DisclosureWindowItem>(
  reports: Record<string, T[]>,
  cutoffIso: string,
): Record<string, T[]> {
  if (!cutoffIso) return reports;
  return Object.fromEntries(
    Object.entries(reports).map(([title, items]) => {
      const filtered = (items ?? [])
        .map((item) => filterDisclosureItemEvidenceByWindow(item, cutoffIso))
        .filter((item): item is T => item !== null);
      return [title, filtered];
    }),
  );
}
