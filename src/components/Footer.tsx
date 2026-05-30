import { Link } from "react-router-dom";

// TODO(사업자 정보): 사업자 등록 후 아래 값을 채워주세요.
//   값이 비어 있으면 사업자 정보 줄은 화면에 표시되지 않습니다.
const BIZ = {
  name: "",      // 상호
  ceo: "",       // 대표자
  regNo: "",     // 사업자등록번호
  address: "",   // 주소
  contact: "",   // 문의 (이메일 또는 전화)
};

export default function Footer() {
  const line1 = [
    BIZ.name && `상호: ${BIZ.name}`,
    BIZ.ceo && `대표자: ${BIZ.ceo}`,
    BIZ.regNo && `사업자등록번호: ${BIZ.regNo}`,
  ].filter(Boolean).join(" · ");
  const line2 = [
    BIZ.address && `주소: ${BIZ.address}`,
    BIZ.contact && `문의: ${BIZ.contact}`,
  ].filter(Boolean).join(" · ");

  return (
    <footer className="mt-16 border-t border-gray-100 bg-white py-6 text-xs text-gray-500">
      <div className="mx-auto max-w-5xl px-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1">
            <p className="font-bold text-gray-700">BOHUMFIT</p>
            {line1 && <p className="text-[11px] text-gray-400">{line1}</p>}
            {line2 && <p className="text-[11px] text-gray-400">{line2}</p>}
          </div>
          <nav className="flex flex-wrap gap-4 text-[12px] font-semibold">
            <Link to="/terms" className="hover:text-gray-900">이용약관</Link>
            <Link to="/privacy" className="hover:text-gray-900">개인정보처리방침</Link>
          </nav>
        </div>
        <p className="mt-4 text-[11px] leading-5 text-gray-400 break-keep">
          BOHUMFIT이 제공하는 분석 결과는 AI 보조 도구가 산출한 참고 자료입니다.
          보험 가입·인수·보험금 지급을 보장하지 않으며, 최종 판단은 보험회사 청약서·약관·인수 기준에 따라 결정됩니다.
        </p>
        <p className="mt-3 text-[11px] text-gray-300">© {new Date().getFullYear()} BOHUMFIT</p>
      </div>
    </footer>
  );
}
