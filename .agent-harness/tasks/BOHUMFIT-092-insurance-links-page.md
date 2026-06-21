# BOHUMFIT-092 전산/약관/팩스 링크모음 페이지
## Goal
GA 설계사용 보험사 39개의 전산 링크·약관 링크·청구 팩스번호를
검색+버튼 UI로 제공하는 페이지 신규 구현.
## Scope
- src/pages/InsuranceLinks.tsx (신규)
- src/App.tsx (라우트 추가)
## Out of Scope
- 백엔드 무변경
- 다른 페이지 무변경 (네비게이션 추가는 093에서)
## UI 스펙(요약)
- 경로 /insurance-links, 단일 파일 자기완결형, Tailwind.
- 헤더(제목/부제) · 검색창(즉시 필터·대소문자 무관) · 탭(전체/손해/생명) · 카드 목록 · 면책 문구.
- 카드: 회사명+구분 뱃지+확인상태 뱃지(공식확인 초록/공식+허브 파랑/허브확인 노랑/확인필요 빨강).
- 버튼 3: [전산 바로가기] system_url 새창 · [약관 바로가기] terms_url 새창 · [팩스 복사] fax_type 분기
  (fixed=복사+"복사됨✓" 1.5s, virtual="가상팩스 발급"→terms_url 새창, unknown="팩스 확인필요" disabled).
## 검증
- 자기검토(39개사·fax_type 분기·검색/탭·JSX) / tsc·lint·test·build = Codex/Windows.
