# BOHUMFIT-216 - 비밀번호 찾기 SMS 재설정

Owner flow: Human -> Codex Windows
Current owner: Human

## Intent
- 이메일 가입 사용자가 등록 휴대폰으로 SMS 인증코드를 받아 비밀번호를 재설정할 수 있게 한다.
- Kakao/Google 소셜 계정은 비밀번호가 없으므로 해당 OAuth 로그인 버튼 사용을 안내한다.
- 207 OTP와 SMS 발송 코드를 중복하지 않도록 공용 NHN SMS 유틸을 둔다.

## Scope
- 수정 허용:
  - `backend/main.py`
  - `backend/sms_nhn.py`
  - `src/pages/Login.tsx`
  - `src/pages/ForgotPassword.tsx`
  - `src/App.tsx`
  - 관련 테스트와 harness 문서
- 수정 금지:
  - 기존 로그인/OAuth 흐름 변경
  - DB 스키마/RLS/Supabase 대시보드 설정
  - `backend/pipeline/`, `backend/coverage/`, 결제 core
  - NHN/Supabase 키·시크릿 커밋

## Result
- 서버 권위 3단계 플로우 구현: `/auth/password-reset/request`, `/auth/password-reset/verify`, `/auth/password-reset/confirm`.
- 등록 휴대폰(`profiles.phone`)이 `phone_verified=true`인 이메일 계정만 SMS 코드를 받을 수 있다.
- Kakao/Google 등 소셜-only 계정은 SMS 발송 전 OAuth 로그인 안내로 차단한다.
- NHN SMS 환경변수/발신번호 승인이 없으면 실발송하지 않고 명시적인 503 안내를 반환한다.
- OTP와 재설정 토큰은 DB 스키마 추가 없이 서버 메모리 TTL로 관리한다. 운영 다중 인스턴스/재시작 내구성은 NHN/OTP 인프라 확정 시 후속 검토가 필요하다.

## Verification
- `npx tsc -p tsconfig.app.json --noEmit` passed.
- `npx tsc -p tsconfig.node.json --noEmit` passed.
- `npm run lint` passed.
- `npm test` passed: `34 passed`.
- `npm run build` passed, existing Vite chunk warning only.
- `python -m py_compile backend\main.py backend\sms_nhn.py` passed.
- `python -m pytest backend\tests\test_password_reset_216.py -vv` passed: `4 passed`.
- `cd backend && python -m pytest -q` passed: `616 passed, 8 skipped`.

## Notes
- NHN 본인확인/발신번호 승인과 실 키가 없으면 실발송은 동작하지 않는다. 이번 태스크는 흐름·UI·서버 검증 로직까지 구현하고, 실발송은 NHN 모듈/승인 완료 후 연결한다.
- `backend/sms_nhn.py`의 `send_sms` 인터페이스는 207 OTP에서도 재사용하는 공용 유틸이다.
