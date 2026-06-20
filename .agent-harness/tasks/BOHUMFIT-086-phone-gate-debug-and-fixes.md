# BOHUMFIT-086: 폰인증 게이트 미동작 진단·수정 + 로그인 로고 잘림 + Footer 정리
## 증상(Human 실측)
1. 백필 SQL(20260620000002) 실행 완료(Success). 그런데 카카오/구글 소셜 로그인 직후 **휴대폰 인증 화면으로 리다이렉트되지 않고 그냥 통과**된다. 085 ProtectedRoute 수정이 실제로 동작하지 않음.
2. 로그인 화면 상단 큰 로고 "보험핏 BohumFit"가 좌우로 잘려 "Fit 보험핏 BohumF..."로 보임(가로 오버플로/폭 계산 문제).
3. Footer.tsx에 의도된 dirty 변경(면책 문구 한 줄 합치고 overflow-x-auto whitespace-nowrap로 바꾼 것) 존재 — 이건 의도된 변경이므로 커밋 대상에 포함.
## 작업 1: 폰인증 게이트 미동작 — ★먼저 진단, 그 다음 조건부 수정
원인 후보를 코드로 직접 확인하고, 확인된 원인만 고친다. 추측으로 광범위 수정 금지.
점검 항목:
- (a) 소셜 로그인 콜백이 ProtectedRoute를 거치는 경로인지. OAuth redirect 후 도착 라우트가 보호 라우트 밖(예: 콜백 처리 페이지)이라 게이트를 안 거치는지.
- (b) ProtectedRoute의 profiles 조회가 성공하는데도 통과되는지. 특히 "오류 → deploy-safe 통과" 분기가 과도하게 동작해서, profiles 조회 실패(RLS/권한/세션 타이밍)를 오류로 보고 통과시키는지. ← 가장 유력
- (c) phone_verified 컬럼 값이 백필로 false인데도 클라이언트가 못 읽는지(RLS select 정책으로 본인 profiles row를 못 읽으면 조회가 비거나 에러 → deploy-safe 통과).
- (d) 세션 로드 타이밍: user/session이 아직 null인 동안 게이트가 통과 판정해버리는지(로딩 미흡).
- (e) App.tsx에서 로그인 후 도착 라우트가 ProtectedRoute로 감싸여 있는지.
진단 결과를 handoff에 적고, 원인에 맞게 수정한다. 수정 가이드(원인별):
- (b)/(c)가 원인이면: "조회 오류=통과"를 좁힌다. 진짜 스키마 부재(컬럼/테이블 없음)만 deploy-safe 통과로 두고, **행 없음·RLS거부·빈 결과는 미인증으로 처리**해 인증 화면으로 보낸다. RLS로 본인 row를 못 읽는 거면, profiles SELECT 정책(본인 id = auth.uid())이 필요 → 그 경우 SQL 마이그레이션(신규)으로 정책 추가하고 Human 실행 항목으로 남긴다.
- (a)/(e)가 원인이면: OAuth 콜백 후 도착 지점도 게이트를 거치도록 라우팅을 교정한다.
- (d)가 원인이면: 세션·profiles 로딩 끝나기 전에는 통과 판정하지 말고 로딩 상태로 둔다.
검증용: 게이트 판정 단위 테스트(행 없음→미인증, false→미인증, true→통과, internal→우회, 로딩중→미판정)를 추가하거나 보강한다.
## 작업 2: 로그인 화면 큰 로고 잘림
- 대상: 로그인 페이지의 큰 로고 영역(src/pages/Login.tsx 또는 해당 파일)과 Logo.tsx.
- 좌우 잘림 원인(고정폭/음수 마진/whitespace-nowrap+overflow 등) 확인 후, 로고 전체가 보이도록 수정. 모바일·데스크톱 모두 안 잘리게. 083 모바일 로고 수정과 충돌하지 않게.
## 작업 3: Footer 커밋 포함
- Footer.tsx 의도된 변경은 그대로 두고(되돌리지 말 것), 086 변경분과 함께 Codex가 커밋하도록 남긴다.
## 비범위
- 실제 본인인증 공급자 연동, 디자인 전면 개편
## 검증
- npx tsc -p tsconfig.app.json --noEmit / tsconfig.node.json / npm run lint / npm test / cd backend && python -m pytest -q / npm run build(기존 chunk size warning만)
