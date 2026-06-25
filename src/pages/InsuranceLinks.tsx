// BOHUMFIT-092: 보험사 전산·약관·팩스 바로가기(GA 설계사용). 단일 파일 자기완결형.
//   외부 fetch 없음 — 39개사 데이터 하드코딩. 082 한국어 타이포(ko-heading/ko-text) 유지.
import { useMemo, useState } from "react";

type Status = "공식확인" | "공식+허브" | "허브확인" | "확인필요";
type FaxType = "fixed" | "virtual" | "unknown";
type InsType = "손해보험" | "생명보험";
// BOHUMFIT-129: 공제회사 카테고리 추가. 탭/배지는 category 기준(없으면 type로 폴백).
type Category = "손해보험" | "생명보험" | "공제회사";
type Browser = "Edge" | "Chrome" | "무관";

type Insurer = {
  type: InsType;
  name: string;
  system_url: string;
  terms_url: string;
  fax: string;
  fax_note: string;
  status: Status;
  fax_type: FaxType;
  // BOHUMFIT-129 확장 필드(없으면 생략 — 빈값/확인필요로 표시). 기존 값은 변경하지 않음.
  category?: Category;
  displayOrder?: number;       // 동일 탭 내 오름차순(메리츠화재=1 상단 고정)
  customerCenter?: string;     // 고객센터
  incallNumber?: string;       // 인콜 모니터링
  helpdeskNumber?: string;     // 전산 헬프데스크
  claimFormUrl?: string;       // 보험금 청구양식 URL
  browser?: Browser;           // 권장 브라우저
  lastVerifiedDate?: string;   // 최종확인일
  claimFaxSub?: string;        // 보조 청구팩스
};

