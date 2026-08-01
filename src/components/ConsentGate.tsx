// BOHUMFIT-048: 설계사 고객 동의 게이트(재사용 컴포넌트).
// 설계사가 고객 자료를 대신 업로드하는 화면에서 고객 본인 동의를 선행 확인한다.
import { type ReactNode } from "react";
import { Link } from "react-router-dom";

export interface ConsentGateProps {
  /** 동의 여부(상위 소유) */
  agreed: boolean;
  onChange: (v: boolean) => void;
  /** 업로드 자료 종류별 추가 안내 */
  note?: ReactNode;
  className?: string;
}

export default function ConsentGate({ agreed, onChange, note, className = "" }: ConsentGateProps) {
  return (
    <div className={`rounded-[10px] border border-line bg-ink-50 p-4 ${className}`}>
      <p className="mb-1.5 text-xs font-bold text-ink-800">고객 동의 확인 (필수)</p>
      <label className="flex min-h-[44px] cursor-pointer items-start gap-3 text-xs leading-5 text-ink-soft">
        <input
          type="checkbox"
          checked={agreed}
          onChange={(e) => onChange(e.target.checked)}
          className="mt-0.5 h-5 w-5 shrink-0 accent-accent-600"
          aria-label="고객 본인 동의 확인"
        />
        <span className="break-keep">
          설계사가 <b className="font-bold text-ink-900">고객 본인의 자료</b>를 대신 업로드합니다. 고객에게 분석 목적,
          민감정보 처리, AI 보조 분석 내용을 안내했고{" "}
          <b className="font-bold text-ink-900">업로드와 분석에 필요한 동의를 받았습니다.</b>
          <Link to="/privacy-policy" className="ml-1 underline hover:text-ink-900">
            개인정보처리방침
          </Link>
          {note && <span className="mt-1 block text-ink-400">{note}</span>}
        </span>
      </label>
      {/* BOHUMFIT-265(보정 · Human 확정 문구): 개인정보처리방침과 **3층 보관 기간**을 일치시킨다.
          ★이전 문구는 "분석 결과는 서버에 저장하지 않는다"고 단언해, 방침 40·50행(히스토리 저장 요청 시 90일)과
            41·51행(요약 자동 기록 7일)과 정면 모순이었다(Codex 반려 2).
          ★저장하지 않는 것은 **업로드 자료 원본**이고, 분석 결과는 90일/7일 서버 보관 + 기기 24시간이 정확하다.
          ★보조 문구 하한 15px 규칙 준수(고객에게 보여주는 고지문). */}
      <p className="mt-2 text-[15px] leading-[1.55] text-ink-soft break-keep">
        업로드하신 <b className="font-semibold text-ink-900">자료 원본은 분석 후 저장하지 않습니다</b>. 분석 결과는
        히스토리 저장을 요청하신 경우 <b className="font-semibold text-ink-900">90일간</b>, 요약 기록은{" "}
        <b className="font-semibold text-ink-900">7일간</b> 서버에 보관되며, 오프라인 열람을 위해 최근 5건이{" "}
        <b className="font-semibold text-ink-900">이 기기에 24시간 임시 보관</b>됩니다(로그아웃 시 즉시 삭제). 출력물은
        고객 본인이 보유하며, 설계사가 고객에게 직접 보여주는 참고자료입니다.
      </p>
    </div>
  );
}
