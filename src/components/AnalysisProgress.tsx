// BOHUMFIT-138(항목2): 분석 중 단계 목록 제거 — 스피너 + 안내 문구만 유지.
import Spinner from "./Spinner";

export default function AnalysisProgress() {
  return (
    <div className="rounded-2xl border border-accent-100 bg-accent-50/40 px-5 py-6">
      {/* BOHUMFIT-131: 브랜드 그린 원형 스피너 */}
      <div className="flex justify-center">
        <Spinner size={48} label="분석 중입니다..." />
      </div>
      <p className="mt-4 text-center text-[11px] text-gray-400">
        PDF 페이지가 많을수록 시간이 더 걸릴 수 있어요. 페이지를 닫지 말고 잠시만 기다려주세요.
      </p>
    </div>
  );
}
