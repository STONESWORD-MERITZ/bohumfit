# BOHUMFIT-233 — 관리자 tier 관리 화면 (직원 승격/강등 SQL 운영 졸업)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Codex (1차 검증 완료 — 2차 검증·커밋 대기)
Risk tier: 중위험 — 풀 하네스. git 쓰기 금지(커밋 Codex), 프로덕션 DB 연결·실행 0.
Date: 2026-07-21

## 배경

231로 bohumfit_tier 분리, 232로 클라이언트 UPDATE 전면 봉인 완료. tier 변경은 service role 경유
백엔드만 가능 — 관리자 화면에서 admin이 직접 관리하게 한다(2026-07-20 Human 요구).

## 목적

admin(bohumfit_tier='admin')만 쓸 수 있는 직원 관리 UI: 이메일로 조회 → internal 지정/해제.

## 수정 금지 (준수)

- backend/pipeline/·backend/coverage/·supabase/(DB 변경 없음) 무접촉
- 212 게이트 판정 로직 무변경(tier 읽는 쪽 그대로 — 쓰는 API만 신설)
- 인증 코어·profiles 외 테이블 무접촉

## S0 — 실측 (2026-07-21)

- service role profiles 갱신 기존 패턴: `main.py:1004` `admin.table("profiles").upsert(patch, on_conflict="id")` — 233 set API가 동일 패턴 재사용(`{"id", "bohumfit_tier"}`만 upsert — role 등 타 컬럼 무접촉).
- 요청자 tier 취득: 231 게이트와 동일 — `select("bohumfit_tier")` + `_normalize_bohumfit_tier`(fail-closed customer → 비admin 403).
- auth.users 이메일 접근: SQL JOIN은 PostgREST 불가 → supabase-py admin API(`auth.admin.list_users` 페이지네이션 / `get_user_by_id`)로 대체(서비스 롤 전용·PII는 이메일만).
- 대시보드(163): `Widget` 셸 + `isAdmin = billing.is_admin || quota_scope==='unlimited'` 분기 기존재 → admin 전용 섹션은 이 분기 재사용. 위젯별 독립 fetch·graceful 격리 관례 준수.
- "지정일" 표시는 제외: profiles에 tier 지정 시각 컬럼이 없고(231-01은 컬럼 1개만 추가) 스키마 확장은 범위 밖 — email·tier만 반환(PII 최소화 정합).

## S1~S3 구현 요지

- `GET /admin/tier/list`: 요청자 admin 검증(403) → profiles에서 tier ∈ {admin, internal} 조회 → 각 id의 이메일을 auth admin API로 해석(실패 시 "(이메일 확인 불가)") → admin 우선·이메일 순 정렬 반환. 반환 필드 = email·tier만.
- `POST /admin/tier/set` {email, tier}: tier ∈ {'internal','customer'}만 허용(★'admin' 지정은 422 — admin 추가는 SQL 유지, API 권한 상승 오남용 방지). 대상은 auth.users 이메일 lower 매칭(프로필 email NULL 안전). 미가입 404. 자기 자신 변경 400(마지막 admin 잠금 사고 방지). service role upsert(232 봉인과 무충돌).
- 프런트: `src/components/AdminTierSection.tsx` 신규(목록·이메일 입력·지정/해제·피드백, 404 시 "가입 이력 없음 — 가입 후 다시 시도" 안내) + Dashboard에 admin 분기 1블록 추가(FIT 토큰 준수).
- 테스트: backend `tests/test_admin_tier_233.py`(admin 200/비admin 403/미가입 404/admin 지정 422/자기 자신 400/지정·해제 왕복/이메일 형식 422) + 프런트 `AdminTierSection.test.tsx`·Dashboard admin 분기 렌더/비노출.

## 검증 체크리스트 (1차 — Code, 2026-07-21 결과)

- [x] backend pytest — **632 passed, 8 skipped** (기준선 623 + 신규 9: 233 테스트 9건, 기존 무손실. 게이트+233 합산 33 passed)
- [x] tsc app/node · lint 통과 · npm test **73 passed**(68 + 신규 5) · build 통과(청크 343.22 kB — 기록만)
- [x] git diff 범위 = backend/main.py + tests/test_admin_tier_233.py + src(AdminTierSection·test, Dashboard) + harness만. `git diff --check` 통과
- [x] grep: 구브랜드 색상 0 · SURIT 0 · 면 전용 색상 텍스트 사용 0

## 이상 신호 1건 — 복구 완료 (환경, 코드 무관)

- 최초 pytest에서 전 테스트 ImportError: `charset_normalizer`의 mypyc 네이티브 모듈(.pyd)이 Windows
  애플리케이션 제어 정책(Smart App Control류 추정)에 차단 — 231 턴까지 정상이었고 다른 네이티브 모듈
  (pandas·PIL·pydantic_core)은 정상 로드라 해당 파일 1개 대상 오탐으로 특정.
- 동일 버전 바이너리 재설치 무효 → **동일 버전 3.4.9의 소스 빌드(`--no-binary`, 순수 파이썬)로 교체**해
  해소. requirements 무변경(전이 의존성·버전 동일), 로컬 환경만 복구. Codex 2차 검증 시 같은 증상이면
  동일 절차 적용.

## 스펙 보강 1건 (기록)

- 대상이 admin인 계정의 강등도 API로 거부(400) — 자기 자신 거부와 같은 취지의 상호 강등·마지막 admin
  잠금 사고 방지. admin 등급의 모든 변경(추가·강등)은 SQL 절차로 일원화.

## Stage 목록 (Codex용)

backend/main.py, backend/tests/test_admin_tier_233.py, src/components/AdminTierSection.tsx(+test), src/pages/Dashboard.tsx, tasks/BOHUMFIT-233-*.md, handoff.md, locks.md

## 커밋 메시지 (Codex용)

feat(BOHUMFIT-233): 관리자 tier 관리 화면 — internal 지정/해제 API + 대시보드 섹션
