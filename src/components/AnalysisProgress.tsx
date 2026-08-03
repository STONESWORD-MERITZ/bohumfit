// BOHUMFIT-138(항목2): 분석 중 단계 목록 제거 — 스피너 + 안내 문구만 유지.
// BOHUMFIT-268b: 모바일에 한해 **실제 파싱 산출물** 티커를 덧붙인다.
//   ★데스크톱은 기존 화면 그대로다(제1원칙). 진행 정보가 없으면 모바일도 기존과 같다.
//   ★퍼센트를 만들지 않는다 — "N개 중 M개 완료"는 서버가 준 실제 값이라 그대로 쓴다.
import Spinner from "./Spinner";
import { useIsMobile } from "./mobile/useIsMobile";
import { tickerLine, type AnalysisProgress as AnalysisProgressData } from "../lib/analysisProgress";
import { MOBILE_LAYOUT } from "./mobile/tokens";

export default function AnalysisProgress({ progress }: { progress?: AnalysisProgressData | null } = {}) {
  const isMobile = useIsMobile();
  // 완료된 파일이 하나라도 있어야 보여줄 것이 생긴다(빈 티커를 만들지 않는다).
  const showTicker = isMobile && !!progress && progress.done_files > 0;

  return (
    <div className="rounded-2xl border border-accent-100 bg-accent-50/40 px-5 py-6">
      {/* BOHUMFIT-131: 브랜드 그린 원형 스피너 */}
      <div className="flex justify-center">
        <Spinner size={48} label="분석 중입니다..." />
      </div>

      {showTicker && progress && (
        <div className="mt-4" data-testid="analysis-ticker">
          <p className="text-[15px] font-bold leading-[1.5] text-ink-900">
            서류 {progress.total_files}개 중 {progress.done_files}개 확인 완료
          </p>
          {/* ★완료된 것부터 채워진다 — 파일 순서가 아니라 완료 순서다(병렬 파싱 전제). */}
          <ul className="mt-2 space-y-1">
            {progress.files.map((file, index) => (
              <li
                key={`${file.filename}-${index}`}
                className="break-keep bg-white px-3 py-2 text-[15px] leading-[1.55] text-ink-soft"
                style={{ borderRadius: MOBILE_LAYOUT.radiusBadge }}
              >
                {tickerLine(file)}
              </li>
            ))}
          </ul>
          {progress.total_records > 0 && (
            <p className="mt-2 text-[15px] leading-[1.55] text-ink-soft">
              지금까지 {progress.total_records.toLocaleString("ko-KR")}건을 읽었습니다.
            </p>
          )}
        </div>
      )}

      <p className="mt-4 text-center text-[11px] text-gray-500">
        PDF 페이지가 많을수록 시간이 더 걸릴 수 있어요. 페이지를 닫지 말고 잠시만 기다려주세요.
      </p>
    </div>
  );
}
