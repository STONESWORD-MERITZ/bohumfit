# BOHUMFIT-129d 전산 URL 복원

## 배경
BOHUMFIT-129b 데이터 교체 시 기존 설계사 전산 URL이
"확인 필요"로 덮어써진 것 확인.
git 히스토리(cf5f6f3 BOHUMFIT-092)에서
원본 URL 전체 복원.

## 작업
src/pages/InsuranceLinks.tsx 에서
각 보험사의 systemUrl이 "확인 필요"인 경우만
아래 원본 URL로 교체.
이미 실제 URL이 있는 항목은 건드리지 말 것.
UI/로직 코드 수정 금지.

## 복원할 systemUrl 목록

손해보험:
- 메리츠화재: "https://sales.meritzfire.com/"
- 삼성화재: "https://erp.samsungfire.com/"
- DB손해보험: "https://www.mdbins.com/"
- KB손해보험: "https://nsales.kbinsure.co.kr/"
- 현대해상: "https://sp.hi.co.kr/"
- 한화손해보험: "https://portal.hwgeneralins.com/"
- 롯데손해보험: "https://lottero.lotteins.co.kr/"
- 흥국화재: "https://sales.heungkukfire.co.kr/"
- 농협손해보험: "https://ss.nhfire.co.kr/"
- 하나손해보험: "https://sfa.saleshana.com/"
- AIG손해보험: "https://ga.aig.co.kr/"
- AXA손해보험: "https://www.axa.co.kr/"
- MG손해보험: "https://mganet.mggeneralins.com/"

생명보험:
- 삼성생명: "https://connectplus.samsunglife.com:10443/"
- 한화생명: "https://hmp.hanwhalife.com/"
- 교보생명: "https://ga.kyobo.com/"
- 신한라이프: "https://ga.shinhanlife.co.kr/"
- KB라이프생명: "https://sfa.kblife.co.kr/"
- NH농협생명: "https://sfa.nhlife.co.kr:8443/"
- 동양생명: "https://1004.myangel.co.kr/"
- DB생명: "https://etopia.idblife.com/"
- 미래에셋생명: "https://www.loveageplan.com/"
- 흥국생명: "https://e-life.heungkuklife.co.kr/"
- ABL생명: "https://ga.abllife.co.kr/"
- KDB생명: "https://kss.kdblife.co.kr/"
- AIA생명: "https://imap.aia.co.kr/"
- 푸본현대생명: "https://ez.fubonhyundai.com/"
- 하나생명: "https://ga.hanalife.co.kr/"
- BNP파리바카디프생명: "https://ga.cardif.co.kr/"
- 처브라이프: "https://esmart.chubblife.co.kr/"
- iM라이프: "https://fgs.dgbfnlife.com:8443/"
- 교보라이프플래닛: "https://www.lifeplanet.co.kr/"

유지 (이미 URL 있음, 건드리지 말 것):
- 라이나생명: "https://ga.lina.co.kr/" (유지)

신규 추가 항목 (원본에 없었음, 확인 필요 유지):
- 캐롯손해보험, 악사다이렉트, 더케이손해보험,
  삼성화재해상, 메리츠생명, 카디프생명,
  교직원공제회, 새마을금고중앙회, 군인공제회,
  경찰공제회, 과학기술인공제회, 소방공제회
  → 이 12개는 "확인 필요" 그대로 유지

추가 결정:
- 메리츠생명은 존재하지 않는 회사이므로 목록에서 삭제한다.

## 검증
- npx tsc -p tsconfig.app.json --noEmit
- npm run build

## 완료 조건
- 32개 보험사 systemUrl 복원
- 메리츠생명 행 삭제
- tsc/build pass
- 커밋: "fix(BOHUMFIT-129d): 설계사 전산 URL 복원 (129b에서 덮어쓰인 원본 URL 32개 재적용)"
