# BOHUMFIT-167b — Disclosure.tsx FIT v1.1 리브랜딩 (리브랜딩 최종)

## 배경
166·167a·170으로 Disclosure 제외 전체 FIT v1.1 완료. Disclosure.tsx(핵심 분석 화면, 168에서 소견 UI 제거됨, raw gray 잔여)를 단독 격리.
★스타일만 — 로직·데이터·카피·숫자·JSX 구조 절대 불변.

## 매핑(166·167a 결정적 테이블)
text-gray-950/900→text-ink-900 · 800/700→text-ink · 600/500/400→text-ink-soft · 300→text-ink-400 · placeholder:text-gray-300/400→placeholder:text-ink-400 · bg-gray-50→bg-ink-50 · bg-gray-100/200→bg-ink-100 · bg-gray-900/950→bg-ink-900 · border-gray-100/200→border-line · 300→border-line-strong · divide/ring-gray→divide-line/ring-line · hover:bg-gray-50/100→hover:bg-ink-50/100 · hover:text-gray-*(≤600→ink-soft, ≥700→ink) · #15663D 등 구브랜드→accent 토큰. 표에 없는 gray(투명도/gradient)는 최근접 ink 토큰 매핑 후 기록.

## 접근성(동시)
아이콘 전용 버튼 aria-label(한국어), placeholder-only input→aria-label, 저대비는 매핑이 자동 해소.

## 수정 금지(절대)
- 로직·상태·핸들러·계산·조건·JSX 구조·카피·숫자.
- 시맨틱 컬러(text-red-*·emerald 상태색·text-white·기존 accent/ink/line 토큰). 뱃지 의미색(투약/입원/수술 green/blue/red 등) 현행 유지.
- backend·타 페이지 전체.

## 진행(대형 파일 안전)
1. 착수 raw gray 실측 grep→handoff 기록.
2. 클래스 문자열 replace_all(충돌 방지 순서), 로직 라인 무접촉.
3. 완료 grep text-gray-|bg-gray-|border-gray-|divide-gray-|ring-gray-|#15663D → 0.
4. diff가 className·aria만인지 자체 검토(로직 diff 0).

## 검증
- raw gray 0(잔여 사유) · 라임/그린티 text 0 · 스타일·aria 외 변경 0 · tsc/build/pytest·계산 스모크=Codex.

## 커밋(Codex)
feat(BOHUMFIT-167b): Disclosure FIT v1.1 리브랜딩 (분석 화면 토큰 통일 — 리브랜딩 완결)
