// BOHUMFIT-045: Mercury 라이트 푸터 — 문구·링크 불변(시각 계층만).
import { Link } from "react-router-dom";

const BIZ = {
  serviceName: "BOHUMFIT",
  contact: "contact@bohumfit.ai",
};

export default function Footer() {
  return (
    <footer className="mt-20 border-t border-line bg-canvas py-10 text-caption text-ink-soft">
      <div className="mx-auto max-w-5xl px-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1">
            <p className="text-base font-extrabold tracking-tight text-ink-900">
              BOHUMFIT<span className="text-accent-600">.</span>
            </p>
            <p>
              서비스명: {BIZ.serviceName} · 문의: {BIZ.contact}
            </p>
          </div>
          <nav aria-label="푸터 메뉴" className="flex flex-wrap gap-4 font-semibold">
            <Link to="/terms" className="text-ink-700 transition-colors hover:text-ink-900">
              이용약관
            </Link>
            <Link to="/privacy" className="text-ink-700 transition-colors hover:text-ink-900">
              개인정보처리방침
            </Link>
          </nav>
        </div>
        <p className="mt-5 max-w-3xl leading-5 break-keep">
          BOHUMFIT이 제공하는 분석 결과는 AI 보조 도구가 산출한 참고 자료입니다.
          보험 가입·인수·보험금 지급을 보장하지 않으며, 최종 판단은 보험회사 청약서·약관·인수 기준에 따라 결정됩니다.
        </p>
        <p className="mt-6 border-t border-line pt-4 text-ink-400">
          © {new Date().getFullYear()} BOHUMFIT
        </p>
      </div>
    </footer>
  );
}
