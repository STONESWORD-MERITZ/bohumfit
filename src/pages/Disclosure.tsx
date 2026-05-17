import { useState, useRef, useEffect } from "react";

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

function connectionErrorMessage(apiBase: string): string {
  return (
    "서버에 연결할 수 없습니다(Failed to fetch). " +
    (typeof window !== "undefined" && window.location.hostname !== "localhost"
      ? `프론트 배포 환경에서는 VITE_API_URL로 백엔드 주소를 설정해야 합니다. (현재 요청: ${apiBase}) `
      : "") +
    "백엔드가 실행 중인지, CORS 설정을 확인해 주세요."
  );
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
  additional_test_hit?: boolean;
  additional_test_reason?: string;
  treatment_ongoing?: boolean | null;
  treatment_ongoing_reason?: string;
  hospitals: string[];
  first_hospital?: string;
  last_hospital?: string;
  detail: string;
};

type AnalyzeResult = {
  flagged_count: number;
  total_q_count: number;
  total_visit_sum: number;
  total_med_sum: number;
  standard_reports: Record<string, SummaryItem[]>;
  easy_reports: Record<string, SummaryItem[]>;
  all_disease_summary: DiseaseSummary[];
  standard_kakao: string;
  easy_kakao: string;
  parse_errors: string[];
  warnings: string[];
  meritz_easy_message: string;
};

// ── 위험도 판정 ──────────────────────────────────────────────
type Risk = "red" | "orange" | "gray" | "yellow" | "green";

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

const RISK: Record<Risk, { border: string; label: string; pill: string; bg: string; text: string }> = {
  red:    { border: "border-red-400",     label: "text-red-600",     pill: "bg-red-100 text-red-600",        bg: "bg-red-50",     text: "text-red-700" },
  orange: { border: "border-orange-400",  label: "text-orange-600",  pill: "bg-orange-100 text-orange-600",  bg: "bg-orange-50",  text: "text-orange-700" },
  gray:   { border: "border-gray-400",    label: "text-gray-500",    pill: "bg-gray-100 text-gray-600",      bg: "bg-gray-50",    text: "text-gray-600" },
  yellow: { border: "border-amber-400",   label: "text-amber-600",   pill: "bg-amber-100 text-amber-700",    bg: "bg-amber-50",   text: "text-amber-700" },
  green:  { border: "border-emerald-400", label: "text-emerald-600", pill: "bg-emerald-100 text-emerald-700",bg: "bg-emerald-50", text: "text-emerald-700" },
};

function Chip({ label, tone = "gray" }: { label: string; tone?: string }) {
  const tones: Record<string, string> = {
    gray:        "bg-gray-100 text-gray-600",
    "gray-light":"bg-gray-50 text-gray-400 border border-gray-200",
    red:         "bg-red-100 text-red-600",
    "red-light": "bg-red-50 text-red-500 border border-red-200",
    amber:       "bg-amber-100 text-amber-700",
    emerald:     "bg-emerald-100 text-emerald-700",
    orange:      "bg-orange-100 text-orange-600",
    indigo:      "bg-indigo-100 text-indigo-600",
    rose:        "bg-rose-100 text-rose-600",
  };
  return (
    <span className={`text-xs px-3 py-1 rounded-full font-semibold ${tones[tone] ?? tones.gray}`}>
      {label}
    </span>
  );
}

function extractQNumber(qTitle: string): string {
  const m = qTitle.match(/\[(?:간편)?(\d+)번질문\]/);
  return m ? `Q${m[1]}` : "Q";
}

