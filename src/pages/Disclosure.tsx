import { useState, useRef } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

type SummaryItem = {
  first_date: string;
  latest_date: string;
  code: string;
  name: string;
  visit: number;
  med_days: number;
  inpatient: number;
  surgeries: string[];
  hospitals: string[];
  detail: string;
  weight: string;
};

type AnalyzeResult = {
  flagged_count: number;
  total_q_count: number;
  total_visit_sum: number;
  total_med_sum: number;
  summary_reports: Record<string, SummaryItem[]>;
  kakao_message: string;
  parse_errors: string[];
  warnings: string[];
};

const weightColor: Record<string, string> = {
  critical: "bg-red-500/15 text-red-400 border-red-400/30",
  high: "bg-amber-500/15 text-amber-400 border-amber-400/30",
  mid: "bg-blue-500/15 text-blue-300 border-blue-400/30",
  low: "bg-white/10 text-white/60 border-white/20",
};

export default function Disclosure() {
  const [productType, setProductType] = useState("standard");
  const [refDate, setRefDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [birthdate, setBirthdate] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const analyze = async () => {
    const files = fileRef.current?.files;
    if (!files?.length) {
      setError("PDF 파일을 업로드해 주세요.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    const form = new FormData();
    for (const f of files) form.append("files", f);
    form.append("product_type", productType);
    form.append("reference_date", refDate);
    if (birthdate) form.append("birthdate_pw", birthdate);

    try {
      const res = await fetch(`${API_BASE}/api/analyze`, { method: "POST", body: form });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `서버 오류 (${res.status})`);
      }
      setResult(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "알 수 없는 오류");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="py-6">
      {/* Header */}
      <div className="pb-4 mb-5 border-b border-white/10">
        <p className="text-xs font-semibold text-blue-400 tracking-wider mb-1">AI 고지 분석</p>
        <h1 className="text-xl font-extrabold text-white tracking-tight">알릴의무 필터</h1>
        <p className="text-xs text-white/40 mt-1">심평원 진료 PDF를 업로드하면 AI가 고지 의무 항목을 자동으로 추출합니다.</p>
      </div>

      {/* Controls */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
        {/* Product type */}
        <div>
          <label className="block text-sm font-semibold text-white/75 mb-2">심사 기준</label>
          <div className="flex gap-2">
            {[
              { value: "standard", label: "건강체/표준체" },
              { value: "easy", label: "간편심사" },
            ].map((opt) => (
              <button
                key={opt.value}
                onClick={() => setProductType(opt.value)}
                className={`flex-1 py-2 px-3 rounded-lg text-sm font-semibold border transition-colors ${
                  productType === opt.value
                    ? "bg-blue-500/20 border-blue-400/60 text-white"
                    : "bg-white/[0.06] border-white/15 text-white/70 hover:bg-white/10"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Date */}
        <div>
          <label className="block text-sm font-semibold text-white/75 mb-2">기준일 (청약예정일)</label>
          <input
            type="date"
            value={refDate}
            onChange={(e) => setRefDate(e.target.value)}
            className="w-full bg-white/[0.07] border border-white/[0.18] rounded-lg px-3 py-2 text-sm text-white/90 focus:border-blue-500 focus:outline-none"
          />
        </div>

        {/* Birthdate */}
        <div>
          <label className="block text-sm font-semibold text-white/75 mb-2">
            생년월일 <span className="text-white/40 font-normal">(선택)</span>
          </label>
          <input
            type="text"
            placeholder="예: 19900101"
            value={birthdate}
            onChange={(e) => setBirthdate(e.target.value)}
            className="w-full bg-white/[0.07] border border-white/[0.18] rounded-lg px-3 py-2 text-sm text-white/90 placeholder:text-white/30 focus:border-blue-500 focus:outline-none"
          />
        </div>
      </div>

      {/* Upload */}
      <div className="bg-white/[0.04] border border-dashed border-white/20 rounded-xl p-6 mb-5 text-center hover:border-blue-400/50 transition-colors">
        <input ref={fileRef} type="file" accept=".pdf" multiple className="block w-full text-sm text-white/70 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-500 file:text-white hover:file:bg-blue-600 cursor-pointer" />
        <p className="text-xs text-white/40 mt-2">건강e음 기본진료·세부진료·처방조제 PDF (1개 이상)</p>
      </div>

      {/* Analyze Button */}
      <button
        onClick={analyze}
        disabled={loading}
        className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white font-bold rounded-xl text-sm transition-colors mb-6"
      >
        {loading ? "분석 중..." : "AI 고지사항 추출"}
      </button>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-400/30 rounded-xl p-4 mb-5 text-sm text-red-400 font-semibold">
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div>
          {/* Stat Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
            {[
              { label: "고지 질병 수", value: result.flagged_count, warn: result.flagged_count > 0 },
              { label: "해당 질문 수", value: result.total_q_count, warn: result.total_q_count > 3 },
              { label: "총 통원 횟수", value: result.total_visit_sum, warn: false },
              { label: "총 투약일수", value: result.total_med_sum, warn: result.total_med_sum >= 30 },
            ].map((s) => (
              <div
                key={s.label}
                className={`rounded-xl p-4 border shadow-md ${
                  s.warn
                    ? "bg-red-500/[0.08] border-red-400/30"
                    : "bg-white/[0.05] border-white/10"
                }`}
              >
                <div className="text-[0.7rem] text-white/45 font-semibold mb-1.5">{s.label}</div>
                <div className={`text-3xl font-bold font-mono leading-none ${s.warn ? "text-red-400" : "text-white"}`}>
                  {s.value}
                </div>
              </div>
            ))}
          </div>

          {/* Warnings */}
          {result.parse_errors.map((e, i) => (
            <div key={i} className="bg-amber-500/10 border border-amber-400/30 rounded-lg p-3 mb-2 text-sm text-amber-300 font-semibold">
              {e}
            </div>
          ))}

          {/* Duty Cards */}
          {Object.entries(result.summary_reports).map(([qTitle, items]) => (
            <div key={qTitle} className="bg-white/[0.05] border border-white/10 rounded-xl mb-3 overflow-hidden shadow-lg">
              {/* Card Head */}
              <div className="flex items-center gap-3 px-4 py-3 bg-white/[0.07] border-b border-white/[0.08]">
                <span className="text-[0.68rem] font-bold bg-blue-500 text-white px-2.5 py-0.5 rounded-full">
                  {qTitle.match(/Q\d+|간편\d+번/)?.[0] || "Q"}
                </span>
                <span className="text-sm font-bold text-white/90">{qTitle.replace(/^\[.*?\]\s*/, "")}</span>
              </div>

              {/* Items */}
              {items.map((item, idx) => (
                <div key={idx} className="px-4 py-3 border-b border-white/[0.06] last:border-b-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-bold text-white/90">{item.name}</span>
                    {item.code && (
                      <span className="font-mono text-[0.7rem] text-white/40 bg-white/[0.08] px-1.5 py-0.5 rounded">
                        {item.code}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-white/40 mb-1">
                    {item.first_date && item.latest_date && item.first_date !== item.latest_date
                      ? `${item.first_date} ~ ${item.latest_date}`
                      : item.first_date || item.latest_date}
                    {item.hospitals?.length > 0 && ` · ${item.hospitals.join(", ")}`}
                  </div>
                  {item.detail && (
                    <div className="text-xs text-blue-300 font-semibold bg-blue-500/10 border-l-[3px] border-blue-500 rounded-md px-2.5 py-1 my-1">
                      {item.detail}
                    </div>
                  )}
                  <div className="flex flex-wrap gap-1 mt-2">
                    {item.inpatient > 0 && (
                      <span className="text-[0.7rem] px-2 py-0.5 rounded-full border font-medium bg-red-500/10 text-red-400 border-red-400/30">
                        입원 {item.inpatient}일
                      </span>
                    )}
                    {item.surgeries?.length > 0 && (
                      <span className="text-[0.7rem] px-2 py-0.5 rounded-full border font-medium bg-red-500/10 text-red-400 border-red-400/30">
                        수술: {item.surgeries.join(", ")}
                      </span>
                    )}
                    {item.visit > 0 && (
                      <span className="text-[0.7rem] px-2 py-0.5 rounded-full border font-medium bg-white/[0.08] text-white/60 border-white/12">
                        통원 {item.visit}회
                      </span>
                    )}
                    {item.med_days > 0 && (
                      <span className="text-[0.7rem] px-2 py-0.5 rounded-full border font-medium bg-blue-500/10 text-blue-300 border-blue-400/30">
                        투약 {item.med_days}일
                      </span>
                    )}
                    <span className={`text-[0.7rem] px-2 py-0.5 rounded-full border font-medium ${weightColor[item.weight] || weightColor.mid}`}>
                      {item.weight}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ))}

          {/* Empty */}
          {Object.keys(result.summary_reports).length === 0 && (
            <div className="flex items-center gap-3 bg-emerald-500/[0.08] border border-emerald-400/25 rounded-xl p-5 text-sm font-bold text-emerald-400">
              고지 대상 없음
            </div>
          )}

          {/* Kakao Copy */}
          {result.kakao_message && (
            <div className="mt-5">
              <div className="text-xs font-bold text-white/80 mb-2 flex items-center gap-1.5 pb-2 border-b border-white/10">
                카카오톡 전송용 메시지
              </div>
              <div className="bg-white/[0.05] border border-white/10 rounded-xl p-4">
                <pre className="text-xs text-white/70 whitespace-pre-wrap font-sans leading-relaxed mb-3">
                  {result.kakao_message}
                </pre>
                <button
                  onClick={() => navigator.clipboard.writeText(result.kakao_message)}
                  className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg transition-colors"
                >
                  복사
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!result && !loading && !error && (
        <div className="text-center py-14 bg-white/[0.04] border border-white/10 rounded-2xl">
          <div className="text-5xl mb-3">📂</div>
          <div className="text-sm font-bold text-white/90 mb-1">심평원 진료자료 PDF를 업로드하세요</div>
          <div className="text-xs text-white/40 leading-relaxed">
            건강e음(health.kr)에서 기본진료·세부진료·처방조제 3종을 발급받아 올려주세요.
            <br />
            1개만 올려도 분석 가능합니다.
          </div>
        </div>
      )}
    </div>
  );
}
