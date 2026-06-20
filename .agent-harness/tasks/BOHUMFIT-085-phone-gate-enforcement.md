# BOHUMFIT-085: 소셜 로그인 후 휴대폰 인증 게이트 실동작 (Supabase 연동)
## 목적
카카오/구글 소셜 로그인 및 기존 가입자를 포함한 모든 사용자가 휴대폰 인증 전에는 보호 라우트에 접근하지 못하도록 게이트를 실제 동작시킨다. 현재 profiles 행이 없는 계정이 게이트를 그냥 통과하는 버그를 수정한다.
## 배경
- 074: profiles.phone, phone_verified 추가(마이그레이션 20260620000001_phone_verification.sql)
- 075: ProtectedRoute/PhoneVerify/App/Layout 게이트 UI 추가
- 트리거 handle_new_user는 추가했으나 "기존 계정"엔 profiles 행이 없어 게이트 통과됨
## 대상 파일 (정확한 경로·라우팅은 Cowork가 확인 후 수정)
- supabase/migrations/20260620000002_backfill_profiles_phone.sql (신규)
- src/components/ProtectedRoute.tsx (게이트 판정 로직 수정)
- src/pages/PhoneVerify.tsx (인증 성공 시 profiles 업데이트 확인)
- 필요 시 App.tsx 라우팅 정합성 점검
## 요구사항
### 1. 백필 마이그레이션(신규 SQL)
- auth.users 중 public.profiles 행이 없는 계정에 profiles 행 INSERT(phone_verified=false)
- 멱등성: INSERT ... ON CONFLICT DO NOTHING 또는 NOT EXISTS
- handle_new_user 트리거가 OAuth(소셜) 최초 로그인에도 발화하는지 점검, 미흡 시 보강
- ★ 이 SQL 실제 실행은 Human이 Supabase SQL 에디터에서 수행 → handoff.md에 "Human 실행 필요" 명시
### 2. ProtectedRoute 게이트 판정(버그 수정)
- 현재 로그인 사용자의 profiles.phone_verified 조회
- 판정:
  - profiles 행 없음(null) → 미인증 간주 → 인증 화면 리다이렉트 (★ 기존 버그 수정 핵심)
  - phone_verified = false → 인증 화면 리다이렉트
  - phone_verified = true → 통과
- 조회 중 로딩 표시, 깜빡임/무한루프 방지
- internal 예외: profiles.role = 'internal' 이면 게이트 우회 (정책 기본값 YES)
### 3. PhoneVerify 성공 처리
- 성공 시 profiles UPDATE: phone=입력값, phone_verified=true → 원래 가려던 경로(또는 홈)로 이동
- ※ 실제 SMS/PASS 본인인증 공급자 연동은 범위 밖. 기존 스텁/검증 방식 유지, 성공 시 profiles 반영만 확실히.
## 정책 기본값(이미 확정, 그대로 구현)
1. 기존 가입자도 다음 로그인 시 휴대폰 인증 강제: YES
2. internal 역할 게이트 우회: YES
→ 둘 다 handoff.md에 "적용됨, Human 사후 확인 가능"으로 기록
## 비범위
- 실제 본인인증 공급자(유료) 연동, 중복 휴대폰번호 1인1계정 강제(별도 태스크)
## 검증
- npx tsc -p tsconfig.app.json --noEmit / npm run lint / npm run build
- 프런트 테스트 통과(기준선 45 tests). ProtectedRoute 변경으로 깨지는 테스트는 범위 내 수정
