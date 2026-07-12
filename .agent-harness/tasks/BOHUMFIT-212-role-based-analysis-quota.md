# BOHUMFIT-212 Role-Based Analysis Quota

Owner flow: Human -> Codex Windows
Current owner: Codex

## Intent
- `profiles.role = admin` 사용자가 무료 체험 5회 소진으로 분석 차단되는 버그를 수정한다.
- 분석 횟수 정책을 서버 권위로 정리한다: admin 무제한, internal 월 100회, customer/기타 누적 최초 5회.
- 프런트는 서버 `/billing/status` 결과를 표시만 하며, 조작으로 우회할 수 없게 한다.

## Scope
- 수정 허용:
  - `backend/main.py` usage/billing status gate
  - usage gate tests
  - `/billing/status`를 소비하는 프런트 표시 컴포넌트/테스트
  - harness docs
- 수정 금지:
  - `backend/pipeline/`
  - coverage 계산 규칙
  - DB schema/RLS/auth 설정
  - 결제/구독 플로우 본체

## S0 Findings
- `/api/analyze`는 `_enforce_subscription()`으로 분석 전 차단하고 성공 후 `_log_usage()`로 `usage_logs`에 적재한다.
- 현재 role 분기는 `internal`만 월 100회 처리하고, `admin`은 customer/기타 경로로 떨어져 무료 체험 5회 차단을 받을 수 있다.
- 현재 customer 무료 체험은 `_month_bounds()`를 사용해 월별로 집계되어 있다. 사용자 확정 정책은 customer/기타 = 누적 최초 5회(리셋 없음)이므로 누적 집계로 바꿔야 한다.
- `usage_logs`에는 `used_at`가 있고, 월별 집계는 기존 `used_at` range로 가능하다. 누적 집계도 같은 테이블에서 user_id 전체 count로 가능해 DB 스키마 변경은 필요 없다.
- `/billing/status`는 동일하게 `profiles.role`을 조회하지만 `is_internal`만 내려보낸다. admin 표시 분기가 없다.
- `/coverage/analyze`는 인증·IP rate limit만 있고 사용량 게이트/로그가 없다. 사용자 요청의 "고지 analyze·KB analyze" 범위에 맞춰 같은 서버 권위 게이트를 적용한다.

## Work
- role 조회를 `admin/internal/customer`로 정규화하고 서버 게이트에 적용한다.
- admin: 분석 제한 없음, usage 로그 적재하지 않음.
- internal: 이번 달 사용량 < 100이면 허용, 100 도달 시 429. 다음 달은 `used_at` 월 range로 리셋.
- customer/기타: 전체 누적 사용량 < 5이면 허용, 5 도달 시 402. 월 리셋 없음.
- `/billing/status` 응답에 `role`, `is_admin`, `quota_scope`를 추가해 프런트 표시를 단순화한다. 기존 필드는 하위 호환 유지.
- `/api/analyze`와 `/coverage/analyze` 모두 같은 `_enforce_subscription/_log_usage` 흐름을 사용한다.

## Verification
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm test`
- `npm run build`
- `cd backend && python -m pytest -q`
- 신규/수정 usage test: admin 무제한, internal 100/101 및 월 경계 리셋, customer 누적 5/6 차단, coverage analyze gate/log.

## Result
- 완료. `profiles.role` 기준 분석 횟수 게이트를 서버 권위로 분기했다.
- admin: 무제한 허용, usage 로그 미적재.
- internal: `usage_logs.used_at` 월 범위 기준 100회까지 허용, 101회 차단, 다음 달 자동 리셋.
- customer/기타: `usage_logs` 누적 기준 최초 5회까지 허용, 6회 차단, 월 리셋 없음.
- `/billing/status`는 `role`, `is_admin`, `quota_scope`를 내려 프런트가 무제한/월 잔여/누적 잔여를 표시한다.
- `/api/analyze`와 `/coverage/analyze` 모두 같은 서버 권위 게이트와 성공 후 usage logging을 사용한다.

## Verified
- `npx tsc -p tsconfig.app.json --noEmit` — passed.
- `npx tsc -p tsconfig.node.json --noEmit` — passed.
- `npm run lint` — passed.
- `npm test` — `7` files, `25 passed`.
- `npm run build` — passed, 기존 Vite 500kB chunk warning만 발생.
- `cd backend && python -m pytest tests/test_usage_middleware.py -vv` — `19 passed`.
- `cd backend && python -m pytest -q` — `600 passed, 8 skipped`.
