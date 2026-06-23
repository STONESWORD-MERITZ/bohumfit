# BOHUMFIT-117: 보장분석서 가이드 이미지 정리·익명화

## 목적
BOHUMFIT-116에서 추가한 보장분석서 가이드 PNG 중 타사이트/벤치마크 사이트 내용과 실제 샘플 데이터 노출 위험을 제거한다.

## 사용자 요청
- 한화손보
  - 1페이지 제목을 PDF 다운로드 방법으로 변경
  - "마이매니저 보장분석에 업로드" 문구 제거
  - 우측 GA보험컨설팅 이미지 삭제
  - 7~9페이지 삭제
- KB손보
  - 1페이지 MYMANAGER 삭제
  - 11~18페이지 삭제
  - 이미지 하단 MYMANAGER 전부 삭제
- DB손보
  - 21~25페이지 삭제
- 남는 이미지의 이름, 숫자, 보험료, 날짜 등 타사이트 자료 값은 임의 최신 날짜/예시 데이터로 변경 또는 비식별화한다.

## Scope
- `src/pages/CoverageGuide.tsx`
- `public/images/coverage-guide/*.png`
- `.agent-harness/tasks/BOHUMFIT-117-coverage-guide-image-sanitize.md`
- `.agent-harness/handoff.md`
- `.agent-harness/locks.md`

## Non-goals
- 보험사 링크 페이지 변경 금지
- 보장분석 파서/백엔드 변경 금지
- 원본 PDF 커밋 금지

## 검증
- PNG 개수: 한화 6장, KB 10장, DB 20장
- `MYMANAGER` 코드 텍스트 잔존 0
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run lint`
- `npm test`
- `npm run build`

## 완료 조건
- 요청한 페이지 삭제 완료
- 표지/하단 브랜드 제거 완료
- 남는 PNG에 예시 데이터 오버레이 또는 비식별화 처리 완료
- 검증 통과 후 커밋·푸시
