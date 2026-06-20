# BOHUMFIT-075-nav-social-auth
## 목적
1. 상단 네비게이션에 구독 메뉴 추가
2. 카카오/구글 소셜 로그인 시 휴대폰 인증 게이트 추가
## Owner
Cowork (구현) → Codex (검증·커밋)
## 파일 범위
- src/components/Layout.tsx (구독 메뉴 추가)
- src/components/ProtectedRoute.tsx (소셜/이메일 공통 phone_verified 게이트)
- src/pages/PhoneVerify.tsx (신규)
- src/App.tsx (/phone-verify 라우트)
## 완료 조건
- 로그인 후 상단 네비게이션에 "구독" 메뉴 표시 → /subscription
- 로그인(소셜 포함) 후 profiles.phone_verified=false 이면 /phone-verify 리다이렉트
- 이메일 가입은 기존대로 Signup.tsx 처리(폰 게이트는 ProtectedRoute가 DB 기준 일원화)
## 구현 메모
- ProtectedRoute: 세션 있으면 supabase `profiles.phone_verified`(RLS 본인 SELECT) 1회 조회. false면 `/phone-verify`로(이미 그 경로면 통과). 로딩 중 깜빡임 방지.
- PhoneVerify.tsx: 번호 입력+인증 요청(스텁) → POST `/auth/verify-phone`(074·phone_verified=true 영속) → `/disclosure` 이동. "1인 1계정 최초 1회 인증" 안내.
- phone_verified=true면 게이트 통과. 미설정(컬럼 없음·게이트 비활성) 시 안전 통과.
