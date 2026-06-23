# BOHUMFIT-103-kakao-session-timeout
## 목표
카카오 로그인 후 로그아웃 시 카카오 브라우저 세션이 남아 재로그인 시 자동 로그인되는 문제 해결
+ 분석 결과 세션 시간제한 및 로컬 상태 초기화 적용
## 배경
- 카카오 OAuth는 카카오 서버 세션(쿠키)을 브라우저에 유지함
- Supabase signOut()만 호출하면 앱 세션은 끊기지만 카카오 세션은 유지됨 → 재로그인 시 동의 화면 없이 자동 로그인
- 분석 결과 화면은 로그인 유지 중에도 새 분석 시 이전 결과가 잔존할 수 있음
## 작업 범위
- src/lib/auth-context.ts 또는 로그아웃 로직이 있는 파일(실제: src/lib/AuthContext.tsx)
- src/pages/Login.tsx (카카오 로그인 버튼)
- Supabase 세션 만료 시간 확인 (코드 변경 불필요, 확인만)
## 수정 지침
### 1. 카카오 세션 강제 만료 (로그아웃 시)
로그아웃 함수에서 Supabase signOut() 호출 후
`https://kauth.kakao.com/oauth/logout?client_id={카카오앱키}&logout_redirect_uri={앱로그아웃URI}` 로 리다이렉트.
- 카카오 앱키·logout_redirect_uri는 환경변수로 관리. 하드코딩 시 env로 이동.
- logout_redirect_uri = https://bohumfit.ai/
- 카카오 개발자 콘솔에 로그아웃 Redirect URI 등록 필요 → handoff Notes 기록.
### 2. 분석 결과 세션 시간제한
- Supabase 세션 자체 만료는 대시보드 설정(코드 아님) → 현재 설정값만 확인해 handoff 기록
- 프론트 비활성 타임아웃(선택): 메모리(변수) 기반 마지막 활동 추적, 30분 비활성 시 자동 signOut. 복잡하면 설계만 handoff.
## 비목표
- 카카오 앱 설정 직접 변경(Human, handoff 안내만) / Supabase 세션 만료 시간 변경(Human)
## 완료 조건
- [x] 로그아웃 시 카카오 세션 만료 URL 리다이렉트 적용
- [x] 환경변수로 카카오 앱키 관리
- [x] tsc 통과
- [x] handoff Notes에 카카오 콘솔 설정 안내 기록
