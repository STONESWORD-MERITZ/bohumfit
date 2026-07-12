// BOHUMFIT-205: 결과 조회용 기간 필터다. 실제 고지문항별 기간과 서버 판정은 바꾸지 않는다.
// 날짜가 전혀 없으면 누락 표시를 피하기 위해 유지하고, 하나라도 창 안이면 표시한다.
export type DisclosureWindowItem = {
  first_date?: string;
  latest_date?: string;
  first_diagnosis_date?: string;
  inpatient_periods?: { start?: string }[];
  surgery_dates?: string[];
  surgery_suspected_dates?: string[];
  procedure_dates?: string[];
};

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
