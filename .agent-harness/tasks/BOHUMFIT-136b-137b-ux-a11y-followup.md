# BOHUMFIT-136b/137b UX/A11y follow-up

## 목표
Disclosure 업로드 UX와 접근성을 보강한다.

## 범위
- `src/pages/Disclosure.tsx`

## 구현 확인 항목
- drag-and-drop 업로드 상태 시각화
- `onDragOver`, `onDragEnter`, `onDragLeave`, `onDrop` 핸들러 추가
- `isDragging`, `selectedNames`, `showSticky` 상태 추가
- `Upload`, `FileText`, `CheckCircle2` lucide 아이콘 사용
- 모바일 하단 고정 CTA(`md:hidden fixed bottom-0`) 추가
- 스크롤 240px 이후 `showSticky` 표시 로직
- 업로드 input `aria-label` 추가
- 오류 토스트 메시지 구체화
- 보조 문구 대비 보강(`text-gray-400` -> `text-gray-500`)

## 비목표
- 백엔드 변경 금지
- 분석 로직 변경 금지
- 업로드 파이프라인 변경 금지
- 전체 색상 대비/ARIA 전수 보정은 후속 137c

## 검증
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run build`
- `cd backend && python -m pytest -q`
