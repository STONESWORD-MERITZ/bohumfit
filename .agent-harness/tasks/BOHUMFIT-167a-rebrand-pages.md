# BOHUMFIT-167a — 잔여 페이지 FIT v1.0 리브랜딩 (Disclosure 제외)

## 배경
166에서 토큰/로고/자산 + 인증·구독·법무 페이지 완료. 잔여 페이지에 신규 브랜드 토큰 적용.
Disclosure.tsx(1891줄)는 리스크 격리를 위해 167b 별도 — 이번 범위 절대 제외.

## 브랜드 스펙(166=FIT 가이드 v1.0)
에메랄드 #084734(메인)·라임 #CEF17B(면 전용)·그린티 #CDEDB3(면 전용)·잉크 #0A0A0A(헤드라인)·본문 #1E293B.
금지: 흰 위 라임·그린티 텍스트/선, 라임 위 흰 텍스트. 버튼 3종(프라이머리 에메랄드+흰/세컨더리 아웃라인/라임 CTA 다크 위 1회). 166 토큰·ui 재사용, 신규 토큰 금지.

## 수정 범위(10)
Home·HomeMission·DisclosureHub·InsuranceCalculator·CoverageAnalysis·CoverageCompare·CoverageGuide·DownloadGuide·ReportSample·WhyDisclosure·InsuranceLinks.

## 수정 금지(절대)
- **src/pages/Disclosure.tsx 무접촉(167b)**. backend 전체. 페이지 로직/상태/핸들러/카피/데이터(INSURANCE_DATA 값) 무변경 — 스타일·토큰·접근성만.

## 매핑(166 Part C와 동일)
text-gray-950/900→text-ink-900 · 800/700→text-ink · 600/500/400→text-ink-soft · placeholder:text-gray-*→placeholder:text-ink-400 · bg-gray-50→bg-ink-50 · bg-gray-100→bg-ink-100 · bg-gray-900/950→bg-ink-900 · border-gray-100/200→border-line · 300→border-line-strong · accent-[#15663D]→accent-accent-600 · text-[#15663D]→text-accent-600. 접근성: 저대비→AA 토큰, 아이콘버튼 aria-label, placeholder-only→aria-label, focus-visible 에메랄드.

## 검증(샌드박스)
- 10페이지 raw gray grep 0(잔여 사유) · #15663D/#0E4A2C 0 · 라임/그린티 text 0 · Disclosure.tsx 무접촉 확인.
- tsc/build/pytest = Codex/Windows.

## 커밋(Codex)
feat(BOHUMFIT-167a): 잔여 페이지 FIT v1.0 리브랜딩 (Disclosure 제외 10페이지)
