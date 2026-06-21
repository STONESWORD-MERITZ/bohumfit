# BOHUMFIT-093 링크모음 네비게이션 연결
## Goal
092에서 만든 InsuranceLinks 페이지를 기존 네비게이션/메뉴에 연결.
## Scope
- 기존 네비게이션 컴포넌트 (src/components/Layout.tsx — NAV 배열)
- src/App.tsx (이미 092에서 라우트 추가됨, 추가 수정 최소화)
## Out of Scope
- 백엔드 무변경
- InsuranceLinks.tsx 무변경
## 작업
- Layout.tsx NAV 배열에 `{ kind: "link", to: "/insurance-links", label: "보험사 링크" }` 추가
  (기존 /download-guide "자료 받기" 와 동일 link 패턴). 데스크탑·모바일 동일 소스 → 자동 반영.