const INSURANCE_DATA: Insurer[] = [
  { type: "손해보험", name: "삼성화재", system_url: "https://erp.samsungfire.com/", terms_url: "https://www.samsungfire.com/vh/page/VH.HPIF0103.do", fax: "0505-161-1166", fax_note: "장기/상해·질병 서류접수 기준. 일부 물보험/여행 등은 0505-162-0777 등 별도 안내 가능", status: "공식확인", fax_type: "fixed", displayOrder: 2, customerCenter: "1588-5114", browser: "무관", lastVerifiedDate: "2026-06-25", claimFormUrl: "https://www.samsungfire.com/" },
  { type: "손해보험", name: "메리츠화재", system_url: "https://sales.meritzfire.com/", terms_url: "https://www.meritzfire.com/disclosure/product-announcement/product-list.do?vMode=PC", fax: "0505-021-3400 / 0505-021-3500", fax_note: "100만원 이하 팩스/인터넷/모바일 가능 안내 확인", status: "공식확인", fax_type: "fixed", displayOrder: 1, customerCenter: "1566-7711", incallNumber: "1566-7711", helpdeskNumber: "1588-9802", claimFormUrl: "https://www.meritzfire.com/", browser: "Edge", lastVerifiedDate: "2026-06-25", claimFaxSub: "0505-021-3500" },
  { type: "손해보험", name: "DB손해보험", system_url: "https://www.mdbins.com/", terms_url: "https://www.idbins.com/FWMAIV1534.do", fax: "0505-181-4862", fax_note: "장기보험 보험금청구 대표 팩스번호", status: "공식확인", fax_type: "fixed" },
  { type: "손해보험", name: "KB손해보험", system_url: "https://nsales.kbinsure.co.kr/", terms_url: "https://www.kbinsure.co.kr/CG802030001.ecs", fax: "0505-136-6500", fax_note: "장기 상해/질병 기준. 일반 단체 0505-136-6600, 재물배상 0505-136-6700 별도", status: "공식확인", fax_type: "fixed" },
  { type: "손해보험", name: "현대해상", system_url: "https://sp.hi.co.kr/", terms_url: "https://www.hi.co.kr/bin/CI/ON/CION3200G.jsp", fax: "0507-774-6060", fax_note: "공식 ARS는 문자로 팩스번호 안내. 청구서/GA허브 기준 번호로 발송 전 확인 권장", status: "공식+허브", fax_type: "fixed" },
  { type: "손해보험", name: "한화손해보험", system_url: "https://portal.hwgeneralins.com/", terms_url: "https://www.hwgeneralins.com/", fax: "0502-779-1004", fax_note: "공식 페이지 직접 확인 제한. GA허브/청구서 기준으로 발송 전 1566-8000 확인 권장", status: "허브확인", fax_type: "fixed" },
  { type: "손해보험", name: "롯데손해보험", system_url: "https://lottero.lotteins.co.kr/", terms_url: "https://www.lotteins.co.kr/web/C/D/H/cdh190.jsp", fax: "0507-333-9999", fax_note: "300만원 미만 팩스 청구 가능 안내 확인", status: "공식확인", fax_type: "fixed" },
  { type: "손해보험", name: "흥국화재", system_url: "https://sales.heungkukfire.co.kr/", terms_url: "https://www.heungkukfire.co.kr/FRW/announce/insGoodsGongsiSale.do", fax: "가상팩스 발급 / 0504-800-0700", fax_note: "공식 청구서류는 콜센터 사고접수 후 가상팩스번호 발급 안내. GA허브 기준 장기 대표 0504-800-0700", status: "공식+허브", fax_type: "virtual" },
  { type: "손해보험", name: "NH농협손해보험", system_url: "https://ss.nhfire.co.kr/", terms_url: "https://www.nhfire.co.kr/announce/productAnnounce/retrieveInsuranceProductsAnnounce.nhfire", fax: "0505-060-7000", fax_note: "단체별 별도 팩스 존재: 임직원 0505-060-4100, 단체 0505-060-4099", status: "공식확인", fax_type: "fixed" },
  { type: "손해보험", name: "하나손해보험", system_url: "https://sfa.saleshana.com/", terms_url: "https://www.hanainsure.co.kr/", fax: "이메일 hanaclaim@hanafn.com / 일부 안전보험 0505-152-0698", fax_note: "2026년 상해·질병 청구서에는 홈페이지·모바일·이메일·우편 중심으로 표기. 팩스 사용 시 콜센터 확인", status: "공식확인", fax_type: "fixed" },
  { type: "손해보험", name: "AIG손해보험", system_url: "https://ga.aig.co.kr/", terms_url: "https://www.aig.co.kr/", fax: "02-2011-4607", fax_note: "보험금 청구 접수 관련 FAX 번호", status: "공식확인", fax_type: "fixed" },
  { type: "손해보험", name: "라이나손해보험(에이스/Chubb)", system_url: "https://ga.linagi.com/", terms_url: "https://www.chubb.com/kr-kr/disclosure/product-disclosure.html", fax: "02-2127-2308", fax_note: "처브라이프 공식 서류안내에 손보 고객센터 1566-5800, 팩스 02-2127-2308 표기", status: "공식+허브", fax_type: "fixed" },
  { type: "손해보험", name: "AXA손해보험", system_url: "https://www.axa.co.kr/", terms_url: "https://www.axa.co.kr/", fax: "가상팩스 발급", fax_note: "사고접수 후 문자 메시지로 서류등록 웹링크 또는 가상FAX번호 안내", status: "공식확인", fax_type: "virtual" },
  { type: "손해보험", name: "서울보증보험", system_url: "https://www.sgic.co.kr/", terms_url: "https://www.sgic.co.kr/biz/ccp/index.html?p=CCPUTL030001F01", fax: "고정 청구 팩스 확인불가", fax_note: "보증보험 특성상 지점/온라인 제출 중심. 민원팩스와 청구팩스 혼동 주의", status: "확인필요", fax_type: "unknown" },
  { type: "손해보험", name: "신한EZ손해보험", system_url: "https://www.shinhanez.co.kr/", terms_url: "https://www.shinhanez.co.kr/", fax: "고정 청구 팩스 확인불가", fax_note: "디지털 손보사. 홈페이지/모바일 청구 중심으로 확인 필요", status: "확인필요", fax_type: "unknown" },
  { type: "손해보험", name: "카카오페이손해보험", system_url: "https://kakaopayinscorp.co.kr/", terms_url: "https://kakaopayinscorp.co.kr/disclosure/goods", fax: "카카오톡 채널/웹 청구 중심", fax_note: "공식 보상 안내는 카카오톡 채널 접수 중심. 팩스번호는 공식 확인 불가", status: "공식확인", fax_type: "fixed" },
  { type: "손해보험", name: "예별손해보험(MG계약 포함)", system_url: "https://mganet.mggeneralins.com/", terms_url: "https://www.yebyeol.co.kr/", fax: "0505-088-1646 / 1647 / 1648 / 1649", fax_note: "장기/재물·배상 등 접수 성격에 따라 팩스번호 구분 가능. 기존 MG 계약 이관 관련 확인 필요", status: "공식확인", fax_type: "fixed" },
  { type: "생명보험", name: "삼성생명", system_url: "https://connectplus.samsunglife.com:10443/", terms_url: "https://www.samsunglife.com/individual/products/disclosure/sales/PDO-PRPRI010110M", fax: "가상번호 사용", fax_note: "보험금청구 팩스는 상담/가상번호 방식으로 운영", status: "허브확인", fax_type: "virtual" },
  { type: "생명보험", name: "한화생명", system_url: "https://hmp.hanwhalife.com/", terms_url: "https://www.hanwhalife.com/main/disclosure/goods/disclosurenotice/DF_GDDN000_P10000.do?MENU_ID1=DF_GDDN000_P10000", fax: "가상번호 사용", fax_note: "콜센터/청구 절차에서 안내받은 팩스번호로 송부", status: "공식확인", fax_type: "virtual" },
  { type: "생명보험", name: "교보생명", system_url: "https://ga.kyobo.com/", terms_url: "https://www.kyobo.com/dgt/web/product-official/all-product/search", fax: "가상번호 사용", fax_note: "사고보험금센터/담당 컨설턴트 지점에서 팩스번호 안내", status: "공식확인", fax_type: "virtual" },
  { type: "생명보험", name: "신한라이프", system_url: "https://ga.shinhanlife.co.kr/", terms_url: "https://www.shinhanlife.co.kr/", fax: "가상팩스번호 발급", fax_note: "ARS에서 보험금청구 가상팩스번호 발급 메뉴 확인", status: "공식확인", fax_type: "virtual" },
  { type: "생명보험", name: "KB라이프생명", system_url: "https://sfa.kblife.co.kr/", terms_url: "https://m.kblife.co.kr/customer-common/productList.do", fax: "가상번호 사용", fax_note: "공식 페이지 접근은 방화벽 제한. GA허브 기준 가상번호", status: "허브확인", fax_type: "virtual" },
  { type: "생명보험", name: "NH농협생명", system_url: "https://sfa.nhlife.co.kr:8443/", terms_url: "https://www.nhlife.co.kr/ho/on/HOON0000M00.nhl", fax: "02-6971-6040", fax_note: "사고보험금 팩스. 분할보험금은 02-6971-6060", status: "공식확인", fax_type: "fixed" },
  { type: "생명보험", name: "동양생명", system_url: "https://1004.myangel.co.kr/", terms_url: "https://pbano.myangel.co.kr/paging/WE_AC_WEPAAP020100L", fax: "02-3289-4517", fax_note: "GA허브 기준 청구 팩스번호", status: "허브확인", fax_type: "fixed" },
  { type: "생명보험", name: "DB생명", system_url: "https://etopia.idblife.com/", terms_url: "https://www.idblife.com/notice/product/sale", fax: "0505-129-3134", fax_note: "보험금 신청 전용 팩스. 200만원 초과 시 원본 제출 요청 가능", status: "공식확인", fax_type: "fixed" },
  { type: "생명보험", name: "미래에셋생명", system_url: "https://www.loveageplan.com/", terms_url: "https://life.miraeasset.com/micro/disclosure/product/PC-HO-080301-000000.do", fax: "가상번호 사용", fax_note: "콜센터/전산을 통한 가상팩스번호 발급 기준", status: "공식+허브", fax_type: "virtual" },
  { type: "생명보험", name: "라이나생명", system_url: "https://ga.lina.co.kr/", terms_url: "https://www.lina.co.kr/", fax: "02-6944-1200", fax_note: "사고보험금청구 안내에서 팩스전송 번호 확인", status: "공식확인", fax_type: "fixed" },
  { type: "생명보험", name: "흥국생명", system_url: "https://e-life.heungkuklife.co.kr/", terms_url: "https://www.heungkuklife.co.kr/", fax: "가상번호 사용", fax_note: "GA허브 기준 가상번호. 청구 전 콜센터 확인 권장", status: "허브확인", fax_type: "virtual" },
  { type: "생명보험", name: "ABL생명", system_url: "https://ga.abllife.co.kr/", terms_url: "https://abllife.co.kr/st/custDesk/cspCntr/fncLvngInfo/fncLvngInfo3?page=index", fax: "가상번호 사용", fax_note: "GA허브 기준 가상번호. 청구 전 콜센터 확인 권장", status: "허브확인", fax_type: "virtual" },
  { type: "생명보험", name: "KDB생명", system_url: "https://kss.kdblife.co.kr/", terms_url: "https://www.kdblife.com/ajax.do?pcmode=1&scrId=HDLMA002M02P", fax: "02-2669-7939", fax_note: "GA허브 기준. 일부 구버전 자료는 02-2669-7930 등 상이하므로 발송 전 확인 권장", status: "허브확인", fax_type: "fixed" },
  { type: "생명보험", name: "메트라이프생명", system_url: "https://metplus.metlife.co.kr/", terms_url: "https://www.metlife.co.kr/", fax: "02-3469-9428", fax_note: "100만원 이하 팩스 접수 가능 기준 확인", status: "공식확인", fax_type: "fixed" },
  { type: "생명보험", name: "AIA생명", system_url: "https://imap.aia.co.kr/", terms_url: "https://www.aia.co.kr/ko/disclosure/our-products/disclosing-process.html", fax: "02-2021-4540", fax_note: "AIA+ 청구방법 안내에서 팩스 접수 번호 확인", status: "공식확인", fax_type: "fixed" },
  { type: "생명보험", name: "푸본현대생명", system_url: "https://ez.fubonhyundai.com/", terms_url: "https://www.fubonhyundai.com/", fax: "0505-106-0311", fax_note: "청구서 기준 100만원 이하 팩스 가능. 공식 페이지/청구서 최신 여부 확인 권장", status: "공식+허브", fax_type: "fixed" },
  { type: "생명보험", name: "하나생명", system_url: "https://ga.hanalife.co.kr/", terms_url: "https://www.hanalife.co.kr/", fax: "가상팩스번호 발급 / 02-3709-8628", fax_note: "신규 안내는 고객센터 1577-1112를 통한 가상팩스 발급. 일부 사고보험금 안내에는 FAX 02-3709-8628 표기", status: "공식확인", fax_type: "virtual" },
  { type: "생명보험", name: "BNP파리바카디프생명", system_url: "https://ga.cardif.co.kr/", terms_url: "https://www.cardif.co.kr/", fax: "02-3788-8939", fax_note: "100만원 이하 팩스 접수. 사망·장해·진단은 금액과 무관하게 접수 불가 안내", status: "공식확인", fax_type: "fixed" },
  { type: "생명보험", name: "처브라이프생명", system_url: "https://esmart.chubblife.co.kr/", terms_url: "https://www.chubblife.co.kr/", fax: "02-3480-7801", fax_note: "300만원 이하 팩스 접수 가능 안내 확인", status: "공식확인", fax_type: "fixed" },
  { type: "생명보험", name: "iM라이프생명", system_url: "https://fgs.dgbfnlife.com:8443/", terms_url: "https://www.imlifeins.co.kr/BA/BA_A020.do", fax: "0505-083-5420", fax_note: "GA허브 기준. 일부 공식 페이지는 보험범죄신고 팩스와 별도이므로 청구 전 확인 권장", status: "허브확인", fax_type: "fixed" },
  { type: "생명보험", name: "IBK연금보험", system_url: "https://sf.ibki.co.kr/", terms_url: "https://www.ibki.co.kr/", fax: "02-2270-1577", fax_note: "GA허브 기준. 공식 사이트에서는 민원 FAX로도 동일 번호 확인, 보험금 청구 전 콜센터 확인 권장", status: "허브확인", fax_type: "fixed" },
  { type: "생명보험", name: "교보라이프플래닛생명", system_url: "https://www.lifeplanet.co.kr/", terms_url: "https://www.lifeplanet.co.kr/disclosure/good/HPDA01S0.dev", fax: "고정 청구 팩스 확인불가", fax_note: "디지털 생보사. 홈페이지/모바일 접수 중심 확인 필요", status: "확인필요", fax_type: "unknown" },
  // BOHUMFIT-129: 공제회사 샘플(더미). 실제 값은 Human이 별도 입력 예정.
  { type: "손해보험", category: "공제회사", name: "한국교직원공제회(더 The-K)", system_url: "https://www.ktcu.or.kr/", terms_url: "https://www.ktcu.or.kr/", fax: "확인 필요", fax_note: "[샘플] 공제 상품 청구 팩스는 공식 안내 확인 필요", status: "확인필요", fax_type: "unknown", displayOrder: 1, customerCenter: "1577-0050", browser: "무관", lastVerifiedDate: "2026-06-25" },
  { type: "손해보험", category: "공제회사", name: "새마을금고중앙회 공제(MG)", system_url: "https://www.kfcc.co.kr/", terms_url: "https://www.kfcc.co.kr/", fax: "확인 필요", fax_note: "[샘플] 공제 상품 청구 절차는 가까운 금고/공식 안내 확인 필요", status: "확인필요", fax_type: "unknown", displayOrder: 2, customerCenter: "1599-9000", browser: "무관", lastVerifiedDate: "2026-06-25" },
];

