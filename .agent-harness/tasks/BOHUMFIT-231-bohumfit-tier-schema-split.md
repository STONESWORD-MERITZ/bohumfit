# BOHUMFIT-231 — 보험핏 등급을 profiles.bohumfit_tier로 분리 (role은 FitHere 전용화)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Codex (1차 검증 완료 — 2차 검증·커밋 대기)
Risk tier: 고위험(DB 스키마 동반) — 풀 하네스. git 쓰기 금지(커밋 Codex), 프로덕션 DB 연결·실행 0(SQL 파일 산출만, 실행은 Human).
Date: 2026-07-20

## 배경 (2026-07-20 Human 실측 확정)

profiles.role을 두 서비스가 다른 의미로 공유: 보험핏=분석 한도 등급, FitHere=전문가 신분(advisor).
내근직이 FitHere 전문가 등록 시 role이 advisor로 전환 → 212 게이트 미인식 → 5회 제한 오적용
(hssong302984 사례 확정, 유사 2명 추정). 결정: 스키마 분리(정석안).

## 목적

보험핏 분석 등급을 신규 컬럼 bohumfit_tier로 이관해 role과 완전 독립. FitHere는 무변경·무영향(추가 전용 설계).

## 수정 금지 (준수 확인)

- profiles.role 컬럼·값·enum 무접촉 ✓ (게이트 읽기 지점 교체만 — 그 외 role 사용처는 아래 목록화)
- supabase/migrations/ 미사용 ✓ (manual 전용)
- backend/pipeline/·backend/coverage/·src/ 무접촉 ✓
- 프로덕션 DB 연결·쿼리·적용 0 ✓

## S0 — 실측 (2026-07-20)

### backend에서 profiles.role 읽는 지점 전수

| 파일:라인 | 용도 | 이번 조치 |
| --- | --- | --- |
| main.py:679-680 (구 라인 기준) `_enforce_subscription._check` | ★212 분석 한도 게이트 — `select("role")` 후 admin/internal/customer 판정 | ✅ `bohumfit_tier` 읽기로 교체 |
| main.py:919-920 `/billing/status._query` | ★212 사용량 표시(게이트와 동일 판정 공유) | ✅ `bohumfit_tier` 읽기로 교체(표시·게이트 불일치 방지) |
| main.py:1237-1242 `_history_is_internal` | 156/171 히스토리 저장 한도의 internal 무제한 | ❌ 목록화만 — 동일 오적용 가능성 있음, 후속 태스크 재료 |
| (참고) `SUPABASE_SERVICE_ROLE_KEY`·coverage `ROLE_MARKERS` | 무관(서비스 키/PDF 페이지 분류) | 무접촉 |

### 212 게이트 현재 정책(무변경 확인)

admin=무제한·비차감 / internal=월 100회(`PLANS["pro"].limit`, `_month_bounds` UTC 월창) /
활성 구독=플랜 한도(basic 30·pro 100) / 미구독 customer/기타=누적 5회(402) — 한도 값·순서 무변경, 판정 원천만 교체.

### src/ role 기반 분기 (목록화만 — 수정 0)

| 파일:라인 | 용도 | 비고 |
| --- | --- | --- |
| `src/lib/phoneGate.ts:33` + `usePhoneGate.tsx:24` | ★phone gate가 `role === "internal"`이면 본인인증 우회 | 내근직 role→advisor 전환 시 우회 소실(동일 계열 충돌) — 후속 태스크 재료 |
| Dashboard/UsageBadge/Subscription | billing/status의 `is_admin`/`is_internal`/`quota_scope`만 소비 — 원시 `role` 필드 미사용 실측 | 백엔드 이관만으로 표시 정합 — 프런트 무수정 |

## S1 — SQL 산출

`supabase/manual/BOHUMFIT-231-01-add-bohumfit-tier.sql`: 세션 가드 'BOHUMFIT-231'·단일 트랜잭션·idempotent·드리프트 가드,
① 컬럼 신설(text not null default 'customer' + named check) ② role 기준 백필 — **컬럼 신설 시에만 1회 실행**(DO 블록에서
기존재 감지 시 백필 skip → 재실행이 운영 중 강등된 tier를 되돌리지 않음) ③ `revoke update (bohumfit_tier)` 컬럼 봉인
④ 실행 전/후 확인쿼리(분포·role×tier 크로스탭·column_privileges·★테이블 단위 UPDATE grant 잔존 확인)·롤백 절차
⑤ 파일 머리 배포 순서(SQL→확인→코드 push, 역순 시 fail-closed 동작 명시).

