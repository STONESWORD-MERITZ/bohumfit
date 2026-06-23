import { useState } from "react";
import { Link } from "react-router-dom";

type GuideKey = "hanwha" | "kb" | "db";
type GuideStep = {
  title: string;
  body: string;
  warning?: string;
  tone?: "amber" | "red";
};
type Guide = {
  tab: string;
  title: string;
  portal: string;
  systemUrl: string;
  intro: string;
  steps: GuideStep[];
  images: string[];
};

const TAB_KEYS: GuideKey[] = ["hanwha", "kb", "db"];
const imagePages = (prefix: GuideKey, count: number) =>
  Array.from({ length: count }, (_, i) => `/images/coverage-guide/${prefix}-${String(i + 1).padStart(2, "0")}.png`);

const GUIDES: Record<GuideKey, Guide> = {
  hanwha: {
    tab: "한화손보",
    title: "한화손보 보장분석서 PDF 받기",
    portal: "한화손해보험 GA 전산",
    systemUrl: "https://portal.hwgeneralins.com/",
    intro: "고객등록과 가입설계동의 후 정액담보상세출력으로 저장합니다.",
    steps: [
      { title: "포탈 로그인", body: "한화손해보험 GA 전산에 로그인한 뒤 고객등록을 클릭합니다." },
      { title: "가입설계동의", body: "고객등록 화면에서 가입설계동의를 클릭합니다." },
      {
        title: "문자동의 요청",
        body: "문자동의(LMS) 탭에서 고객명, 생년월일, 휴대폰번호를 입력한 뒤 인증요청을 진행합니다.",
      },
      { title: "실명인증", body: "주민등록번호를 입력하고 실명인증을 완료합니다." },
      { title: "고객정보 저장", body: "주소를 입력한 뒤 저장합니다." },
      {
        title: "실손/정액조회 진입",
        body: "메인화면에서 실손/정액조회로 이동한 뒤 주민번호 탭에서 고객이름을 클릭합니다.",
      },
      {
        title: "정액담보상세출력",
        body: "화면 우측하단의 [정액담보상세출력] 버튼을 클릭합니다.",
        warning: "일반 [출력] 버튼은 사용하지 마세요. 정액담보가 포함되지 않을 수 있습니다.",
        tone: "red",
      },
      {
        title: "PDF 저장",
        body: "프린터에서 Microsoft Print to PDF 또는 PDF24를 선택해 저장합니다.",
        warning: "Microsoft Print to PDF 저장본이 이미지 PDF로 만들어져 파싱 오류가 나면 PDF24로 다시 출력해 주세요.",
        tone: "amber",
      },
    ],
    images: imagePages("hanwha", 6),
  },
  kb: {
    tab: "KB손보",
    title: "KB손보 보장분석서 PDF 받기",
    portal: "KB손해보험 GA 전산",
    systemUrl: "https://nsales.kbinsure.co.kr/",
    intro: "고객 동의 등록 후 보장분석의 출력/발송 메뉴에서 PDF저장을 사용합니다.",
    steps: [
      { title: "포탈 로그인", body: "KB손해보험 GA 전산에 로그인한 뒤 고객등록/수정을 클릭합니다." },
      { title: "동의서입력", body: "고객등록 화면에서 동의서입력을 클릭합니다." },
      {
        title: "인증요청",
        body: "고객 주민번호, 고객명, 통신사, 휴대폰번호를 입력한 뒤 인증요청을 진행합니다.",
      },
      { title: "인증번호 등록", body: "인증번호를 입력하고 등록한 뒤 창을 닫습니다." },
      { title: "고객정보 저장", body: "고객 휴대폰번호, 주소, 직업을 입력한 뒤 저장합니다." },
      { title: "보장분석 진입", body: "메인화면에서 보장분석을 클릭합니다." },
      { title: "신규분석", body: "가설동의순을 클릭한 뒤 등록고객의 신규분석을 클릭합니다." },
      { title: "출력/발송", body: "출력/발송 아이콘을 클릭합니다." },
      { title: "PDF저장", body: "전체 선택/해제를 클릭해 항목을 선택한 뒤 PDF저장을 클릭합니다." },
    ],
    images: imagePages("kb", 10),
  },
  db: {
    tab: "DB손보",
    title: "DB손보 보장분석서 PDF 받기",
    portal: "DB손해보험 영업포탈",
    systemUrl: "https://www.mdbins.com/",
    intro: "스마트보장분석에서 계약분석과 세부가입내용을 함께 체크해 텍스트 방식 PDF로 저장합니다.",
    steps: [
      { title: "포탈 로그인", body: "DB손해보험 영업포탈에 로그인한 뒤 고객등록을 클릭합니다." },
      { title: "설계동의", body: "고객등록 화면에서 설계동의를 클릭합니다." },
      {
        title: "동의 발송",
        body: "고객정보(고객명, 생년월일, 휴대폰번호)를 입력한 뒤 발송합니다.",
      },
      { title: "인증확인", body: "인증번호를 입력하고 인증확인 후 확인을 클릭합니다." },
      {
        title: "상세정보 저장",
        body: "고객 상세정보(주민번호, 주소, 직업, 운행차량)를 입력한 뒤 저장합니다.",
      },
      { title: "스마트보장분석", body: "메인화면에서 스마트보장분석을 클릭합니다." },
      {
        title: "고객 선택",
        body: "등록한 고객명을 입력해 검색하고 고객을 더블클릭한 뒤 보장분석을 클릭합니다.",
      },
      { title: "분석 실행", body: "분석하기를 클릭하고 신용정보원 가입정보 조회를 확인합니다." },
      { title: "출력", body: "출력 버튼을 클릭합니다." },
      {
        title: "필수 항목 체크",
        body: "계약분석과 세부가입내용을 모두 체크한 뒤 출력하기를 클릭합니다.",
        warning: "세부가입내용을 체크하지 않으면 담보 상세가 빠질 수 있습니다.",
        tone: "red",
      },
      {
        title: "텍스트 방식 설정",
        body: "환경설정에서 페이지 품질을 텍스트 방식으로 선택한 뒤 확인합니다.",
        warning: "이미지 방식 PDF는 파싱 정확도가 떨어질 수 있습니다.",
        tone: "amber",
      },
      { title: "PDF 저장", body: "저장을 클릭해 PDF 파일로 저장합니다." },
    ],
    images: imagePages("db", 20),
  },
};

