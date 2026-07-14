# BOHUMFIT-220 - CSP hCaptcha 허용 + 회원가입 fail-open

Owner flow: Human -> Codex Windows -> Human
Current owner: Codex
Date: 2026-07-15

## Intent

- Vercel CSP가 hCaptcha 스크립트와 challenge iframe을 차단해 회원가입이 멈추는 긴급 장애를 해소한다.
- 위젯이 정상 준비되면 토큰 방어를 유지하고, 키 미설정·명시적 로드 실패·조용한 미렌더에서는 기존 이메일 인증 흐름을 사용할 수 있게 한다.
- Kakao/Google OAuth는 hCaptcha 상태와 무관하게 항상 동작하게 유지한다.

## S0

- CSP 정본은 `vercel.json`의 전역 `Content-Security-Policy` 헤더 한 곳이다.
- 기존 `script-src`는 self + TossPayments만 허용해 `https://js.hcaptcha.com/1/api.js?render=explicit`을 차단한다.
- 기존 `frame-src`와 `connect-src`에도 hCaptcha origin이 없다. TossPayments, Supabase, Railway 등 기존 항목은 모두 유지해야 한다.
- `Login.tsx`와 `Signup.tsx`는 `HCaptcha.onUnavailable` 이후에는 token 없이 진행하지만, 공용 로더가 `error` 이벤트 없이 미완료되면 `captchaUnavailable=false`가 계속되어 이메일 경로가 막힌다.
- OAuth 함수는 captcha gate를 호출하지 않아 현재도 독립적이다.

## Scope

- 수정 허용: `vercel.json`, `src/components/HCaptcha.tsx`, hCaptcha/CSP/auth frontend tests, harness 문서.
- 수정 금지: `backend/`, `backend/pipeline/`, `backend/coverage/`, DB/RLS, 결제, 인증 코어, `PhoneVerify.tsx`와 207~209 휴대폰 인증 영역.
- 실 hCaptcha sitekey/secret은 저장하거나 커밋하지 않는다.

## Work

1. CSP `script-src`, `frame-src`, `connect-src`에 hCaptcha 전용 origin만 추가한다.
2. `onUnavailable` 소비자가 있는 위젯은 일정 시간 내 render되지 않으면 fail-open 상태와 안내를 전달한다. 정상 render 시 timer를 해제하고 기존 토큰 요구를 유지한다.
3. 사이트키 없음, script error, silent non-render, 정상 token, Kakao/Google/email 경로를 회귀 테스트한다.

## Verification

- `npx tsc -p tsconfig.app.json --noEmit`: passed.
- `npx tsc -p tsconfig.node.json --noEmit`: passed.
- `npm run lint`: passed.
- `npm test`: **10 files, 41 passed**. CSP 기존 origin 보존/hCaptcha 추가, keyless signup, script error signup, silent non-render fail-open, 정상 token 전달, Kakao/Google 독립 경로를 포함한다.
- `npm run build`: passed. 기존 500 kB chunk warning만 발생했다.
- `cd backend && python -m pytest -q`: **618 passed, 8 skipped** (기준선 불변).
- 로컬 브라우저 `http://127.0.0.1:5175`: 사이트키 미설정 상태에서 hCaptcha script 0, 로그인 Kakao/Google/email 버튼 활성, 가입 Kakao/Google 버튼 활성, console error/warning 0을 확인했다. 가입 제출 버튼은 기존 휴대폰 본인인증 조건 때문에 비활성이며 captcha 차단이 아니다.

## Result

- CSP의 TossPayments, Supabase, Railway, CDN, `style-src 'unsafe-inline'` 항목을 보존하면서 hCaptcha origin만 추가했다.
- `script-src`: `https://js.hcaptcha.com`, `https://*.hcaptcha.com`.
- `frame-src`: `https://newassets.hcaptcha.com`, `https://*.hcaptcha.com`.
- `connect-src`: `https://*.hcaptcha.com`.
- auth 화면에서 사용하는 위젯만 5초 silent non-render를 unavailable로 전환한다. 정상 render 시 timeout을 취소하고 token 요구를 유지하며, keyless/명시적 실패/silent non-render에서는 token 없이 기존 흐름을 사용한다.
- `PhoneVerify.tsx`는 수정하지 않았고 `onUnavailable`을 전달하지 않으므로 207~209 휴대폰 인증 게이트에 timeout fail-open이 적용되지 않는다.
- backend, pipeline, coverage, DB/RLS, 결제, 인증 코어, 실 key/secret 변경은 없다.

## Handoff Requirements

- CSP 기존 항목 보존과 hCaptcha 추가 목록.
- signup keyless/load failure/token/OAuth 및 login 3경로 검증 결과.
- 프로덕션 재배포 후 CSP 콘솔 오류와 실제 위젯 렌더는 Human 확인.
