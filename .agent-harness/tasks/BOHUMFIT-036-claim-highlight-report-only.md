# BOHUMFIT-036 실손 청구 추정액 강조 + 030 PDF 전용화

## Owner
Codex

## 배경
사용자 확인 결과 건강보험 본인부담상한제 환급액 강조는 반영됐지만, 실손 청구 가능성의 청구 추정 금액도 같은 수준의 강조가 필요하다. 또한 `/insurance` PDF 버튼이 BOHUMFIT-030 백엔드 PDF 실패 시 브라우저 인쇄 fallback을 열어 과거 UI처럼 보여, 030 디자인이 반영되지 않은 것처럼 보인다.

## 작업
- 화면/인쇄 fallback/백엔드 리포트 템플릿에서 실손 청구 추정 금액을 큰 글자와 강조 색상으로 표시한다.
- `/insurance` PDF 버튼은 BOHUMFIT-030 백엔드 PDF 다운로드만 시도한다.
- 백엔드 PDF 생성 실패 시 브라우저 인쇄 fallback을 자동으로 열지 않고, 실패 원인을 화면에 표시한다.
- Railway Playwright/Chromium 미설치 등 서버 PDF 생성 실패가 사용자가 확인 가능한 오류로 드러나게 한다.

## 검증
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run lint`
- `npm test`
- `npm run build`
- `cd backend && python -m pytest -q tests/test_report_pdf.py`
- `cd backend && python -m pytest -q`
