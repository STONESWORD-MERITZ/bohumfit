# BOHUMFIT-072-pricing-plan

## 목적
가격 플랜 변경 및 오픈 이벤트 적용.

## Owner
Cowork (구현) → Codex (검증·커밋)

## 파일 범위
- backend/main.py (플랜 상수·_enforce_subscription·/billing/status·issue-key plan)
- backend/tests/test_usage_middleware.py (체험 로직 반영 갱신)
- src/pages/Subscription.tsx (UI 가격·이벤트·체험 표시)
- src/components/UsageBadge.tsx (체험 횟수 반영)

## 완료 조건
- 베이직 14,900원/30회, 프로 24,900원/100회
- 신규 가입자 체험 5회 무료 (구독 없이도 5회까지 분석 가능)
- 오픈 이벤트: 베이직 첫 3개월 9,900원 표시
- 체험 5회 소진 시 구독 유도 메시지

## 구현 메모
- `PLANS={trial:0/5, basic:14900/30, pro:24900/100}`, `TRIAL_LIMIT=5`.
- `_enforce_subscription`: active 구독→플랜 limit, 미구독→이번 달 usage_logs<5면 trial 통과·≥5면 402("무료 체험 5회…"), internal 무제한.
- `/billing/status`에 `trial_used`/`trial_limit` 추가, `limit`=플랜별(또는 trial 5).
- 체험 usage_logs는 월 경계(period)로 적재 → 매월 5회 freemium.