const STATUS_BADGE: Record<Status, string> = {
  공식확인: "bg-emerald-50 text-emerald-700 border border-emerald-200",
  "공식+허브": "bg-blue-50 text-blue-700 border border-blue-200",
  허브확인: "bg-amber-50 text-amber-700 border border-amber-200",
  확인필요: "bg-red-50 text-red-700 border border-red-200",
};

const CATEGORY_BADGE: Record<Category, string> = {
  손해보험: "bg-ink-100 text-ink-600",
  생명보험: "bg-accent-50 text-accent-700",
  공제회사: "bg-violet-50 text-violet-700",
};

// BOHUMFIT-129: 탭/배지 기준 카테고리(없으면 type로 폴백).
const catOf = (ins: Insurer): Category => ins.category ?? ins.type;
const shortCat = (c: Category): string => (c === "손해보험" ? "손해" : c === "생명보험" ? "생명" : "공제");

function openUrl(url: string) {
  window.open(url, "_blank", "noopener,noreferrer");
}

function CopyButton({ text, label = "복사" }: { text: string; label?: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      onClick={() => {
        void navigator.clipboard.writeText(text);
        setDone(true);
        window.setTimeout(() => setDone(false), 1500);
      }}
      className="shrink-0 rounded-[6px] border border-line-strong bg-white px-2 py-0.5 text-[11px] font-semibold text-ink-700 transition-colors hover:bg-ink-50"
    >
      {done ? "복사됨 ✓" : label}
    </button>
  );
}

