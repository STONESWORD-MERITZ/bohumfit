// BOHUMFIT-084: 병력 자료 다운로드 가이드 전면 개편(심평원 HIRA + 건강보험공단 NHIS).
//   두 기관 기준 단계별 안내 + 최종 체크리스트(useState). 스크린샷은 플레이스홀더(실 캡처·PII 금지).
//   082 한국어 타이포 규칙(ko-heading/ko-text/safe-break) 유지·기존 토큰 재사용·모바일 우선.
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

const HIRA_URL = "https://www.hira.or.kr/main.do";
const NHIS_URL = "https://www.nhis.or.kr/nhis/index.do";

// ── 스크린샷(BOHUMFIT-089: 실제 이미지 연결) ──────────────────
//   이미지 파일(public/images/guide/*)은 Codex가 Windows에서 복사. 여기선 경로·alt만.
function Shot({ src, alt }: { src: string; alt: string }) {
  return (
    <figure className="mt-3 overflow-hidden rounded-[10px] border border-line bg-ink-50">
      <img src={src} alt={alt} loading="lazy" className="block w-full" />
    </figure>
  );
}

// ── 단계 행 ───────────────────────────────────────────────────
function StepRow({
  no,
  shot,
  alt,
  children,
}: {
  no: number;
  shot?: string;
  alt?: string;
  children: React.ReactNode;
}) {
  return (
    <li className="flex gap-3.5">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-600 text-sm font-bold text-white">
        {no}
      </span>
      <div className="min-w-0 flex-1 pb-2">
        <div className="ko-text text-[14px] leading-7 text-ink-800">{children}</div>
        {shot && <Shot src={shot} alt={alt ?? ""} />}
      </div>
    </li>
  );
}

// 설정 키-값 한 줄
function Setting({ label, value, mark }: { label: string; value: string; mark?: boolean }) {
  return (
    <li className="ko-text flex flex-wrap gap-x-2 text-[13px] leading-6 text-ink-soft">
      <span className="font-semibold text-ink-800">{label}</span>
      <span>{value}</span>
      {mark && <span className="font-semibold text-accent-700">★ 고지의무 분석 필수</span>}
    </li>
  );
}

// ── 최종 체크리스트 데이터 ────────────────────────────────────
const CHECKLIST: ReadonlyArray<{ group: string; items: ReadonlyArray<string> }> = [
  { group: "심평원 · 건강보험", items: ["기본진료내역", "세부진료정보", "처방조제정보"] },
  { group: "심평원 · 자동차보험", items: ["기본진료내역", "세부진료정보"] },
  // BOHUMFIT-134: 공단 요양급여내역은 심평원 5년 이후(5~10년 전) 구간. 심평원 자료(최근 1~5년)와
  //   혼동을 막기 위해 표시 라벨을 'N년차' → '5~6년 전' 식으로 변경(체크박스 key는 인덱스라 불변).
  { group: "건강보험공단 · 요양급여내역", items: ["5~6년 전", "6~7년 전", "7~8년 전", "8~9년 전", "9~10년 전"] },
];

