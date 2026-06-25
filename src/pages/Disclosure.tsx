import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import AnalysisProgress from "../components/AnalysisProgress";
import UsageBadge from "../components/UsageBadge";
import { useToast } from "../components/ToastContext"; // BOHUMFIT-131
import { useAuth } from "../lib/auth-context";

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");
const MAX_FILE_COUNT = 10; // BOHUMFIT-053: 10년 고지형 전체 = 발급기간별 분할 파일 최대 10개
const MAX_FILE_SIZE = 15 * 1024 * 1024;
const MAX_TOTAL_SIZE = 40 * 1024 * 1024;

type AudienceMode = "customer" | "agent";

function connectionErrorMessage(apiBase: string): string {
  if (typeof console !== "undefined") {
    console.error("[보험핏] API 연결 실패:", apiBase);
  }
  return "서버에 연결하지 못했어요. 인터넷 연결을 확인하시고 잠시 후 다시 시도해 주세요. 문제가 계속되면 관리자에게 문의해 주세요.";
}

type DiseaseSummary = {
  code: string;
  display_code?: string;
  name: string;
  first_date: string;
  latest_date: string;
  visit_count: number;
  inpatient_count: number;
  inpatient_days: number;
  surgery_count: number;
  med_days: number;
  hospitals: string[];
};

type SummaryItem = {
  first_date: string;
  latest_date: string;
  first_diagnosis_date: string;
  code: string;
  display_code?: string;
  name: string;
  visit: number;
  med_days: number;
  med_days_30plus?: boolean;
  inpatient: number;
  inpatient_count: number;
  inpatient_periods?: { start: string; end: string; days: number }[];
  surgery_count?: number;
  surgeries: string[];
  procedures?: string[];
  surgery_suspected?: string[];
  surgery_suspected_grade?: string;  // BOHUMFIT-033: 공단 수술의심 등급(강/약/"")
  insurance_only?: boolean;          // BOHUMFIT-039: 직장·항문(Q5만)→실손 가입 시에만 고지
  additional_test_hit?: boolean;
  additional_test_reason?: string;
  exam_check_only?: boolean;         // BOHUMFIT-128: Q2 추가검사·재검사 확인용(고지 대상 아님)
  q2_suspicion?: string;
  treatment_ongoing?: boolean | null;
  treatment_ongoing_reason?: string;
  hospitals: string[];
  first_hospital?: string;
  last_hospital?: string;
  detail: string;
};

type AnalyzeResult = {
  // BOHUMFIT-009: 신구조 — 건강체/간편 탭 + Q1~Q4 6 키 복구. easy_reports/easy_kakao 도 호환 유지.
  flagged_count: number;
  total_q_count: number;
  total_visit_sum: number;
  total_med_sum: number;
  standard_reports: Record<string, SummaryItem[]>;
  easy_reports?: Record<string, SummaryItem[]>;
  // BOHUMFIT-009: 신구조 6 키 (결정론 raw items list). 프런트가 점진적 마이그레이션 가능.
  q1?: SummaryItem[];
  q2_health?: SummaryItem[];
  q2_easy?: SummaryItem[];
  q3_health?: SummaryItem[];
  q3_easy?: SummaryItem[];
  q4_health?: SummaryItem[];
  all_disease_summary: DiseaseSummary[];
  standard_kakao: string;
  easy_kakao?: string;
  customer_name?: string;   // BOHUMFIT-065: 출력 파일명용(공단 PDF 성명, 없으면 폴백)
  parse_errors: string[];
  warnings: string[];
  // BOHUMFIT-023: 실손 안내용 급여 본인부담(내가 낸 의료비) 연도별 (additive — 백엔드 surfaced).
  covered_self_pay_by_year?: Record<string, number>;
  covered_self_pay_captured?: boolean;
};

type Risk = "red" | "orange" | "gray" | "yellow" | "green";
type TourPhase = "pre" | "post";

const TOUR_STORAGE_KEY = "bohumfit_tour_seen_v1";
function readTourSeen(): { pre: boolean; post: boolean } {
  if (typeof window === "undefined") return { pre: false, post: false };
  try {
    const raw = window.localStorage.getItem(TOUR_STORAGE_KEY);
    if (!raw) return { pre: false, post: false };
    const v = JSON.parse(raw);
    return { pre: !!v.pre, post: !!v.post };
  } catch {
    return { pre: false, post: false };
  }
}
function markTourSeen(phase: "pre" | "post") {
  if (typeof window === "undefined") return;
  try {
    const cur = readTourSeen();
    cur[phase] = true;
    window.localStorage.setItem(TOUR_STORAGE_KEY, JSON.stringify(cur));
  } catch { /* localStorage 비활성 환경 무시 */ }
}
type TourStep = {
  target: string;
  title: string;
  body: string;
};

const modeCopy: Record<AudienceMode, {
  badge: string;
  title: string;
  subtitle: string;
  dateLabel: string;
  dateHelp: string;
  uploadHelp: string;
  button: string;
  emptyTitle: string;
  resultTitle: string;
  memoLabel: string;
}> = {
  customer: {
    badge: "고객용 점검",
    title: "내 보험 고지 점검",
    subtitle: "이전에 가입한 보험의 청약 당시 병력 고지 누락 가능성을 참고용으로 점검합니다.",
    dateLabel: "가입일 또는 점검 기준일",
    dateHelp: "이미 가입한 보험을 확인할 때는 해당 상품의 청약일을 넣어 주세요.",
    uploadHelp: "건강e음에서 발급한 기본진료, 세부진료, 처방조제 PDF를 올려 주세요.",
    button: "내 고지 리스크 점검",
    emptyTitle: "현재 기준으로 뚜렷한 고지 검토 항목이 없습니다.",
    resultTitle: "가입 당시 고지 검토 결과",
    memoLabel: "고객 안내용 점검 메모",
  },
  agent: {
    badge: "설계사용",
    title: "알릴의무 필터",
    subtitle: "심평원 병력 PDF를 기준으로 건강체와 간편심사 고지 검토 항목을 정리합니다.",
    dateLabel: "청약 예정일",
    dateHelp: "상품 가입 예정일 기준으로 3개월, 1년, 5년, 10년 기간을 계산합니다.",
    uploadHelp: "기본진료, 세부진료, 처방조제 PDF를 함께 올리면 정확도가 올라갑니다.",
    button: "AI 고지 리스크 점검",
    emptyTitle: "선택한 상품 기준의 고지 대상 항목이 없습니다.",
    resultTitle: "상품별 고지사항",
    memoLabel: "카카오 전송용 메시지",
  },
};

function riskOf(item: SummaryItem): Risk {
  const surgN = item.surgery_count ?? item.surgeries?.length ?? 0;
  const procN = item.procedures?.length ?? 0;
  const suspN = item.surgery_suspected?.length ?? 0;
  if (item.inpatient > 0 || surgN > 0) return "red";
  if (procN > 0) return "orange";
  if (suspN > 0) return "gray";
  if (item.med_days >= 30 || item.visit >= 7) return "yellow";
  return "green";
}

const RISK: Record<Risk, { border: string }> = {
  red: { border: "border-red-400" },
  orange: { border: "border-orange-400" },
  gray: { border: "border-gray-400" },
  yellow: { border: "border-amber-400" },
  green: { border: "border-emerald-400" },
};

function Chip({ label, tone = "gray", title }: { label: string; tone?: string; title?: string }) {
  const tones: Record<string, string> = {
    gray: "bg-gray-100 text-gray-600",
    "gray-light": "border border-gray-200 bg-gray-50 text-gray-500",
    red: "bg-red-100 text-red-600",
    "red-light": "border border-red-200 bg-red-50 text-red-500",
    amber: "bg-amber-100 text-amber-700",
    emerald: "bg-emerald-100 text-emerald-700",
    orange: "bg-orange-100 text-orange-600",
    indigo: "bg-accent-100 text-accent-600",
    rose: "bg-rose-100 text-rose-600",
  };
  return (
    <span title={title} className={`rounded-full px-3 py-1 text-xs font-semibold ${tones[tone] ?? tones.gray}`}>
      {label}
    </span>
  );
}

function extractQNumber(qTitle: string): string {
  const exact = qTitle.match(/(\d+)\s*번\s*질문/);
  if (exact) return `Q${exact[1]}`;
  if (qTitle.includes("참고")) return "참고";
  const any = qTitle.match(/\d+/);
  return any ? `Q${any[0]}` : "Q";
}

function cleanQTitle(qTitle: string): string {
  return qTitle.replace(/^\[.*?\]\s*/, "");
}

function getMetricVisibility(item: SummaryItem, qNum: string, isEasy: boolean) {
  const detail = item.detail || "";
  const surgN = item.surgery_count ?? item.surgeries?.length ?? 0;
  const hasInpatient = (item.inpatient ?? 0) > 0 || (item.inpatient_count ?? 0) > 0;
  const hasSurgery = surgN > 0;
  const hasVisitTrigger = (item.visit ?? 0) >= 7 || detail.includes("통원");
  const hasMedTrigger = (item.med_days ?? 0) >= 30 || detail.includes("투약") || detail.includes("처방");

  if (isEasy) {
    return {
      visit: false,
      inpatient: qNum === "Q2" && hasInpatient,
      inpatientCount: qNum === "Q2" && (item.inpatient_count ?? 0) > 0,
      surgery: qNum === "Q2" && hasSurgery,
      med: false,
    };
  }

  if (qNum === "Q1") {
    return {
      visit: false,
      inpatient: hasInpatient,
      inpatientCount: (item.inpatient_count ?? 0) > 0,
      surgery: hasSurgery,
      med: hasMedTrigger,
    };
  }

  if (qNum === "Q3") {
    return {
      visit: hasVisitTrigger,
      inpatient: hasInpatient,
      inpatientCount: (item.inpatient_count ?? 0) > 0,
      surgery: hasSurgery,
      med: hasMedTrigger,
    };
  }

  // BOHUMFIT-034: Q4(5년 초과 10년 이내) = 입원·수술만(통원·투약 없음). 공단 수술의심은
  // surgery_suspected_grade 배지로 별도 노출(result_builder가 Q4에서만 채움).
  if (qNum === "Q4") {
    return {
      visit: false,
      inpatient: hasInpatient,
      inpatientCount: (item.inpatient_count ?? 0) > 0,
      surgery: hasSurgery,
      med: false,
    };
  }

  // Q5(중대질환) 및 기타 = 메트릭 칩 없음(기존 Q4 중대질환과 동일).
  return {
    visit: false,
    inpatient: false,
    inpatientCount: false,
    surgery: false,
    med: false,
  };
}