function ContactRow({ label, value }: { label: string; value?: string }) {
  return (
    <div className="flex items-center justify-between gap-2 py-1.5">
      <span className="text-[12px] text-ink-500">{label}</span>
      {value ? (
        <span className="flex items-center gap-2 text-[12px] font-medium text-ink-800">
          <span className="break-all text-right">{value}</span>
          <CopyButton text={value} />
        </span>
      ) : (
        <span className="text-[12px] font-medium text-amber-600">확인 필요</span>
      )}
    </div>
  );
}

function InsurerCard({ ins }: { ins: Insurer }) {
  const [copied, setCopied] = useState(false);
  const [open, setOpen] = useState(false);
  const cat = catOf(ins);
  const hasClaimForm = !!ins.claimFormUrl;

  const handleFax = () => {
    if (ins.fax_type === "virtual") {
      openUrl(ins.terms_url);
      return;
    }
    if (ins.fax_type === "unknown") return;
    void navigator.clipboard.writeText(ins.fax);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  const faxLabel =
    ins.fax_type === "virtual" ? "가상팩스 발급" : ins.fax_type === "unknown" ? "팩스 확인필요" : copied ? "복사됨 ✓" : "팩스 복사";

  // BOHUMFIT-129: 고객 안내문 복사 문구.
  const customerNotice =
    `[보험금 청구 안내]\n보험사: ${ins.name}\n청구팩스: ${ins.fax}\n` +
    "보험금 청구 전, 보험사별 필요서류와\n청구 가능 기준은 해당 보험사 공식 안내를\n함께 확인해 주세요.";

  return (
    <div className="rounded-card border border-line bg-white p-5">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="card-title text-base font-bold text-ink-900">{ins.name}</h3>
        <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${CATEGORY_BADGE[cat]}`}>
          {shortCat(cat)}
        </span>
        <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${STATUS_BADGE[ins.status]}`}>
          {ins.status}
        </span>
      </div>

      {/* 버튼: 전산 · 약관 · 청구양식 · 팩스 */}
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => openUrl(ins.system_url)}
          className="button-text rounded-btn bg-accent-600 px-3.5 py-2 text-[13px] font-semibold text-white transition-colors hover:bg-accent-700"
        >
          전산 바로가기
        </button>
        <button
          type="button"
          onClick={() => openUrl(ins.terms_url)}
          className="button-text rounded-btn border border-line-strong bg-white px-3.5 py-2 text-[13px] font-semibold text-ink-800 transition-colors hover:bg-ink-50"
        >
          약관 바로가기
        </button>
        <button
          type="button"
          onClick={() => hasClaimForm && openUrl(ins.claimFormUrl!)}
          disabled={!hasClaimForm}
          aria-disabled={!hasClaimForm}
          className={`button-text rounded-btn px-3.5 py-2 text-[13px] font-semibold transition-colors ${
            hasClaimForm
              ? "border border-line-strong bg-white text-ink-800 hover:bg-ink-50"
              : "cursor-not-allowed bg-ink-100 text-ink-400"
          }`}
        >
          청구양식
        </button>
        <button
          type="button"
          onClick={handleFax}
          disabled={ins.fax_type === "unknown"}
          className={`button-text rounded-btn px-3.5 py-2 text-[13px] font-semibold transition-colors ${
            ins.fax_type === "unknown"
              ? "cursor-not-allowed bg-ink-100 text-ink-400"
              : "border border-line-strong bg-white text-ink-800 hover:bg-ink-50"
          }`}
        >
          {faxLabel}
        </button>
      </div>

      <p className="ko-text mt-3 text-[13px] font-medium text-ink-700">
        <span className="text-ink-400">청구 팩스: </span>
        {ins.fax}
      </p>
      <p className="ko-text mt-1 text-[12px] leading-5 text-ink-400">{ins.fax_note}</p>

      {/* 하단: 권장 브라우저 배지 + 최종확인일 */}
      <div className="mt-3 flex items-end justify-between gap-2">
        <div className="flex flex-wrap gap-1.5">
          {ins.browser && (
            <span className="rounded-full bg-sky-50 px-2 py-0.5 text-[11px] font-semibold text-sky-700">
              권장: {ins.browser}
            </span>
          )}
        </div>
        {ins.lastVerifiedDate && (
          <span className="text-[11px] text-ink-300">최종확인 {ins.lastVerifiedDate}</span>
        )}
      </div>

      {/* 상세보기 토글 */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="button-text mt-3 w-full rounded-btn border border-line bg-ink-50 px-3 py-2 text-[12px] font-semibold text-ink-600 transition-colors hover:bg-ink-100"
      >
        {open ? "상세보기 접기 ▲" : "상세보기 ▼"}
      </button>

      {open && (
        <div className="mt-3 space-y-3 rounded-[8px] border border-line bg-ink-50/60 p-3">
          <div>
            <p className="text-[12px] font-bold text-ink-700">업무 연락처</p>
            <div className="mt-1 divide-y divide-line/70">
              <ContactRow label="고객센터" value={ins.customerCenter} />
              <ContactRow label="인콜 모니터링" value={ins.incallNumber} />
              <ContactRow label="전산 헬프데스크" value={ins.helpdeskNumber} />
            </div>
          </div>
          <div>
            <p className="text-[12px] font-bold text-ink-700">청구 정보</p>
            <div className="mt-1 divide-y divide-line/70">
              <ContactRow label="대표 청구팩스" value={ins.fax} />
              {ins.claimFaxSub && <ContactRow label="보조 청구팩스" value={ins.claimFaxSub} />}
            </div>
            <p className="mt-1.5 text-[11px] leading-5 text-ink-400">청구 안내: {ins.fax_note}</p>
          </div>
          <div>
            <p className="text-[12px] font-bold text-ink-700">사용 환경</p>
            <p className="mt-1 text-[12px] text-ink-700">권장 브라우저: {ins.browser ?? "무관"}</p>
          </div>
          <CopyButton text={customerNotice} label="고객 안내문 복사" />
        </div>
      )}
    </div>
  );
}

