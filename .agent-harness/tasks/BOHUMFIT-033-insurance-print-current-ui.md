# BOHUMFIT-033 실손 계산 PDF를 현재 UI 인쇄 방식으로 전환

## Owner
Codex

## 배경
`/insurance`의 `PDF로 저장` 버튼이 백엔드 `/api/report/pdf`를 호출하면서 Railway Playwright 준비 상태에 따라 `리포트 생성 기능을 준비 중입니다` 오류가 발생한다. 또한 백엔드 리포트 템플릿은 현재 화면 UI와 달라 사용자가 보는 실손 계산 화면과 PDF 결과가 어긋난다.

## 작업
- `/insurance` PDF 저장 버튼을 백엔드 리포트 생성 호출이 아니라 브라우저 인쇄(`window.print`)로 전환한다.
- 인쇄 시 현재 개발된 실손 계산 UI 영역만 출력되도록 print CSS와 print area를 추가한다.
- 화면에서는 기존 UI가 그대로 보이고, 입력 폼/모드 토글/PDF 버튼은 인쇄에서 숨긴다.
- PDF에는 현재 결과 카드, 입력 요약, 면책 문구, 생성일, 민감정보 주의 문구가 포함되도록 한다.

## 하지 말 것
- 백엔드 PDF 엔드포인트/템플릿 변경 금지.
- 실손 계산 산식 변경 금지.
- 알릴의무 화면 변경 금지.

## 검증
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run lint`
- `npm test`
- `npm run build`
- `/insurance` dev server 200 및 소스 grep으로 버튼/print area 확인.
