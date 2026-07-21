# BOHUMFIT-232 — profiles UPDATE 열거식 grant 봉인 (231 (f) 후속)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Codex (1차 검증 완료 — 2차 검증·커밋 대기)
Risk tier: 고위험(DB 권한 변경 동반) — 풀 하네스. git 쓰기 금지(커밋 Codex), 프로덕션 DB 연결·실행 0(SQL 산출만), FITHERE 저장소 읽기 전용.
Date: 2026-07-21

## 배경 (2026-07-20 Human (f) 실측)

`information_schema.role_table_grants` 실측: authenticated에 profiles **테이블 단위 UPDATE 잔존**.
→ 231 컬럼 revoke에도 불구하고 로그인 사용자가 자기 행의 bohumfit_tier·role 포함 전 컬럼 수정 가능
(RLS `profiles_update_own`은 행 범위만 제한). 기존부터 있던 구조 — 열거식 grant로 전환해 봉인한다.

## S0 — 양측 클라이언트 UPDATE 컬럼 전수 실측 (2026-07-21)

- FITHERE 저장소: `C:\Users\18_rk\Desktop\FITHERE` (package.json·AGENTS.md 존재 검증, HEAD `166cabd`). **읽기 전용 준수 — 파일·git 무변경.**

### profiles 쓰기 지점 전수 (양측)

| # | 위치 | 갱신 컬럼 | 경로 | grant 영향 |
| --- | --- | --- | --- | --- |
| B1 | BOHUMFIT `backend/main.py:1004` (verify-phone) | `id`·`phone_verified`·`phone` upsert | **service** (`_get_supabase_admin` = SUPABASE_SERVICE_ROLE_KEY) | 무관 |
| B2 | BOHUMFIT `src/` 전수 | — | 클라이언트 UPDATE/UPSERT **0건** (profiles 접근은 `usePhoneGate.tsx:23` select뿐) | — |
| F1 | FITHERE `src/lib/actions/mutations.ts:116` | 고객 행 upsert(`id`·`role:'customer'`·…) | **service** (`admin` = getSupabaseAdminClient) | 무관 |
| F2 | FITHERE `mutations.ts:1198` (전문가 승인) | `role:'advisor'` update | **service** (`currentAdminOrRedirect`의 admin) | 무관 |
| F3 | FITHERE `mutations.ts:1515` (추방) | `role:'customer'` update | **service** | 무관 |
| F4 | FITHERE `src/lib/actions/account.ts:62` (탈퇴 표식) | `deleted_at` update | **service** (getSupabaseAdminClient) | 무관 |
| F5 | FITHERE `account.ts:116` (복구) | `deleted_at:null` update | **service** | 무관 |

- `getSupabaseAdminClient` = `SUPABASE_SERVICE_ROLE_KEY` 기반(`src/lib/supabase/admin.ts:7-10` 실측).
- FITHERE의 나머지 profiles 접근(middleware·data.ts·admin 페이지 등)은 전부 **select** — UPDATE 아님.
- 프로필 "편집" 동선은 profiles가 아니라 advisors 테이블을 갱신(승인 시 연락처 복사 등) — profiles 클라이언트 편집 부재.

### 컬럼별 요약

| 컬럼 | BOHUMFIT 사용 | FITHERE 사용 | 경로 | 열거 grant 필요 |
| --- | --- | --- | --- | --- |
| phone_verified·phone | ○ (B1) | — | service | ✕ |
| role | — | ○ (F1·F2·F3) | service | ✕ — **클라이언트 사용 없음 → 제외 확정**(스펙 분기) |
| deleted_at | — | ○ (F4·F5) | service | ✕ |
| bohumfit_tier | (게이트 읽기만) | — | — | ✕ — 절대 제외(스펙) |
| 기타 전 컬럼 | 클라이언트 UPDATE 실사용 0건 | 동일 | — | ✕ |

**결론: anon/authenticated 경로의 profiles UPDATE 실사용 = 양측 모두 0건 → 열거식 재grant 컬럼 0개.**
232-01은 테이블 UPDATE 회수만 수행한다(스펙 ②의 열거 grant는 "실측 확정 컬럼만" — 실측 결과 공집합).
role 포함/제외의 [정책 결정 필요] 분기는 "실측상 클라이언트 사용 없음 → 제외 확정"으로 해소되어
변형 제시가 불필요해졌다(향후 클라이언트 편집 신설 시의 열거 grant 형식은 SQL 주석에 명시).

## S1 — SQL 산출

`supabase/manual/BOHUMFIT-232-01-profiles-update-lockdown.sql`:
- ★신규 표준 적용: `set bohumfit.human_approved = 'BOHUMFIT-232';`를 **파일 첫 줄 실행문**으로 포함.
- 단일 트랜잭션·가드·드리프트 가드(profiles 존재 필수 / bohumfit_tier 부재 시 231 순서 경고 notice)·idempotent(revoke no-op 안전).
- `revoke update on public.profiles from anon, authenticated;` — 열거 재grant 0개(실측 근거 주석).
- 실행 전/후 확인쿼리((f) 재실행 0행 기대·column_privileges·타 권한 무접촉 확인), 회귀 체크리스트
  (FitHere 승인/탈퇴·복구, 보험핏 본인인증→분석, PostgREST 직접 UPDATE 401 확인), 롤백 한 줄
  (`grant update on public.profiles to authenticated;` — anon은 원래 UPDATE 무보유라 미포함).

## 검증 체크리스트 (1차 — Code, 2026-07-21 결과)

- [x] S0 실측 표 완성(양측·컬럼·경로 구분·근거 파일:라인)
- [x] SQL 정적 검사: 가드·트랜잭션 짝·set 첫 줄 실행문·열거 컬럼=실측 일치(0개)·bohumfit_tier 미포함·secret 0
- [x] BOHUMFIT 코드 diff 0 (src/·backend/ 무접촉 — SQL·문서만)
- [x] FITHERE 저장소 무변경 — 읽기만 수행, `git status` 청정 증명(아래 검증 로그)
- [x] backend pytest 미실행 사유: 코드 diff 0 (SQL·문서 전용 태스크)

## Stage 목록 (Codex용)

supabase/manual/BOHUMFIT-232-01-*.sql, tasks/BOHUMFIT-232-*.md, handoff.md, locks.md (.env* 제외)

## 커밋 메시지 (Codex용)

docs(BOHUMFIT-232): profiles UPDATE 열거식 grant 봉인 SQL — 양측 클라이언트 실측 기반
