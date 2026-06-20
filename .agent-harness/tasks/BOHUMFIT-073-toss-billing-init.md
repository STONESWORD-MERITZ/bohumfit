# BOHUMFIT-073-toss-billing-init

## 목적
결제위젯 방식 → 빌링키 방식으로 토스 초기화 수정.
사업자 등록 완료 후 라이브 키 교체만 하면 즉시 결제 가능한 상태로 준비.

## Owner
Cowork (구현) → Codex (검증·커밋)

## 파일 범위
- src/pages/Subscription.tsx (토스 SDK 초기화 방식 + plan 파라미터)

## 완료 조건
- "결제 모듈을 불러오지 못했어요" 오류 제거
- "구독 시작" 버튼 클릭 시 토스 카드 등록 페이지로 정상 이동
- 라이브 키 교체 시 실결제 가능한 구조

## 구현 메모
- CDN `https://js.tosspayments.com/v1/payment`(071-hotfix2에서 이미 적용).
- `handleSubscribe(plan)`: `(window as any).TossPayments(VITE_TOSS_CLIENT_KEY).requestBillingAuth('카드',{customerKey:user.id, successUrl:.../subscription?result=success&plan=${plan}, failUrl})`.
- 베이직/프로 버튼에 plan 전달, success 리다이렉트 시 `/billing/issue-key`에 plan 함께 전송.
- ※ 071-hotfix2(v1 init)와 동일 파일 — 누적 작업.