★스펙과 다른 명시 1건: "revoke update (컬럼)은 owner UPDATE 정책이 있어도 차단됨" 전제는 PostgreSQL 의미론과 다름 —
컬럼 revoke는 컬럼 단위 grant만 회수하며, **테이블 단위 UPDATE grant가 잔존하면 여전히 수정 가능**(RLS는 행 범위만 제한).
SQL에 (f) 확인쿼리와 "[봉인 한계]" 절을 넣어 Human이 잔존 여부를 확인하고, 잔존 시 열거식 컬럼 grant 후속(양쪽 앱
UPDATE 컬럼 실측 선행 필요)을 결정하도록 했다.

## S2 — 백엔드 게이트 이관

- `_normalize_profile_role` → `_normalize_bohumfit_tier`(null·미지값 → customer, fail-closed).
- `_enforce_subscription`·`/billing/status` 둘 다 `select("bohumfit_tier")`로 교체. 한도 정책 값 무변경.
- 구DB(컬럼 부재)에서는 조회 예외 → customer 폴백 — 코드 선배포 안전망(테스트로 보증).
- `/billing/status` 응답의 `role` 키는 하위호환으로 유지하되 값은 tier(프런트 원시 role 미사용 실측 — 키 개명은 후속).
- 테스트: 기존 212 테스트 19건을 tier 픽스처로 갱신 + 신규 5건(advisor role+tier=internal 월100 게이트/표시,
  tier 미지값→customer, 컬럼 부재 예외→customer fail-closed, advisor role+tier=admin 무제한·비차감).

## S3 — 운영 절차 표준 (향후 직원 승격/강등)

**role 갱신 절차는 폐기한다.** 보험핏 등급 변경은 bohumfit_tier만 갱신한다(FitHere 신분과 완전 독립).

```sql
-- 승격/강등 표준(SQL Editor, Human 전용). 이메일로 대상 특정 → tier만 갱신.
update public.profiles p
   set bohumfit_tier = 'internal'          -- 'admin' | 'internal' | 'customer'
  from auth.users u
 where u.id = p.id
   and u.email = '대상@이메일';
-- 확인:
-- select u.email, p.role, p.bohumfit_tier from public.profiles p
--   join auth.users u on u.id = p.id where u.email = '대상@이메일';
```

빠진 내근직 2명(Human 특정 예정) 지정 템플릿:

```sql
update public.profiles p
   set bohumfit_tier = 'internal'
  from auth.users u
 where u.id = p.id
   and u.email in ('직원1@이메일', '직원2@이메일');   -- Human이 실제 이메일로 교체
-- 실행 후: select u.email, p.role, p.bohumfit_tier from public.profiles p
--   join auth.users u on u.id = p.id where u.email in ('직원1@이메일', '직원2@이메일');
```

(hssong302984는 백필 시 role이 이미 advisor라 customer로 초기화됨 — 위 템플릿으로 internal 지정 필요.)

## 검증 체크리스트 (1차 — Code 직접 실행, 2026-07-20 결과)

- [x] SQL 정적 검사: `$$` 4(짝)·`$ddl$` 2(짝)·주석 제외 괄호 균형 0·commit 종결·가드 'BOHUMFIT-231'·secret 패턴 0 — PASS
- [x] backend pytest — **623 passed, 8 skipped** (기준선 618 + 신규 5, 기존 무손실. 게이트 테스트 24 passed = 기존 19 tier 픽스처 갱신 + 신규 5)
- [x] 게이트 코드가 로컬 DB 없이 테스트로 검증 — 기존 212 가짜 Supabase admin 주입 패턴 동일 사용
- [x] git diff 범위 = backend/main.py + tests/test_usage_middleware.py + supabase/manual/231-01 + harness 문서만. `git diff --check` 통과
- [x] 프런트 무접촉 — src/ diff 0. 구 함수명(`_normalize_profile_role`) 잔재 0
- 프로덕션 DB 연결·쿼리·적용: **0**

## Stage 목록 (Codex용 — Code 실행 금지)

backend/main.py, backend/tests/test_usage_middleware.py, supabase/manual/BOHUMFIT-231-01-add-bohumfit-tier.sql,
tasks/BOHUMFIT-231-*.md, handoff.md, locks.md (.env*·실 PDF 제외)

## 커밋 메시지 (Codex용)

feat(BOHUMFIT-231): 보험핏 등급 bohumfit_tier 분리 — role 공유 충돌 해소(212 게이트 이관)
