// BOHUMFIT-049: 메인 창업 미션·회사소개 섹션 (히어로 바로 아래, id="mission").
// Mercury 라이트 톤. 회사 기본정보(상호·연락처·사업자번호)는 푸터에 있으므로 중복 표기 금지.
import { Link } from "react-router-dom";
import Badge from "../components/ui/Badge";
import Card from "../components/ui/Card";
import BrandWordmark from "../components/BrandWordmark";

const VALUES = [
  {
    title: "고객 권리 보호",
    body: "보험금이 필요한 순간 몰랐던 고지 하나로 보장을 잃지 않도록, 알릴의무를 먼저 짚습니다.",
  },
  {
    title: "중립적 점검",
    body: "특정 상품의 가입이나 해지를 권유하지 않습니다. 사실을 정리해 보여 줄 뿐입니다.",
  },
  {
    title: "데이터 기반",
    body: "기억·구두 확인이 아니라 건강보험심사평가원 원자료를 근거로 고지 리스크를 판단합니다.",
  },
];

export default function HomeMission() {
  return (
    <section id="mission" className="scroll-mt-20 py-24">
      <div className="mx-auto max-w-4xl px-6">
        <BrandWordmark size="sm" className="mb-6" />
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">Our Mission</p>
        <h2 className="mt-4 text-3xl font-extrabold leading-snug tracking-tight text-ink-900 md:text-4xl break-keep">
          보험은 가입보다 점검이 먼저입니다
        </h2>

        <div className="mt-5">
          <Badge tone="navy">메리츠화재 정규직 지점장 · 1만 명 이상 설계사 업무 지원</Badge>
        </div>

        <div className="mt-7 space-y-5 text-[15px] leading-8 text-ink-soft break-keep">
          <p>
            저는 메리츠화재 정규직 지점장으로 근무하며 1만 명이 넘는 설계사의 업무를 지원했습니다.
            그 과정에서 고객이 가장 자주 손해 보는 지점이 ‘알릴의무’라는 걸 현장에서 확인했습니다.
            정작 보험금이 필요한 순간, 몰랐던 고지 하나로 보장을 받지 못하는 분들이 너무 많았습니다.
          </p>
          <p>
            그래서 회사를 나왔습니다. 고지사항을 비롯한 고객의 권리를 지키는 시스템과 조직을 만들기
            위해서입니다. BOHUMFIT은 건강보험심사평가원 원자료를 분석해, 고객과 설계사가 함께 확인해야 할
            고지 리스크를 한 화면에 정리합니다.
          </p>
          <p className="font-semibold text-ink-900">
            보험을 파는 도구가 아니라, 제대로 보장받게 하는 도구입니다.
          </p>
        </div>

        <p className="mt-6 text-body font-semibold text-ink-900">— 보험핏 대표 이민규</p>

        <div className="mt-10 grid gap-4 sm:grid-cols-3">
          {VALUES.map((v) => (
            <Card key={v.title}>
              <h3 className="text-title text-ink-900">{v.title}</h3>
              <p className="mt-2 text-caption leading-6 text-ink-soft break-keep">{v.body}</p>
            </Card>
          ))}
        </div>

        <div className="mt-10 flex flex-wrap gap-3">
          <Link
            to="/why"
            className="rounded-btn border border-line-strong bg-white px-5 py-2.5 text-sm font-semibold text-ink-800 transition hover:bg-ink-50"
          >
            왜 중요한가 →
          </Link>
          <Link
            to="/disclosure"
            className="rounded-btn bg-accent-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-accent-700"
          >
            지금 점검하기 →
          </Link>
        </div>
      </div>
    </section>
  );
}
