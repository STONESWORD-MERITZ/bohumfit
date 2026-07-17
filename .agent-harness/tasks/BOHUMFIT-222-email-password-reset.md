# BOHUMFIT-222 - 비밀번호 재설정 이메일 링크 경로 추가
Owner flow: Human -> Codex Windows
Current owner: Human

## Intent
- NHN SMS 심사 대기로 BOHUMFIT-216 SMS 비밀번호 찾기가 실사용 불가한 동안, 이메일 링크 기반 비밀번호 재설정을 주 경로로 제공한다.
- 기존 216 SMS 구현은 제거하지 않고 유지하며, NHN 승인 후 별도 환경 플래그로 다시 노출할 수 있게 한다.
- 계정 존재 여부를 화면에서 구분하지 않도록 동일한 완료 안내를 사용한다.

## Scope
- 수정 허용:
  - `src/pages/ForgotPassword.tsx`
  - `src/pages/ForgotPassword.test.tsx`
  - `src/pages/ResetPassword.tsx`
  - `src/pages/ResetPassword.test.tsx`
  - `src/App.tsx`
  - `src/vite-env.d.ts`
  - harness 문서
- 수정 금지:
  - BOHUMFIT-216 SMS 서버 유틸 제거 또는 동작 변경
  - `PhoneVerify.tsx`, 207~209 휴대폰 인증 영역
  - backend/pipeline, backend/coverage, DB/RLS, 인증 코어 정책
  - hCaptcha 220/221 로더·CSP 회귀

## Work
- `/forgot-password` 기본 화면을 이메일 입력 기반 `supabase.auth.resetPasswordForEmail` 플로우로 바꾼다.
- `redirectTo`는 `${window.location.origin}/reset-password`로 지정한다.
- 성공 안내는 계정 존재 여부와 무관하게 동일하게 표시한다.
- SMS 경로는 `VITE_ENABLE_SMS_PASSWORD_RESET=true`일 때만 노출한다.
- `/reset-password` 페이지를 추가해 recovery 세션 확인 후 `supabase.auth.updateUser({ password })`로 새 비밀번호를 저장한다.
- recovery 세션 없이 직접 접근하거나 링크가 만료된 경우 재요청 경로를 안내한다.

## Verification
- `npx tsc -p tsconfig.app.json --noEmit` - passed.
- `npx tsc -p tsconfig.node.json --noEmit` - passed.
- `npm run lint` - passed.
- `npm test` - passed: 11 files, 50 passed.
- `npm run build` - passed; existing chunk-size warning only.
- `cd backend && python -m pytest -q` - passed: 618 passed, 8 skipped.
- Local browser smoke on `http://127.0.0.1:5177` - `/forgot-password`, `/reset-password`, `/login`, `/signup` rendered with console warning/error 0.
- After adding `VITE_ENABLE_SMS_PASSWORD_RESET` to `src/vite-env.d.ts`, app tsc and targeted password-reset tests were rerun and passed.

## Notes
- 실제 이메일 발송은 Supabase Auth SMTP 설정에 의존한다. SMTP가 미설정이면 앱 코드는 정상이어도 사용자가 메일을 받지 못할 수 있다.
- SMS reset remains implemented from BOHUMFIT-216 and is shown only when `VITE_ENABLE_SMS_PASSWORD_RESET=true`.
