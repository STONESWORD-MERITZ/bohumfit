import { filterDisclosureReportsByWindow, type DisclosureWindowItem } from "./disclosureWindow";

export type DisclosureMemoItem = Omit<DisclosureWindowItem, "inpatient_periods"> & {
  first_date?: string;
  latest_date?: string;
  display_code?: string;
  code?: string;
  name?: string;
  visit?: number;
  med_days?: number;
  inpatient?: number;
  inpatient_count?: number;
  inpatient_periods?: { start?: string; end?: string; days?: number; hospital?: string }[];
  surgeries?: string[];
  surgery_suspected?: string[];
  surgery_suspected_grade?: string;
  detail?: string;
  hospitals?: string[] | Set<string>;
  exam_check_only?: boolean;
};

const KAKAO_DISCLAIMER =
  "\n※ BOHUMFIT은 보험 가입·인수·보험금 지급을 보장하지 않는 AI 보조 점검 도구입니다. " +
  "최종 고지 범위와 심사 결과는 실제 청약서 문항, 약관, 보험회사 인수 기준에 따라 달라질 수 있습니다.\n";

function s(value: unknown) {
  return value == null ? "" : String(value);
}

function cleanQTitle(qTitle: string) {
  return qTitle.replace(/^\[.*?\]\s*/, "");
}

function qSortKey(title: string) {
  const m = /\d+/.exec(title || "");
  return m ? Number(m[0]) : 999;
}

function values(value: unknown): string[] {
  if (!value) return [];
  const raw = Array.isArray(value) || value instanceof Set ? Array.from(value) : [value];
  return raw.map((v) => s(v).trim()).filter(Boolean);
}

function hasSurgerySignal(item: DisclosureMemoItem) {
  return values(item.surgeries).length > 0 || values(item.surgery_suspected).length > 0;
}

function displayDetail(item: DisclosureMemoItem) {
  const detail = s(item.detail).trim();
  if (!detail || !detail.includes("입원")) return detail;
  const hasInpatient = (item.inpatient ?? 0) > 0 || (item.inpatient_count ?? 0) > 0 || (item.inpatient_periods?.length ?? 0) > 0;
  if (!hasInpatient) return detail;
  if (!/수술|통원|투약|처방/.test(detail)) return "";
  return detail
    .replace(/입원\s*(또는|및|과|와|\/|·|,)\s*(수술|통원|투약|처방)/g, "$2")
    .replace(/(수술|통원|투약|처방)\s*(또는|및|과|와|\/|·|,)\s*입원/g, "$1")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function memoItem(item: DisclosureMemoItem) {
  const fd = s(item.first_date);
  const ld = s(item.latest_date);
  const dateStr = fd && ld && fd !== ld ? `${fd} ~ ${ld}` : (fd || ld || "");
  const code = s(item.display_code || item.code);
  const hospitals = values(item.hospitals);
  const hospStr = hospitals.join(", ");
  const kind = ["한의원", "한방", "한의"].some((k) => hospStr.includes(k)) ? "(한방)" : "(양방)";
  const inpatient = item.inpatient ?? 0;
  const periods = (item.inpatient_periods ?? []).filter((p) => p && s(p.start));

  let line1: string;
  if (inpatient > 0 && periods.length > 0) {
    line1 = [...periods]
      .sort((a, b) => s(a.start).localeCompare(s(b.start)))
      .map((p) => {
        const st = s(p.start);
        const en = s(p.end);
        const pDate = en && en !== st ? `${st} ~ ${en}` : st;
        const days = (p.days ?? 0) > 0 ? `입원${p.days}일` : "입원";
        const tail = s(p.hospital).trim() ? ` / ${s(p.hospital).trim()}` : "";
        return `${pDate} / ${days} / ${code} / ${kind}${s(item.name)}${tail}\n`;
      })
      .join("");
    if (periods.length >= 2) line1 += `→ 입원 총 ${periods.length}회 · 합산 ${inpatient}일\n`;
  } else {
    const visitStr = inpatient > 0 ? `입원${inpatient}일` : `통원${item.visit ?? 1}회`;
    const tail = hospitals.length ? ` / ${hospitals[0]}${hospitals.length > 1 ? ` 외 ${hospitals.length - 1}곳` : ""}` : "";
    line1 = `${dateStr} / ${visitStr} / ${code} / ${kind}${s(item.name)}${tail}\n`;
  }

  const surgeries = values(item.surgeries);
  const suspected = values(item.surgery_suspected);
  const suspectedGrade = s(item.surgery_suspected_grade).trim();
  let line2: string;
  if (surgeries.length) {
    const named = surgeries.filter((x) => x && x !== "수술");
    line2 = `${named.length ? named.join(", ") : "수술"}\n`;
  } else if (suspected.length) {
    line2 = `수술 의심: ${suspected.join(", ")}${suspectedGrade ? ` (${suspectedGrade})` : ""}\n`;
  } else {
    const detail = displayDetail(item);
    line2 = detail ? `${detail.slice(0, 60)}\n` : "";
  }
  return `${line1}${line2}\n`;
}

export function disclosureSelectionHeader(productQuestionYears: number, selectedYears: number) {
  return `가입예정상품 ${productQuestionYears}년 고지형 · 선택 ${selectedYears}년 고지`;
}

export function withDisclosureSelectionHeader(memo: string, productQuestionYears: number, selectedYears: number) {
  const header = disclosureSelectionHeader(productQuestionYears, selectedYears);
  if (!memo.trim()) return `${header}\n\n고지 대상 없음`;
  return `${header}\n\n${memo.trim()}`;
}

export function buildFilteredDisclosureMemo(params: {
  productLabel: string;
  referenceDate: string;
  reports: Record<string, DisclosureMemoItem[]>;
  cutoffIso: string;
  selectedYears: number;
  productQuestionYears: number;
}) {
  const filtered = filterDisclosureReportsByWindow(params.reports, params.cutoffIso);
  let msg = `${disclosureSelectionHeader(params.productQuestionYears, params.selectedYears)}\n\n`;
  msg += `[${params.productLabel} 고지 사항]\n`;
  msg += `기준일: ${params.referenceDate || "-"}\n\n`;

  let hasAny = false;
  for (const qTitle of Object.keys(filtered).sort((a, b) => qSortKey(a) - qSortKey(b))) {
    const items = (filtered[qTitle] ?? []).filter((item) => !item.exam_check_only);
    if (!items.length) continue;
    hasAny = true;
    msg += `> ${cleanQTitle(qTitle)}\n`;
    const inpatientItems = items.filter((item) => (item.inpatient ?? 0) > 0);
    const surgeryItems = items.filter((item) => !((item.inpatient ?? 0) > 0) && hasSurgerySignal(item));
    const otherItems = items.filter((item) => !((item.inpatient ?? 0) > 0) && !hasSurgerySignal(item));
    if (inpatientItems.length) {
      msg += "[입원]\n";
      inpatientItems.forEach((item) => { msg += memoItem(item); });
    }
    if (surgeryItems.length) {
      msg += "[수술]\n";
      surgeryItems.forEach((item) => { msg += memoItem(item); });
    }
    if (otherItems.length) {
      msg += "[통원]\n";
      otherItems.forEach((item) => { msg += memoItem(item); });
    }
    msg += "\n";
  }
  if (!hasAny) msg += "고지 대상 없음\n";
  return msg.trimEnd() + KAKAO_DISCLAIMER;
}
