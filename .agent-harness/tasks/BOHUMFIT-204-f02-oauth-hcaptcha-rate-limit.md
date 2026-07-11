# BOHUMFIT-204 - F-02 OAuth 우선 가입, hCaptcha, 레이트리밋

Owner flow: Human -> Codex Windows
Current owner: Codex

## Intent

- 소셜 로그인 중심의 자연스러운 가입 경로를 제공하고, 인증·휴대폰 인증·분석 요청의 자동화 남용을 줄인다.
- Supabase 대시보드, RLS, 스키마, CAPTCHA 공급자 설정은 Human 영역으로 보존한다.

## Scope

- 수정 허용: 로그인·가입·휴대폰 인증 UI, 공용 hCaptcha 컴포넌트, `backend/main.py`의 hCaptcha 검증 및 레이트리밋, 보안 회귀 테스트, security.txt, harness 기록.
- 수정 금지: `backend/pipeline/`, `backend/coverage/`, Supabase RLS/스키마/대시보드, 결제·인증 핵심 로직, 이메일 가입 제거.
- 기존 보존: `VITE_HCAPTCHA_SITEKEY` 또는 `HCAPTCHA_SECRET`이 없는 환경은 hCaptcha 없이 기존 흐름을 유지한다. 카카오 OAuth는 이메일 제공 여부와 무관하게 진행한다.

## Work

1. 카카오·Google OAuth 버튼을 가입·로그인의 주 경로로 배치하고 이메일 경로는 보조로 유지한다.
2. `VITE_HCAPTCHA_SITEKEY`가 있을 때만 위젯을 렌더하고, Supabase 이메일 로그인·가입에 `captchaToken`을 전달한다. 현재 설치된 Supabase Auth OAuth API는 `captchaToken` 옵션을 제공하지 않으므로 토큰을 URL query로 우회 전달하지 않는다.
3. `HCAPTCHA_SECRET`이 있을 때만 휴대폰 인증 요청의 `X-HCaptcha-Token`을 hCaptcha siteverify로 검증한다.
4. 휴대폰 인증 및 분석 엔드포인트에 IP 한도를 추가해 기존 사용자 단위 한도와 함께 적용한다.
5. 개인 Gmail이 있던 security.txt 연락처는 기존 도메인 별칭 `contact@bohumfit.ai`로 교체한다.

## Verification

- 키 없는 프런트 환경에서 hCaptcha 위젯이 렌더되지 않고 이메일·OAuth 로그인/가입 코드 경로가 유지된다.
- secret 없는 서버는 hCaptcha 헤더 없이 휴대폰 인증 흐름을 유지하고, secret 설정 시 누락·실패 토큰을 거절한다.
- hCaptcha siteverify는 secret을 로그·응답에 노출하지 않는다.
- TypeScript, Vite build, frontend tests, backend pytest, 신규 보안 회귀 테스트를 실행한다.

## Notes

- 사용자 요청의 BOHUMFIT-197 번호는 기존 완료 작업 `BOHUMFIT-197-report-amount-focused-layout`과 충돌한다. 하네스 번호 충돌 방지 규칙에 따라 본 구현은 BOHUMFIT-204로 기록한다.
- 별도 상담 연결 폼은 현재 저장소에 없다. 로그인 후 고객 연락처를 받는 유일한 공개 표면인 휴대폰 인증에 서버 hCaptcha 검증을 적용한다.
- OAuth CAPTCHA 정책은 Supabase 대시보드 설정을 확인해야 한다. 이 작업은 대시보드 설정을 변경하지 않는다.

## Result

- 카카오·Google OAuth를 로그인과 가입의 최상단 경로로 배치하고, 이메일 가입·로그인은 보조 경로로 유지했다.
- `VITE_HCAPTCHA_SITEKEY`가 비어 있으면 위젯·차단 없이 기존 흐름을 유지한다. 키가 있으면 이메일 로그인·가입에 `captchaToken`을 전달하고, 휴대폰 인증에는 `X-HCaptcha-Token`을 보낸다.
- `HCAPTCHA_SECRET`가 설정되면 FastAPI가 hCaptcha siteverify를 호출해 휴대폰 인증 토큰 누락·실패를 차단한다. secret·토큰은 로그나 응답에 노출하지 않는다.
- 기존 사용자별 slowapi 한도를 유지하면서 휴대폰 인증, KB 보장분석, 심평원 분석에 IP 집계 한도를 추가했다.
- `security.txt`의 개인 Gmail을 기존 도메인 별칭 `contact@bohumfit.ai`로 교체했다.

## Verification Result

- `python -m pytest tests/test_f02_hcaptcha_rate_limit_204.py -vv`: `6 passed`.
- `python -m pytest -q`: `572 passed, 8 skipped`.
- `npx tsc -p tsconfig.app.json --noEmit`, `npx tsc -p tsconfig.node.json --noEmit`, `npm test` (`18 passed`), `npm run build`: 통과. 기존 Vite chunk-size/plugin timing warning만 출력.
- 키 없는 Vite 브라우저 스모크: `/login`, `/signup` 렌더 및 `/phone-verify` 비인증 로그인 리다이렉트 유지, hCaptcha 외부 스크립트 미로딩 확인.
- 전체 `npm run lint`는 범위 밖 기존 7 errors(`useCountUp`, `CoverageRemodel`, `Disclosure`, `History`)로 실패했다. 이번 변경 파일만 lint는 통과.

## Human Follow-up

- Vercel에 `VITE_HCAPTCHA_SITEKEY`, Railway에 `HCAPTCHA_SECRET`을 함께 설정해야 서버 검증이 활성화된다. `contact@bohumfit.ai` 수신 별칭도 실제 운영 메일함으로 전달되는지 확인한다.
- 설치된 `@supabase/auth-js` 2.105.1의 `signInWithOAuth`는 `captchaToken` 옵션을 제공하지 않는다. URL query로 우회 전달하지 않았으며, Supabase 대시보드에서 OAuth CAPTCHA 적용 정책은 Human이 확인한다.
