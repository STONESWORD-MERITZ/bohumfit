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
          className="mt-0.5 h-5 w-5 shrink-0 accent-[#7C3AED]"
          aria-label="고객 본인 동의 확인"
        />
        <span className="break-keep">
          설계사가 <b className="font-bold text-ink-900">고객 본인의 자료</b>를 대신 업로드합니다. 고객에게 분석 목적,
          민감정보 처리, AI 보조 분석 내용을 안내했고{" "}
          <b className="font-bold text-ink-900">업로드와 분석에 필요한 동의를 받았습니다.</b>
          <Link to="/privacy" className="ml-1 underline hover:text-ink-900">
            개인정보처리방침
          </Link>
          {note && <span className="mt-1 block text-ink-400">{note}</span>}
        </span>
      </label>
      <p className="mt-2 text-[11px] text-ink-400 break-keep">
        업로드 자료와 분석 결과는 <b className="font-semibold text-ink-soft">저장하지 않으며</b>, 출력물은 고객 본인이
        보유합니다. 설계사가 고객에게 직접 보여주는 참고자료입니다.
      </p>
    </div>
  );
}
