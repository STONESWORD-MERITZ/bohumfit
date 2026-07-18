# BOHUMFIT-225 - 219 강화 SQL 실DB 드리프트 재검증·재작성

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Codex (S1~S3 산출 완료 — 2차 검증·커밋 대기)
Risk tier: 고위험 — 풀 하네스. DB 변경은 Human 게이트(SQL은 Code/Chat 작성, 실행은 Human만).
Date: 2026-07-17

## Intent

- Human이 `BOHUMFIT-219-01-public-view-hardening.sql`을 프로덕션에 실행 시도 → `column r.reconsult_intent does not exist` (42703)로 트랜잭션 롤백(DB 무변경).
- 원인: 219-01~04는 218 감사(2026-07-14) 시점 OpenAPI 메타데이터 기준인데, 실DB가 그 사이 변경(FitHere 측 FITHERE-158~162 추정)되어 드리프트 발생. `reconsult_intent`는 FitHere 측 `reviews` 컬럼으로, BOHUMFIT 저장소 내 근거는 219-01 자신뿐(2026-07-17 grep 실측 — 저장소에 원본 정의 없음).
- 목적: 219-01~04를 실DB **현재 상태** 기준으로 검증·재작성한다. 218의 원칙("실DB가 218 기대와 다르면 즉시 실행하지 말고 차이를 반영" — 218 §7 F-218-05)을 그대로 따른다.

## Scope

- 수정 허용: `supabase/manual/BOHUMFIT-225-*.sql`(신규), Human 실측 확보 후 `supabase/manual/BOHUMFIT-219-01~04-*.sql` 재작성(또는 225 번호의 대체 파일 신설 — 재작성 세션에서 결정·기록), 변경 근거 문서, harness 문서(tasks/handoff/locks).
- 수정 금지: `src/`, `backend/`, `supabase/migrations/`(기존 못박기 2파일 무접촉), 프로덕션 연결·query·apply **0**.
- 보존: 세션 가드(`bohumfit.human_approved`) 및 파일별 독립 트랜잭션 구조, `is_published` 경계(강화 목적 자체) 유지.

## 단계

- **S0 (완료, 이번 세션)**: 실DB 직접 연결 불가 → Human이 실행할 읽기 전용 "현재 상태 확인 쿼리 세트" 산출: `supabase/manual/BOHUMFIT-225-00-current-state-check.sql` (Q1~Q8: 공개 뷰 4개 `pg_get_viewdef`+옵션, 관련 테이블 10개 컬럼 전체, `reconsult_intent` 존재 위치 검색, enum 목록, 함수 5종 정의, 대상 테이블 정책 전체, anon/authenticated grant, RLS 활성화 상태).
- **S1 (Human 실측 후)**: Q1~Q3 결과 기준으로 219-01 재작성 — 존재하는 컬럼만 참조. `reconsult_intent`가 삭제됐으면 `reconsult_intent_rate` 산출을 제거(또는 개명된 컬럼으로 치환), `is_published` 경계는 유지. 컬럼 shape 변경이 FitHere 소비 화면에 미치는 영향은 Human 확인 항목으로 기록.
- **S2**: 219-02(연락처 컬럼 3종·connection_requests 컬럼), 219-03(owner_id/applicant_id/advisor_id/requester_id/user_id 소유자 컬럼·정책명·grant), 219-04(advisors/advisors_public grant)를 같은 실측과 대조, 드리프트 있으면 재작성.
- **S3**: 재작성본 전부에 세션 가드(`bohumfit.human_approved = 'BOHUMFIT-219'` — 유지 여부/225로 갱신 여부는 재작성 시 Chat 확인) 유지, 각 파일 독립 트랜잭션 유지, 정적 검사(lexer/괄호/트랜잭션/가드/secret 패턴).

## Verification

- 이번 세션(S0): 문서·읽기 전용 SQL 신설만 — 코드 diff 0, 프로덕션 연결 0. `git diff` 범위 확인.
- 재작성 세션(S1~S3): SQL 정적 검사 + `npm run build` + backend pytest 618/8 기준선(코드 무변경 확인용) + Codex 2차 검증.
- 실행: Human만. 실행 순서·백업·롤백은 219 태스크 §4·§5 절차를 그대로 따른다.

## S1~S3 산출 (2026-07-17, Human Q1~Q8 실측 반영)

### 파일

| 신규 | 대체 대상 | 내용 |
| --- | --- | --- |
| `supabase/manual/BOHUMFIT-225-01-public-view-hardening.sql` | 219-01 [SUPERSEDED] | 공개 뷰 4개 재작성 — 실측 라이브 정의 기준, `reconsult_intent` 미참조, 전 뷰 `is_published=true` 경계, advisors_public 컬럼 shape 16개 유지 |
| `supabase/manual/BOHUMFIT-225-02-contact-rpc-hardening.sql` | 219-02 [SUPERSEDED] | `get_advisor_contact`에 `is_published` + `has_consult_with_advisor()` 조건 추가, anon EXECUTE 회수, search_path `public, pg_temp` 보강 |
| `supabase/manual/BOHUMFIT-225-03-profiles-select-dedup.sql` | 219-03 [SUPERSEDED] | profiles SELECT 중복 2건 → `profiles_select_own` 1개로 통합(legacy `"본인 프로필 조회"` 제거)만 수행 |
| `supabase/manual/BOHUMFIT-225-04-advisors-base-select-cutover.sql` | 219-04 [SUPERSEDED] | 실질 동일(드리프트 없음 실측) — 가드 키 갱신·드리프트 가드·전후 확인쿼리 보강. ★FitHere `advisors.select('*')`→`advisors_public` 전환 후에만 실행(BLOCKED 유지) |

