import { Link } from "react-router-dom";
import Logo from "./Logo";

const BUSINESS = {
  serviceName: "보험핏",
  companyName: "핏 컴퍼니(FIT COMPANY)",
  representative: "이민규",
  registrationNumber: "174-29-01975",
  address: "충청북도 청주시 서원구 용평로113번길 17, 1동 3층 301호 (분평동, 서광빌딩)",
  businessType: "정보통신업",
  businessItem: "응용 소프트웨어 개발 및 공급업, 포털 및 기타 인터넷 정보 매개 서비스업",
  openedAt: "2026년 6월 15일",
  contact: "이메일 추가 예정",
};

export default function Footer() {
  return (
    <footer className="mt-20 border-t border-line bg-canvas py-10 text-caption text-ink-soft">
      <div className="mx-auto max-w-5xl px-5">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="max-w-3xl space-y-3">
            <Logo size={24} variant="light" />
            <dl className="grid gap-x-4 gap-y-1 text-[12px] leading-5 sm:grid-cols-[auto_1fr]">
              <dt className="font-semibold text-ink-700">서비스명</dt>
              <dd>{BUSINESS.serviceName}</dd>
              <dt className="font-semibold text-ink-700">상호</dt>
              <dd>{BUSINESS.companyName}</dd>
              <dt className="font-semibold text-ink-700">대표</dt>
              <dd>{BUSINESS.representative}</dd>
              <dt className="font-semibold text-ink-700">사업자등록번호</dt>
              <dd>{BUSINESS.registrationNumber}</dd>
              <dt className="font-semibold text-ink-700">주소</dt>
              <dd>{BUSINESS.address}</dd>
              <dt className="font-semibold text-ink-700">업태/종목</dt>
              <dd>
                {BUSINESS.businessType} / {BUSINESS.businessItem}
              </dd>
              <dt className="font-semibold text-ink-700">개업일</dt>
              <dd>{BUSINESS.openedAt}</dd>
              <dt className="font-semibold text-ink-700">고객센터</dt>
              <dd>{BUSINESS.contact}</dd>
            </dl>
          </div>
          <nav aria-label="푸터 메뉴" className="flex flex-wrap gap-4 font-semibold">
            <Link to="/terms-of-service" className="text-ink-700 transition-colors hover:text-ink-900">
              이용약관
            </Link>
            <Link to="/privacy-policy" className="text-ink-700 transition-colors hover:text-ink-900">
              개인정보처리방침
            </Link>
          </nav>
        </div>
        <p className="mt-6 leading-5">
          보험핏이 제공하는 분석 결과는 AI 보조 도구가 산출한 참고 자료입니다. 보험 가입, 인수, 보험금 지급을
          보장하지 않으며 최종 판단은 보험회사 청약서, 약관, 인수 기준에 따라 결정됩니다.
        </p>
        <p className="mt-6 border-t border-line pt-4 text-ink-400">
          © {new Date().getFullYear()} {BUSINESS.companyName}. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