function FinalChecklist() {
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const total = useMemo(() => CHECKLIST.reduce((n, g) => n + g.items.length, 0), []);
  const done = Object.values(checked).filter(Boolean).length;
  const toggle = (key: string) => setChecked((p) => ({ ...p, [key]: !p[key] }));

  return (
    <section id="checklist" className="scroll-mt-20 rounded-card border border-accent-200 bg-accent-50 p-6">
      <div className="flex items-end justify-between gap-3">
        <h2 className="ko-heading text-lg font-bold tracking-tight text-ink-900">📋 최종 준비 체크리스트</h2>
        <span className="shrink-0 text-sm font-bold text-accent-700">{done} / {total}</span>
      </div>
      <p className="ko-text mt-1 text-[13px] leading-6 text-ink-soft">
        공단 요양급여내역은 5년 기준입니다. 장기 병력이 의심되면 최대 10년차까지 같은 방식으로 추가하세요.
      </p>
      <div className="mt-4 space-y-4">
        {CHECKLIST.map((g, gi) => (
          <div key={g.group}>
            <p className="card-title text-[13px] font-bold text-ink-900">{g.group}</p>
            <ul className="mt-2 space-y-1.5">
              {g.items.map((item, ii) => {
                const key = `${gi}-${ii}`;
                const on = !!checked[key];
                return (
                  <li key={key}>
                    <label className="flex cursor-pointer items-center gap-2.5">
                      <input
                        type="checkbox"
                        checked={on}
                        onChange={() => toggle(key)}
                        className="h-4 w-4 shrink-0 accent-accent-600"
                      />
                      <span className={`ko-text text-[14px] ${on ? "text-ink-400 line-through" : "text-ink-800"}`}>
                        {item}
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
      <Link
        to="/disclosure?mode=agent"
        className="button-text mt-6 inline-flex rounded-btn bg-accent-600 px-6 py-3.5 text-sm font-semibold text-white transition hover:bg-accent-700"
      >
        준비 완료 — 고지의무 분석 시작 →
      </Link>
    </section>
  );
}

export default function DownloadGuide() {
  const [tab, setTab] = useState<"hira" | "nhis">("hira");

  return (
    <div className="mx-auto max-w-4xl">
      {/* 헤더 */}
      <header className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">Download Guide</p>
        <h1 className="ko-heading mt-3 text-3xl font-extrabold tracking-tight text-ink-900 md:text-4xl break-keep">
          병력 자료 다운로드 가이드
        </h1>
        <p className="ko-text mobile-copy mt-3 text-[15px] leading-7 text-ink-soft">
          정확한 고지의무 분석을 위해 <b className="font-semibold text-ink-800">심평원</b>과{" "}
          <b className="font-semibold text-ink-800">건강보험공단</b> 두 기관 자료가 모두 필요합니다.
          심평원은 최근 5년 상세 진료·처방을, 공단은 최대 10년 요양급여 이력을 제공해 장기 병력 누락을 막아줍니다.
        </p>
        <a
          href="#checklist"
          className="button-text mt-4 inline-flex rounded-btn border border-line-strong bg-white px-5 py-2.5 text-sm font-semibold text-ink-800 transition hover:bg-ink-50"
        >
          최종 체크리스트로 이동 ↓
        </a>
      </header>

      <section className="mb-6 rounded-card border border-accent-200 bg-accent-50 p-5">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-accent-700">Coverage Compare</p>
        <h2 className="ko-heading mt-2 text-lg font-extrabold text-ink-900">보장분석서 받기</h2>
        <p className="ko-text mt-2 text-[14px] leading-7 text-ink-soft">
          한화손보, KB손보, DB손보 보장분석서 PDF 저장 방법은 별도 가이드에서 확인할 수 있습니다.
        </p>
        <Link
          to="/coverage-guide"
          className="button-text mt-4 inline-flex rounded-btn bg-accent-600 px-5 py-2.5 text-sm font-bold text-white transition hover:bg-accent-700"
        >
          보험사별 보장분석서 가이드 보기
        </Link>
      </section>

      {/* 탭 */}
      <div role="tablist" aria-label="기관 선택" className="mb-5 flex gap-2 rounded-btn border border-line bg-white p-1">
        {([["hira", "① 심평원(HIRA)"], ["nhis", "② 건강보험공단(NHIS)"]] as const).map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={`button-text flex-1 rounded-[8px] px-3 py-2.5 text-sm font-bold transition-colors ${
              tab === key ? "bg-accent-600 text-white" : "text-ink-soft hover:bg-ink-50"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* 섹션 A — 심평원(HIRA) */}
      {tab === "hira" && (
        <section className="rounded-card border border-line bg-white p-6">
          <h2 className="ko-heading text-xl font-bold tracking-tight text-ink-900">
            건강보험심사평가원(HIRA) — 내 진료정보 열람
          </h2>
          <a
            href={HIRA_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="safe-break mt-1 inline-flex text-[13px] font-semibold text-accent-700 hover:text-accent-800"
          >
            {HIRA_URL}
          </a>
          <ol className="mt-5 space-y-4">
            <StepRow no={1} shot="/images/guide/hira-1-menu.png" alt="심평원 메뉴 진입">
              로그인 후 <b className="font-semibold text-ink-900">[조회·신청 &gt; 내 진료정보 열람]</b> 으로 들어갑니다.
            </StepRow>
            <StepRow no={2} shot="/images/guide/hira-2-login.png" alt="로그인">
              '고유식별정보 처리 고지' 화면에서 <b className="font-semibold text-ink-900">['내 진료정보 열람' 조회하기]</b> 를 누릅니다.
            </StepRow>
            <StepRow no={3}>
              로그인 방식을 선택합니다(간편인증 / 공동인증서 / 금융인증서 / 모바일 신분증).
            </StepRow>
            <StepRow no={4} shot="/images/guide/hira-3-basic.png" alt="기본진료내역 다운로드">
              진료정보 조회 설정을 맞춥니다:
              <ul className="mt-2 space-y-1.5 border-l-2 border-accent-100 pl-3">
                <Setting label="보험종별" value="건강보험 · 의료급여 · 보훈 선택" />
                <Setting label="상병항목 표시" value="체크" />
                <Setting label="민감상병 표시" value="체크" mark />
                <Setting label="전체 병·의원&약국" value="체크" />
                <Setting label="대상기간" value="5년" />
              </ul>
            </StepRow>
            <StepRow no={5} shot="/images/guide/hira-4-detail.png" alt="세부진료정보 다운로드">
              아래 3개 탭에서 각각 <b className="font-semibold text-ink-900">[전체 다운로드]</b>:
              <span className="mt-1 block text-ink-soft">기본진료내역 · 세부진료정보 · 처방조제정보</span>
            </StepRow>
            <StepRow no={6} shot="/images/guide/hira-5-prescription.png" alt="처방조제정보 다운로드">
              보험종별을 <b className="font-semibold text-ink-900">[자동차보험]</b> 으로 바꾼 뒤 2개 탭에서 <b className="font-semibold text-ink-900">[전체 다운로드]</b>:
              <span className="mt-1 block text-ink-soft">기본진료내역 · 세부진료정보</span>
            </StepRow>
            <StepRow no={7} shot="/images/guide/hira-6-auto-basic.png" alt="자동차보험 기본진료내역 다운로드">
              보험종별을 <b className="font-semibold text-ink-900">'자동차보험'</b> 으로 변경 후 기본진료내역 전체 다운로드
            </StepRow>
            <StepRow no={8} shot="/images/guide/hira-7-auto-detail.png" alt="자동차보험 세부진료정보 다운로드">
              자동차보험 세부진료정보 전체 다운로드
            </StepRow>
          </ol>
          <p className="ko-text mt-5 rounded-[8px] bg-accent-50 px-4 py-3 text-[13px] font-semibold text-accent-800">
            → 심평원 합계: 5개 파일
          </p>
        </section>
      )}

      {/* 섹션 B — 건강보험공단(NHIS) */}
      {tab === "nhis" && (
        <section className="rounded-card border border-line bg-white p-6">
          <h2 className="ko-heading text-xl font-bold tracking-tight text-ink-900">
            국민건강보험공단(NHIS) — 건강보험 요양급여내역 조회
          </h2>
          <a
            href={NHIS_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="safe-break mt-1 inline-flex text-[13px] font-semibold text-accent-700 hover:text-accent-800"
          >
            {NHIS_URL}
          </a>
          <ol className="mt-5 space-y-4">
            <StepRow no={1} shot="/images/guide/nhis-1-search.png" alt="통합검색 클릭">
              로그인 후 상단 <b className="font-semibold text-ink-900">[통합검색]</b> 에서 "요양급여" 를 검색합니다.
            </StepRow>
            <StepRow no={2} shot="/images/guide/nhis-2-keyword.png" alt="요양급여 검색어 입력">
              <b className="font-semibold text-ink-900">[건강보험 요양급여내역 조회]</b> → <b className="font-semibold text-ink-900">[조회하기]</b>.
            </StepRow>
            <StepRow no={3}>
              1단계 유의사항 → 2단계 사전면담 → 3단계 내역조회 순서로 진행합니다.
            </StepRow>
            <StepRow no={4} shot="/images/guide/nhis-3-service.png" alt="요양급여내역 조회 서비스 클릭">
              진료개시일 기간을 설정합니다:
              <ul className="mt-2 space-y-1.5 border-l-2 border-accent-100 pl-3">
                <Setting label="조회 구간" value="최대 1년 — 1년 단위로 끊어 조회" mark />
                <Setting label="예시" value="2021.01.01~2021.12.31, 2022.01.01~2022.12.31 …" />
                <Setting label="총 범위" value="최대 10년 치까지 가능" />
              </ul>
            </StepRow>
            <StepRow no={5}>
              특수상병 포함 여부: <b className="font-semibold text-ink-900">체크</b>.
            </StepRow>
            <StepRow no={6} shot="/images/guide/nhis-4-overview.png" alt="내역조회 개요 확인">
              <b className="font-semibold text-ink-900">[조회]</b> → <b className="font-semibold text-ink-900">[프린트발급]</b> 으로 PDF 저장(연도별 1개씩).
            </StepRow>
            <StepRow no={7} shot="/images/guide/nhis-5-result.png" alt="조회 결과 확인 및 프린트/발급">
              조회 결과 확인 후 우측 하단 <b className="font-semibold text-ink-900">'프린트/발급'</b> 클릭하여 자료 저장
            </StepRow>
          </ol>
          <p className="ko-text mt-5 rounded-[8px] bg-accent-50 px-4 py-3 text-[13px] font-semibold text-accent-800">
            → 공단 합계: 5년 기준 5개(1년 1개), 최대 10개
          </p>
        </section>
      )}

      {/* 최종 체크리스트 */}
      <div className="mt-8">
        <FinalChecklist />
      </div>
    </div>
  );
}
