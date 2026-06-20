# BOHUMFIT-069-usage-middleware
## 목적
/analyze API 호출 성공 시 월 30회 한도 체크·차감.
내부 사용자(profiles.role = 'internal')는 무제한 허용.
## Owner
Cowork (구현) → Codex (검증·커밋)
## 파일 범위
- backend/main.py (수정)
- backend/requirements.txt (supabase 추가)
- backend/tests/test_usage_middleware.py (신규)
## 완료 조건
- 30회 초과 시 429 반환
- 구독 없으면 402 반환
- internal 사용자 정상 통과
## 구현 메모
- `_get_supabase_admin()` 지연 초기화(서비스롤 키·supabase 패키지 없으면 None → 게이트 비활성·기존 무료 동작 유지, graceful).
- `_enforce_subscription(user_id)` → {is_internal, period_start, period_end, enabled}. 위반 시 402/429.
- `/analyze`: verify_jwt 직후 enforce, run_analysis 성공 후 `_log_usage`(internal·비활성 시 skip).
- 068 스키마(subscriptions/usage_logs/profiles.role) 의존 — Human Supabase 실행 후 활성.
## 검증
- test_usage_middleware: supabase admin mock으로 30회→429·internal 무제한·inactive→402, 패키지/env 없으면 skip.
