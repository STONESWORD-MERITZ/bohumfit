# BOHUMFIT-032 실손 계산기 최소공제 자동화 + PDF 저장 버튼

## Owner
Codex

## 배경
독립 실손 계산기(`/insurance`)의 `실손 최소공제 적용 추정` 영역이 사용자가 알기 어려운 기관종별·건별 진료비를 직접 입력하도록 되어 있어 실사용성이 낮다. 또한 리포트 PDF 출력 엔드포인트는 있지만 `/insurance` 화면에는 별도 PDF 저장 버튼이 없다.

## 작업
- 최소공제 영역을 사용자 입력형 옵션에서 자동 추정 표시로 변경한다.
- 사용자가 입력한 연간 급여 본인부담·비급여 금액과 선택 세대를 기준으로 최소공제 기준을 자동 반영한다.
- 기관종별을 사용자가 입력하지 않는 독립 계산기 특성상 등급 미상은 기존 공용 산식의 상급 기준으로 보수 적용한다.
- `/api/report/pdf` 보험 리포트 엔드포인트와 연결되는 `PDF로 저장` 버튼을 추가한다.

## 하지 말 것
- 백엔드 보험 산식 변경 금지.
- Disclosure 화면의 기존 최소공제 수동 상세 입력 흐름 변경 금지.
- 알릴의무 분석 로직 변경 금지.

## 검증
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run lint`
- `npm test`
- `npm run build`
- 가능하면 `/insurance` 화면 smoke 확인.
