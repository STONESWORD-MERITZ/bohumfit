# BOHUMFIT-071-hotfix2-toss-billing-init
## 목적
결제위젯 방식(사업자 신청 필요) → 빌링키 방식(테스트 즉시 가능)으로 토스 초기화 수정.
## Owner
Cowork (구현) → Codex (검증·커밋)
## 파일 범위
- src/pages/Subscription.tsx (수정)
## 완료 조건
- /subscription 페이지에서 "결제 모듈을 불러오지 못했어요" 오류 제거
- "구독 시작" 버튼 클릭 시 토스 카드 등록 페이지로 정상 이동
## 구현 메모
- CDN script src: `https://js.tosspayments.com/v2/standard` → `https://js.tosspayments.com/v1/payment`.
- 초기화: `window.TossPayments(VITE_TOSS_CLIENT_KEY)` (v1 인스턴스).
- 카드 등록(빌링키): `toss.requestBillingAuth('카드', { customerKey: user.id, successUrl, failUrl })` (v1 — 인스턴스 직접 호출·method 문자열 '카드').
- TS 오류 방지: `(window as any).TossPayments` 사용. v2 전용 타입(payment().requestBillingAuth) 제거.
- `setTossReady(true)`는 script.onload 그대로 유지.