function StepCard({ step, index }: { step: GuideStep; index: number }) {
  const warningClass =
    step.tone === "red"
      ? "border-red-100 bg-red-50 text-red-700"
      : "border-amber-100 bg-amber-50 text-amber-700";

  return (
    <li className="rounded-card border border-line bg-white p-4">
      <div className="flex gap-3">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-600 text-sm font-bold text-white">
          {index + 1}
        </span>
        <div className="min-w-0">
          <h3 className="ko-heading text-[15px] font-bold text-ink-900">{step.title}</h3>
          <p className="ko-text mt-1 text-[14px] leading-7 text-ink-700">{step.body}</p>
          {step.warning && (
            <p className={`ko-text mt-3 rounded-[8px] border px-3 py-2 text-[13px] font-semibold ${warningClass}`}>
              주의: {step.warning}
            </p>
          )}
        </div>
      </div>
    </li>
  );
}

export default function CoverageGuide() {
  const [active, setActive] = useState<GuideKey>("hanwha");
  const guide = GUIDES[active];

  return (
    <div className="mx-auto max-w-4xl">
      <header className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">Coverage PDF Guide</p>
        <h1 className="ko-heading mt-3 text-3xl font-extrabold tracking-tight text-ink-900 md:text-4xl break-keep">
          보장분석서 PDF 받는 방법
        </h1>
        <p className="ko-text mt-3 text-[15px] leading-7 text-ink-soft">
          보장 비교분석에 필요한 PDF를 받는 방법을 안내합니다. 화면 캡처나 이미지 PDF가 아니라,
          담보명이 텍스트로 들어간 PDF를 저장해야 분석 정확도가 올라갑니다.
        </p>
      </header>

      <div role="tablist" aria-label="보험사 선택" className="mb-5 grid grid-cols-3 gap-2 rounded-btn border border-line bg-white p-1">
        {TAB_KEYS.map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={active === key}
            onClick={() => setActive(key)}
            className={`button-text rounded-[8px] px-3 py-2.5 text-sm font-bold transition-colors ${
              active === key ? "bg-accent-600 text-white" : "text-ink-soft hover:bg-ink-50"
            }`}
          >
            {GUIDES[key].tab}
          </button>
        ))}
      </div>

      <section className="rounded-card border border-line bg-ink-50 p-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent-700">{guide.portal}</p>
            <h2 className="ko-heading mt-2 text-2xl font-extrabold text-ink-900">{guide.title}</h2>
            <p className="ko-text mt-2 text-[14px] leading-7 text-ink-soft">{guide.intro}</p>
          </div>
          <div className="flex shrink-0 flex-col gap-2 sm:flex-row md:flex-col">
            <a
              href={guide.systemUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="button-text inline-flex justify-center rounded-btn border border-line-strong bg-white px-5 py-3 text-sm font-bold text-ink-800 transition hover:bg-ink-50"
            >
              전산 바로가기
            </a>
            <Link
              to="/coverage-compare"
              className="button-text inline-flex justify-center rounded-btn bg-accent-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-accent-700"
            >
              보장 비교분석 바로가기
            </Link>
          </div>
        </div>
      </section>

      <ol className="mt-5 space-y-3">
        {guide.steps.map((step, index) => (
          <StepCard key={`${active}-${step.title}`} step={step} index={index} />
        ))}
      </ol>

      <section className="mt-6 rounded-card border border-line bg-white p-5">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="ko-heading text-lg font-extrabold text-ink-900">이미지로 확인하기</h2>
            <p className="ko-text mt-1 text-[13px] leading-6 text-ink-soft">
              제공된 PDF 가이드를 PNG로 변환했습니다. 실제 화면 흐름은 아래 이미지 순서대로 확인해 주세요.
            </p>
          </div>
          <span className="shrink-0 rounded-full bg-ink-100 px-3 py-1 text-xs font-bold text-ink-600">
            {guide.images.length}장
          </span>
        </div>
        <div className="mt-4 space-y-4">
          {guide.images.map((src, index) => (
            <figure key={src} className="overflow-hidden rounded-[8px] border border-line bg-ink-50">
              <figcaption className="ko-text border-b border-line bg-white px-3 py-2 text-[12px] font-semibold text-ink-soft">
                {guide.tab} 가이드 {index + 1} / {guide.images.length}
              </figcaption>
              <img
                src={src}
                alt={`${guide.tab} 보장분석서 PDF 저장 가이드 ${index + 1}쪽`}
                loading="lazy"
                decoding="async"
                className="block w-full"
              />
            </figure>
          ))}
        </div>
      </section>

      <section className="mt-6 rounded-card border border-amber-200 bg-amber-50 p-5">
        <h2 className="ko-heading text-base font-bold text-ink-900">저장 전 마지막 확인</h2>
        <ul className="ko-text mt-3 space-y-2 text-[14px] leading-7 text-ink-700">
          <li>파일 확장자는 PDF인지 확인해 주세요.</li>
          <li>담보명과 가입금액이 드래그되는 텍스트 PDF가 가장 좋습니다.</li>
          <li>고객 개인정보가 포함되므로 보험핏 분석 목적에 필요한 파일만 업로드해 주세요.</li>
        </ul>
      </section>
    </div>
  );
}
