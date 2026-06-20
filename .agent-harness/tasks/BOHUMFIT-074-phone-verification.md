# BOHUMFIT-074-phone-verification

## 목적
가입 시 휴대폰 본인인증 필수화. 1인 1계정 강제, 어뷰징 방지.
토스페이먼츠 본인인증 API 사용(추후 라이브 키 후 실연동).

## Owner
Cowork (구현) → Codex (검증·커밋)

## 파일 범위
- src/pages/Signup.tsx (본인인증 단계 추가)
- backend/main.py (/auth/verify-phone 스텁)
- supabase/migrations/20260620000001_phone_verification.sql (신규)

## Human 작업
- 토스페이먼츠 본인인증은 별도 계약 필요 → 사업자 승인 후 진행
- 현재는 UI 게이트만 구현, 실제 인증은 추후 연동
- 마이그레이션 Supabase 수동 실행(human-gated)

## 완료 조건
- 회원가입 시 "휴대폰 본인인증" 단계 UI 표시
- 인증 완료 전 가입 불가 (버튼 비활성화)
- profiles에 phone·phone_verified 컬럼 추가
- 현재는 토스 인증 미연동 상태로 UI만(추후 라이브 키 후 실인증)