// ── 전체 병력 요약 섹션 ──────────────────────────────────────
function AllDiseaseSection({ diseases }: { diseases: DiseaseSummary[] }) {
  const [open, setOpen] = useState(true);

  if (!diseases.length) return null;

  return (
    <div className="bg-white rounded-2xl shadow-[0_2px_12px_rgba(0,0,0,0.06)] mb-5 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full px-5 py-4 flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-2.5">
          <svg className={`w-4 h-4 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
          <span className="text-sm font-bold text-gray-800">전체 병력 요약</span>
          <span className="text-xs font-semibold text-gray-400">{diseases.length}개 질환</span>
        </div>
      </button>

      {open && (
        <div className="border-t border-gray-100">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-gray-50 text-gray-400 font-semibold">
                  <th className="px-4 py-2.5 text-left">코드</th>
                  <th className="px-4 py-2.5 text-left">질병명</th>
                  <th className="px-4 py-2.5 text-left">최초~최근</th>
                  <th className="px-4 py-2.5 text-center">통원</th>
                  <th className="px-4 py-2.5 text-center">입원</th>
                  <th className="px-4 py-2.5 text-center">수술</th>
                  <th className="px-4 py-2.5 text-center">투약</th>
                  <th className="px-4 py-2.5 text-left">병원</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {diseases.map((d, i) => (
                  <tr key={i} className="hover:bg-gray-50/60">
                    <td className="px-4 py-2 font-mono text-gray-500">{d.display_code || d.code}</td>
                    <td className="px-4 py-2 text-gray-800 font-medium max-w-[160px] truncate">{d.name || "—"}</td>
                    <td className="px-4 py-2 text-gray-400 whitespace-nowrap">
                      {d.first_date}
                      {d.latest_date && d.latest_date !== d.first_date ? ` ~ ${d.latest_date}` : ""}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {d.visit_count > 0 ? (
                        <span className={`font-semibold ${d.visit_count >= 7 ? "text-amber-600" : "text-gray-600"}`}>
                          {d.visit_count}회
                        </span>
                      ) : <span className="text-gray-300">—</span>}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {d.inpatient_days > 0 ? (
                        <span className="font-semibold text-red-500">{d.inpatient_days}일</span>
                      ) : <span className="text-gray-300">—</span>}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {d.surgery_count > 0 ? (
                        <span className="font-semibold text-red-500">{d.surgery_count}건</span>
                      ) : <span className="text-gray-300">—</span>}
                    </td>
                    <td className="px-4 py-2 text-center">
                      {d.med_days > 0 ? (
                        <span className={`font-semibold ${d.med_days >= 30 ? "text-amber-600" : "text-emerald-600"}`}>
                          {d.med_days}일
                        </span>
                      ) : <span className="text-gray-300">—</span>}
                    </td>
                    <td className="px-4 py-2 text-gray-400 max-w-[140px] truncate">
                      {d.hospitals.slice(0, 2).join(", ") || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ── 질환 카드 ────────────────────────────────────────────────
function DiseaseCard({ item, qNum }: { item: SummaryItem; qNum: string }) {
  const risk  = riskOf(item);
  const sc    = RISK[risk];
  const surgN = item.surgery_count ?? item.surgeries?.length ?? 0;
  const procN = item.procedures?.length ?? 0;
  const suspN = item.surgery_suspected?.length ?? 0;
  const period = item.first_date && item.latest_date && item.first_date !== item.latest_date
    ? `${item.first_date} ~ ${item.latest_date}`
    : (item.first_date || "");
  const hasBottom = suspN > 0 || item.additional_test_hit || item.treatment_ongoing != null;

  return (
    <div className={`px-5 py-4 border-l-4 ${sc.border}`}>
      {/* 헤더: 질병명 + 코드 + Q배지 */}
      <div className="flex items-start justify-between gap-3 mb-1">
        <div className="flex items-center gap-2 flex-wrap min-w-0">
          <span className="text-[15px] font-bold text-gray-900">
            {item.name || "질병명 없음"}
          </span>
          {item.code && (
            <span className="font-mono text-[11px] text-gray-400 bg-gray-100 px-2 py-0.5 rounded shrink-0">
              {item.display_code || item.code}
            </span>
          )}
        </div>
        <span className="text-[11px] font-bold bg-[#4F46E5] text-white px-2 py-0.5 rounded-md shrink-0">
          {qNum}
        </span>
      </div>

      {/* 진료기간 + 최초진단 */}
      <div className="text-xs text-gray-500 mb-2.5 space-y-0.5">
        {period && (
          <div className="flex items-center gap-2">
            <span className="text-gray-400 shrink-0">진료기간</span>
            <span>{period}</span>
            {item.last_hospital && (
              <span className="text-gray-400 truncate">{item.last_hospital}</span>
            )}
          </div>
        )}
        {item.first_diagnosis_date && (
          <div className="flex items-center gap-2">
            <span className="text-gray-400 shrink-0">최초진단</span>
            <span>{item.first_diagnosis_date}</span>
            {item.first_hospital && (
              <span className="text-gray-400 truncate">{item.first_hospital}</span>
            )}
          </div>
        )}
      </div>

      {/* 알릴의무 사유 */}
      {item.detail && (
        <div className="text-[13px] font-medium mb-3 leading-relaxed text-gray-700">
          <span className="mr-1">📋</span>{item.detail}
        </div>
      )}

      {/* 5대 통계 칩 */}
      <div className="flex flex-wrap gap-2 mb-2">
        <Chip label={`통원 ${item.visit ?? 0}회`}
              tone={(item.visit ?? 0) >= 7 ? "amber" : "gray"} />
        <Chip label={`입원 ${item.inpatient ?? 0}일`}
              tone={(item.inpatient ?? 0) > 0 ? "red" : "gray"} />
        <Chip label={`입원 ${item.inpatient_count ?? 0}회`}
              tone={(item.inpatient_count ?? 0) > 0 ? "red-light" : "gray"} />
        <Chip label={`수술 ${surgN}건`}
              tone={surgN > 0 ? "red" : "gray"} />
        <Chip label={`투약 ${item.med_days ?? 0}일`}
              tone={(item.med_days ?? 0) >= 30 ? "amber"
                    : (item.med_days ?? 0) > 0 ? "emerald" : "gray"} />
      </div>

      {/* 보조 칩 */}
      <div className="flex flex-wrap gap-2">
        {procN > 0 && <Chip label={`시술 ${procN}건`} tone="orange" />}
        {suspN > 0 && <Chip label={`⚠️ 수술 의심 ${suspN}건`} tone="gray-light" />}
        {item.additional_test_hit && <Chip label="재검사" tone="indigo" />}
        {item.treatment_ongoing === true  && <Chip label="치료 중" tone="rose" />}
        {item.treatment_ongoing === false && <Chip label="종결" tone="emerald" />}
      </div>

      {/* 하단 부가정보 */}
      {hasBottom && (
        <div className="mt-3 pt-2.5 border-t border-gray-100 space-y-1 text-xs leading-relaxed">
          {suspN > 0 && (
            <p className="text-gray-400">
              <span className="text-gray-300 mr-1.5">의심 행위</span>
              {item.surgery_suspected!.slice(0, 3).join(", ")}
            </p>
          )}
          {item.additional_test_hit && item.additional_test_reason && (
            <p className="text-indigo-500">
              <span className="text-indigo-300 mr-1.5">재검사</span>
              {item.additional_test_reason}
            </p>
          )}
          {item.treatment_ongoing === true && item.treatment_ongoing_reason && (
            <p className="text-rose-500">
              <span className="text-rose-300 mr-1.5">치료 중</span>
              {item.treatment_ongoing_reason}
            </p>
          )}
          {item.treatment_ongoing === false && item.treatment_ongoing_reason && (
            <p className="text-emerald-600">
              <span className="text-emerald-400 mr-1.5">종결</span>
              {item.treatment_ongoing_reason}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── 고지사항 섹션 (상품별) ───────────────────────────────────
function DisclosureSection({
  reports, kakaoMsg, label,
}: {
  reports: Record<string, SummaryItem[]>;
  kakaoMsg: string;
  label: string;
}) {
  const [kakaoOpen, setKakaoOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(kakaoMsg);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const hasItems = Object.keys(reports).length > 0;

  return (
    <div>
      {/* 카카오 메시지 */}
      {kakaoMsg && (
        <div className="bg-white rounded-2xl shadow-[0_2px_12px_rgba(0,0,0,0.06)] mb-4 overflow-hidden">
          <div className="px-5 py-4 flex items-center justify-between">
            <button
              onClick={() => setKakaoOpen(!kakaoOpen)}
              className="flex items-center gap-2 text-left"
            >
              <svg className={`w-4 h-4 text-gray-400 transition-transform ${kakaoOpen ? "rotate-180" : ""}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
              <span className="text-sm font-bold text-gray-800">카카오톡 전송용 메시지</span>
            </button>
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl font-bold text-sm"
              style={{ background: "#FEE500", color: "#191919" }}
            >
              <svg width="16" height="16" viewBox="0 0 18 18" fill="none">
                <path d="M9 1C4.58 1 1 3.8 1 7.24c0 2.22 1.48 4.17 3.7 5.27l-.94 3.47c-.08.3.26.54.52.36L8.05 13.7c.31.03.63.05.95.05 4.42 0 8-2.8 8-6.24S13.42 1 9 1Z" fill="#191919" />
              </svg>
              {copied ? "복사 완료!" : "복사하기"}
            </button>
          </div>
          {kakaoOpen && (
            <pre className="text-xs text-gray-600 whitespace-pre-wrap font-sans leading-relaxed bg-gray-50 px-5 py-4">
              {kakaoMsg}
            </pre>
          )}
        </div>
      )}

      {/* 질환 카드 */}
      {hasItems ? (
        <div className="space-y-4">
          {Object.entries(reports).map(([qTitle, items]) => {
            const qNum = extractQNumber(qTitle);
            const sectionTitle = qTitle.replace(/^\[.*?\]\s*/, "");
            return (
              <div key={qTitle} className="bg-white rounded-2xl shadow-[0_2px_12px_rgba(0,0,0,0.06)] overflow-hidden">
                <div className="px-5 py-3.5 flex items-center gap-2.5 border-b border-gray-100">
                  <span className="text-xs font-bold bg-[#4F46E5] text-white px-2.5 py-1 rounded-md shrink-0">
                    {qNum}
                  </span>
                  <span className="text-sm font-bold text-gray-800">{sectionTitle}</span>
                </div>
                <div className="divide-y divide-gray-50">
                  {items.map((item, idx) => (
                    <DiseaseCard key={idx} item={item} qNum={qNum} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="bg-emerald-50 rounded-2xl p-8 text-center shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
          <div className="text-4xl mb-3">✅</div>
          <p className="text-sm font-bold text-emerald-700">{label} 고지 대상 항목이 없습니다</p>
        </div>
      )}
    </div>
  );
}

// ── 결과 뷰 ─────────────────────────────────────────────────
function ResultView({ result }: { result: AnalyzeResult }) {
  const [productTab, setProductTab] = useState<"standard" | "easy">("standard");

  const activeReports = productTab === "standard" ? result.standard_reports : result.easy_reports;
  const activeKakao   = productTab === "standard" ? result.standard_kakao   : result.easy_kakao;
  const activeLabel   = productTab === "standard" ? "건강체/표준체" : "간편심사";

  const stdCount  = Object.values(result.standard_reports).reduce((s, arr) => s + arr.length, 0);
  const easyCount = Object.values(result.easy_reports).reduce((s, arr) => s + arr.length, 0);

  return (
    <div>
      {/* 파싱 오류 */}
      {result.parse_errors
        .filter(e => e.includes("🔒") || e.includes("손상") || e.includes("비밀번호"))
        .map((e, i) => (
          <div key={i} className="bg-amber-50 rounded-xl p-3 mb-3 text-sm text-amber-700 font-semibold">{e}</div>
        ))}

      {/* 메리츠 간편 경고 */}
      {result.meritz_easy_message && (
        <div className="bg-orange-50 border border-orange-200 rounded-xl p-4 mb-4 text-xs text-orange-800 whitespace-pre-wrap leading-relaxed">
          {result.meritz_easy_message}
        </div>
      )}

      {/* ① 전체 병력 요약 */}
      <AllDiseaseSection diseases={result.all_disease_summary} />

      {/* ② 상품별 고지사항 */}
      <div className="bg-white rounded-2xl shadow-[0_2px_12px_rgba(0,0,0,0.06)] overflow-hidden mb-5">
        {/* 탭 헤더 */}
        <div className="flex border-b border-gray-100">
          {(["standard", "easy"] as const).map((tab) => {
            const label = tab === "standard" ? "건강체/표준체" : "간편심사";
            const count = tab === "standard" ? stdCount : easyCount;
            const active = productTab === tab;
            return (
              <button
                key={tab}
                onClick={() => setProductTab(tab)}
                className={`flex-1 py-3.5 text-sm font-bold transition-all relative ${
                  active
                    ? "text-[#4F46E5]"
                    : "text-gray-400 hover:text-gray-600"
                }`}
              >
                {label}
                {count > 0 && (
                  <span className={`ml-1.5 text-xs px-1.5 py-0.5 rounded-full font-semibold ${
                    active ? "bg-indigo-100 text-indigo-600" : "bg-gray-100 text-gray-500"
                  }`}>{count}</span>
                )}
                {active && (
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#4F46E5]" />
                )}
              </button>
            );
          })}
        </div>

        {/* 탭 콘텐츠 */}
        <div className="p-4">
          <DisclosureSection
            reports={activeReports}
            kakaoMsg={activeKakao}
            label={activeLabel}
          />
        </div>
      </div>
    </div>
  );
}

// ── 메인 ────────────────────────────────────────────────────
export default function Disclosure() {
  const [refDate, setRefDate]     = useState(() => new Date().toISOString().slice(0, 10));
  const [birthdate, setBirthdate] = useState("");
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState("");
  const [result, setResult]       = useState<AnalyzeResult | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/health`).catch(() => {});
  }, []);

  const analyze = async () => {
    const files = fileRef.current?.files;
    if (!files?.length) { setError("PDF 파일을 업로드해 주세요."); return; }
    setLoading(true); setError(""); setResult(null);

    const form = new FormData();
    for (const f of files) form.append("files", f);
    form.append("reference_date", refDate);
    if (birthdate) form.append("birthdate_pw", birthdate);

    try {
      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: "POST",
        body: form,
        signal: AbortSignal.timeout(180_000),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `서버 오류 (${res.status})`);
      }
      setResult(await res.json());
    } catch (e: unknown) {
      if (e instanceof TypeError && e.message.includes("fetch"))
        setError(connectionErrorMessage(API_BASE));
      else
        setError(e instanceof Error ? e.message : "알 수 없는 오류");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* 헤더 */}
      <div className="mb-6">
        <p className="text-xs font-bold text-[#4F46E5] tracking-wider mb-1">AI 고지 분석</p>
        <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">알릴의무 필터</h1>
        <p className="text-sm text-gray-400 mt-1">
          심평원 진료 PDF를 업로드하면 AI가 고지 의무 항목을 자동으로 추출합니다.
        </p>
      </div>

      {/* 설정 카드 */}
      <div className="bg-white rounded-2xl shadow-[0_2px_12px_rgba(0,0,0,0.06)] p-6 mb-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">기준일 (청약예정일)</label>
            <input
              type="date"
              value={refDate}
              onChange={(e) => setRefDate(e.target.value)}
              className="w-full bg-gray-50 rounded-xl px-4 py-2.5 text-sm text-gray-800 focus:ring-2 focus:ring-[#4F46E5]/30 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              생년월일 <span className="text-gray-300 font-normal">(선택)</span>
            </label>
            <input
              type="text"
              placeholder="예: 19900101"
              value={birthdate}
              onChange={(e) => setBirthdate(e.target.value)}
              className="w-full bg-gray-50 rounded-xl px-4 py-2.5 text-sm text-gray-800 placeholder:text-gray-300 focus:ring-2 focus:ring-[#4F46E5]/30 focus:outline-none"
            />
          </div>
        </div>

        <div className="mt-5 bg-indigo-50 border-2 border-dashed border-indigo-200 rounded-2xl p-6 text-center hover:border-indigo-400 hover:bg-indigo-100/50 transition-all duration-200">
          <input
            ref={fileRef}
            type="file"
            accept=".pdf"
            multiple
            className="block w-full text-sm text-gray-600 file:mr-4 file:py-3 file:px-6 file:rounded-xl file:border-0 file:text-sm file:font-bold file:bg-[#4F46E5] file:text-white file:shadow-md hover:file:bg-[#4338CA] hover:file:shadow-lg hover:file:scale-105 file:transition-all file:duration-200 cursor-pointer"
          />
          <p className="text-xs text-gray-500 mt-3">
            건강e음 기본진료·세부진료·처방조제 PDF (1개 이상)
          </p>
        </div>

        <button
          onClick={analyze}
          disabled={loading}
          className="w-full mt-5 py-3 bg-[#4F46E5] hover:bg-[#4338CA] disabled:opacity-50 text-white font-bold rounded-xl text-sm transition-colors shadow-[0_2px_8px_rgba(79,70,229,0.3)]"
        >
          {loading ? "분석 중..." : "AI 고지사항 추출"}
        </button>
      </div>

      {/* 에러 */}
      {error && (
        <div className="bg-red-50 rounded-2xl p-4 mb-5 text-sm text-red-600 font-semibold">{error}</div>
      )}

      {/* 결과 */}
      {result && <ResultView result={result} />}

      {/* 빈 상태 */}
      {!result && !loading && !error && (
        <div className="text-center py-16 bg-white rounded-2xl shadow-[0_2px_12px_rgba(0,0,0,0.06)]">
          <div className="text-5xl mb-4">📂</div>
          <div className="text-sm font-bold text-gray-700 mb-1">심평원 진료자료 PDF를 업로드하세요</div>
          <div className="text-xs text-gray-400 leading-relaxed">
            건강e음에서 기본진료·세부진료·처방조제 3종을 발급받아 올려주세요.
            <br />
            1개만 올려도 분석 가능합니다.
          </div>
        </div>
      )}
    </div>
  );
}