export default function InsuranceLinks() {
  const [query, setQuery] = useState("");
  const [tab, setTab] = useState<"전체" | Category>("전체");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return INSURANCE_DATA
      .filter((ins) => {
        if (tab !== "전체" && catOf(ins) !== tab) return false;
        if (q && !ins.name.toLowerCase().includes(q)) return false;
        return true;
      })
      // BOHUMFIT-129: displayOrder 오름차순(메리츠화재=1 상단 고정). 미지정은 뒤로(원래 순서 유지).
      .sort((a, b) => (a.displayOrder ?? 999) - (b.displayOrder ?? 999));
  }, [query, tab]);

  return (
    <div className="mx-auto max-w-4xl">
      {/* 헤더 */}
      <header className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-accent-600">Insurance Links</p>
        <h1 className="ko-heading mt-3 text-3xl font-extrabold tracking-tight text-ink-900 md:text-4xl break-keep">
          보험사 전산·약관·팩스 바로가기
        </h1>
        <p className="ko-text mt-2 text-[14px] text-ink-soft">GA 설계사용 · 손해·생명·공제 전산/약관/청구양식/팩스 + 상세 연락처</p>
      </header>

      {/* 검색 */}
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="보험사명 검색 (예: 삼성, 메리츠, 농협)"
        className="w-full rounded-btn border border-line-strong bg-white px-4 py-2.5 text-sm text-ink-800 placeholder:text-ink-300 focus:outline-none focus:ring-2 focus:ring-accent-600/30"
      />

      {/* 탭 */}
      <div role="tablist" aria-label="보험 구분" className="mt-3 flex gap-2 rounded-btn border border-line bg-white p-1">
        {(["전체", "손해보험", "생명보험", "공제회사"] as const).map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className={`button-text flex-1 rounded-[8px] px-3 py-2 text-sm font-bold transition-colors ${
              tab === t ? "bg-accent-600 text-white" : "text-ink-soft hover:bg-ink-50"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* 목록 */}
      <p className="mt-4 text-[12px] text-ink-400">{filtered.length}개 보험사</p>
      <div className="mt-2 grid gap-4 sm:grid-cols-2">
        {filtered.map((ins) => (
          <InsurerCard key={ins.name} ins={ins} />
        ))}
      </div>
      {filtered.length === 0 && (
        <p className="ko-text mt-8 text-center text-sm text-ink-400">검색 결과가 없습니다.</p>
      )}

      {/* 면책 문구 */}
      <div className="mt-8 rounded-card border border-line bg-ink-50 p-5">
        <p className="ko-text text-[13px] leading-6 text-ink-soft break-keep">
          청구 팩스는 상품·청구금액·사고유형에 따라 달라질 수 있습니다.
          발송 전 보험사 전산 또는 고객센터에서 최종 확인해 주세요.
          자동차보험 청구처는 별도 안내를 따르세요.
        </p>
      </div>
    </div>
  );
}
