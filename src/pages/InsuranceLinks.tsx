// BOHUMFIT-092: 보험사 전산·약관·팩스 바로가기(GA 설계사용). 단일 파일 자기완결형.
//   외부 fetch 없음 — 39개사 데이터 하드코딩. 082 한국어 타이포(ko-heading/ko-text) 유지.
import { useMemo, useState } from "react";
import Badge, { type BadgeVariant } from "../components/ui/Badge"; // BOHUMFIT-131
import { useToast } from "../components/ToastContext"; // BOHUMFIT-131
import AnimatedNumber from "../components/AnimatedNumber"; // BOHUMFIT-132

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
  { type: "손해보험", name: "메리츠화재", system_url: "https://sales.meritzfire.com/", terms_url: "https://www.meritzfire.com/disclosure/product-announcement/product-list.do?vMode=PC", fax: "0505-021-3400", fax_note: "공식 확인 기준 0505-021-3400 반영, 추가 팩스번호는 확인 필요", status: "공식확인", fax_type: "fixed", displayOrder: 1, customerCenter: "1566-7711", incallNumber: "1577-7711", helpdeskNumber: "02-3786-2777", claimFormUrl: "https://cmdown.meritzfire.com/manager/cm/document/meritzfire_claim_form.pdf", browser: "Edge" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "손해보험", name: "삼성화재", system_url: "https://erp.samsungfire.com/", terms_url: "https://www.samsungfire.com/vh/page/VH.HPIF0103.do", fax: "0505-161-1166", fax_note: "공식 질병/상해 보험금 청구 안내 기준. 팩스 청구는 보험금 청구액 100만원 이하건만 가능", status: "공식확인", fax_type: "fixed", displayOrder: 2, customerCenter: "1588-5114", incallNumber: "1566-0553", helpdeskNumber: "1899-5005", claimFormUrl: "https://www.samsungfire.com/download/claim/claim_new.pdf", browser: "Edge" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "손해보험", name: "DB손해보험", system_url: "https://www.mdbins.com/", terms_url: "https://www.idbins.com/FWMAIV1534.do", fax: "0505-181-4862", fax_note: "장기보상청구 대표 팩스번호로 공식 공지 확인. 대표 이메일 DB2017@dnins.co.kr 병행 안내 확인", status: "공식확인", fax_type: "fixed", displayOrder: 3, customerCenter: "1588-0100", incallNumber: "1566-0757", helpdeskNumber: "02-2262-1241", claimFormUrl: "https://www.idbins.com/pc/bizxpress/ct/dc/FWCUSV1301.shtm", browser: "Chrome" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "손해보험", name: "KB손해보험", system_url: "https://nsales.kbinsure.co.kr/", terms_url: "https://www.kbinsure.co.kr/CG802030001.ecs", fax: "0505-136-6500", fax_note: "공식 도메인 내 보험금청구 안내/양식 기준. 팩스 청구는 100만원 이하 접수 가능 안내 확인", status: "공식확인", fax_type: "fixed", displayOrder: 4, customerCenter: "1544-0114", incallNumber: "1544-0019", helpdeskNumber: "1544-8119", claimFormUrl: "https://www.kbinsure.co.kr/images/claim_svc/reqdoc_genal.pdf", browser: "Edge" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "손해보험", name: "현대해상", system_url: "https://sp.hi.co.kr/", terms_url: "https://www.hi.co.kr/bin/CI/ON/CION3200G.jsp", fax: "0507-774-6060", fax_note: "공식 ARS 안내에서 보험금청구 서류 제출용 팩스번호 문자 안내 방식 확인", status: "공식확인", fax_type: "unknown", displayOrder: 5, customerCenter: "1588-5656", incallNumber: "1577-3223", helpdeskNumber: "02-2628-4567", claimFormUrl: "https://www.hi.co.kr/serviceAction.do?menuId=100631", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "손해보험", name: "한화손해보험", system_url: "https://portal.hwgeneralins.com/", terms_url: "https://m.mall.hwgeneralins.com/etc/public.do", fax: "0502-779-1004", fax_note: "공식 홈페이지 내 장기/상해/질병 대표 청구팩스 번호 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 6, customerCenter: "1566-8000", incallNumber: "1670-1882", helpdeskNumber: "02-316-0111", claimFormUrl: "https://www.hwgeneralins.com/upload/download/customer/insurance.pdf", browser: "무관" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "0502-777-6488" },
  { type: "손해보험", name: "롯데손해보험", system_url: "https://lottero.lotteins.co.kr/", terms_url: "https://www.lotteins.co.kr/web/C/D/H/cdh170.jsp", fax: "0507-333-9999", fax_note: "장기/단체/여행자보험 팩스 0507-333-9999, 재물/배상책임 팩스 02-2094-5973 공식 접수처 확인", status: "공식확인", fax_type: "fixed", displayOrder: 7, customerCenter: "1588-3344", incallNumber: "1600-5182", helpdeskNumber: "02-3455-3984", claimFormUrl: "https://www.lotteins.co.kr/web/C/D/C/cdc_claim_0502.jsp", browser: "Edge" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "02-2094-5973" },
  { type: "손해보험", name: "MG손해보험", system_url: "https://mganet.mggeneralins.com/", terms_url: "https://www.yebyeol.co.kr/PB031210DM.scp?menuId=MN0803006", fax: "0505-088-1649", fax_note: "예별손해보험 공식 페이지 기준. 재물/배상책임 청구는 보험금청구서 작성 후 0505-088-1649 접수 안내 확인, 장기/상해/질병 대표 팩스는 확인 필요", status: "공식확인", fax_type: "fixed", displayOrder: 8, customerCenter: "1588-5959", incallNumber: "1577-3777", helpdeskNumber: "02-3788-2261", claimFormUrl: "https://www.mggeneralins.com/webdocs/resources/files/rw031010dm/inbohum_chunggu.pdf", browser: "Edge" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "손해보험", name: "흥국화재", system_url: "https://sales.heungkukfire.co.kr/", terms_url: "https://www.heungkukfire.co.kr/FRW/announce/insGoodsGongsiSale.do", fax: "0504-800-0700", fax_note: "공식 구비서류/양식 페이지에서 고객센터 1688-1688 확인. 대표 청구팩스 번호는 공식 페이지 기준 추가 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 9, customerCenter: "1688-1688", incallNumber: "1688-6997", helpdeskNumber: "031-786-8088", claimFormUrl: "https://www.heungkukfire.co.kr/FRW/helpdesk/docInfoTemplate.do", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "손해보험", name: "농협손해보험", system_url: "https://ss.nhfire.co.kr/", terms_url: "https://www.nhfire.co.kr/announce/productAnnounce/retrieveInsuranceProductsAnnounce.nhfire", fax: "0505-060-7000", fax_note: "공식 보험금청구 안내 기준. 대표 팩스 0505-060-7000, 단체보험 관련 팩스는 별도 번호 확인", status: "공식확인", fax_type: "fixed", displayOrder: 10, customerCenter: "1644-9000", incallNumber: "1644-9600", helpdeskNumber: "1644-0090", claimFormUrl: "https://www.nhfire.co.kr/customer/bilgdcm/retrieveBilgDcmList.nhfire", browser: "Chrome" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "0505-060-4100 / 0505-060-4099" },
  { type: "손해보험", name: "하나손해보험", system_url: "https://sfa.saleshana.com/", terms_url: "https://m.hanainsure.co.kr/w/disclosure/product/saleProduct", fax: "확인 필요", fax_note: "공식 청구서 양식 확인. 장기/상해/질병 대표 청구팩스 번호는 공식 페이지 기준 추가 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 11, customerCenter: "1566-3000", incallNumber: "1566-3000", helpdeskNumber: "02-6670-8110", claimFormUrl: "https://www.hanainsure.co.kr/download?a=healthRewardGuide1_1", browser: "Chrome" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "손해보험", name: "캐롯손해보험", system_url: "확인 필요", terms_url: "https://www.carrotins.com/desktop/disclosure/price/", fax: "0303-3136-0300", fax_note: "공식 청구안내 기준 팩스 0303-3136-0300, 이메일 carrot@hanwha.com 확인", status: "공식확인", fax_type: "fixed", displayOrder: 12, customerCenter: "1566-0300", incallNumber: "확인 필요", helpdeskNumber: "확인 필요", claimFormUrl: "https://www.carrotins.com/desktop/reward/claim/guide/", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "손해보험", name: "AXA손해보험", system_url: "https://www.axa.co.kr/", terms_url: "https://www.axa.co.kr/AsianPlatformInternet/html/axacms/common/intro/disclosure/insurance/index.html", fax: "확인 필요", fax_note: "상해/질병 청구서 공식 양식 및 고객센터 안내 확인. 팩스 대표번호는 공식 페이지 기준 추가 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 13, customerCenter: "1566-1566 / 1566-2266", incallNumber: "확인 필요", helpdeskNumber: "확인 필요", claimFormUrl: "https://www.axa.co.kr/AsianPlatformInternet/doc/internet/claim_invoice_accident_illness.pdf", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "손해보험", name: "AIG손해보험", system_url: "https://ga.aig.co.kr/", terms_url: "https://www.aig.co.kr/wm/content.html?contentId=DPWMS701", fax: "02-2011-4607", fax_note: "공식 보험금청구 접수방법에서 팩스 접수 가능 및 1,000만원 이하 기준 확인. 팩스 대표번호는 공식 페이지 기준 추가 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 14, customerCenter: "1544-2792", incallNumber: "1544-2792", helpdeskNumber: "02-2260-6855", claimFormUrl: "https://m.aig.co.kr/wm/content.html?contentId=DPWMS406", browser: "Chrome" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "손해보험", name: "악사다이렉트", system_url: "확인 필요", terms_url: "https://www.axa.co.kr/AsianPlatformInternet/html/axacms/common/intro/disclosure/insurance/index.html", fax: "확인 필요", fax_note: "AXA손해보험 공식 홈페이지 기준 동일. 상해/질병 청구서 공식 양식 확인, 팩스 대표번호는 추가 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 15, customerCenter: "1566-1566 / 1566-2266", incallNumber: "확인 필요", helpdeskNumber: "확인 필요", claimFormUrl: "https://www.axa.co.kr/AsianPlatformInternet/doc/internet/claim_invoice_accident_illness.pdf", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "손해보험", name: "더케이손해보험", system_url: "확인 필요", terms_url: "확인 필요", fax: "확인 필요", fax_note: "현행 공식 홈페이지/업무 정보 확인 필요. 하나손해보험 전환 이력으로 별도 검증 필요", status: "확인필요", fax_type: "unknown", displayOrder: 16, customerCenter: "1566-3000", incallNumber: "확인 필요", helpdeskNumber: "02-6670-8110", claimFormUrl: "확인 필요", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "손해보험", name: "삼성화재해상", system_url: "확인 필요", terms_url: "https://www.samsungfire.com/vh/page/VH.HPIF0103.do", fax: "0505-161-1166", fax_note: "공식 질병/상해 보험금 청구 안내 기준. 팩스 청구는 보험금 청구액 100만원 이하건만 가능", status: "공식확인", fax_type: "fixed", displayOrder: 18, customerCenter: "1588-5114", incallNumber: "1566-0553", helpdeskNumber: "1899-5005", claimFormUrl: "https://www.samsungfire.com/download/claim/claim_new.pdf", browser: "Edge" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "삼성생명", system_url: "https://connectplus.samsunglife.com:10443/", terms_url: "https://www.samsunglife.com/individual/products/disclosure/sales/PDO-PRPRI010110M", fax: "확인 필요", fax_note: "공식 홈페이지에서 보험금 청구 메뉴 및 콜센터 확인. 팩스 대표번호는 공식 페이지 기준 추가 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 19, customerCenter: "1588-3114", incallNumber: "1588-3115", helpdeskNumber: "02-311-4500", claimFormUrl: "https://direct.samsunglife.com/customerSupport/insuranceClaimInformation/CustomerSupportInsuranceClaimInformationView", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "한화생명", system_url: "https://hmp.hanwhalife.com/", terms_url: "https://www.hanwhalife.com/main/disclosure/goods/disclosurenotice/DF_GDDN000_P10000.do", fax: "콜센터 상담 후 안내", fax_note: "공식 청구절차 기준 콜센터 상담 후 안내받은 Fax 번호로 구비서류 송부", status: "공식확인", fax_type: "fixed", displayOrder: 20, customerCenter: "1588-6363", incallNumber: "1800-6633", helpdeskNumber: "02-1522-6379", claimFormUrl: "https://www.hanwhalife.com/static/main/myPage/insurance/accident/document/MY_INAPADC_T10000.jsp", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "교보생명", system_url: "https://ga.kyobo.com/", terms_url: "https://www.kyobo.com/dgt/web/product-official/information", fax: "콜센터/담당 컨설턴트 안내", fax_note: "사고보험금 고객센터 1588-1810 및 담당 컨설턴트/심사담당자 안내 기준", status: "공식확인", fax_type: "fixed", displayOrder: 21, customerCenter: "1588-1001", incallNumber: "1588-1636", helpdeskNumber: "02-721-3130", claimFormUrl: "https://www.kyobo.com/dgt/web/customer/support/need-papers/list", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "신한라이프", system_url: "https://ga.shinhanlife.co.kr/", terms_url: "https://www.shinhanlife.co.kr/hp/cdhi0010.do", fax: "확인 필요", fax_note: "공식 보험금 청구서류 페이지 및 신한라이프 온콜센터 기준. 팩스 대표번호는 추가 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 22, customerCenter: "1588-5580", incallNumber: "1522-2285", helpdeskNumber: "02-3455-4119", claimFormUrl: "https://www.shinhanlife.co.kr/hp/cdhf0020t02.do", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "흥국생명", system_url: "https://e-life.heungkuklife.co.kr/", terms_url: "https://www.heungkuklife.co.kr/front/public/saleProduct.do?searchFlgSale=Y", fax: "확인 필요", fax_note: "공식 사고보험금 구비서류 안내 및 고객센터 기준. 팩스 대표번호는 공식 페이지 기준 추가 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 24, customerCenter: "1588-2288", incallNumber: "1877-7006", helpdeskNumber: "031-786-8088", claimFormUrl: "https://www.heungkuklife.co.kr/cyber/accident/Accident_File_Info.do", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "동양생명", system_url: "https://1004.myangel.co.kr/", terms_url: "https://pbano.myangel.co.kr/paging/WE_AC_WEPAAP020100L", fax: "02-3289-4517", fax_note: "공식 홈페이지 기준 보험금 청구서 양식/팩스 대표번호 추가 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 25, customerCenter: "1577-1004 / 1800-1004", incallNumber: "080-899-1004", helpdeskNumber: "02-728-9900", claimFormUrl: "https://www.동양생명.com/assets/pdf/동양생명-보험금청구서.pdf", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "ABL생명", system_url: "https://ga.abllife.co.kr/", terms_url: "https://abllife.co.kr/st/pban/prdtPban/utilzGudn?page=index", fax: "02-3299-5544", fax_note: "공식 사고보험금 청구안내 기준. 팩스 접수 가능 기준은 청구금액/서류 성격별 확인 필요", status: "공식확인", fax_type: "fixed", displayOrder: 26, customerCenter: "1588-6500", incallNumber: "1566-1002", helpdeskNumber: "02-3787-8583", claimFormUrl: "https://abllife.co.kr/st/custDesk/insSrvcGudn/acdtInsmClamGudn/acdtInsmClamGudn1?page=index", browser: "Edge" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "DB생명", system_url: "https://etopia.idblife.com/", terms_url: "https://www.idblife.com/notice/product/sale", fax: "0505-129-3134", fax_note: "보험금 신청 전용 팩스. 200만원 초과 시 원본서류 우편 또는 방문 제출 안내 확인", status: "공식확인", fax_type: "fixed", displayOrder: 27, customerCenter: "1588-3131", incallNumber: "02-6470-7663", helpdeskNumber: "02-2119-5151", claimFormUrl: "https://www.idblife.com/support/guide/acbf_clm", browser: "Edge" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "KB라이프생명", system_url: "https://sfa.kblife.co.kr/", terms_url: "https://www.kblife.co.kr/customer-common/productList.do", fax: "02-6220-9912", fax_note: "공식 보험금청구서 양식 기준. 팩스 대표번호는 공식 홈페이지 기준 추가 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 28, customerCenter: "1588-3374", incallNumber: "1566-2730", helpdeskNumber: "1899-3899", claimFormUrl: "https://www.kblife.co.kr/api/archive/archives/download-for-guide/fileDown/sago_report1.do", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "푸본현대생명", system_url: "https://ez.fubonhyundai.com/", terms_url: "확인 필요", fax: "0505-106-0311", fax_note: "공식 홈페이지 기준 보험금 청구서 양식, 고객센터, 청구팩스 추가 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 29, customerCenter: "1577-3311", incallNumber: "확인 필요", helpdeskNumber: "080-860-1212", claimFormUrl: "https://www.푸본현대생명.com/assets/pdf/푸본현대생명-보험금청구서.pdf", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "하나생명", system_url: "https://ga.hanalife.co.kr/", terms_url: "https://www.hanalife.co.kr/anm/product/allProduct.do?status=on", fax: "고객센터 가상팩스번호 발급", fax_note: "공식 청구절차 기준 고객센터 접수 후 가상팩스번호 발급 방식 확인", status: "공식확인", fax_type: "fixed", displayOrder: 30, customerCenter: "1577-1112", incallNumber: "1577-1112", helpdeskNumber: "02-3709-8602", claimFormUrl: "https://www.hanalife.co.kr/csc/accidentGuideRenew/accidentPaymentProcedure.do", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "NH농협생명", system_url: "https://sfa.nhlife.co.kr:8443/", terms_url: "https://www.nhlife.co.kr/ho/on/HOON0000M00.nhl", fax: "02-6971-6040", fax_note: "공식 사고보험금 청구 안내 및 상품공시실 경로 확인. 대표 고객센터/팩스번호는 공식 페이지 기준 추가 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 31, customerCenter: "1544-4000", incallNumber: "1544-4422", helpdeskNumber: "02-3786-8800", claimFormUrl: "https://m.nhlife.co.kr/mo/cm/30/20/MOCM3020P00", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "미래에셋생명", system_url: "https://www.loveageplan.com/", terms_url: "https://life.miraeasset.com/micro/disclosure/product/PC-HO-080301-000000.do", fax: "0505-130-0000", fax_note: "공식 사고보험금/고객센터 기준. 대표 청구팩스 번호는 공식 페이지 기준 추가 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 32, customerCenter: "1588-0220", incallNumber: "1588-0220", helpdeskNumber: "02-3271-5108", claimFormUrl: "https://life.miraeasset.com/Cmmn/lifePage.do?cp=MNT-IS-173", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "AIA생명", system_url: "https://imap.aia.co.kr/", terms_url: "https://www.aia.co.kr/ko/customer-support/customer-guide/insurance-guide/personal-insurance.html", fax: "02-2021-4540", fax_note: "AIA+ 공식 청구 방법 안내 기준. 우편/팩스/고객센터/병원 키오스크 접수 가능", status: "공식확인", fax_type: "fixed", displayOrder: 33, customerCenter: "1588-9898", incallNumber: "확인 필요", helpdeskNumber: "확인 필요", claimFormUrl: "https://aiaplus.aia.co.kr/ko/claims/guide/claimsPaper.html", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "처브라이프", system_url: "https://esmart.chubblife.co.kr/", terms_url: "https://www.chubblife.co.kr/front/official/sale/listSale.do", fax: "02-3480-7801", fax_note: "공식 보험금 청구 안내 기준. 지급금액 300만원 이하 청구 시 FAX 접수 가능", status: "공식확인", fax_type: "fixed", displayOrder: 34, customerCenter: "1599-4600", incallNumber: "1599-4600", helpdeskNumber: "1599-4646", claimFormUrl: "https://www.chubblife.co.kr/front/ctmcenter/insurance/listDocu.do", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "라이나생명", system_url: "https://ga.lina.co.kr/", terms_url: "https://www.lina.co.kr/disclosure/product-public-announcement/product-guide", fax: "02-6944-1200", fax_note: "공식 GA영업지원시스템 및 보험금청구서류 안내 기준. 청구팩스 대표번호는 공식 고객센터 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 35, customerCenter: "1588-0058 / 080-377-1111", incallNumber: "1588-2442", helpdeskNumber: "1588-2215", claimFormUrl: "https://www.lina.co.kr/customer/required/?tab=second", browser: "Chrome", lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "카디프생명", system_url: "확인 필요", terms_url: "https://www.cardif.co.kr/disclosure/papag101.do", fax: "02-3788-8939", fax_note: "공식 보험금청구 페이지 기준. 팩스 접수는 청구보험금 100만원 이하, 사망·장해·진단건은 접수 불가", status: "공식확인", fax_type: "fixed", displayOrder: 36, customerCenter: "1688-1118", incallNumber: "1688-1118", helpdeskNumber: "1577-3435", claimFormUrl: "https://www.cardif.co.kr/customer-center/hcwgi001.do", browser: "Edge" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "BNP파리바카디프생명", system_url: "https://ga.cardif.co.kr/", terms_url: "https://www.cardif.co.kr/disclosure/papag101.do", fax: "02-3788-8939", fax_note: "공식 보험금청구 페이지 기준. 팩스 접수는 청구보험금 100만원 이하, 사망·장해·진단건은 접수 불가", status: "공식확인", fax_type: "fixed", displayOrder: 37, customerCenter: "1688-1118", incallNumber: "1688-1118", helpdeskNumber: "1577-3435", claimFormUrl: "https://www.cardif.co.kr/customer-center/hcwgi001.do", browser: "Edge" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "KDB생명", system_url: "https://kss.kdblife.co.kr/", terms_url: "https://www.kdblife.com/ajax.do?pcmode=1&scrId=HDLMA002M02P", fax: "02-2669-7930", fax_note: "공식 보험가입 가이드 내 사고보험금 청구/콜센터 팩스 접수번호 확인", status: "공식확인", fax_type: "fixed", displayOrder: 38, customerCenter: "1588-4040", incallNumber: "1588-4040", helpdeskNumber: "02-6303-2771", claimFormUrl: "https://direct.kdblife.co.kr/edirect/customer/insGuideList.do", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "iM라이프", system_url: "https://fgs.dgbfnlife.com:8443/", terms_url: "https://www.imlifeins.co.kr/BA/BA_A010.do", fax: "0505-083-5420", fax_note: "공식 사고보험금청구 서류안내 기준. FAX는 청구금액 300만원 이하, 홈페이지/모바일은 1,000만원 이하", status: "공식확인", fax_type: "fixed", displayOrder: 39, customerCenter: "1588-4770", incallNumber: "1588-4770", helpdeskNumber: "02-2087-9594", claimFormUrl: "https://www.imlifeins.co.kr/BB/BB_D010.do", browser: "Chrome" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "생명보험", name: "교보라이프플래닛", system_url: "https://www.lifeplanet.co.kr/", terms_url: "https://www.lifeplanet.co.kr/disclosure/good/HPDA01S0.dev", fax: "1566-9831", fax_note: "공식 상품공시실 확인. 보험금 청구서 양식, 고객센터, 청구팩스는 공식 페이지 기준 추가 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 40, customerCenter: "1566-0999", incallNumber: "확인 필요", helpdeskNumber: "확인 필요", claimFormUrl: "확인 필요", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "손해보험", category: "공제회사", name: "교직원공제회", system_url: "확인 필요", terms_url: "https://m.ktcu.or.kr/PMW-FIC-800301", fax: "02-3278-9696", fax_note: "공식 FAQ 기준 보험금 300만원 이하 팩스/PC/모바일 접수 가능. 일반 보험금 청구 대표 팩스번호는 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 41, customerCenter: "1577-3400 / 보험컨택센터 1577-3993", incallNumber: "확인 필요", helpdeskNumber: "확인 필요", claimFormUrl: "https://m.ktcu.or.kr/PMW-CSA-100101", browser: "Edge" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "손해보험", category: "공제회사", name: "새마을금고중앙회", system_url: "확인 필요", terms_url: "확인 필요", fax: "02-3016-7614", fax_note: "공제 보험금 청구 양식, 고객센터, 대표 청구팩스는 공식 페이지 기준 추가 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 42, customerCenter: "1599-9010", incallNumber: "확인 필요", helpdeskNumber: "확인 필요", claimFormUrl: "확인 필요", browser: "Edge" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "손해보험", category: "공제회사", name: "군인공제회", system_url: "확인 필요", terms_url: "확인 필요", fax: "확인 필요", fax_note: "공식 홈페이지 기준 보험금/급여금 청구 양식, 대표번호, 팩스번호 추가 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 43, customerCenter: "1544-9090", incallNumber: "확인 필요", helpdeskNumber: "확인 필요", claimFormUrl: "확인 필요", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "손해보험", category: "공제회사", name: "경찰공제회", system_url: "확인 필요", terms_url: "확인 필요", fax: "확인 필요", fax_note: "공식 홈페이지 고객센터/자료실 기준. 보험금 또는 급여금 청구 전용 팩스번호는 추가 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 44, customerCenter: "1577-0112", incallNumber: "확인 필요", helpdeskNumber: "1644-0128", claimFormUrl: "https://www.policefund.or.kr/www/1461126409163/bbs.do", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "손해보험", category: "공제회사", name: "과학기술인공제회", system_url: "확인 필요", terms_url: "확인 필요", fax: "확인 필요", fax_note: "공식 홈페이지 대표 고객센터 확인. 보험금/급여금 청구 양식 및 전용 팩스번호는 추가 확인 필요", status: "공식확인", fax_type: "unknown", displayOrder: 45, customerCenter: "1577-0789 / 1433-23", incallNumber: "확인 필요", helpdeskNumber: "확인 필요", claimFormUrl: "확인 필요", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
  { type: "손해보험", category: "공제회사", name: "소방공제회", system_url: "확인 필요", terms_url: "확인 필요", fax: "02-430-7459", fax_note: "공식 서식자료실 기준 급여금 청구서 및 대표 팩스 02-430-7459 확인", status: "공식확인", fax_type: "fixed", displayOrder: 46, customerCenter: "02-407-7119", incallNumber: "확인 필요", helpdeskNumber: "확인 필요", claimFormUrl: "https://www.focu.or.kr/center/archive.do", browser: "확인 필요" as Browser, lastVerifiedDate: "2026-06-25", claimFaxSub: "" },
];

// BOHUMFIT-131: 배지 의미 매핑(Badge variant). 손해=info·생명=success·공제=outline / 상태별.
const CATEGORY_VARIANT: Record<Category, BadgeVariant> = {
  손해보험: "info",
  생명보험: "success",
  공제회사: "outline",
};
const STATUS_VARIANT: Record<Status, BadgeVariant> = {
  공식확인: "success",
  "공식+허브": "info",
  허브확인: "warning",
  확인필요: "danger",
};

// BOHUMFIT-129: 탭/배지 기준 카테고리(없으면 type로 폴백).
const catOf = (ins: Insurer): Category => ins.category ?? ins.type;
const shortCat = (c: Category): string => (c === "손해보험" ? "손해" : c === "생명보험" ? "생명" : "공제");

function isExternalUrl(url?: string): url is string {
  return !!url && /^https?:\/\//i.test(url);
}

function openUrl(url?: string) {
  if (!isExternalUrl(url)) return false;
  window.open(url, "_blank", "noopener,noreferrer");
  return true;
}

function CopyButton({ text, label = "복사" }: { text: string; label?: string }) {
  const [done, setDone] = useState(false);
  const { showToast } = useToast(); // BOHUMFIT-131
  return (
    <button
      type="button"
      onClick={() => {
        void navigator.clipboard.writeText(text);
        setDone(true);
        showToast("복사되었습니다", "success");
        window.setTimeout(() => setDone(false), 1500);
      }}
      className="shrink-0 rounded-[6px] border border-line-strong bg-white px-2 py-0.5 text-[11px] font-semibold text-ink-700 transition-colors hover:bg-ink-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500"
      aria-label={`${label} 복사`}
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
  const { showToast } = useToast(); // BOHUMFIT-131
  const cat = catOf(ins);
  const hasSystemUrl = isExternalUrl(ins.system_url);
  const hasTermsUrl = isExternalUrl(ins.terms_url);
  const hasClaimForm = isExternalUrl(ins.claimFormUrl);

  const handleFax = () => {
    if (ins.fax_type === "virtual") {
      if (!openUrl(ins.terms_url)) showToast("링크 확인이 필요합니다.", "warning");
      return;
    }
    if (ins.fax_type === "unknown") return;
    void navigator.clipboard.writeText(ins.fax);
    setCopied(true);
    showToast("팩스번호가 복사되었습니다", "success");
    window.setTimeout(() => setCopied(false), 1500);
  };

  const faxLabel =
    ins.fax_type === "virtual" ? "가상팩스 발급" : ins.fax_type === "unknown" ? "팩스 확인필요" : copied ? "복사됨 ✓" : "팩스 복사";

  // BOHUMFIT-129: 고객 안내문 복사 문구.
  const customerNotice =
    `[보험금 청구 안내]\n보험사: ${ins.name}\n청구팩스: ${ins.fax}\n` +
    "보험금 청구 전, 보험사별 필요서류와\n청구 가능 기준은 해당 보험사 공식 안내를\n함께 확인해 주세요.";

  return (
    <div className="rounded-card border border-line bg-white p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-green-200 hover:shadow-lg">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="card-title text-base font-bold text-ink-900">{ins.name}</h3>
        <Badge variant={CATEGORY_VARIANT[cat]}>{shortCat(cat)}</Badge>
        <Badge variant={STATUS_VARIANT[ins.status]}>{ins.status}</Badge>
      </div>

      {/* 버튼: 전산 · 약관 · 청구양식 · 팩스 */}
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => {
            if (!openUrl(ins.system_url)) showToast("전산 링크 확인이 필요합니다.", "warning");
          }}
          disabled={!hasSystemUrl}
          aria-disabled={!hasSystemUrl}
          className={`button-text rounded-btn px-3.5 py-2 text-[13px] font-semibold transition-colors ${
            hasSystemUrl
              ? "bg-accent-600 text-white hover:bg-accent-700"
              : "cursor-not-allowed bg-ink-100 text-ink-400"
          }`}
        >
          전산 바로가기
        </button>
        <button
          type="button"
          onClick={() => {
            if (!openUrl(ins.terms_url)) showToast("약관 링크 확인이 필요합니다.", "warning");
          }}
          disabled={!hasTermsUrl}
          aria-disabled={!hasTermsUrl}
          className={`button-text rounded-btn px-3.5 py-2 text-[13px] font-semibold transition-colors ${
            hasTermsUrl
              ? "border border-line-strong bg-white text-ink-800 hover:bg-ink-50"
              : "cursor-not-allowed bg-ink-100 text-ink-400"
          }`}
        >
          약관 바로가기
        </button>
        <button
          type="button"
          onClick={() => {
            if (!openUrl(ins.claimFormUrl)) showToast("청구양식 링크 확인이 필요합니다.", "warning");
          }}
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
      {/* BOHUMFIT-131: underline 슬라이드 애니메이션 탭(브랜드 그린·hover 연한 그린) */}
      <div role="tablist" aria-label="보험 구분" className="mt-3 flex gap-1 border-b border-line">
        {(["전체", "손해보험", "생명보험", "공제회사"] as const).map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className={`button-text relative flex-1 rounded-t-[8px] px-3 py-2.5 text-sm font-bold transition-all duration-200 hover:bg-green-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500 ${
              tab === t ? "text-[#2d6a4f]" : "text-ink-soft"
            }`}
          >
            {t}
            <span
              aria-hidden
              className={`absolute inset-x-2 -bottom-px h-0.5 origin-center rounded-full bg-[#2d6a4f] transition-all duration-200 ${
                tab === t ? "scale-x-100 opacity-100" : "scale-x-0 opacity-0"
              }`}
            />
          </button>
        ))}
      </div>

      {/* 목록 */}
      <p className="mt-4 text-[12px] text-ink-400">
        <AnimatedNumber value={filtered.length} />개 보험사
      </p>
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
