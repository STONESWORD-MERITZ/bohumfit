// BOHUMFIT-029: 독립 실손 예상 보험금 계산기 (알릴의무 분석과 분리된 진입점).
// 계산은 src/lib/insuranceCalc.ts (검증된 미러)만 사용 — Disclosure·backend 와 동일 금액.
// 모드: (A) 수기 직접입력 / (B) PDF 업로드(진료비 자동 채움). PDF 모드도 알릴의무 Q&A 는 표시하지 않는다.
import { useState, type ReactNode } from "react";
import { useAuth } from "../lib/auth-context";
import {
  INS_GEN_RATES,
  INS_GRADE_LABELS,
  INS_DISCLAIMER,
  insProviderDeductible,
  insClaimPerRow,
  insEstimateClaim,
  insCheckSelfPayCap,
  insCheckNhisCap,
  insWon,
  wonToMan,
} from "../lib/insuranceCalc";

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="text-xs font-semibold text-gray-600">
      {label}
      {children}
    </label>
  );
}

const SELECT_CLS = "mt-1 w-full rounded-[6px] border border-gray-200 p-2 text-sm";

export default function InsuranceCalculator() {
  const { session } = useAuth();

  // 공통 입력
  const [mode, setMode] = useState<"manual" | "pdf">("manual");
  const [gen, setGen] = useState<number | "">("");
  const [ncOption, setNcOption] = useState<number | null>(null);
  const [bracket, setBracket] = useState<number | "">("");
  const [nonCovered, setNonCovered] = useState("");      // 비급여 금액(연)
  const [covManual, setCovManual] = useState("");        // 수기: 연간 급여 본인부담(내가 낸 의료비)

  // PDF 모드
  const [files, setFiles] = useState<FileList | null>(null);
  const [birthdate, setBirthdate] = useState("");
  const [refDate, setRefDate] = useState(new Date().toISOString().slice(0, 10));
  const [loading, setLoading] = useState(false);
  const [pdfError, setPdfError] = useState("");
  const [coveredByYear, setCoveredByYear] = useState<Record<string, number>>({});
  const [pdfCaptured, setPdfCaptured] = useState<boolean | null>(null);

  const genNum = typeof gen === "number" ? gen : 0;

  // 급여 본인부담(연): 수기=직접입력, PDF=최근 연도 자동
  const pdfYears = Object.keys(coveredByYear).sort();
  const pdfLatestYear = pdfYears.length ? pdfYears[pdfYears.length - 1] : "";
  const coveredSelfPay = mode === "manual"
    ? insWon(covManual)
    : (pdfLatestYear && coveredByYear[pdfLatestYear] ? coveredByYear[pdfLatestYear] : 0);
  const ncAmount = insWon(nonCovered);

  // ① 청구 가능성
  const claim = genNum ? insEstimateClaim(coveredSelfPay, genNum, ncAmount, ncOption) : null;

  // 자기부담금 share (자기부담률 상한 기준 — Disclosure 와 동일)
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

  // BOHUMFIT-032: 독립 계산기에서는 사용자가 기관종별/건별 금액을 알기 어렵다.
  // 등급 미상은 공용 산식의 상급 기준으로 보수 적용하고, 현재 화면 입력값 기준으로 자동 추정한다.
  const autoGrade = "unknown";
  const minDed = genNum ? insProviderDeductible(genNum, autoGrade) : null;
  const covRateHi = genNum ? INS_GEN_RATES[genNum].covered[1] : 0;
  const covRateLo = genNum ? INS_GEN_RATES[genNum].covered[0] : 0;
  const ncRateHi = genNum
    ? (ncOption != null && INS_GEN_RATES[genNum].nonCoveredOptions && INS_GEN_RATES[genNum].nonCoveredOptions![ncOption] != null
        ? INS_GEN_RATES[genNum].nonCoveredOptions![ncOption]
        : INS_GEN_RATES[genNum].nonCovered[1])
    : 0;
  const ncRateLo = genNum
    ? (ncOption != null && INS_GEN_RATES[genNum].nonCoveredOptions && INS_GEN_RATES[genNum].nonCoveredOptions![ncOption] != null
        ? INS_GEN_RATES[genNum].nonCoveredOptions![ncOption]
        : INS_GEN_RATES[genNum].nonCovered[0])
    : 0;
  const mdCovLow = minDed != null ? insClaimPerRow(coveredSelfPay, covRateHi, minDed) : null;
  const mdCovHigh = minDed != null ? insClaimPerRow(coveredSelfPay, covRateLo, minDed) : null;
  const mdNcLow = minDed != null ? insClaimPerRow(ncAmount, ncRateHi, minDed) : null;
  const mdNcHigh = minDed != null ? insClaimPerRow(ncAmount, ncRateLo, minDed) : null;
  const mdAutoLow = (mdCovLow?.reimbursement || 0) + (mdNcLow?.reimbursement || 0);
  const mdAutoHigh = (mdCovHigh?.reimbursement || 0) + (mdNcHigh?.reimbursement || 0);
  const printedAt = new Date().toLocaleString("ko-KR");
  const genLabel = genNum ? `${genNum}세대 (${INS_GEN_RATES[genNum].period})` : "미선택";
  const bracketLabel = typeof bracket === "number" ? `${bracket}분위` : "미선택";

  async function runPdf() {
    const token = session?.access_token;
    if (!token) { setPdfError("로그인이 필요합니다."); return; }
    if (!files || files.length === 0) { setPdfError("심평원 PDF를 선택해 주세요."); return; }
    const form = new FormData();
    for (const f of Array.from(files)) form.append("files", f);
    form.append("reference_date", refDate);
    if (birthdate) form.append("birthdate_pw", birthdate);
    setLoading(true); setPdfError("");
    try {
      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `분석 실패 (${res.status})`);
      }
      const data = await res.json();
      // 진료비(급여 본인부담)만 사용 — 알릴의무 Q&A 결과는 사용/표시하지 않음.
      setCoveredByYear(data.covered_self_pay_by_year || {});
      setPdfCaptured(!!data.covered_self_pay_captured);
    } catch (e) {
      setPdfError(e instanceof Error ? e.message : "분석 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <style>{`
        @media screen {
          .print-only { display: none !important; }
        }
        @media print {
          @page { margin: 12mm; }
          body * { visibility: hidden !important; }
          #insurance-print-area, #insurance-print-area * { visibility: visible !important; }
          #insurance-print-area {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            padding: 0;
          }
          .no-print { display: none !important; }
          .print-only { display: block !important; }
        }
      `}</style>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-xl font-extrabold text-gray-950">실손 예상 보험금 계산</h1>
          <p className="mt-1 text-sm text-gray-600 break-keep">
            알릴의무 분석 없이 실손 청구 실익만 빠르게 추정합니다. 확정 금액이 아니며, 정확한 금액·보장 여부는
            보험사·공단 확인이 필요합니다. 본 계산은 보험 모집·상품추천·가입권유가 아닙니다.
          </p>
        </div>
        <div className="flex flex-col items-start gap-1 sm:items-end">
          <button
            type="button"
            onClick={() => window.print()}
            className="rounded-[8px] bg-gray-950 px-4 py-2 text-sm font-bold text-white transition-colors hover:bg-gray-800 disabled:opacity-50"
          >
            PDF로 저장
          </button>
        </div>
      </div>

      {/* 모드 토글 */}
      <div className="no-print inline-flex rounded-[8px] border border-gray-200 bg-white p-1 text-sm font-bold">
        {(["manual", "pdf"] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            className={`rounded-[6px] px-4 py-1.5 transition-colors ${mode === m ? "bg-[#4F46E5] text-white" : "text-gray-500 hover:text-gray-800"}`}
          >
            {m === "manual" ? "수기 입력" : "PDF 자동 채움"}
          </button>
        ))}
      </div>

      {/* PDF 모드 입력 */}
      {mode === "pdf" && (
        <div className="no-print rounded-[8px] border border-gray-100 bg-white p-4">
          <p className="mb-2 text-xs text-gray-500 break-keep">
            심평원 PDF에서 <b>급여 진료비(내가 낸 의료비)</b>만 추출해 자동 채웁니다. 알릴의무 Q&amp;A 결과는 이 화면에 표시하지 않습니다.
            업로드한 PDF는 진료기록 민감정보를 포함하며 저장하지 않습니다.
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="심평원 PDF">
              <input type="file" accept="application/pdf" multiple
                onChange={(e) => setFiles(e.target.files)}
                className="mt-1 w-full text-xs text-gray-500" />
            </Field>
            <Field label="기준일(청약/조회일)">
              <input type="date" value={refDate} onChange={(e) => setRefDate(e.target.value)} className={SELECT_CLS} />
            </Field>
            <Field label="PDF 비밀번호(생년월일, 선택)">
              <input value={birthdate} onChange={(e) => setBirthdate(e.target.value)} placeholder="예: 900101" className={SELECT_CLS} />
            </Field>
            <div className="flex items-end">
              <button type="button" onClick={runPdf} disabled={loading}
                className="rounded-[8px] bg-[#4F46E5] px-4 py-2 text-sm font-bold text-white disabled:opacity-50">
                {loading ? "분석 중…" : "진료비 추출"}
              </button>
            </div>
          </div>
          {pdfError && <p className="mt-2 text-xs font-semibold text-amber-700">{pdfError}</p>}
          {pdfCaptured === true && (
            <p className="mt-2 text-xs text-emerald-600">급여 진료비 자동 채움 완료 — 최근 연도({pdfLatestYear}) {wonToMan(coveredSelfPay)}. 아래에서 수정 가능합니다.</p>
          )}
          {pdfCaptured === false && (
            <p className="mt-2 text-xs text-amber-700">PDF에서 급여 진료비를 찾지 못했습니다. 수기 입력으로 확인해 주세요.</p>
          )}
        </div>
      )}

      {/* 공통 입력 */}
      <div className="no-print rounded-[8px] border border-gray-100 bg-white p-4">
        <h2 className="mb-3 text-sm font-bold text-gray-800">실손 정보</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="실손 세대">
            <select value={gen === "" ? "" : String(gen)}
              onChange={(e) => { const v = e.target.value; setGen(v === "" ? "" : parseInt(v, 10)); setNcOption(null); }}
              className={SELECT_CLS}>
              <option value="">모름</option>
              {[1, 2, 3, 4, 5].map((g) => <option key={g} value={g}>{g}세대 ({INS_GEN_RATES[g].period})</option>)}
            </select>
          </Field>
          {gen === 3 && (
            <Field label="3세대 비급여 자기부담">
              <select value={ncOption == null ? "" : String(ncOption)}
                onChange={(e) => setNcOption(e.target.value === "" ? null : parseInt(e.target.value, 10))}
                className={SELECT_CLS}>
                <option value="">선택</option>
                <option value="20">20%</option>
                <option value="30">30%</option>
              </select>
            </Field>
          )}
          <Field label="소득분위 (건보 상한제)">
            <select value={bracket === "" ? "" : String(bracket)}
              onChange={(e) => { const v = e.target.value; setBracket(v === "" ? "" : parseInt(v, 10)); }}
              className={SELECT_CLS}>
              <option value="">모름</option>
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((b) => <option key={b} value={b}>{b}분위</option>)}
            </select>
          </Field>
          {mode === "manual" && (
            <Field label="연간 급여 본인부담금 (내가 낸 의료비)">
              <input inputMode="numeric" value={covManual} onChange={(e) => setCovManual(e.target.value)} placeholder="예: 800000" className={SELECT_CLS} />
            </Field>
          )}
          <Field label="비급여 금액 (선택)">
            <input inputMode="numeric" value={nonCovered} onChange={(e) => setNonCovered(e.target.value)} placeholder="예: 500000" className={SELECT_CLS} />
          </Field>
        </div>
        <p className="mt-3 text-[11px] text-gray-400">입력값은 저장하지 않으며 이 화면에서만 사용됩니다.</p>
      </div>

      <div id="insurance-print-area" className="space-y-4">
        <div className="print-only">
          <h2 className="text-lg font-extrabold text-gray-950">실손 청구 안내 리포트</h2>
          <p className="mt-1 text-[11px] text-gray-500">생성일: {printedAt}</p>
          <p className="mt-1 text-[11px] text-gray-500">본 문서는 진료기록 기반 민감정보를 포함할 수 있습니다. 고객 안내 및 보관 시 취급에 주의하세요.</p>
        </div>

        <div className="print-only rounded-[8px] border border-gray-200 bg-white p-3 text-xs text-gray-700">
          <b>입력 요약</b> — 실손 세대: {genLabel} · 소득분위: {bracketLabel} · 급여 본인부담: {wonToMan(coveredSelfPay)} · 비급여: {wonToMan(ncAmount)}
        </div>

      {/* 결과 ① */}
      <ResultCard n="①" title="실손 청구 가능성">
        {claim ? (
          <>
            <p className="font-semibold text-gray-800">{claim.possibility}</p>
            {claim.has && (
              <p className="text-gray-600">청구 추정 {claim.low === claim.high ? wonToMan(claim.low) : `${wonToMan(claim.low)}~${wonToMan(claim.high)}`} 수준일 수 있습니다.</p>
            )}
            <p className="text-[11px] text-gray-400">급여 본인부담 {wonToMan(coveredSelfPay)}{ncAmount > 0 ? ` · 비급여 ${wonToMan(ncAmount)}` : ""} 기준 추정.</p>
          </>
        ) : <p className="text-gray-500">실손 세대를 선택하면 청구 추정 범위를 안내합니다.</p>}
      </ResultCard>

      {/* 결과 ② */}
      <ResultCard n="②" title="실손 자기부담금 상한제">
        {selfPayCap ? (
          <>
            <p className="font-semibold text-gray-800">{selfPayCap.exceeded ? "초과분 추가 보장 가능성 있음" : "상한 초과 아닐 수 있음"}</p>
            <p className="text-gray-600">연 자기부담금 합산 {wonToMan(selfPayCap.eligible)} / 세대 상한 {wonToMan(selfPayCap.cap)}{selfPayCap.exceeded ? ` · 초과 ${wonToMan(selfPayCap.excess)} 수준` : ""}.</p>
            {selfPayCap.nonCoveredExcluded && <p className="text-[11px] text-gray-400">4~5세대는 비급여 자기부담이 상한 대상이 아니라 급여 자기부담만 합산합니다.</p>}
          </>
        ) : <p className="text-gray-500">실손 세대를 선택해 주세요.</p>}
      </ResultCard>

      {/* 결과 ③ */}
      <ResultCard n="③" title="건강보험 본인부담상한제 (2026 기준)">
        {nhisCap ? (
          <>
            <p className="font-semibold text-gray-800">{nhisCap.exceeded ? "공단 환급 가능성 있음" : "환급 대상 아닐 수 있음"}</p>
            <p className="text-gray-600">연 급여 본인부담 {wonToMan(coveredSelfPay)} / {bracket}분위 상한 {wonToMan(nhisCap.cap)}{nhisCap.exceeded ? ` · 환급 ${wonToMan(nhisCap.refund)} 수준` : ""}.</p>
            <p className="text-[11px] text-gray-400">급여 본인부담만 대상(비급여 제외). 요양병원 120일 초과 시 상한이 달라질 수 있습니다.</p>
          </>
        ) : <p className="text-gray-500">소득분위를 선택하면 환급 가능성을 안내합니다.</p>}
      </ResultCard>

      {/* 결과 ①-b 최소공제 (BOHUMFIT-032: 입력형 옵션 제거, 자동 적용) */}
      <ResultCard n="①-b" title="실손 최소공제 자동 반영">
        {minDed == null ? (
          <p className="text-gray-500">{genNum ? "이 세대는 통원 정액공제 자동 적용 대상이 아닙니다." : "실손 세대를 선택하면 최소공제 기준을 자동 반영합니다."}</p>
        ) : (
          <>
            <p className="font-semibold text-gray-800">
              자동 기준: {INS_GRADE_LABELS[autoGrade]} {wonToMan(minDed)} 공제
            </p>
            <p className="text-gray-600">
              최소공제 반영 후 청구 추정 {mdAutoLow === mdAutoHigh ? wonToMan(mdAutoLow) : `${wonToMan(mdAutoLow)}~${wonToMan(mdAutoHigh)}`} 수준일 수 있습니다.
            </p>
            <p className="text-[11px] text-gray-400 break-keep">
              독립 계산기는 기관종별·건별 진료비를 입력받지 않으므로 등급 미상은 상급 기준으로 보수 적용합니다.
              실제 청구는 진료 건별 공제와 약관 심사에 따라 달라질 수 있습니다.
            </p>
          </>
        )}
      </ResultCard>

      <p className="text-[11px] leading-relaxed text-gray-400">{INS_DISCLAIMER}</p>
      </div>
    </div>
  );
}

function ResultCard({ n, title, children }: { n: string; title: string; children: ReactNode }) {
  return (
    <div className="rounded-[8px] border-l-4 border-indigo-200 bg-white px-4 py-3 text-sm">
      <h3 className="mb-1 font-bold text-[#4F46E5]">{n} {title}</h3>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}
