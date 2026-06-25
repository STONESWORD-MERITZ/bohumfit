# BOHUMFIT-134 건강보험공단 년차 라벨 수정

## 배경
건강보험공단 요양급여내역은 실제로 심평원 최근 5년 이후의 5~10년 전 구간이다.
현재 다운로드 가이드 최종 체크리스트가 `1년차~5년차`로 표시되어 최근 1~5년 자료처럼 오해될 수 있다.

## 수정 대상
- `src/pages/DownloadGuide.tsx`
- `FinalChecklist`의 `CHECKLIST` 배열 중 `건강보험공단 · 요양급여내역` 그룹 라벨 5개

## 라벨 변경
- `1년차` -> `5~6년 전`
- `2년차` -> `6~7년 전`
- `3년차` -> `7~8년 전`
- `4년차` -> `8~9년 전`
- `5년차` -> `9~10년 전`

## 비목표
- 체크박스 key/value/상태 로직 변경 금지
- 백엔드 파라미터 변경 금지
- 다른 페이지 변경 금지

## 검증
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run build`
- `cd backend && python -m pytest -q`
