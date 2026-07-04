import { Link } from "react-router-dom";

const EFFECTIVE_DATE = "2026년 6월 30일";

type Section = {
  title: string;
  body: string[];
};

const sections: Section[] = [
  {
    title: "1. 목적",
    body: [
      "본 약관은 핏 컴퍼니(FIT COMPANY)가 제공하는 보험핏 서비스의 이용 조건, 회사와 이용자의 권리·의무 및 책임 사항을 정하는 것을 목적으로 합니다.",
    ],
  },
  {
    title: "2. 용어의 정의",
    body: [
      "서비스란 건강보험심사평가원, 국민건강보험공단, 보험사 보장분석서 등 이용자가 업로드한 자료를 기반으로 보험 고지의무와 보장 비교분석을 보조하는 웹 기반 정보 서비스를 말합니다.",
      "이용자란 본 약관에 따라 서비스를 이용하는 회원 또는 비회원 사용자를 말합니다.",
      "분석 결과란 업로드 자료를 기반으로 시스템과 AI 보조 도구가 산출한 고지 검토 항목, 보장 비교 항목, 안내 문구 등을 말합니다.",
    ],
  },
  {
    title: "3. 약관의 효력 및 변경",
    body: [
      "본 약관은 서비스 화면에 게시하거나 기타 방법으로 공지함으로써 효력이 발생합니다.",
      "회사는 관련 법령을 위반하지 않는 범위에서 약관을 변경할 수 있으며, 중요한 변경 사항은 시행 전 서비스 화면을 통해 안내합니다.",
    ],
  },
  {
    title: "4. 서비스의 제공 및 변경",
    body: [
      "회사는 보험 고지의무 분석 보조, 보장 비교분석, 실손 계산, 보험사 링크 안내 등 서비스를 제공합니다.",
      "회사는 운영상 또는 기술상 필요에 따라 서비스의 전부 또는 일부를 변경하거나 중단할 수 있습니다.",
      "분석 기능은 업로드된 PDF의 품질, 발급기관 양식, OCR 상태, 외부 AI 응답 상태에 따라 결과가 달라질 수 있습니다.",
    ],
  },
  {
    title: "5. 서비스 이용 시간",
    body: [
      "서비스는 연중무휴 24시간 제공을 원칙으로 합니다.",
      "다만 시스템 점검, 장애, 외부 인프라 문제, 보안상 필요가 있는 경우 일시적으로 서비스 이용이 제한될 수 있습니다.",
    ],
  },
  {
    title: "6. 회원가입 및 계정 관리",
    body: [
      "이용자는 회사가 정한 절차에 따라 회원가입을 신청할 수 있습니다.",
      "이용자는 계정 정보가 정확하게 유지되도록 관리해야 하며, 계정의 부정 사용을 알게 된 경우 즉시 회사에 알려야 합니다.",
    ],
  },
  {
    title: "7. 이용자의 의무",
    body: [
      "이용자는 본인 또는 적법한 권한이 있는 고객의 자료만 업로드해야 합니다.",
      "타인의 진료정보, 건강정보, 보험 관련 자료를 무단으로 업로드하거나 분석하는 행위는 금지됩니다.",
      "이용자는 분석 결과를 보험 가입, 청약, 보험금 청구 또는 고객 상담에 활용할 때 실제 청약서 질문과 보험회사 심사 기준을 별도로 확인해야 합니다.",
      "이용자는 서비스의 정상 운영을 방해하거나 허위 자료를 입력하는 행위를 해서는 안 됩니다.",
    ],
  },
  {
    title: "8. 회사의 의무",
    body: [
      "회사는 관련 법령과 본 약관에 따라 안정적인 서비스 제공을 위해 노력합니다.",
      "회사는 개인정보와 민감정보 보호를 위하여 개인정보처리방침에 따른 보호 조치를 수행합니다.",
    ],
  },
  {
    title: "9. 면책조항",
    body: [
      "보험핏의 분석 결과는 참고용 보조 자료이며, 법률 자문, 의료 자문, 보험 인수 판단 또는 보험금 지급 판단이 아닙니다.",
      "최종 고지 여부, 보험 가입 가능 여부, 보험금 지급 여부는 실제 청약서 문항, 보험회사 약관, 인수 기준, 심사 결과에 따라 결정됩니다.",
      "이용자는 분석 결과만으로 고지 여부를 최종 결정해서는 안 되며, 필요한 경우 보험회사, 담당 설계사, 의료 전문가 또는 법률 전문가에게 확인해야 합니다.",
      "회사는 이용자가 분석 결과를 최종 판단으로 오인하여 발생한 손해에 대하여 회사의 고의 또는 중대한 과실이 없는 한 책임을 부담하지 않습니다.",
    ],
  },
  {
    title: "10. 저작권 및 지식재산권",
    body: [
      "서비스 화면, 소프트웨어, 데이터 구조, 분석 로직, 문구 및 디자인에 관한 권리는 회사 또는 정당한 권리자에게 있습니다.",
      "이용자는 회사의 사전 동의 없이 서비스를 복제, 배포, 역설계하거나 상업적 목적으로 무단 이용할 수 없습니다.",
    ],
  },
  {
    title: "11. 분쟁해결",
    body: [
      "회사와 이용자는 서비스 이용과 관련한 분쟁을 원만히 해결하기 위하여 성실히 협의합니다.",
      "협의로 해결되지 않는 분쟁은 관련 법령에 따른 관할 법원에서 해결합니다.",
    ],
  },
  {
    title: "12. 사업자 정보 및 시행일자",
    body: [
      "상호: 핏 컴퍼니(FIT COMPANY)",
      "대표자: 이민규",
      "사업자등록번호: 174-29-01975",
      "사업장 소재지: 충청북도 청주시 서원구 용평로113번길 17, 1동 3층 301호 (분평동, 서광빌딩)",
      `시행일자: ${EFFECTIVE_DATE}`,
    ],
  },
];

export default function TermsOfService() {
  return (
    <main className="mx-auto max-w-3xl px-5 py-10">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent-600">BOHUMFIT</p>
      <h1 className="mt-2 text-2xl font-extrabold text-ink-900">이용약관</h1>
      <p className="mt-3 text-sm leading-6 text-ink-soft">
        보험핏 서비스의 이용 조건과 책임 범위를 안내합니다. 분석 결과는 보험 고지 검토를 돕는 참고 자료이며,
        최종 판단은 실제 청약서 질문과 보험회사 심사 기준에 따라 확인해야 합니다.
      </p>
      <p className="mt-2 text-xs text-ink-soft">시행일자: {EFFECTIVE_DATE}</p>

      <div className="mt-8 space-y-7">
        {sections.map((section) => (
          <section key={section.title} className="rounded-[8px] border border-line bg-white p-5">
            <h2 className="text-sm font-extrabold text-ink-900">{section.title}</h2>
            <div className="mt-3 space-y-2 text-[13px] leading-6 text-ink-soft">
              {section.body.map((line) => (
                <p key={line}>{line}</p>
              ))}
            </div>
          </section>
        ))}
      </div>

      <div className="mt-10 flex flex-wrap gap-3 text-xs font-semibold">
        <Link to="/privacy-policy" className="rounded-[8px] border border-line px-3 py-2 text-ink hover:border-accent-600 hover:text-accent-700">
          개인정보처리방침 보기
        </Link>
        <Link to="/" className="rounded-[8px] border border-line px-3 py-2 text-ink hover:border-accent-600 hover:text-accent-700">
          홈으로 돌아가기
        </Link>
      </div>
    </main>
  );
}
