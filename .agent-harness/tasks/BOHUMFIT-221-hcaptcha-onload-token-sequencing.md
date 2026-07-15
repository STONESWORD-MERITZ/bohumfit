# BOHUMFIT-221 - hCaptcha onload 시퀀싱 + 토큰 미수신 안전화

Owner flow: Human -> Codex Windows -> Human
Current owner: Human
Date: 2026-07-15

## Intent

- CSP 해소 후 hCaptcha 위젯은 보이지만 API 초기화 전에 `render()`가 호출되어 verify callback이 연결되지 않는 가입 차단을 해소한다.
- hCaptcha 공식 explicit-onload 순서로 단일 script와 단일 widget을 관리하고 token, expire, error 상태를 폼에 정확히 전달한다.
- keyless/load failure/render failure는 기존 인증 흐름으로 진행하되, 정상 위젯이 렌더되어 사용자가 푸는 동안에는 시간만으로 성급히 fail-open하지 않는다.

## Scope

- 수정 허용: `src/components/HCaptcha.tsx`, hCaptcha/auth/CSP frontend tests, harness 문서.
- 보존: 220 `vercel.json` CSP 전체, Kakao/Google OAuth, Login/Signup captcha gate, Supabase captcha token 전달.
- 수정 금지: `backend/`, `backend/pipeline/`, `backend/coverage/`, DB/RLS, 결제, 인증 코어, `PhoneVerify.tsx`와 207~209 휴대폰 인증 영역.
- 사이트키는 `VITE_HCAPTCHA_SITEKEY`, secret은 서버 `HCAPTCHA_SECRET`만 사용하며 값·폴백 키를 커밋하지 않는다.

## S0 Questions

1. 로더가 script load 이벤트와 hCaptcha API onload 중 어느 시점에 resolve하는가.
2. Login/Signup이 token/ready/unavailable 상태를 어떻게 gate와 Supabase options에 연결하는가.
3. 공용 컴포넌트의 expire/error가 token을 지우고 fail-open 여부를 어떻게 전달하는가.
4. script/widget 중복과 하드코딩·폴백 sitekey가 있는가.

## S0 Findings

- 220 로더는 `api.js?render=explicit`의 일반 `load` 이벤트에서 promise를 resolve했다. hCaptcha는 이 시점에 전역 객체가 있어도 SDK 내부 준비가 끝났다고 보장하지 않으며, 운영 콘솔의 `should not render before js api is fully loaded` 경고와 일치했다.
- Login/Signup은 verify token을 React state에 저장하고 Supabase email auth의 `options.captchaToken`으로 전달한다. `onReady`/`onUnavailable`은 captcha gate를 정상/우회 상태로 전환하며 OAuth 함수는 이 gate를 호출하지 않는다.
- 기존 expire는 token만 비우고, error는 auth fail-open으로 연결됐다. render throw/유효하지 않은 widget id는 별도 검증이 없었다.
- 사이트키 출처는 `src/lib/hcaptcha.ts`의 `VITE_HCAPTCHA_SITEKEY` 한 곳뿐이며 하드코딩·폴백 키는 없었다. `@hcaptcha/react-hcaptcha` 의존성도 없으므로 새 패키지 없이 공식 explicit-onload 순서로 공용 로더를 수정했다.

## Completion

- API URL이 `render=explicit&onload=<callback>`을 사용하고 loader는 callback에서만 resolve한다.
- `hcaptcha.render()`는 API onload 뒤 한 번만 호출되며 verify token, expire, error가 각각 폼 상태에 반영된다.
- 정상 render는 대기 타이머를 종료해 사용자의 챌린지를 기다린다. 명시적 load/error/render failure와 API onload 미완료만 auth fail-open한다.
- keyless 가입, Kakao/Google OAuth, PhoneVerify 정책, 220 CSP가 회귀하지 않는다.

## Verification

- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run lint`
- `npm test`
- `npm run build`
- `cd backend && python -m pytest -q` (기준선 618 passed, 8 skipped)
- 브라우저: keyless 로컬 auth 화면, 가능한 경우 실제 sitekey 위젯/token/console smoke.

## Handoff Requirements

- onload 시퀀싱 원인과 수정 경계, token/expire/error/중복 방지 테스트 결과.
- 실제 sitekey 브라우저 검증 가능 여부와 남은 Human 확인.
- `VITE_HCAPTCHA_SITEKEY`와 `HCAPTCHA_SECRET`은 동일 hCaptcha site 쌍이어야 siteverify가 통과함을 명시한다.

## Result

- script URL을 `api.js?render=explicit&onload=__bohumfitHCaptchaOnload`로 변경하고 callback을 script 삽입 전에 등록했다. 일반 script `load` 이벤트는 render를 시작하지 않는다.
- API onload 이후에만 단일 shared promise를 resolve하고, StrictMode 재실행에서도 컴포넌트당 widget을 한 번만 render한다. 실패 script는 제거하고 loader를 초기화해 재시도할 수 있다.
- verify callback은 token과 ready 상태를 폼에 반영한다. expire/error/render throw/유효하지 않은 widget id/API onload timeout은 token을 비우고 auth `onUnavailable`로 fail-open한다.
- 렌더 후 5초마다 `getResponse(widgetId)`를 확인해 verify callback만 누락된 경우 실제 SDK token을 복구한다. 응답이 비어 있다는 이유만으로는 fail-open하지 않아 사용자가 정상 챌린지를 푸는 동안 자동 우회되지 않는다.
- `PhoneVerify.tsx`, Login/Signup 인증 코어, OAuth, 220 CSP, backend/DB는 수정하지 않았다.

## Verification Result

- `npx tsc -p tsconfig.app.json --noEmit`: passed.
- `npx tsc -p tsconfig.node.json --noEmit`: passed.
- `npm run lint`: passed. 최종 수정 파일 scoped lint도 passed.
- `npm test`: **10 files, 44 passed**.
- hCaptcha/CSP/auth target: **3 files, 15 passed**. 일반 load 전 render 0, official onload 후 StrictMode render 1, 환경 sitekey, verify/expire/error, render failure, API timeout, missed-callback token recovery, empty response non-bypass, keyless/OAuth/CSP를 검증한다.
- `npm run build`: passed. 기존 500 kB chunk warning만 발생했다.
- `cd backend && python -m pytest -q`: **618 passed, 8 skipped** (기준선 불변).
- 로컬 keyless `:5175/signup`: hCaptcha script 0, Kakao/Google 활성, console error/warning 0.
- 공식 hCaptcha test sitekey를 프로세스 env로만 주입한 `:5176`: 새 onload URL/ready marker/iframe render, 기존 초기화 경고 0. hCaptcha가 loopback/IP host를 거부해 error-callback→auth fail-open을 확인했으며 test key는 파일에 저장하지 않았다.
- 배포 전 운영 `bohumfit.ai/signup`에서는 220 번들의 기존 URL과 경고를 재현했다. 221 운영 token smoke는 push 후 새 Vercel 배포에서 확인한다.

## Operations Note

- `VITE_HCAPTCHA_SITEKEY`와 server/Supabase의 hCaptcha secret은 동일 hCaptcha site에 속한 쌍이어야 siteverify가 통과한다. 서로 다른 site의 key/secret이면 `sitekey-secret-mismatch`가 발생한다.
