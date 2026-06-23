# BOHUMFIT-118: 보장분석서 가이드 이미지 모자이크 원복

## 목적
BOHUMFIT-117에서 과하게 적용된 전체 모자이크/예시값 오버레이를 되돌리고, 사용자가 원한 페이지 삭제 상태만 유지한다.

## 배경
- 사용자의 추가 문장: "이미지에 나와있는 데이터들은 ... 임의로 이름 숫자 등 전부다 ... 수정"은 전체 모자이크 지시가 아니었음.
- 추후 사용자가 각 회사 전산에서 새 캡처를 다시 제공할 예정.

## Scope
- `public/images/coverage-guide/*.png`
- `src/pages/CoverageGuide.tsx`는 페이지 개수 유지 여부 확인만 한다.
- `.agent-harness/handoff.md`
- `.agent-harness/locks.md`

## 작업 내용
- 117 직전 원본 이미지에서 남겨둘 페이지를 복원한다.
- 삭제 유지:
  - 한화 7~9쪽
  - KB 11~18쪽
  - DB 21~25쪽
- 이미지 개수 유지:
  - 한화 6장
  - KB 10장
  - DB 20장

## 검증
- 이미지 개수 확인
- `npx tsc -p tsconfig.app.json --noEmit`
- `npm run build`

## 완료 조건
- 남은 이미지가 117 직전 원본 상태로 복원됨
- 삭제 페이지는 계속 삭제 상태
- 커밋/푸시 완료
