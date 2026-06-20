# BOHUMFIT-071-subscription-ui
## 목적
구독 상태·남은 횟수 표시 및 토스 결제 플로우 UI 추가.
## Owner
Cowork (구현) → Codex (검증·커밋)
## 파일 범위
- src/pages/Subscription.tsx (신규)
- src/components/UsageBadge.tsx (신규)
- src/App.tsx (라우트 추가)
- src/pages/Disclosure.tsx (UsageBadge 삽입)
- src/package.json (@tosspayments/tosspayments-sdk)
## Human 작업 (Codex 커밋 후)
- Vercel 환경변수: VITE_TOSS_CLIENT_KEY
## 완료 조건
- UsageBadge가 Disclosure 상단에 표시
- /subscription 페이지 구독 상태 조회 및 결제 버튼 동작
- 토스 SDK 카드 등록 플로우 진입 확인
## 구현 메모
- UsageBadge: 마운트 시 /billing/status 1회, "이번 달 {used} / 30회 사용"·미구독→"구독 필요"(→/subscription)·internal 숨김.
- Subscription: status 로드→구독중(플랜·다음결제일·사용량·해지 안내) / 미구독(플랜카드 9,900·30회 + 구독 시작→토스 SDK 카드등록). result 쿼리 토스트.
- App.tsx /subscription 라우트, Disclosure 결과 상단 <UsageBadge/>.