function shouldShowClinicalReview(qNum: string, isEasy: boolean) {
  if (isEasy) return qNum === "Q1";
  return qNum === "Q1" || qNum === "Q2";
}

type ClinicalReviewState = {
  label: string;
  tone: string;
  text: string;
};

function stripClinicalLikelihoodPrefix(text: string): string {
  return text.replace(/^\[추가검사·재검사 가능성 (높음|낮음)\]\s*/, "").trim();
}

function getClinicalReviewState(item: SummaryItem): ClinicalReviewState {
  const rawText = (item.q2_suspicion || item.additional_test_reason || "").trim();
  const cleanText = stripClinicalLikelihoodPrefix(rawText);
  const isLow = rawText.includes("가능성 낮음") || (!item.additional_test_hit && !!item.additional_test_reason);
  const isHigh = Boolean(item.additional_test_hit) || rawText.includes("가능성 높음") || (!!item.q2_suspicion && !isLow);

  if (isHigh) {
    return {
      label: "추가검사·재검사 가능성 높음",
      tone: "indigo",
      text: cleanText
        ? `자동 분석: 가능성 높음 - ${cleanText}`
        : "자동 분석상 추가검사·재검사 필요 소견 가능성이 높습니다.",
    };
  }

  if (isLow) {
    return {
      label: "추가검사·재검사 가능성 낮음",
      tone: "gray-light",
      text: cleanText
        ? `자동 분석: 가능성 낮음 - ${cleanText}`
        : "자동 분석상 추가검사·재검사 필요 소견 가능성은 낮습니다.",
    };
  }

  return {
    label: "추가검사·재검사 가능성 미확인",
    tone: "gray-light",
    text: "검사 시행 여부와 관계없이, 의사로부터 추가검사나 재검사가 필요하다는 소견 또는 권유를 받으셨는지 고객에게 직접 확인해 주세요.",
  };
}

