# BOHUMFIT-097-auth-phone-loop-fix
> ⚠️ 원 요청 파일명은 `BOHUMFIT-095-auth-phone-loop-fix.md`였으나, **095는 윤년 컷오프(commit 85dc30c)에 이미 사용**되어 ID 충돌. 본 태스크를 **097**로 재번호함. 코드/커밋 태그도 097 사용.

## 목표
인증·회원가입 흐름의 버그 3건 수정 + 스펙 변경 1건 적용

## 배경 / 증상
1. [버그] 이미 다른 계정에서 사용된 번호 입력 시 "이미 인증에 사용된 번호" 에러 → 진행 불가
2. [버그] 로그인 상태에서 "무료로 시작하기" → 회원가입 화면으로 이동(/disclosure 아님)
3. [버그] 회원가입 → "이메일 확인" → "로그인으로 돌아가기" → (이메일 미확인 로그인) → 회원가입 루프
4. [스펙] 휴대폰 본인인증: 번호 소유 확인 수준으로 완화(통신사 PASS 미연동), 중복 hard-block 제거

## 작업 범위
- src/App.tsx (라우팅 가드)
- src/pages/Login.tsx (이메일 미확인 안내) — 원 범위엔 미명시였으나 버그3 수정 지점
- backend/main.py (verify-phone 번호 중복 409 제거)
- (검토만·무변경) src/pages/Signup.tsx, src/pages/PhoneVerify.tsx, src/lib/auth-context.ts

## ⚠️ Cowork 진단(2026-06-22) — 태스크 가설과 코드 현황 차이
- **OTP 흐름 없음.** `/api/phone-request`·OTP 입력창·`phone_verifications` 테이블 **미존재**.
  실제 폰 인증은 `/auth/verify-phone`(085/088) 1개뿐 — 번호 입력 → `profiles.phone_verified=true` upsert.
  Signup.tsx의 폰 인증은 **순수 클라이언트 스텁**(백엔드 호출·중복검사·OTP 없음).
- 버그1의 "이미 인증에 사용된 번호" 409는 **로그인 후 게이트 `PhoneVerify.tsx` → `/auth/verify-phone`(088)** 에서 발생(가입화면 아님). → 백엔드 409 제거로 해소.
- 버그2: `Home.tsx`의 "무료로 시작하기" → `/signup`. 로그인 상태 가드 부재. → App.tsx에 가드 추가(Home은 범위 밖이라 미수정).
- 버그3: `Login.tsx`는 `setError(error.message)`만 — /register로 보내는 코드 루프는 없음. 'Email not confirmed' 원문 노출로 사용자가 재가입 반복(UX 루프). → 친절 안내 메시지로 해소.

## 완료 조건
- [ ] 로그인 상태 + /login·/signup 접근 → /disclosure 리다이렉트
- [ ] 이메일 미확인 로그인 → 한국어 안내(루프 없음)
- [ ] 번호 중복 409 제거 → 인증 진행 가능
- [ ] tsc 타입 오류 없음, handoff 기록

## 비목표
- 실제 통신사 PASS/OTP(SMS) 연동(별도 태스크 — 인프라 필요)
- Supabase 마이그레이션 직접 실행(필요 SQL은 handoff 기록)
- 이메일 인증 우회/제거
