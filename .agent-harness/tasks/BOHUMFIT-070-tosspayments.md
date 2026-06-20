# BOHUMFIT-070-tosspayments
## 목적
토스페이먼츠 자동결제(빌링) 연동.
빌링키 발급·최초결제·웹훅 수신·구독 상태 조회 API 구현.
## Owner
Cowork (구현) → Codex (검증·커밋)
## 파일 범위
- backend/tosspayments.py (신규)
- backend/main.py (엔드포인트 3개 추가)
- backend/tests/test_tosspayments.py (신규)
## Human 작업 (Codex 커밋 후)
- Railway 환경변수: TOSS_CLIENT_KEY, TOSS_SECRET_KEY, TOSS_WEBHOOK_SECRET
- 토스 대시보드 웹훅 URL 등록: https://{api도메인}/billing/webhook
## 완료 조건
- /billing/issue-key, /billing/webhook, /billing/status 정상 응답
- 웹훅 HMAC 시그니처 검증 포함
- 환경변수 없으면 graceful 오류 반환
## 구현 메모
- tosspayments.py: issue_billing_key·charge_billing·verify_webhook_signature(HMAC-SHA256). base=https://api.tosspayments.com/v1, 인증 Basic base64(secret:).
- main.py: /billing/issue-key(빌링키→9,900 최초결제→subscriptions upsert), /billing/webhook(시그니처→status 갱신), /billing/status({status,plan,period_end,used,limit:30,is_internal}).
- 환경변수 미설정 시 503 graceful.
