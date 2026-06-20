# BOHUMFIT-081-coverage-compare

## 목적
보장 비교분석 페이지 UI 뼈대 생성.
파일 업로드 → "분석 준비 중" 상태까지 구현.
실제 분석 로직은 추후 별도 태스크.

## Owner
Cowork (구현) → Codex (검증·커밋)

## 파일 범위
- src/pages/CoverageCompare.tsx (신규)
- src/App.tsx (라우트 추가)

## 완료 조건
- /coverage-compare 페이지 접근 가능
- 이전 보험 파일 + 신규 보험 파일 업로드 UI (비활성 미리보기)
- "분석 기능 준비 중" 안내 배너 + 알림 신청 이메일 폼(추후 Supabase 연동)
- 분석 시작 버튼 비활성(회색)
- 로그인 필요 (ProtectedRoute)
