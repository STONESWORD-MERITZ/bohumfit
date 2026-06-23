# BOHUMFIT-111: 요금제 페이지 비로그인 접근 허용
## 목표
현재 로그인해야만 볼 수 있는 요금제(/subscription) 페이지를
비로그인 상태에서도 접근 가능하게 변경한다. (결제 버튼 클릭 시에만 로그인 유도)
## 변경 대상
### 라우팅 (src/App.tsx)
- /subscription 경로의 인증 필요(ProtectedRoute) 제거
- 비로그인 시 요금제 카드 노출, 결제 버튼 클릭 시 로그인 페이지로 이동
### src/pages/Subscription.tsx
- 비로그인 상태에서도 플랜 카드 렌더링
- 결제 버튼: 비로그인 시 "로그인 후 구독하기" 텍스트 + 로그인 이동
## 검증
- npx tsc app/node / npm run lint / npm test
## 완료 조건
- 비로그인 상태로 /subscription 직접 접근 시 플랜 카드 노출
- 결제 버튼 클릭 시 로그인 유도
