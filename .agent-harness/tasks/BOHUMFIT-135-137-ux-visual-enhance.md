# BOHUMFIT-135~137 UX/visual/accessibility enhance

## 목표
외부 UI 라이브러리 없이 Tailwind/CSS/기존 컴포넌트만 사용해 UX 시각 효과와 접근성을 강화한다.

## 범위
- `src/index.css`
  - `.bf-shimmer` 키프레임/클래스 추가
  - `.bf-beam` 키프레임/클래스 추가
  - `prefers-reduced-motion` 가드 추가
- `src/pages/Home.tsx`
  - 메인 CTA 버튼에 shimmer 효과 적용
- `src/pages/Disclosure.tsx`
  - 결과 카드 article에 border beam 효과 적용
- `src/components/AnimatedNumber.tsx`
  - ticker 스타일 보강
  - `aria-label` 추가
- `src/components/Toast.tsx`
  - error/warning toast에 `role="alert"` 및 `aria-live="assertive"` 적용
- `src/pages/InsuranceLinks.tsx`
  - 탭/복사 버튼 focus-visible ring 강화
  - CopyButton `aria-label` 추가

## 비목표
- 백엔드 변경 금지
- 분석 로직/상태 변경 금지
- 외부 UI 라이브러리 추가 금지
- 136b/137b 후속 UX 전체 개편은 이번 범위 밖

## 검증
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run build`
- `cd backend && python -m pytest -q`