function AllDiseaseSection({ diseases }: { diseases: DiseaseSummary[] }) {
  const [open, setOpen] = useState(false);

  if (!diseases.length) return null;

  return (
    <section data-tour="summary" className="mb-5 overflow-hidden rounded-[8px] bg-white shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex w-full items-center justify-between px-5 py-4 text-left"
      >
        <div>
          <span className="text-sm font-extrabold text-gray-900">전체 병력 요약</span>
          <span className="ml-2 text-xs font-semibold text-gray-400">{diseases.length}개 질환</span>
        </div>
        <span className="text-xs font-bold text-gray-400">{open ? "접기" : "펼치기"}</span>
      </button>

      {open && (
        <div className="border-t border-gray-100">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] text-xs">
              <thead>
                <tr className="bg-gray-50 text-gray-500">
                  <th className="px-4 py-2.5 text-left">코드</th>
                  <th className="px-4 py-2.5 text-left">질병명</th>
                  <th className="px-4 py-2.5 text-left">진료기간</th>
                  <th className="px-4 py-2.5 text-center">통원</th>
                  <th className="px-4 py-2.5 text-center">입원</th>
                  <th className="px-4 py-2.5 text-center">수술</th>
                  <th className="px-4 py-2.5 text-center">투약</th>
                  <th className="px-4 py-2.5 text-left">병원</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {diseases.map((d, i) => (
                  <tr key={`${d.code}-${i}`} className="hover:bg-gray-50/60">
                    <td className="px-4 py-2 font-mono text-gray-500">{d.display_code || d.code}</td>
                    <td className="max-w-[180px] truncate px-4 py-2 font-semibold text-gray-800">{d.name || "-"}</td>
                    <td className="whitespace-nowrap px-4 py-2 text-gray-500">
                      {d.first_date}
                      {d.latest_date && d.latest_date !== d.first_date ? ` ~ ${d.latest_date}` : ""}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {d.visit_count > 0 ? (
                        <span className={`font-semibold ${d.visit_count >= 7 ? "text-amber-600" : "text-gray-600"}`}>
                          {d.visit_count}회
                        </span>
                      ) : <span className="text-gray-300">-</span>}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {d.inpatient_days > 0 ? (
                        <span className="font-semibold text-red-500">{d.inpatient_days}일</span>
                      ) : <span className="text-gray-300">-</span>}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {d.surgery_count > 0 ? (
                        <span className="font-semibold text-red-500">{d.surgery_count}건</span>
                      ) : <span className="text-gray-300">-</span>}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {d.med_days > 0 ? (
                        <span className={`font-semibold ${d.med_days >= 30 ? "text-amber-600" : "text-emerald-600"}`}>
                          {d.med_days}일
                        </span>
                      ) : <span className="text-gray-300">-</span>}
                    </td>
                    <td className="max-w-[180px] truncate px-4 py-2 text-gray-500">
                      {(d.hospitals || []).slice(0, 2).join(", ") || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}

function DiseaseCard({ item, qNum, isEasy = false }: { item: SummaryItem; qNum: string; isEasy?: boolean }) {
  const risk = riskOf(item);
  const surgN = item.surgery_count ?? item.surgeries?.length ?? 0;
  const procN = item.procedures?.length ?? 0;
  const suspN = item.surgery_suspected?.length ?? 0;
  const metric = getMetricVisibility(item, qNum, isEasy);
  const showClinicalReview = shouldShowClinicalReview(qNum, isEasy);
  const period = item.first_date && item.latest_date && item.first_date !== item.latest_date
    ? `${item.first_date} ~ ${item.latest_date}`
    : (item.first_date || "");
  const hasMetricChips = metric.visit || metric.inpatient || metric.inpatientCount || metric.surgery || metric.med;
  // BOHUMFIT-054 STEP3: 질문별 집계 창 라벨 — 칩(통원·투약 등)이 어느 기간 기준 횟수인지 명시(정답표 전기간/10년 혼동 방지).
  const windowLabels: Record<string, string> = isEasy
    ? { Q1: "3개월 이내", Q2: "10년 이내", Q3: "5년 이내" }
    : { Q1: "3개월 이내", Q2: "1년 이내", Q3: "5년 이내", Q4: "5년 초과 10년 이내", Q5: "5년 이내" };
  const windowLabel = windowLabels[qNum] || "";
  const windowTip = windowLabel ? `가입예정일 기준 ${windowLabel} 집계입니다.` : undefined;
  const clinicalReview = getClinicalReviewState(item);
  const hasClinicalChips = showClinicalReview;
  const hasBottom = showClinicalReview;

  return (
    <article className={`border-l-4 px-5 py-4 ${RISK[risk].border}`}>
      <div className="mb-1 flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <span className="text-[15px] font-bold text-gray-900">{item.name || "질병명 없음"}</span>
          {item.code && (
            <span className="shrink-0 rounded bg-gray-100 px-2 py-0.5 font-mono text-[11px] text-gray-500">
              {item.display_code || item.code}
            </span>
          )}
        </div>
        <span className="shrink-0 rounded-[8px] bg-accent-600 px-2 py-0.5 text-[11px] font-bold text-white">
          {qNum}
        </span>
      </div>

      {item.insurance_only && (
        <div className="mb-2 rounded-[8px] bg-sky-50 px-3 py-1.5 text-[11px] leading-relaxed text-sky-700">
          실손의료비보험 가입 시에만 고지가 필요한 항목입니다(직장·항문 질환). 일반 사망·질병 보험 고지 대상은 아닙니다.
        </div>
      )}

      <div className="mb-2.5 space-y-0.5 text-xs text-gray-500">
        {period && (
          <div className="flex items-center gap-2">
            <span className="shrink-0 text-gray-400">진료기간</span>
            <span>{period}</span>
            {item.last_hospital && <span className="truncate text-gray-400">{item.last_hospital}</span>}
          </div>
        )}
        {item.first_diagnosis_date && (
          <div className="flex items-center gap-2">
            <span className="shrink-0 text-gray-400">최초진단</span>
            <span>{item.first_diagnosis_date}</span>
            {item.first_hospital && <span className="truncate text-gray-400">{item.first_hospital}</span>}
          </div>
        )}
      </div>

      {item.detail && (
        <div className="mb-3 text-[13px] font-medium leading-relaxed text-gray-700">
          {item.detail}
        </div>
      )}

      {hasMetricChips && (
        <div className="mb-2 flex flex-wrap gap-2">
          {metric.visit && <Chip label={`통원 ${item.visit ?? 0}회`} title={windowTip} tone={(item.visit ?? 0) >= 7 ? "amber" : "gray"} />}
          {metric.inpatient && <Chip label={`입원 ${item.inpatient ?? 0}일`} title={windowTip} tone="red" />}
          {metric.inpatientCount && <Chip label={`입원 ${item.inpatient_count ?? 0}회`} title={windowTip} tone="red-light" />}
          {metric.surgery && <Chip label={`수술 ${surgN}건`} title={windowTip} tone="red" />}
          {metric.med && (
            <Chip
              label={`투약 ${item.med_days ?? 0}일`}
              title={windowTip}
              tone={(item.med_days ?? 0) >= 30 ? "amber" : (item.med_days ?? 0) > 0 ? "emerald" : "gray"}
            />
          )}
        </div>
      )}

      {item.surgery_suspected_grade && (
        <div className="mb-2 rounded-[8px] bg-amber-50 px-3 py-2">
          <div className="flex flex-wrap items-center gap-2">
            <Chip
              label={`수술 의심—확인 필요 (${item.surgery_suspected_grade})`}
              tone={item.surgery_suspected_grade === "강" ? "red-light" : "amber"}
            />
          </div>
          <p className="mt-1 text-[11px] leading-relaxed text-amber-700">
            건보(공단) 자료엔 수술이 명시되지 않아, 진료비 합산(공단부담금+본인부담금)과 수술 관련 행위를 근거로 추정한 의심 항목입니다. 입원 진료비 50만원 이상, 또는 수술 관련 행위가 동반된 진료비 10만원 이상을 수술 가능성으로 추정합니다(강=가능성 높음, 약=가능성 낮음, 금액은 모두 ‘이상’ 기준). 실제 수술 여부는 고객님 확인이 필요합니다.
          </p>
        </div>
      )}

      {hasClinicalChips && (
        <div className="flex flex-wrap gap-2">
          {procN > 0 && <Chip label={`시술 ${procN}건`} tone="orange" />}
          {suspN > 0 && <Chip label={`수술 의심 ${suspN}건`} tone="gray-light" />}
          <Chip label={clinicalReview.label} tone={clinicalReview.tone} />
          {item.treatment_ongoing === true && <Chip label="치료 중" tone="rose" />}
          {item.treatment_ongoing === false && <Chip label="종결" tone="emerald" />}
        </div>
      )}

      {hasBottom && (
        <div className="mt-3 space-y-1 border-t border-gray-100 pt-2.5 text-xs leading-relaxed">
          {suspN > 0 && (
            <p className="text-gray-500">
              <span className="mr-1.5 text-gray-400">의심 행위</span>
              {item.surgery_suspected!.slice(0, 3).join(", ")}
            </p>
          )}
          <p className={clinicalReview.tone === "indigo" ? "text-accent-600" : "text-gray-500"}>
            <span className={clinicalReview.tone === "indigo" ? "mr-1.5 text-accent-300" : "mr-1.5 text-gray-400"}>
              소견 확인
            </span>
            {clinicalReview.text}
          </p>
          <p className="text-[11px] text-gray-400">
            ※ 실제 검사 시행 여부와 별개로, 의사의 추가검사·재검사 필요 소견 또는 권유가 있었는지 확인하는 항목입니다.
          </p>
          {item.treatment_ongoing === true && item.treatment_ongoing_reason && (
            <p className="text-rose-600">
              <span className="mr-1.5 text-rose-300">치료 중</span>
              {item.treatment_ongoing_reason}
            </p>
          )}
          {item.treatment_ongoing === false && item.treatment_ongoing_reason && (
            <p className="text-emerald-600">
              <span className="mr-1.5 text-emerald-400">종결</span>
              {item.treatment_ongoing_reason}
            </p>
          )}
        </div>
      )}
    </article>
  );
}

function DisclosureSection({
  reports,
  memo,
  label,
  mode,
  isEasy = false,
}: {
  reports: Record<string, SummaryItem[]>;
  memo: string;
  label: string;
  mode: AudienceMode;
  isEasy?: boolean;
}) {
  const [memoOpen, setMemoOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const { showToast } = useToast(); // BOHUMFIT-131
  const copy = modeCopy[mode];
  const hasItems = Object.keys(reports).length > 0;

  const handleCopy = () => {
    void navigator.clipboard.writeText(memo);
    setCopied(true);
    showToast("복사되었습니다", "success"); // BOHUMFIT-131
    window.setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div>
      {memo && (
        <section data-tour="copy" className="mb-4 overflow-hidden rounded-[8px] bg-white shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
          <div className="flex items-center justify-between gap-3 px-5 py-4">
            <button type="button" onClick={() => setMemoOpen(!memoOpen)} aria-expanded={memoOpen} className="text-left text-sm font-bold text-gray-800">
              {copy.memoLabel}
              <span className="ml-2 text-xs text-gray-400">{memoOpen ? "접기" : "펼치기"}</span>
            </button>
            <button
              onClick={handleCopy}
              className="rounded-[8px] bg-[#FEE500] px-4 py-2 text-sm font-bold text-[#191919]"
            >
              {copied ? "복사 완료" : "복사하기"}
            </button>
          </div>
          {memoOpen && (
            <pre className="whitespace-pre-wrap bg-gray-50 px-5 py-4 font-sans text-xs leading-relaxed text-gray-600">
              {memo}
            </pre>
          )}
        </section>
      )}

      {hasItems ? (
        <div data-tour="cards" className="space-y-4">
          {Object.entries(reports).map(([qTitle, items]) => {
            const qNum = extractQNumber(qTitle);
            const sortByDate = (arr: SummaryItem[]) => [...arr].sort((a, b) => {
              const al = a.latest_date || a.first_date || "";
              const bl = b.latest_date || b.first_date || "";
              if (al !== bl) return bl.localeCompare(al);
              return (b.first_date || "").localeCompare(a.first_date || "");
            });
            // BOHUMFIT-128: Q2 추가검사·재검사 확인용 항목은 [B] 설계사 참고용으로 분리(고지 항목 [A]와 구분)
            const normalItems = sortByDate(items.filter((it) => !it.exam_check_only));
            const examItems = sortByDate(items.filter((it) => it.exam_check_only));
            return (
              <section key={qTitle} className="overflow-hidden rounded-[8px] bg-white shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
                <div className="flex items-center gap-2.5 border-b border-gray-100 px-5 py-3.5">
                  <span className="shrink-0 rounded-[8px] bg-accent-600 px-2.5 py-1 text-xs font-bold text-white">
                    {qNum}
                  </span>
                  <h3 className="text-sm font-bold text-gray-800">{cleanQTitle(qTitle)}</h3>
                </div>
                {normalItems.length > 0 && (
                  <div className="divide-y divide-gray-50">
                    {normalItems.map((item, idx) => (
                      <DiseaseCard key={`${item.code}-${idx}`} item={item} qNum={qNum} isEasy={isEasy} />
                    ))}
                  </div>
                )}
                {examItems.length > 0 && (
                  <div className="border-t border-amber-200 bg-amber-50/60 px-5 py-4">
                    <p className="text-sm font-bold text-amber-800">설계사 확인 필요 항목</p>
                    <p className="mt-1 text-xs leading-relaxed text-amber-700">
                      고지 대상은 아니나 아래 질병에 대해 의사의 추가검사·재검사 소견 또는 권유가 있었는지 고객에게 직접 확인해 주세요.
                    </p>
                    <div className="mt-3 divide-y divide-amber-100 overflow-hidden rounded-[8px] border border-amber-100 bg-white/70">
                      {examItems.map((item, idx) => (
                        <DiseaseCard key={`exam-${item.code}-${idx}`} item={item} qNum={qNum} isEasy={isEasy} />
                      ))}
                    </div>
                  </div>
                )}
              </section>
            );
          })}
        </div>
      ) : (
        <div data-tour="cards" className="rounded-[8px] bg-emerald-50 p-8 text-center shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
          <p className="text-sm font-bold text-emerald-700">{label}</p>
        </div>
      )}
    </div>
  );
}

function DisclaimerBox() {
  return (
    <div className="mt-5 rounded-[8px] border border-gray-200 bg-gray-50 p-4 text-[11px] leading-5 text-gray-500">
      <p className="font-bold text-gray-600">분석 결과 이용 시 유의사항</p>
      <p className="mt-1.5 break-keep">
        보험핏 결과는 업로드한 진료자료를 바탕으로 AI가 산출한 <b className="font-bold">참고용 보조자료</b>이며,
        의학적 진단이나 보험 가입·인수·보험금 지급 여부를 확정하지 않습니다. 실제 알릴의무(고지) 대상과 범위는
        보험사별 청약서 문항·약관·인수지침에 따라 달라질 수 있으므로, 청약 전 반드시 해당 청약서
        문항과 대조해 주세요. 고지 누락에 대한 최종 책임은 청약자 본인에게 있으며, 본 서비스는
        분석 결과의 사용으로 인한 법적 책임을 지지 않습니다.
      </p>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────
// BOHUMFIT-023: 실손 청구 안내 (설계 v3-1). 백엔드 backend/insurance 모듈을 기준으로 TS 미러.
//   - 프런트는 insurance 모듈을 직접 호출할 수 없어(HTTP API 부재) 동일 로직을 미러한다.
//   - source of truth = backend/insurance + 그 단위 테스트. 수치/로직 변경 시 양쪽 동기화.
//   - 출력은 추정 범위 + 가능성. 단정/보험 모집·추천·권유 표현 금지. 입력값 비저장(useState만).
// ──────────────────────────────────────────────────────────────
const INS_GEN_RATES: Record<number, {
  period: string;
  covered: [number, number];
  nonCovered: [number, number];
  nonCoveredOptions?: Record<number, number>;
}> = {
  1: { period: "~2009.9", covered: [0.0, 0.2], nonCovered: [0.0, 0.2] },
  2: { period: "2009.10~2017.3", covered: [0.1, 0.2], nonCovered: [0.2, 0.2] },
  3: { period: "2017.4~2021.6", covered: [0.1, 0.2], nonCovered: [0.2, 0.3], nonCoveredOptions: { 20: 0.2, 30: 0.3 } },
  4: { period: "2021.7~2026.5", covered: [0.2, 0.2], nonCovered: [0.3, 0.3] },
  5: { period: "2026.5.6~", covered: [0.2, 0.6], nonCovered: [0.5, 0.5] },
};
const INS_SELF_PAY_CAP = 2_000_000; // §4-2 전 세대 연 200만
const INS_CAP_SCOPE: Record<number, "both" | "covered"> = { 1: "both", 2: "both", 3: "both", 4: "covered", 5: "covered" };
// §4-3 건보 본인부담상한제 2026 (분위 → [일반, 요양병원 120일 초과]) 단위: 원
const INS_NHIS_CAP_2026: Record<number, [number, number]> = {
  1: [900000, 1430000], 2: [1120000, 1810000], 3: [1120000, 1810000],
  4: [1730000, 2450000], 5: [1730000, 2450000], 6: [3260000, 4040000],
  7: [3260000, 4040000], 8: [4460000, 5800000], 9: [5360000, 6980000],
  10: [8430000, 10960000],
};
const INS_DISCLAIMER = "추정값입니다. 정확한 보험금·환급금 지급 여부와 금액은 보험사 약관·심사 및 국민건강보험공단 확인이 필요합니다. 본 안내는 보험 모집·중개·권유를 목적으로 하지 않습니다.";

// BOHUMFIT-028: 최소공제 미러 — backend/insurance constants §4-4 / calculator §6-1 와 동일 산식.
// ⚠️ 수치/로직 변경 시 backend/insurance 와 반드시 양쪽 동기화(설계 v4 §6-3 케이스10 미러 일치).
const INS_MIN_DEDUCTIBLE_BY_GEN: Record<number, Record<string, number> | null> = {
  1: null,                                          // legacy
  2: { clinic: 10000, general: 15000, tertiary: 20000 },
  3: { clinic: 10000, general: 15000, tertiary: 20000 },
  4: { clinic: 10000, general: 15000, tertiary: 20000 },
  5: null,                                          // 준비중
};
const INS_MIN_DEDUCTIBLE_DEFAULT_GRADE = "tertiary";
const INS_GRADE_LABELS: Record<string, string> = {
  clinic: "의원", general: "종합병원", tertiary: "상급종합병원", unknown: "등급 미상(상급 기준)",
};

function insClassifyProvider(name: string): "clinic" | "unknown" {
  const n = (name || "").replace(/[\s·ㆍ/\\&()[\]_-]+/g, "");
  return n.includes("의원") && !n.includes("병원") ? "clinic" : "unknown";
}

function insProviderDeductible(gen: number, grade: string): number | null {
  const table = INS_MIN_DEDUCTIBLE_BY_GEN[gen];
  if (!table) return null;
  const g = grade in table ? grade : INS_MIN_DEDUCTIBLE_DEFAULT_GRADE;
  return table[g] ?? table[INS_MIN_DEDUCTIBLE_DEFAULT_GRADE];
}

function insClaimPerRow(charge: number, copayRate: number, fixedDeductible: number) {
  const c = Math.max(0, Math.round(charge || 0));
  const pct = Math.round(c * (copayRate || 0));
  const fixed = Math.max(0, Math.round(fixedDeductible || 0));
  const finalDeductible = Math.max(fixed, pct);
  const reimbursement = Math.max(0, c - finalDeductible);
  return { charge: c, finalDeductible, reimbursement, lowValue: reimbursement <= 0 };
}

function insWon(s: string): number {
  return Math.max(0, parseInt((s || "").replace(/[^\d]/g, "") || "0", 10));
}

// BOHUMFIT-025: 실손 결과만 인쇄(브라우저 인쇄→PDF). 새 의존성 없이 @media print 로 처리.
// 화면 표시 불변(print-only 은 화면 숨김, no-print 은 인쇄 숨김). #insurance-print-area 만 인쇄.
const INS_PRINT_CSS = `
@media screen { .print-only { display: none !important; } }
@media print {
  .no-print { display: none !important; }
  body * { visibility: hidden !important; }
  #insurance-print-area, #insurance-print-area * { visibility: visible !important; }
  #insurance-print-area { position: absolute; left: 0; top: 0; width: 100%; padding: 0; }
  @page { margin: 14mm; }
}
`;

function wonToMan(won: number): string {
  if (!won || won <= 0) return "0원";
  return `약 ${Math.round(won / 10000).toLocaleString()}만원`;
}

function insEstimateClaim(coveredSelfPay: number, gen: number, nonCovered: number, ncOption: number | null) {
  const r = INS_GEN_RATES[gen];
  const [covLo, covHi] = r.covered;
  let ncLo = r.nonCovered[0];
  let ncHi = r.nonCovered[1];
  if (ncOption != null && r.nonCoveredOptions && r.nonCoveredOptions[ncOption] != null) {
    ncLo = r.nonCoveredOptions[ncOption];
    ncHi = r.nonCoveredOptions[ncOption];
  }
  const low = Math.round(coveredSelfPay * (1 - covHi)) + Math.round(nonCovered * (1 - ncHi));
  const high = Math.round(coveredSelfPay * (1 - covLo)) + Math.round(nonCovered * (1 - ncLo));
  const has = coveredSelfPay + nonCovered > 0;
  return { low, high, has, possibility: has ? "청구 대상일 수 있음" : "청구 대상 아닐 수 있음" };
}

// BOHUMFIT-035: 세대 '모름' 시 보수적 추정 — insuranceCalc.ts insConservativeEstimate 와 verbatim 미러.
//   세대별 산출 후 '공제 가장 큰(환급 가장 작은) 세대' 기준. 규제 자기부담률만 사용, 새 값 추정 없음.
function insConservativeEstimate(coveredSelfPay: number, nonCovered: number) {
  let best: { gen: number; low: number; high: number; has: boolean; possibility: string } | null = null;
  for (const gen of [1, 2, 3, 4, 5]) {
    const r = INS_GEN_RATES[gen];
    const ncOpt = r.nonCoveredOptions
      ? Math.max(...Object.keys(r.nonCoveredOptions).map(Number))
      : null;
    const est = insEstimateClaim(coveredSelfPay, gen, nonCovered, ncOpt);
    if (best === null || est.low < best.low) {
      best = { gen, low: est.low, high: est.high, has: est.has, possibility: est.possibility };
    }
  }
  return best!; // gen=공제 최대(보수적), low=최소 환급
}

function insCheckSelfPayCap(coveredShare: number, gen: number, nonCoveredShare: number) {
  const scope = INS_CAP_SCOPE[gen];
  const eligible = scope === "covered" ? coveredShare : coveredShare + nonCoveredShare;
  return {
    eligible,
    cap: INS_SELF_PAY_CAP,
    exceeded: eligible > INS_SELF_PAY_CAP,
    excess: Math.max(0, eligible - INS_SELF_PAY_CAP),
    nonCoveredExcluded: scope === "covered",
  };
}

function insCheckNhisCap(annualCovered: number, bracket: number, nursingLongStay: boolean) {
  const pair = INS_NHIS_CAP_2026[bracket];
  const cap = nursingLongStay ? pair[1] : pair[0];
  return { cap, exceeded: annualCovered > cap, refund: Math.max(0, annualCovered - cap) };
}

function InsResultCard({ n, title, children }: { n: string; title: string; children: ReactNode }) {
  return (
    <div className="rounded-[8px] border-l-4 border-accent-200 bg-white px-4 py-3 text-sm">
      <h4 className="mb-1 font-bold text-accent-600">{n} {title}</h4>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

function InsuranceSection({ coveredByYear, captured }: { coveredByYear: Record<string, number>; captured: boolean }) {
  const years = Object.keys(coveredByYear).sort();
  const [gen, setGen] = useState<number | "">("");
  const [ncOption, setNcOption] = useState<number | null>(null);
  const [nonCovered, setNonCovered] = useState<string>("");
  const [bracket, setBracket] = useState<number | "">("");
  const [year, setYear] = useState<string>(years.length ? years[years.length - 1] : "");
  const [receiptName, setReceiptName] = useState<string>("");
  // BOHUMFIT-028: 최소공제 설정 (additive, 세션 내만 — 저장 안 함)
  const [minDedOn, setMinDedOn] = useState(false);
  const [providerName, setProviderName] = useState("");
  const [gradeOverride, setGradeOverride] = useState("");       // "" = 자동분류 사용
  const [covOutCharge, setCovOutCharge] = useState("");         // 급여 통원 1회 진료비
  const [ncOutCharge, setNcOutCharge] = useState("");           // 비급여 통원 1회(또는 총액)
  const [ncVisitCount, setNcVisitCount] = useState("1");
  const [ncTotalMode, setNcTotalMode] = useState(false);        // 비급여 총액 모드
  const [inpatientCharge, setInpatientCharge] = useState("");   // 입원 진료비(정액공제 없음)

  const coveredSelfPay = year && coveredByYear[year] ? coveredByYear[year] : 0;
  const ncAmount = Math.max(0, parseInt((nonCovered || "").replace(/[^\d]/g, "") || "0", 10));
  const genNum = typeof gen === "number" ? gen : 0;

  const claim = genNum ? insEstimateClaim(coveredSelfPay, genNum, ncAmount, ncOption) : null;
  // BOHUMFIT-035: 세대 '모름' + 입력값 있으면 공제 가장 큰(환급 가장 작은) 세대 기준 보수적 추정.
  const consEst = (!genNum && coveredSelfPay + ncAmount > 0) ? insConservativeEstimate(coveredSelfPay, ncAmount) : null;

  let coveredShare = 0;
  let ncShare = 0;
  if (genNum) {
    const r = INS_GEN_RATES[genNum];
    const covHi = r.covered[1];
    let ncHi = r.nonCovered[1];
    if (ncOption != null && r.nonCoveredOptions && r.nonCoveredOptions[ncOption] != null) ncHi = r.nonCoveredOptions[ncOption];
    coveredShare = Math.round(coveredSelfPay * covHi);
    ncShare = Math.round(ncAmount * ncHi);
  }
  const selfPayCap = genNum ? insCheckSelfPayCap(coveredShare, genNum, ncShare) : null;
  const nhisCap = typeof bracket === "number" ? insCheckNhisCap(coveredSelfPay, bracket, false) : null;

  // BOHUMFIT-028: 최소공제 추정 (적용 시). 백엔드 calculator §6-1 와 동일 산식.
  const autoGrade = insClassifyProvider(providerName);
  const effGrade = gradeOverride || autoGrade;
  const minDed = genNum ? insProviderDeductible(genNum, effGrade) : null;  // 정액공제 또는 null(1·5세대/미선택)
  const covRate = genNum ? INS_GEN_RATES[genNum].covered[1] : 0;
  const ncRate = genNum
    ? (ncOption != null && INS_GEN_RATES[genNum].nonCoveredOptions && INS_GEN_RATES[genNum].nonCoveredOptions![ncOption] != null
        ? INS_GEN_RATES[genNum].nonCoveredOptions![ncOption]
        : INS_GEN_RATES[genNum].nonCovered[1])
    : 0;
  const mdNcVisits = Math.max(1, parseInt((ncVisitCount || "1").replace(/[^\d]/g, "") || "1", 10));
  const mdCovOut = minDed != null ? insClaimPerRow(insWon(covOutCharge), covRate, minDed) : null;
  const mdNcRow = minDed != null ? insClaimPerRow(insWon(ncOutCharge), ncRate, minDed) : null;
  const mdNcReimb = mdNcRow ? (ncTotalMode ? mdNcRow.reimbursement : mdNcRow.reimbursement * mdNcVisits) : 0;
  const mdInpatient = (minDed != null) ? insClaimPerRow(insWon(inpatientCharge), covRate, 0) : null;  // 입원 정액공제 없음

  const printedAt = new Date().toLocaleDateString("ko-KR");
  const genLabel = genNum ? `${genNum}세대` : "모름";
  const bracketLabel = typeof bracket === "number" ? `${bracket}분위` : "모름";
  const genOptionLabel = genNum === 3 ? ` (비급여 ${ncOption != null ? ncOption + "%" : "미선택"})` : "";

  return (
    <div className="space-y-4">
      <style dangerouslySetInnerHTML={{ __html: INS_PRINT_CSS }} />

      <div className="no-print rounded-[8px] bg-accent-50 p-3 text-xs leading-relaxed text-accent-900">
        실손보험 <b>청구 가능성</b>과 상한제 <b>환급 가능성</b>을 추정해 안내합니다. 확정 금액이 아니며,
        정확한 금액·보장 여부는 보험사·공단 확인이 필요합니다. 본 안내는 보험 모집·상품 추천·가입 권유가 아닙니다.
      </div>

      <div className="no-print rounded-[8px] border border-gray-100 bg-white p-4">
        <h3 className="mb-3 text-sm font-bold text-gray-800">실손 정보 입력</h3>
        <div className="grid gap-3 sm:grid-cols-2">
          {years.length > 1 && (
            <label className="text-xs font-semibold text-gray-600">
              조회 연도
              <select value={year} onChange={(e) => setYear(e.target.value)}
                className="mt-1 w-full rounded-[6px] border border-gray-200 p-2 text-sm">
                {years.map((y) => <option key={y} value={y}>{y}년</option>)}
              </select>
            </label>
          )}
          <label className="text-xs font-semibold text-gray-600">
            실손 세대
            <select value={gen === "" ? "" : String(gen)}
              onChange={(e) => { const v = e.target.value; setGen(v === "" ? "" : parseInt(v, 10)); setNcOption(null); }}
              className="mt-1 w-full rounded-[6px] border border-gray-200 p-2 text-sm">
              <option value="">모름</option>
              {[1, 2, 3, 4, 5].map((g) => <option key={g} value={g}>{g}세대 ({INS_GEN_RATES[g].period})</option>)}
            </select>
          </label>
          {gen === 3 && (
            <label className="text-xs font-semibold text-gray-600">
              3세대 비급여 자기부담
              <select value={ncOption == null ? "" : String(ncOption)}
                onChange={(e) => setNcOption(e.target.value === "" ? null : parseInt(e.target.value, 10))}
                className="mt-1 w-full rounded-[6px] border border-gray-200 p-2 text-sm">
                <option value="">선택</option>
                <option value="20">20%</option>
                <option value="30">30%</option>
              </select>
            </label>
          )}
          <label className="text-xs font-semibold text-gray-600">
            소득분위 (건보 상한제)
            <select value={bracket === "" ? "" : String(bracket)}
              onChange={(e) => { const v = e.target.value; setBracket(v === "" ? "" : parseInt(v, 10)); }}
              className="mt-1 w-full rounded-[6px] border border-gray-200 p-2 text-sm">
              <option value="">모름</option>
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((b) => <option key={b} value={b}>{b}분위</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-gray-600">
            비급여 금액 직접 입력 (선택)
            <input inputMode="numeric" value={nonCovered}
              onChange={(e) => setNonCovered(e.target.value)} placeholder="예: 500000"
              className="mt-1 w-full rounded-[6px] border border-gray-200 p-2 text-sm" />
          </label>
          <label className="text-xs font-semibold text-gray-600">
            비급여 영수증 첨부 (선택)
            <input type="file" accept="image/*,application/pdf"
              onChange={(e) => setReceiptName(e.target.files && e.target.files[0] ? e.target.files[0].name : "")}
              className="mt-1 w-full text-xs text-gray-500" />
            {receiptName && (
              <span className="mt-1 block text-[11px] text-gray-400">첨부: {receiptName} — 영수증 금액 자동 인식은 후속 단계입니다. 금액을 직접 입력해 주세요.</span>
            )}
          </label>
        </div>
        <p className="mt-3 text-[11px] text-gray-400">입력값(세대·분위·비급여)은 저장하지 않으며 이 화면에서만 사용됩니다.</p>
      </div>

      {!captured && (
        <div className="no-print rounded-[8px] bg-amber-50 p-3 text-xs text-amber-700">
          PDF 기본진료정보에서 급여 본인부담(내가 낸 의료비)을 찾지 못해 급여 청구 추정이 0으로 표시됩니다. 비급여 금액은 직접 입력해 확인할 수 있습니다.
        </div>
      )}

      <div className="no-print flex justify-end">
        <button
          type="button"
          onClick={() => window.print()}
          className="rounded-[8px] bg-accent-600 px-4 py-2 text-sm font-bold text-white transition-colors hover:bg-accent-700"
        >
          PDF로 저장(인쇄)
        </button>
      </div>

      <div id="insurance-print-area" className="space-y-4">
        <div className="print-only mb-2">
          <h2 className="text-base font-bold text-gray-900">실손 청구 안내 리포트</h2>
          <p className="text-[11px] text-gray-500">생성일: {printedAt}</p>
          <p className="text-[11px] text-gray-500">본 문서는 진료기록 기반 민감정보를 포함합니다 — 취급에 주의하세요.</p>
        </div>

        <div className="print-only rounded-[8px] border border-gray-200 p-3 text-xs text-gray-700">
          <b>입력 요약</b> — 실손 세대: {genLabel}{genOptionLabel} · 소득분위: {bracketLabel} · 비급여 입력: {wonToMan(ncAmount)} · 조회 연도: {year || "-"} · 급여 본인부담: {wonToMan(coveredSelfPay)}
        </div>

      <InsResultCard n="①" title="실손 청구 가능성">
        {claim ? (
          <>
            <p className="font-semibold text-gray-800">{claim.possibility}</p>
            {claim.has && (
              <p className="text-gray-600">청구 추정 {claim.low === claim.high ? wonToMan(claim.low) : `${wonToMan(claim.low)}~${wonToMan(claim.high)}`} 수준일 수 있습니다.</p>
            )}
            <p className="text-[11px] text-gray-400">급여 본인부담 {wonToMan(coveredSelfPay)}{ncAmount > 0 ? ` · 비급여 ${wonToMan(ncAmount)}` : ""} 기준 추정. 세대별 자기부담률은 2026-06 약관 확인 기준입니다.</p>
          </>
        ) : consEst ? (
          <>
            <p className="font-semibold text-gray-800">{consEst.possibility}</p>
            <p className="text-gray-600">청구 추정 약 {wonToMan(consEst.low)} 이하 수준일 수 있습니다.</p>
            <p className="text-[11px] text-amber-700">세대 모름 — 세대별 최대 공제 기준(가장 보수적, {consEst.gen}세대)으로 환급을 가장 작게 추정한 값입니다. 실제 세대를 선택하면 더 정확해집니다.</p>
            <p className="text-[11px] text-gray-400">급여 본인부담 {wonToMan(coveredSelfPay)}{ncAmount > 0 ? ` · 비급여 ${wonToMan(ncAmount)}` : ""} 기준. 세대별 자기부담률은 2026-06 약관 확인 기준입니다.</p>
          </>
        ) : <p className="text-gray-500">실손 세대를 선택하면 청구 추정 범위를 안내합니다. (세대를 모르면 급여/비급여 금액 입력 시 가장 보수적인 추정을 보여드립니다.)</p>}
      </InsResultCard>

      {/* BOHUMFIT-028: ①-b 실손 최소공제 적용 추정 (additive 옵션, 기존 ①②③ 불변) */}
      <InsResultCard n="①-b" title="실손 최소공제 적용 추정 (선택)">
        <div className="no-print space-y-2">
          <label className="flex items-center gap-2 text-xs font-semibold text-gray-700">
            <input type="checkbox" checked={minDedOn} onChange={(e) => setMinDedOn(e.target.checked)} />
            최소공제 적용 (통원 자기부담 = 정액·정률 중 큰 값)
          </label>
          {minDedOn && (
            <div className="grid gap-2 sm:grid-cols-2">
              <label className="text-[11px] font-semibold text-gray-600">
                기관명 (등급 추정)
                <input value={providerName} onChange={(e) => setProviderName(e.target.value)} placeholder="예: 서울정형외과의원"
                  className="mt-1 w-full rounded-[6px] border border-gray-200 p-1.5 text-sm" />
                <span className="mt-0.5 block text-[10px] text-gray-400">추정: {INS_GRADE_LABELS[autoGrade]} — 추정이며 실제와 다를 수 있어요(우측에서 수정).</span>
              </label>
              <label className="text-[11px] font-semibold text-gray-600">
                기관 등급 (수정)
                <select value={gradeOverride} onChange={(e) => setGradeOverride(e.target.value)}
                  className="mt-1 w-full rounded-[6px] border border-gray-200 p-1.5 text-sm">
                  <option value="">자동 ({INS_GRADE_LABELS[autoGrade]})</option>
                  <option value="clinic">의원</option>
                  <option value="general">종합병원</option>
                  <option value="tertiary">상급종합병원</option>
                </select>
              </label>
              <label className="text-[11px] font-semibold text-gray-600">
                급여 통원 1회 진료비
                <input inputMode="numeric" value={covOutCharge} onChange={(e) => setCovOutCharge(e.target.value)} placeholder="예: 30000"
                  className="mt-1 w-full rounded-[6px] border border-gray-200 p-1.5 text-sm" />
              </label>
              <label className="text-[11px] font-semibold text-gray-600">
                입원 진료비 (정액공제 없음)
                <input inputMode="numeric" value={inpatientCharge} onChange={(e) => setInpatientCharge(e.target.value)} placeholder="예: 100000"
                  className="mt-1 w-full rounded-[6px] border border-gray-200 p-1.5 text-sm" />
              </label>
              <label className="text-[11px] font-semibold text-gray-600">
                비급여 통원 {ncTotalMode ? "총액" : "1회 금액"}
                <input inputMode="numeric" value={ncOutCharge} onChange={(e) => setNcOutCharge(e.target.value)} placeholder="예: 30000"
                  className="mt-1 w-full rounded-[6px] border border-gray-200 p-1.5 text-sm" />
              </label>
              <div className="text-[11px] font-semibold text-gray-600">
                <label className="flex items-center gap-1">
                  <input type="checkbox" checked={ncTotalMode} onChange={(e) => setNcTotalMode(e.target.checked)} />
                  비급여 총액으로 입력 (건별 권장)
                </label>
                {!ncTotalMode && (
                  <label className="mt-1 block">횟수
                    <input inputMode="numeric" value={ncVisitCount} onChange={(e) => setNcVisitCount(e.target.value)}
                      className="mt-1 w-full rounded-[6px] border border-gray-200 p-1.5 text-sm" />
                  </label>
                )}
              </div>
            </div>
          )}
        </div>

        {minDedOn && (
          minDed == null ? (
            <p className="text-gray-500">{genNum ? "이 세대는 통원 정액공제를 적용하지 않습니다 (1세대 legacy·5세대 준비중)." : "실손 세대를 선택해 주세요."}</p>
          ) : (
            <div className="space-y-1">
              <p className="text-gray-700">적용 정액공제: {INS_GRADE_LABELS[effGrade]} {wonToMan(minDed)} (통원). 통원 자기부담 = 정액·정률 중 큰 값.</p>
              {mdCovOut && insWon(covOutCharge) > 0 && (
                <p className="text-gray-600">급여 통원 보상 추정 {wonToMan(mdCovOut.reimbursement)}{mdCovOut.lowValue ? " — 청구 실익 낮음" : ""}.</p>
              )}
              {mdNcRow && insWon(ncOutCharge) > 0 && (
                <p className="text-gray-600">비급여 통원 보상 추정 {wonToMan(mdNcReimb)}{ncTotalMode ? " (총액 1회 공제)" : ` (1회×${mdNcVisits}회)`}{mdNcRow.lowValue ? " — 청구 실익 낮음" : ""}.</p>
              )}
              {mdInpatient && insWon(inpatientCharge) > 0 && (
                <p className="text-gray-600">입원 보상 추정 {wonToMan(mdInpatient.reimbursement)} (정액공제 없음·정률만){mdInpatient.lowValue ? " — 청구 실익 낮음" : ""}.</p>
              )}
              <ul className="mt-1 list-disc pl-4 text-[11px] text-gray-400">
                <li>통원 자기부담은 정액·정률(진료비×자기부담률) 중 큰 값으로 추정합니다.</li>
                <li>진료비가 정액공제 이하면 보상이 없어 청구 실익이 낮을 수 있습니다.</li>
                <li>기관 등급은 기관명 추정값이며 실제와 다를 수 있어요 — 직접 수정 가능합니다.</li>
                <li>비급여는 회차별(1회 금액×횟수) 입력이 더 정확합니다. 총액만 입력하면 공제를 1회만 적용합니다.</li>
                <li>1세대·5세대는 통원 정액공제 미적용, 입원은 정액 통원공제가 없습니다.</li>
              </ul>
            </div>
          )
        )}
      </InsResultCard>

      <InsResultCard n="②" title="실손 자기부담금 상한제">
        {selfPayCap ? (
          <>
            <p className="font-semibold text-gray-800">{selfPayCap.exceeded ? "초과분 추가 보장 가능성 있음" : "상한 초과 아닐 수 있음"}</p>
            <p className="text-gray-600">연 자기부담금 합산 {wonToMan(selfPayCap.eligible)} / 세대 상한 {wonToMan(selfPayCap.cap)}{selfPayCap.exceeded ? ` · 초과 ${wonToMan(selfPayCap.excess)} 수준` : ""}.</p>
            {selfPayCap.nonCoveredExcluded && <p className="text-[11px] text-gray-400">4~5세대는 비급여 자기부담이 상한 대상이 아니라 급여 자기부담만 합산합니다.</p>}
          </>
        ) : <p className="text-gray-500">실손 세대를 선택해 주세요.</p>}
      </InsResultCard>

      <InsResultCard n="③" title="건강보험 본인부담상한제 (2026 기준)">
        {nhisCap ? (
          <>
            <p className="font-semibold text-gray-800">{nhisCap.exceeded ? "공단 환급 가능성 있음" : "환급 대상 아닐 수 있음"}</p>
            <p className="text-gray-600">연 급여 본인부담 {wonToMan(coveredSelfPay)} / {bracket}분위 상한 {wonToMan(nhisCap.cap)}{nhisCap.exceeded ? ` · 환급 ${wonToMan(nhisCap.refund)} 수준` : ""}.</p>
            <p className="text-[11px] text-gray-400">급여 본인부담만 대상(비급여 제외). 요양병원 120일 초과 시 상한이 달라질 수 있습니다.</p>
          </>
        ) : <p className="text-gray-500">소득분위를 선택하면 환급 가능성을 안내합니다.</p>}
      </InsResultCard>

        <div className="text-[11px] leading-relaxed text-gray-400">
          <p>{INS_DISCLAIMER}</p>
          <p className="print-only mt-1">본 안내는 추정이며 확정 금액이 아닙니다. 정확한 금액·보장 여부는 보험사·공단 확인이 필요하며, 보험 모집·상품추천·가입권유가 아닙니다.</p>
        </div>
      </div>
    </div>
  );
}

function ResultView({ result, mode, referenceDate }: { result: AnalyzeResult; mode: AudienceMode; referenceDate: string }) {
  // BOHUMFIT-009: 건강체/간편 탭 + Q1~Q4 신구조 섹션 복구.
  const [productTab, setProductTab] = useState<"standard" | "easy" | "insurance">("standard");
  const easyReports = result.easy_reports || {};
  const stdCount = Object.values(result.standard_reports).reduce((s, arr) => s + arr.length, 0);
  const easyCount = Object.values(easyReports).reduce((s, arr) => s + arr.length, 0);
  const activeReports = productTab === "standard" ? result.standard_reports : easyReports;
  const activeMemo = productTab === "standard" ? result.standard_kakao : (result.easy_kakao || "");
  const activeLabel = productTab === "standard" ? "건강체/표준체" : "간편심사";
  const copy = modeCopy[mode];

  // BOHUMFIT-036: 고지내역(Q1~Q5) 고객용 PDF 저장 — result_builder 결과값 그대로 전달(재계산 없음).
  const { session } = useAuth();
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState("");
  // BOHUMFIT-067: 고객명 직접 입력(선택). 우선순위 = 사용자 입력 > 공단 PDF 자동추출(065) > 날짜 폴백.
  const [customerName, setCustomerName] = useState("");
  const effectiveCustomerName = (customerName.trim() || result.customer_name || "").trim();
  async function saveDisclosurePdf() {
    const token = session?.access_token;
    setPdfLoading(true);
    setPdfError("");
    try {
      const res = await fetch(`${API_BASE}/api/report/pdf`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          report_type: "disclosure",
          reference_date: referenceDate,
          customer_name: effectiveCustomerName,   // BOHUMFIT-067: 입력>자동추출>"" (파일명·본문 공용)
          standard_reports: result.standard_reports,
          easy_reports: result.easy_reports || {},
          all_disease_summary: result.all_disease_summary || [],
          total_med_sum: result.total_med_sum,
        }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `리포트 생성 실패 (${res.status})`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      // BOHUMFIT-065: 파일명 = 보험핏-고지내역-{고객이름}-{분석기준일}. 이름은 공단 PDF 성명(폴백 시
      //   날짜만, 기존 동작). 공백·특수문자 제거(안전한 파일명), 길이 제한.
      const safeName = effectiveCustomerName.replace(/[^가-힣A-Za-z0-9]/g, "").slice(0, 20);
      const datePart = referenceDate || new Date().toISOString().slice(0, 10);
      a.download = safeName
        ? `보험핏-고지내역-${safeName}-${datePart}.pdf`
        : `보험핏-고지내역-${datePart}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      setPdfError(e instanceof Error ? e.message : "PDF 생성에 실패했어요. 잠시 후 다시 시도해 주세요.");
    } finally {
      setPdfLoading(false);
    }
  }

  return (
    <div>
      {(result.parse_errors || []).map((e, i) => (
        <div key={`parse-${i}`} className="mb-3 rounded-[8px] bg-amber-50 p-3 text-sm font-semibold text-amber-700">
          {e}
        </div>
      ))}

      {(result.warnings || [])
        // BOHUMFIT-105: AI 보조 판단 타임아웃/스킵 안내(비-액션 성능 안내)는 결과 화면에 표시하지 않는다.
        //   ("AI 보조 판단이 …초 안에 끝나지 않아…" 외 동일 계열 안내 포함. 다른 경고는 그대로 노출.)
        .filter((w) => !w.includes("AI 보조 판단"))
        .map((w, i) => (
          <div key={`warning-${i}`} className="mb-3 rounded-[8px] bg-gray-50 p-3 text-sm text-gray-600">
            {w}
          </div>
        ))}

      <div className="mb-5 rounded-[8px] bg-white p-5 shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
        <h2 className="text-xs font-bold text-accent-600">{copy.resultTitle}</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-4">
          <Metric label="건강체 고지" value={`${stdCount}건`} tone={stdCount ? "text-amber-600" : "text-emerald-600"} />
          <Metric label="간편 고지" value={`${easyCount}건`} tone={easyCount ? "text-amber-600" : "text-emerald-600"} />
          <Metric label="전체 병력" value={`${result.all_disease_summary.length}개`} />
          <Metric label="총 투약일" value={`${result.total_med_sum}일`} />
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-gray-100 pt-3">
          {/* BOHUMFIT-067: 고객명 직접 입력(선택). 입력 시 파일명·리포트 본문에 우선 적용, 비우면 자동추출/날짜 폴백. */}
          <label className="flex items-center gap-1.5 text-[12px] text-gray-600">
            <span className="whitespace-nowrap">고객명</span>
            <input
              type="text"
              value={customerName}
              onChange={(e) => setCustomerName(e.target.value)}
              placeholder={result.customer_name || "선택 입력"}
              maxLength={20}
              className="w-28 rounded-[6px] border border-gray-300 px-2 py-1 text-sm focus:border-accent-600 focus:outline-none"
            />
          </label>
          <button
            type="button"
            onClick={saveDisclosurePdf}
            disabled={pdfLoading}
            className="rounded-[8px] bg-accent-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-60"
          >
            {pdfLoading ? "PDF 생성 중…" : "고지내역 PDF 저장"}
          </button>
          <span className="text-[11px] text-gray-400">Q1~Q5 고지 검토 내역을 PDF로 저장합니다(개인정보 포함 — 보관에 유의).</span>
          {pdfError && <span className="text-[11px] text-red-500">{pdfError}</span>}
        </div>
      </div>

      <AllDiseaseSection diseases={result.all_disease_summary} />

      <section className="mb-5 overflow-hidden rounded-[8px] bg-white shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
        <div role="tablist" aria-label="심사 유형" className="flex border-b border-gray-100">
          {(["standard", "easy", "insurance"] as const).map((tab) => {
            const label = tab === "standard" ? "건강체/표준체" : tab === "easy" ? "간편심사" : "실손 청구";
            const count = tab === "standard" ? stdCount : tab === "easy" ? easyCount : 0;
            const active = productTab === tab;
            return (
              <button
                key={tab}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => setProductTab(tab)}
                className={`relative flex-1 py-3.5 text-sm font-bold transition-all ${
                  active ? "text-accent-600" : "text-gray-400 hover:text-gray-600"
                }`}
              >
                {label}
                {count > 0 && (
                  <span className={`ml-1.5 rounded-full px-1.5 py-0.5 text-xs font-semibold ${
                    active ? "bg-accent-100 text-accent-600" : "bg-gray-100 text-gray-500"
                  }`}>
                    {count}
                  </span>
                )}
                {active && <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent-600" />}
              </button>
            );
          })}
        </div>

        <div role="tabpanel" className="p-4">
          {productTab === "insurance" ? (
            <InsuranceSection
              coveredByYear={result.covered_self_pay_by_year || {}}
              captured={result.covered_self_pay_captured ?? false}
            />
          ) : (
            <DisclosureSection
              reports={activeReports}
              memo={activeMemo}
              label={`${activeLabel} ${copy.emptyTitle}`}
              mode={mode}
              isEasy={productTab === "easy"}
            />
          )}
        </div>
      </section>

      <DisclaimerBox />
    </div>
  );
}

function Metric({ label, value, tone = "text-gray-900" }: { label: string; value: string; tone?: string }) {
  return (
    <div className="rounded-[8px] bg-gray-50 px-4 py-3">
      <p className="text-xs font-semibold text-gray-400">{label}</p>
      <p className={`mt-1 text-xl font-black ${tone}`}>{value}</p>
    </div>
  );
}

const preTourSteps: TourStep[] = [
  {
    target: "date",
    title: "청약 예정일 입력",
    body: "고지 기간 계산의 기준일입니다. 기존 보험 점검은 실제 가입일을 넣어 주세요.",
  },
  {
    target: "upload",
    title: "PDF 첨부",
    body: "기본진료, 세부진료, 처방조제 PDF를 올리고 암호가 있으면 비밀번호를 입력합니다.",
  },
];

const postTourSteps: TourStep[] = [
  {
    target: "summary",
    title: "병력 요약 펼치기 또는 접기",
    body: "전체 병력은 처음에는 접혀 있습니다. 필요할 때 펼쳐 원자료 집계를 확인합니다.",
  },
  {
    target: "copy",
    title: "카카오톡 복사하기",
    body: "상품 기준별 고지 메시지를 복사해 고객 안내나 내부 검토에 활용합니다.",
  },
  {
    target: "cards",
    title: "하단 병력 확인하기",
    body: "질병별 카드에서 통원, 입원, 수술, 투약, 추가검사 의심 내용을 최종 확인합니다.",
  },
];

function TourOverlay({
  phase,
  index,
  onNext,
  onSkip,
}: {
  phase: TourPhase;
  index: number;
  onNext: () => void;
  onSkip: () => void;
}) {
  const steps = phase === "pre" ? preTourSteps : postTourSteps;
  const step = steps[index];
  const [rect, setRect] = useState<DOMRect | null>(null);
  const displayIndex = phase === "pre" ? index + 1 : index + 4;
  const isLast = index === steps.length - 1;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onSkip();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onSkip]);

  useEffect(() => {
    const target = document.querySelector<HTMLElement>(`[data-tour="${step.target}"]`);
    if (!target) {
      const emptyTimer = window.setTimeout(() => setRect(null), 0);
      return () => window.clearTimeout(emptyTimer);
    }

    const updateRect = () => setRect(target.getBoundingClientRect());
    target.scrollIntoView({ block: "center", inline: "nearest", behavior: "smooth" });
    updateRect();
    const timer = window.setTimeout(updateRect, 220);

    window.addEventListener("resize", updateRect);
    window.addEventListener("scroll", updateRect, true);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("resize", updateRect);
      window.removeEventListener("scroll", updateRect, true);
    };
  }, [step.target]);

  const spotlightStyle = rect
    ? {
        left: Math.max(12, rect.left - 10),
        top: Math.max(12, rect.top - 10),
        width: rect.width + 20,
        height: rect.height + 20,
        borderRadius: 16,
        boxShadow: "0 0 0 9999px rgba(17, 24, 39, 0.68), 0 24px 70px rgba(0, 0, 0, 0.28)",
      }
    : undefined;

  const cardStyle = (() => {
    if (!rect || typeof window === "undefined") return undefined;
    const cardWidth = Math.min(360, window.innerWidth - 32);
    const below = rect.bottom + 34;
    const above = rect.top - 294;
    const top = below + 260 < window.innerHeight ? below : Math.max(18, above);
    const left = Math.min(Math.max(16, rect.left + rect.width / 2 - cardWidth / 2), window.innerWidth - cardWidth - 16);
    return { width: cardWidth, top, left };
  })();

  return (
    <div className="fixed inset-0 z-[1000]">
      {rect ? (
        <div
          aria-hidden="true"
          className="pointer-events-none fixed border-2 border-white bg-transparent ring-2 ring-accent-600/40"
          style={spotlightStyle}
        />
      ) : (
        <div aria-hidden="true" className="absolute inset-0 bg-gray-950/70" />
      )}

      <section
        role="dialog"
        aria-modal="true"
        aria-label="사용 안내 튜토리얼"
        className={`fixed rounded-[8px] bg-white p-5 shadow-[0_22px_70px_rgba(15,23,42,0.3)] ${
          cardStyle ? "" : "left-1/2 top-1/2 w-[min(360px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2"
        }`}
        style={cardStyle}
      >
        <div className="mb-6 flex items-center justify-between text-sm font-semibold text-gray-400">
          <span>{displayIndex} / 6</span>
          <button type="button" onClick={onSkip} className="hover:text-gray-700">
            건너뛰기
          </button>
        </div>
        <div className="mb-5">
          <p className="text-lg font-extrabold text-gray-900 break-keep">{step.title}</p>
          <p className="mt-3 text-sm leading-7 text-gray-600 break-keep">{step.body}</p>
        </div>
        <div className="flex items-center justify-between gap-4">
          <div className="flex gap-1.5">
            {Array.from({ length: 6 }).map((_, dotIndex) => (
              <span
                key={dotIndex}
                className={`h-2 rounded-full ${
                  dotIndex + 1 === displayIndex ? "w-7 bg-accent-600" : "w-2 bg-gray-200"
                }`}
              />
            ))}
          </div>
          <button
            type="button"
            onClick={onNext}
            className="rounded-[8px] bg-accent-600 px-5 py-3 text-sm font-extrabold text-white shadow-sm hover:bg-accent-700"
          >
            {isLast ? "완료" : "다음"}
          </button>
        </div>
      </section>
    </div>
  );
}

export default function Disclosure({ initialMode = "agent" }: { initialMode?: AudienceMode }) {
  const [searchParams] = useSearchParams();
  const requestedMode = searchParams.get("mode");
  const mode: AudienceMode = requestedMode === "customer" || requestedMode === "agent" ? requestedMode : initialMode;
  const copy = modeCopy[mode];

  const { session } = useAuth();
  const [refDate, setRefDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [birthdate, setBirthdate] = useState("");
  const [consent, setConsent] = useState(false);
  const [subjectConsent, setSubjectConsent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [tourPhase, setTourPhase] = useState<TourPhase | null>(() => (readTourSeen().pre ? null : "pre"));
  const [tourIndex, setTourIndex] = useState(0);
  const [postTourShown, setPostTourShown] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/health`).catch(() => {});
  }, []);

  const handleTourNext = () => {
    if (!tourPhase) return;
    const steps = tourPhase === "pre" ? preTourSteps : postTourSteps;
    if (tourIndex >= steps.length - 1) {
      markTourSeen(tourPhase);
      setTourPhase(null);
      return;
    }
    setTourIndex((value) => value + 1);
  };

  const { showToast } = useToast(); // BOHUMFIT-131

  const handleTourSkip = () => {
    if (tourPhase) markTourSeen(tourPhase);
    setTourPhase(null);
  };

  const replayTour = (phase: TourPhase) => {
    setTourPhase(phase);
    setTourIndex(0);
  };

  const showPostTour = () => {
    if (readTourSeen().post) return;
    setTourPhase("post");
    setTourIndex(0);
    setPostTourShown(true);
  };

  const analyze = async () => {
    const files = fileRef.current?.files;
    if (!files?.length) {
      setError("PDF 파일을 업로드해 주세요.");
      return;
    }
    if (files.length > MAX_FILE_COUNT) {
      setError(`PDF는 최대 ${MAX_FILE_COUNT}개까지 업로드할 수 있습니다.`);
      return;
    }
    const nonPdf = Array.from(files).find((f) => !f.name.toLowerCase().endsWith(".pdf"));
    if (nonPdf) {
      setError(`PDF 파일만 업로드할 수 있어요. (${nonPdf.name})`);
      return;
    }
    const tooLarge = Array.from(files).find((f) => f.size > MAX_FILE_SIZE);
    if (tooLarge) {
      setError(`개별 PDF 크기는 ${MAX_FILE_SIZE / 1024 / 1024}MB를 넘을 수 없습니다. (${tooLarge.name})`);
      return;
    }
    const totalSize = Array.from(files).reduce((sum, f) => sum + f.size, 0);
    if (totalSize > MAX_TOTAL_SIZE) {
      setError(`전체 PDF 합계 크기는 ${MAX_TOTAL_SIZE / 1024 / 1024}MB를 넘을 수 없습니다.`);
      return;
    }
    if (!consent) {
      setError("민감정보(건강정보) 처리 동의가 필요합니다. 동의 항목을 확인해 주세요.");
      return;
    }
    if (mode === "agent" && !subjectConsent) {
      setError("고객 진료자료 업로드 권한과 정보주체 동의 확보 여부를 확인해 주세요.");
      return;
    }
    const token = session?.access_token;
    if (!token) {
      setError("로그인이 필요합니다. 다시 로그인한 뒤 시도해 주세요.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    const form = new FormData();
    for (const f of files) form.append("files", f);
    form.append("reference_date", refDate);
    if (birthdate) form.append("birthdate_pw", birthdate);

    try {
      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
        // BOHUMFIT-BUG-007: 서버 ANALYZE_TIMEOUT_SECONDS=300 과 동기화.
        // 기존 180_000(180s) → 350_000(350s). 서버보다 50s 여유를 둬서
        // 서버가 정상 응답할 시간을 보장하고 "signal timed out" 오류를 막는다.
        signal: AbortSignal.timeout(350_000),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || "분석 중 문제가 발생했어요. 잠시 후 다시 시도해 주세요.");
      }
      const data = await res.json();
      setResult(data);
      showToast("분석이 완료되었습니다", "success"); // BOHUMFIT-131
      if (!postTourShown) {
        window.setTimeout(showPostTour, 0);
      }
    } catch (e: unknown) {
      if (e instanceof TypeError && e.message.includes("fetch")) {
        setError(connectionErrorMessage(API_BASE));
      } else {
        setError(e instanceof Error ? e.message : "알 수 없는 오류가 발생했습니다.");
      }
      showToast("파일을 확인해 주세요", "error"); // BOHUMFIT-131
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="mb-5 flex justify-end">
        <button
          type="button"
          onClick={() => replayTour(result ? "post" : "pre")}
          className="rounded-[8px] border border-gray-200 bg-white px-3 py-2 text-xs font-bold text-gray-500 hover:border-accent-600/40 hover:text-accent-600"
        >
          {result ? "결과 가이드 다시보기" : "필터 가이드 다시보기"}
        </button>
      </div>

      <div className="mb-6">
        <p className="mb-1 text-xs font-bold tracking-wider text-accent-600">{copy.badge}</p>
        <h1 className="ko-heading text-2xl font-extrabold tracking-tight text-gray-900">{copy.title}</h1>
        <p className="ko-text mt-1 text-sm leading-6 text-gray-500 break-keep">{copy.subtitle}</p>
      </div>

      <section className="mb-5 rounded-[8px] bg-white p-6 shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
        {/* BOHUMFIT-076: 구독 상태·이번 달 사용량 배지를 분석(업로드) 영역 상단으로 이동(내부 사용자·무료 동작 시 자동 숨김). */}
        <div className="mb-4 flex justify-end">
          <UsageBadge />
        </div>
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
          <div data-tour="date">
            <label className="mb-2 block text-sm font-semibold text-gray-700">{copy.dateLabel}</label>
            <input
              type="date"
              value={refDate}
              onChange={(e) => setRefDate(e.target.value)}
              className="w-full rounded-[8px] bg-gray-50 px-4 py-2.5 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-accent-600/30"
            />
            <p className="mt-2 text-xs leading-5 text-gray-400">{copy.dateHelp}</p>
          </div>

          <div>
            <label className="mb-2 block text-sm font-semibold text-gray-700">
              PDF 비밀번호 <span className="font-normal text-gray-300">선택</span>
            </label>
            <input
              type="text"
              placeholder="예: 19900101"
              value={birthdate}
              onChange={(e) => setBirthdate(e.target.value)}
              className="w-full rounded-[8px] bg-gray-50 px-4 py-2.5 text-sm text-gray-800 placeholder:text-gray-300 focus:outline-none focus:ring-2 focus:ring-accent-600/30"
            />
            <p className="mt-2 text-xs leading-5 text-gray-400">암호화 PDF라면 생년월일 8자리를 입력해 주세요.</p>
          </div>
        </div>

        <div data-tour="upload" className="mt-5 rounded-[8px] border-2 border-dashed border-accent-200 bg-accent-50 p-6 text-center transition hover:border-accent-400">
          <input
            ref={fileRef}
            type="file"
            accept=".pdf"
            multiple
            className="block w-full cursor-pointer text-sm text-gray-600 file:mr-4 file:rounded-[8px] file:border-0 file:bg-accent-600 file:px-5 file:py-2.5 file:text-sm file:font-bold file:text-white hover:file:bg-accent-700"
          />
          <p className="mt-3 text-xs text-gray-500">
            {copy.uploadHelp} 파일은 최대 {MAX_FILE_COUNT}개, 개별 {MAX_FILE_SIZE / 1024 / 1024}MB, 총합 {MAX_TOTAL_SIZE / 1024 / 1024}MB까지 업로드할 수 있습니다.
          </p>
        </div>

        <label className="mt-4 flex items-start gap-2.5 rounded-[8px] bg-gray-50 px-4 py-3 text-xs leading-5 text-gray-600">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            className="mt-0.5 h-4 w-4 shrink-0 accent-[#15663D]"
          />
          <span className="break-keep">
            업로드하는 진료자료에는 <b className="font-bold text-gray-700">민감정보(건강에 관한 정보)</b>가 포함됩니다.
            고지 리스크 점검 목적의 처리에 동의하며, 자료는 분석 직후 보험핏 서버에서 폐기되고 서비스 데이터베이스에 저장되지 않습니다.
            <Link to="/privacy" className="ml-1 underline hover:text-gray-800">개인정보처리방침</Link>
          </span>
        </label>

        {mode === "agent" && (
          <label className="mt-3 flex items-start gap-2.5 rounded-[8px] bg-gray-50 px-4 py-3 text-xs leading-5 text-gray-600">
            <input
              type="checkbox"
              checked={subjectConsent}
              onChange={(e) => setSubjectConsent(e.target.checked)}
              className="mt-0.5 h-4 w-4 shrink-0 accent-[#15663D]"
            />
            <span className="break-keep">
              고객 등 제3자의 진료자료를 업로드하는 경우, 정보주체에게 보험핏 분석 목적·민감정보 처리·AI 위탁 처리 내용을 안내했고
              업로드 및 분석에 필요한 동의를 확보했습니다.
            </span>
          </label>
        )}

        <button
          onClick={analyze}
          disabled={loading || !consent || (mode === "agent" && !subjectConsent)}
          className="mt-5 w-full rounded-[8px] bg-accent-600 py-3 text-sm font-bold text-white shadow-[0_2px_8px_rgba(21,102,61,0.3)] transition-colors hover:bg-accent-700 disabled:opacity-50"
        >
          {loading ? "분석 중..." : copy.button}
        </button>
      </section>

      {mode === "customer" && !result && (
        <section className="mb-5 rounded-[8px] border border-emerald-100 bg-emerald-50 p-5">
          <p className="text-sm font-extrabold text-emerald-800">고객 안내 포인트</p>
          <p className="mt-2 text-xs leading-6 text-emerald-700 break-keep">
            이 점검은 보험 가입 권유가 아니라 기존 보험의 고지 누락 가능성을 미리 확인하는 참고 절차입니다.
            분석 결과는 최종 법률·보험 인수 판단이 아니며, 실제 청약서 질문과 보험사 심사 기준에 맞춰 한 번 더 대조해야 합니다.
          </p>
        </section>
      )}

      {error && (
        <div className="mb-5 rounded-[8px] bg-red-50 p-4 text-sm font-semibold text-red-600">{error}</div>
      )}

      {loading && (
        <div aria-live="polite" className="mb-5">
          <AnalysisProgress />
        </div>
      )}

      {result && <ResultView result={result} mode={mode} referenceDate={refDate} />}

      {!result && !loading && !error && (
        <section className="rounded-[8px] bg-white p-8 text-center shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
          <p className="text-sm font-bold text-gray-800">심평원 진료자료 PDF를 업로드해 주세요.</p>
          <p className="mt-2 text-xs leading-6 text-gray-400 break-keep">
            기본진료, 세부진료, 처방조제 3종을 함께 올리면 통원, 입원, 수술, 투약 기록을 더 정확하게 교차검증할 수 있습니다.
          </p>
        </section>
      )}

      {tourPhase && (
        <TourOverlay
          phase={tourPhase}
          index={tourIndex}
          onNext={handleTourNext}
          onSkip={handleTourSkip}
        />
      )}
    </div>
  );
}