공통: 세션 가드 `bohumfit.human_approved = 'BOHUMFIT-225'`, 파일별 독립 트랜잭션, idempotent(create or replace / drop if exists), 드리프트 가드 DO 블록(참조 객체·컬럼 부재 시 즉시 실패), 실행 전 검증쿼리·실행 후 확인쿼리·롤백 절차 주석 포함.

### 실측 근거 → 변경 매핑

- **Q3**: `reconsult_intent` 전 스키마 0행 → 42703 원인 확정 → 225-01은 라이브 뷰 컬럼(6개)만 산출, `reconsult_intent_rate` 미포함(라이브에도 원래 없음 — create or replace 호환).
- **Q1**: `advisors_public`=invoker 기적용·published 미필터 → 필터만 추가. `advisor_field_ratings`·`advisor_public_certifications`는 advisors 가시성 필터 자체가 없음(비공개 전문가 집계/자격 노출 실재) → join+published 경계 추가.
- **Q5**: 라이브 `get_advisor_contact`=published·연결기록 조건 없음(F-218-04 미해결 확인), `has_consult_with_advisor` 존재 → 225-02는 219-02의 connection_requests 단독 EXISTS 대신 이 함수 재사용(consult 경로 포함 — 제품 의미는 Human이 219 §7 결정과 함께 확인). proacl상 anon EXECUTE 존재 → 회수.
- **Q5**: `is_admin`·`owns_advisor`·`current_profile_role` **부재** → 219-03은 실행 시 42883 실패 예정이었음 → 전면 정책 교체 폐기.
- **Q6**: 소유자 정책 대부분 이미 `auth.uid()` 스코프 정상(applications=applicant_id, drafts/certs/review_links=advisor_id, analysis_history=canonical 4정책) → 225-03은 profiles SELECT 중복 통합만.

### ★Chat 지시와 다르게 구현한 것 (실측 근거 — Human/Chat 재확인 요청)

1. **집계 뷰 3개 invoker 전환 미적용**: `contact_clicks`는 anon grant 없음(218 §4: 401) → invoker 시 `advisor_review_stats` anon 조회가 permission denied로 실패. `certifications`는 공개 SELECT 정책 없음(Q6) → invoker 시 `advisor_public_certifications` 전원 0행. `reviews` SELECT 정책은 미실측. → FitHere 공개 화면 파손 회피를 위해 3개 뷰는 218 Draft 3·219-01의 "검토된 definer + security_barrier + published 경계 + 고정 컬럼" 설계 유지. invoker 전환 원하면 선행조건(grant·공개 정책 정비) 별도 태스크 필요.
2. **225-03 범위 축소**: "기타 Q6 실측과 219-03 의도 대조해 실제 필요한 것만" 지시에 따라, is_admin 부재+정책 정상 실측으로 profiles 통합 1건만 수행.

### 기록만 (변경 0 — Human 결정 필요)

- `has_consult_with_advisor`의 PUBLIC/anon EXECUTE 잔존(Q5 proacl) — 회수 여부.
- `certifications` 소유자 SELECT 정책 부재(본인 자격을 직접 못 읽음), `connection_requests` requester SELECT 정책 부재, `connection_requests` INSERT check에 `is_published` 미포함.
- drafts/certifications/review_links 정책의 `auth.uid() = advisor_id` 의미: `advisors.id`가 소유자 uid와 동일하다는 전제 — Q2 결과와 FitHere 스키마로 확인 필요(225-01의 `a.id = c.advisor_id` join도 같은 전제).

### 검증 (S1~S3)

- SQL 정적 검사: 파일 4종 모두 `$$` 짝수, 주석 제외 괄호 균형 0, begin/commit 단일 트랜잭션, 가드 'BOHUMFIT-225', secret 패턴 0 — PASS.
- `cd backend && python -m pytest -q`: **618 passed, 8 skipped** (기준선 일치, 코드 무변경 확인).
- `npm run build`: 통과. ★단, 이상 신호 1건 — handoff 참조(dist 산출물 급감·500 kB chunk 경고 소실, src/·config·lockfile은 HEAD 일치).
- 프로덕션 Supabase 연결/query/apply: **0**.

## Next

1. **Codex**: 2차 검증(정적 검사 재실행·diff 범위 확인) → 225 범위 파일만 stage → 커밋·push. ★프런트 빌드 산출물 급감 이상 신호는 Human 확인 전 "새 기준선"으로 기록하지 말 것.
2. **Human**: 저트래픽 창에서 실행 — 순서 **01 → 02 → 03**(각 파일 독립 트랜잭션·개별 실행, 각 단계 후 확인쿼리·회귀 검증). **04는 FitHere `advisors_public` 전환 배포 후에만**. 각 파일 실행 전 `set bohumfit.human_approved = 'BOHUMFIT-225';`.
3. **Human**: 위 "기록만" 3건 + invoker 전환 여부 + 로컬 빌드 이상 신호(.env 상태) 결정·회신.
