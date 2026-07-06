import { Link } from "react-router-dom";

const EFFECTIVE_DATE = "2026년 6월 30일";

type Section = {
  title: string;
  body: string[];
};

const business = {
  company: "핏 컴퍼니(FIT COMPANY)",
  representative: "이민규",
  registrationNumber: "174-29-01975",
  address: "충청북도 청주시 서원구 용평로113번길 17, 1동 3층 301호 (분평동, 서광빌딩)",
};

const sections: Section[] = [
  {
    title: "1. 개인정보의 처리 목적",
    body: [
      "회사는 보험핏 서비스를 제공하기 위하여 개인정보를 처리합니다.",
      "처리 목적은 회원 식별 및 로그인, 고지의무 분석 보조, 보장 비교분석, 서비스 부정 이용 방지, 고객 문의 응대입니다.",
      "회사는 수집 목적과 합리적으로 관련된 범위를 넘어 개인정보를 이용하지 않습니다.",
    ],
  },
  {
    title: "2. 수집하는 개인정보 항목",
    body: [
      "회원가입 및 로그인: 이메일, 비밀번호, 소셜 로그인 제공자가 전달하는 식별자와 기본 프로필 정보.",
      "서비스 이용: 이용자가 업로드한 건강보험심사평가원 또는 국민건강보험공단 발급 PDF 진료정보, 보장분석서 PDF, 분석 결과, 서비스 이용 기록.",
      "자동 생성 정보: 접속 일시, 접속 IP, 브라우저 정보, 오류 로그, 쿠키 등 서비스 운영에 필요한 최소한의 기술 정보.",
    ],
  },
  {
    title: "3. 민감정보(건강정보)의 처리",
    body: [
      "업로드 PDF에는 건강에 관한 정보 등 민감정보가 포함될 수 있습니다.",
      "처리 목적은 보험 고지의무 분석 보조, 간편심사 검토, 보장 비교분석을 위한 일시적 처리입니다.",
      "업로드 원본 PDF와 분석 중 생성된 건강정보는 분석 직후 서버에서 폐기하는 것을 원칙으로 하며, 서비스 데이터베이스에 저장하지 않습니다.",
      "다만 이용자가 분석 결과 화면에서 '히스토리에 저장'을 직접 요청한 경우에 한하여, 이용자가 입력한 별칭과 해당 분석 결과가 서비스 데이터베이스에 저장됩니다. 이때 고객 성명은 저장되지 않으며, 별칭에는 실명을 입력하지 않도록 안내합니다.",
      "또한 서비스 편의를 위하여 분석 실행 시 분석 결과 요약이 최근 10건 범위에서 자동 기록됩니다. 자동 기록에도 고객 성명은 저장되지 않으며, 7일이 지나면 자동 파기되고 이용자가 분석 히스토리 화면에서 언제든지 직접 삭제할 수 있습니다.",
      "회사는 법령상 근거 또는 이용자의 별도 동의가 없는 한 건강정보를 제3자에게 제공하지 않습니다.",
    ],
  },
  {
    title: "4. 개인정보의 보유 및 이용기간",
    body: [
      "회원 계정 정보는 회원 탈퇴 시까지 보유하며, 탈퇴 후에는 지체 없이 파기합니다. 단, 관계 법령에 따라 보존이 필요한 정보는 해당 법령에서 정한 기간 동안 보관할 수 있습니다.",
      "업로드 PDF와 건강정보 분석 원천자료는 분석 처리 완료 후 즉시 삭제하는 것을 원칙으로 합니다.",
      "분석 히스토리(이용자가 입력한 별칭, 분석 결과): 이용자가 직접 저장을 요청한 경우에 한하여 저장일부터 90일간 보관하며, 기간이 지나면 자동 파기합니다. 이용자는 서비스 내 분석 히스토리 화면에서 언제든지 직접 삭제할 수 있습니다.",
      "최근 분석 자동 기록(분석 결과 요약): 분석 실행 시 최근 10건 범위에서 자동 기록되며, 7일이 지나면 자동 파기합니다. 분석 히스토리 화면에서 언제든지 직접 삭제할 수 있습니다.",
      "접속 로그 등 서비스 운영 기록은 보안, 장애 대응, 부정 이용 방지를 위하여 필요한 기간 동안 보관 후 파기합니다.",
    ],
  },
  {
    title: "5. 개인정보의 파기 절차 및 방법",
    body: [
      "보유기간이 경과하거나 처리 목적이 달성된 개인정보는 지체 없이 파기합니다.",
      "전자적 파일 형태의 정보는 복구 또는 재생되지 않도록 삭제하며, 출력물 등 종이 문서는 분쇄 또는 이에 준하는 방법으로 파기합니다.",
    ],
  },
  {
    title: "6. 개인정보의 제3자 제공",
    body: [
      "회사는 이용자의 개인정보를 원칙적으로 제3자에게 제공하지 않습니다.",
      "다만 법령에 특별한 규정이 있거나 이용자가 별도로 동의한 경우에는 예외적으로 제공될 수 있습니다.",
    ],
  },
  {
    title: "7. 개인정보 처리 위탁",
    body: [
      "회사는 서비스 제공을 위하여 아래 업체의 인프라 또는 외부 서비스를 이용할 수 있습니다.",
      "Supabase Inc.: 회원 인증, 계정 정보 관리, 서비스 데이터 저장.",
      "Vercel Inc.: 프런트엔드 서비스 배포 및 호스팅.",
      "Railway Corp.: 백엔드 API 서버 운영.",
      "Google LLC: Gemini API를 통한 AI 보조 분석. 회사는 분석 목적에 필요한 최소한의 텍스트만 처리되도록 관리합니다.",
      "위탁 내용 또는 수탁자가 변경되는 경우 본 방침을 통해 공개합니다.",
    ],
  },
  {
    title: "8. 정보주체의 권리와 행사 방법",
    body: [
      "이용자는 언제든지 자신의 개인정보에 대한 열람, 정정, 삭제, 처리정지를 요청할 수 있습니다.",
      "회원 탈퇴 또는 개인정보 관련 요청은 서비스 내 기능 또는 개인정보 보호책임자 연락처를 통해 신청할 수 있습니다.",
      "회사는 관련 법령에서 정한 절차에 따라 지체 없이 조치합니다.",
    ],
  },
  {
    title: "9. 개인정보의 안전성 확보 조치",
    body: [
      "회사는 개인정보와 민감정보 보호를 위하여 접근 권한 관리, 전송 구간 암호화, 로그 점검, 원본 파일 미저장 정책 등 필요한 보호 조치를 적용합니다.",
      "업로드 파일은 분석 목적 외로 사용하지 않으며, 분석 후 폐기하는 것을 원칙으로 합니다.",
    ],
  },
  {
    title: "10. 개인정보 보호책임자",
    body: [
      `성명: ${business.representative}`,
      "직책: 대표",
      "연락처: qqqwe6701@gmail.com",
      "개인정보 처리와 관련한 문의, 열람·정정·삭제 요청, 민원은 위 연락처로 접수할 수 있습니다.",
    ],
  },
  {
    title: "11. 사업자 정보",
    body: [
      `상호: ${business.company}`,
      `대표자: ${business.representative}`,
      `사업자등록번호: ${business.registrationNumber}`,
      `사업장 소재지: ${business.address}`,
    ],
  },
  {
    title: "12. 고지의 의무",
    body: [
      "본 개인정보처리방침은 법령, 서비스 정책 또는 처리 항목의 변경에 따라 개정될 수 있습니다.",
      "중요한 변경이 있는 경우 서비스 화면 또는 공지사항을 통해 안내합니다.",
      `시행일자: ${EFFECTIVE_DATE}`,
    ],
  },
];

export default function PrivacyPolicy() {
  return (
    <main className="mx-auto max-w-3xl px-5 py-10">
      <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent-600">BOHUMFIT</p>
      <h1 className="mt-2 text-2xl font-extrabold text-ink-900">개인정보처리방침</h1>
      <p className="mt-3 text-sm leading-6 text-ink-soft">
        보험핏은 개인정보보호위원회 개인정보 처리방침 작성지침의 공개 항목을 기준으로, 이용자의 개인정보와
        건강정보가 어떤 목적으로 처리되는지 투명하게 안내합니다.
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
        <Link to="/terms-of-service" className="rounded-[8px] border border-line px-3 py-2 text-ink hover:border-accent-600 hover:text-accent-700">
          이용약관 보기
        </Link>
        <Link to="/" className="rounded-[8px] border border-line px-3 py-2 text-ink hover:border-accent-600 hover:text-accent-700">
          홈으로 돌아가기
        </Link>
      </div>
    </main>
  );
}
