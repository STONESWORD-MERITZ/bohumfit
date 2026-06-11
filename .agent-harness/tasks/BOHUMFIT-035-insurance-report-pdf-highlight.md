# BOHUMFIT-035 실손 환급 강조 + BOHUMFIT-030 리포트 PDF 연결

## Owner
Codex

## 배경
사용자 확인 결과 `/insurance` 인쇄/PDF 화면에서 건강보험 본인부담상한제 환급 금액의 시각적 강조가 약하고, BOHUMFIT-030에서 개발한 백엔드 리포트 PDF 템플릿이 독립 실손 계산기 버튼에 연결되지 않아 브라우저 인쇄 UI가 그대로 보이고 있다.

## 작업
- `/insurance` 결과 화면과 인쇄/PDF 화면에서 환급 금액을 더 큰 폰트와 강조 색상으로 표시한다.
- `PDF로 저장` 버튼을 BOHUMFIT-030 `POST /api/report/pdf` 엔드포인트에 연결해 백엔드 리포트 템플릿 PDF를 다운로드한다.
- 백엔드 PDF API 실패 시에는 사용자가 작업을 잃지 않도록 브라우저 인쇄 fallback을 제공한다.
- 리포트 payload는 현재 `/insurance` 계산값과 동일한 값으로 구성한다.
- 백엔드 리포트 HTML 테스트에 환급 강조와 실손 급여 반영액 표시 회귀를 추가한다.

## 검증
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run lint`
- `npm test`
- `npm run build`
- `cd backend && python -m pytest -q`
- `/insurance` dev server smoke 및 `report/pdf` 호출 코드 확인.
