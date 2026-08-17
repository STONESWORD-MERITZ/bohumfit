import {
  currentSurgeryCount,
  dateInWindow,
  displayJudgmentDetail,
  filterDisclosureReportsByWindow,
  visibleSurgeryNames,
  type DisclosureWindowItem,
} from "./disclosureWindow";

// BOHUMFIT-251(3차): 그룹 미특정 수술행(백엔드 unassigned_surgeries) — 서버 카카오 문안과
//   동일 블록을 기간 필터 경로에서도 출력한다(4경로 정합).
export type UnassignedSurgery = { date?: string; surgery_name?: string; hospital?: string };

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
  // BOHUMFIT-251: 수술 건별 원문 기록(백엔드 파이프라인 산출 — 날짜/원문코드/맥락/병명/수술명).
  //   src 최소 정합 사유: 고지 복사 문안 생성부가 프런트에 있어 건별 전개 렌더만 추가(판정 무관,
  //   필드 부재 시 기존 형식 폴백 — 하위호환).
  surgery_records?: { date?: string; code?: string; context?: string; name?: string; surgery_name?: string; hospital?: string; co_diagnoses?: string[] }[];
  display_name?: string; // BOHUMFIT-251: 표시 전용 병명(아티팩트 공백 정리 — 원문 복원)
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
  return currentSurgeryCount(item) > 0 || values(item.surgery_suspected).length > 0;
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

  // BOHUMFIT-294: 같은 블록 안에서 **직전에 이미 출력한 코드·병명과 글자 단위로 동일한 값만** 생략한다.
  //   ★생략된 값은 반드시 그 블록 위쪽 줄에 있다(첫 줄에는 항상 출력) — 정보 손실 0.
  //   ★값이 조금이라도 다르면 그대로 둔다 — 251의 "건별로 그 이벤트의 원문 값을 보인다"가 지켜야 할 지점.
  //   서버 _kakao_item과 동일 규칙(4경로 골든 동등성).
  //   ★적용 범위는 **수술 건별 record 줄로 한정**한다. 입원 회차줄(205)·회차별 근거(213)는 회차마다
  //     자기완결적으로 읽혀야 한다는 별도 설계라 진단을 그대로 반복 출력한다.
  const lastShown = { code: "", name: "" };
  const note = (code: string, name: string) => {
    if (code) lastShown.code = code;
    if (name) lastShown.name = name;
  };
  const dedup = (code: string, name: string): [string, string] => {
    const outCode = code && code === lastShown.code ? "" : code;
    const outName = name && name === lastShown.name ? "" : name;
    note(code, name);
    return [outCode, outName];
  };

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
        // BOHUMFIT-294: 회차줄은 **압축하지 않는다**(205 회차 분리·213 회차별 근거 — 회차마다 자기완결).
        const dn = s(item.display_name || item.name);
        note(code, dn);
        return `${pDate} / ${days} / ${code} / ${kind}${dn}${tail}\n`;
      })
      .join("");
    if (periods.length >= 2) line1 += `→ 입원 총 ${periods.length}회 · 합산 ${inpatient}일\n`;
  } else {
    const visitStr = inpatient > 0 ? `입원${inpatient}일` : `통원${item.visit ?? 1}회`;
    const tail = hospitals.length ? ` / ${hospitals[0]}${hospitals.length > 1 ? ` 외 ${hospitals.length - 1}곳` : ""}` : "";
    const dn = s(item.display_name || item.name);
    note(code, dn);   // 294: 블록 첫 줄 — 출력은 그대로, 직전 값만 기록
    line1 = `${dateStr} / ${visitStr} / ${code} / ${kind}${dn}${tail}\n`;
  }

  const surgeryCount = currentSurgeryCount(item);
  const surgeries = visibleSurgeryNames(item);
  const suspected = values(item.surgery_suspected);
  const suspectedGrade = s(item.surgery_suspected_grade).trim();
  const surgeryRecords = (item.surgery_records ?? []).filter((r) => r && s(r.date));
  let line2: string;
  if (surgeryCount > 0 && surgeryRecords.length > 0) {
    // BOHUMFIT-251(3차): 건별 전개 항목의 합산 줄은 진단 요약(기간/코드/병명)만 유지 —
    //   "통원N회" 방문 합산은 건별 record의 맥락과 중복되므로 제거(서버·프런트 동일 규칙).
    //   입원 회차별 줄(periods)은 합산이 아니라 회차 근거이므로 유지한다.
    if (!(inpatient > 0 && periods.length > 0) && dateStr) {
      line1 = `${dateStr} / ${code} / ${kind}${s(item.display_name || item.name)}\n`;
    }
    // BOHUMFIT-251: 수술 건별 전개 — 날짜 / 원문코드 / 맥락 / 병명 / 수술명 (심평원 원문 충실).
    line2 = surgeryRecords
      .map((r) => {
        // BOHUMFIT-294: 직전 줄과 **글자 단위로 같은** 코드·병명만 생략(다르면 그대로 — 251 원문 충실화).
        const [rc, rn] = dedup(s(r.code), s(r.name));
        const parts = [s(r.date), rc, s(r.context), rn, s(r.surgery_name)].map((p) => p.trim());
        const hospital = s(r.hospital).trim() ? ` / ${s(r.hospital).trim()}` : "";
        // BOHUMFIT-251 ③: 동일 일자 타 진단 병기(예: 모소낭 수술 + 항문농양) — 둘 다 고지 대상.
        const co = values(r.co_diagnoses);
        const coStr = co.length ? ` / 동일일자 진단: ${co.join(", ")}` : "";
        return `${parts.filter(Boolean).join(" / ")}${hospital}${coStr}\n`;
      })
      .join("");
  } else if (surgeryCount > 0) {
    line2 = `${surgeries.length ? surgeries.join(", ") : "수술"}\n`;
  } else if (suspected.length) {
    line2 = `수술 의심: ${suspected.join(", ")}${suspectedGrade ? ` (${suspectedGrade})` : ""}\n`;
  } else {
    const detail = displayJudgmentDetail(item);
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
  unassignedSurgeries?: UnassignedSurgery[];
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
  // BOHUMFIT-251(3차): 미특정 수술 블록 — 서버 _build_kakao_message와 동일 형식·동일 창 기준.
  //   일반 고지 0건이어도 미특정이 있으면 "고지 대상 없음"으로 조기 종료하지 않는다.
  const unassigned = (params.unassignedSurgeries ?? []).filter(
    (r) => r && s(r.date) && (!params.cutoffIso || dateInWindow(s(r.date), params.cutoffIso)),
  );
  if (unassigned.length) {
    msg += "[수술 내역(그룹 미특정)]\n";
    unassigned.forEach((r) => {
      msg += [s(r.date), s(r.surgery_name), s(r.hospital)].filter((p) => p.trim()).join(" / ") + "\n";
    });
    msg += "\n";
  }
  if (!hasAny && !unassigned.length) msg += "고지 대상 없음\n";
  return msg.trimEnd() + KAKAO_DISCLAIMER;
}
