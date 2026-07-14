# BOHUMFIT-219 - 공유 Supabase 드리프트 마이그레이션 정합

Owner flow: Human -> Codex Windows -> Human
Current owner: Human
Date: 2026-07-14
Type: 마이그레이션/문서만, 프로덕션 적용 0

## 1. 목적과 S0 근거

BOHUMFIT-218 감사에서 확인한 공유 Supabase의 실DB/저장소 드리프트를 재현 가능한 SQL로 남긴다. 이 태스크에서는 프로덕션 Supabase에 연결하거나 SQL을 적용하지 않았다. 기준은 218이 이미 확보한 읽기 전용 OpenAPI 메타데이터와 BOHUMFIT/FitHere 저장소 마이그레이션뿐이다.

핵심 안전 결정은 다음과 같다.

1. 현재 실DB 동작을 코드로 못박는 `bohumfit_analysis_history` 생성/RLS만 자동 마이그레이션 경로에 둔다.
2. 공개 뷰, 연락처 RPC, 소유자 정책, grant 회수처럼 동작이 달라지는 SQL은 `supabase/manual/`에 격리한다. Supabase CLI의 자동 마이그레이션 대상이 아니다.
3. 모든 Human 전용 SQL은 `bohumfit.human_approved = 'BOHUMFIT-219'` 세션 설정이 없으면 즉시 실패한다.
4. 공유 DB이므로 강화안은 BOHUMFIT만 보고 실행하지 않는다. 저트래픽, schema/policy/view 백업, FitHere 회귀 검증이 선행 조건이다.

## 2. 파일별 분류

| 파일 | 218 finding | 분류 | 예상 영향 |
| --- | --- | --- | --- |
| `supabase/migrations/20260714000100_bohumfit219_analysis_history_rls_pin.sql` | F-218-01 | 못박기, 자동 경로 | 2026-07-14 실DB에는 테이블과 동일 owner RLS가 있으므로 동작 무변경. 새 로컬 환경에는 테이블/RLS 재현 |
| `supabase/manual/BOHUMFIT-219-01-public-view-hardening.sql` | F-218-03 | 강화, Human 승인 | 공개 뷰 4개를 published 경계로 제한. 비공개 전문가 집계/자격이 사라짐 |
| `supabase/manual/BOHUMFIT-219-02-contact-rpc-hardening.sql` | F-218-04 | 강화, Human 승인 | published + 현재 사용자 연결 기록이 있는 경우만 연락처 반환 |
| `supabase/manual/BOHUMFIT-219-03-owner-policy-hardening.sql` | F-218-01/05/06/07 | 강화, Human 승인 | 실제 `owner_id`, `applicant_id`, `advisor_id` 기준으로 정책 교체; history/review_links server-only; profiles SELECT 통합 |
| `supabase/manual/BOHUMFIT-219-04-advisors-base-select-cutover.sql` | F-218-02 | 강화, 선행 코드 필요 | 기본 `advisors` SELECT 회수. FitHere가 `advisors_public`으로 전환된 뒤에만 실행 |

### 못박기 파일의 무변경 전제

`20260714000100...pin.sql`은 218 감사 기준의 실DB에 테이블과 owner policy가 이미 있다는 전제에서 동작 무변경이다. 다른 환경에서 테이블이 없으면 새로 만들고, canonical policy 이름이 없을 때만 owner 식을 추가한다. 같은 이름의 기존 정책, 다른 이름의 정책, grant는 건드리지 않으므로 이 파일만으로 느슨한 permissive 정책을 제거하지는 않는다. Human은 적용 전 `pg_policies`와 grant를 반드시 비교한다.

## 3. 드리프트 정합 내용

- 히스토리: `id`, `user_id`, `label`, `mode`, `result`, `created_at`, `track`과 `user_id = auth.uid()` SELECT/INSERT/UPDATE/DELETE 정책을 원본 SQL로 추가했다. grant는 현행을 바꾸지 않도록 못박기 파일에서 변경하지 않는다.
- 전문가 소유자: 과거 `advisors.profile_id` 대신 실DB `advisors.owner_id`를 `owns_advisor(uuid)`의 유일 기준으로 사용한다.
- 신청 소유자: 과거 `advisor_applications.profile_id` 대신 `applicant_id`를 사용한다.
- draft/자격: 삭제된 `profile_id`, `status`, `masking_confirmed` 전제를 제거하고 `advisor_id -> advisors.owner_id`로 제한한다.
- 후기 링크: 실DB에 없는 `created_by`, `status`, `review_id` 전제를 제거하고 현재 서버 전용 경계로 정리한다.
- 공개 뷰: `is_active AND is_verified AND is_published`를 명시한다. 원천 RLS 때문에 지표가 0이 되는 것을 피하려고 집계/자격 뷰는 검토된 definer + 제한 출력 컬럼을 유지한다.
- profiles: 중복 permissive SELECT 정책을 self/admin 하나로 통합한다. INSERT/UPDATE 정책과 role 변경 트리거는 건드리지 않는다.

## 4. Human 실행 순서

1. 저트래픽 변경 창을 BOHUMFIT/Railway와 FitHere/Vercel 담당자에게 공유한다.
2. Supabase Dashboard에서 schema-only 백업을 만들고 218 문서 6절 A~I를 실행해 테이블 컬럼, RLS, 모든 policy qual/check, grants, `pg_get_viewdef`, 함수 정의/ACL을 별도 보안 저장소에 보관한다. 정책 결과와 UUID는 이 저장소에 커밋하지 않는다.
3. 일반 사용자 A/B, advisor A/B, admin 운영 테스트 계정을 준비한다. 실제 고객 행을 사용하지 않는다.
4. 자동 경로의 히스토리 못박기 파일을 먼저 별도 transaction으로 적용한다. BOHUMFIT 히스토리 저장/목록/재열람/삭제와 A가 B 행을 읽지 못함을 확인한다.
5. `219-01` 공개 뷰 강화안을 실행한다. 익명 공개 목록/상세/평점/분야/자격의 컬럼 shape가 유지되고 `is_published=false` 전문가가 네 뷰 모두 0행인지 확인한다.
6. “연결 성사”를 `connection_requests` 행으로 보는 제품 의미와 생성 순서를 확인한 뒤 `219-02`를 실행한다. 연결 전 0행, 본인 연결 후 연락처 1행, 타인 연결 기록 재사용 불가를 확인한다.
7. 실제 정책 전체를 다시 대조한 뒤 `219-03`을 실행한다. advisor A가 B의 draft/certification을 읽거나 쓰지 못하고, applicant A가 B 신청을 못 보며, admin 흐름은 유지되는지 확인한다. review link 서버 액션과 BOHUMFIT history도 확인한다.
8. FitHere의 공개 조회가 기본 `advisors.select('*')`를 사용하지 않도록 코드 전환/배포한 뒤에만 `219-04`를 실행한다. 현재 코드를 그대로 둔 상태에서는 실행 금지다.
9. 각 단계 직후 BOHUMFIT 로그인/phone gate/billing/분석/history와 FitHere 공개 목록/상세/연결/신청/workspace/admin/review link를 회귀 검증한다. 한쪽 앱만 정상인 상태로 변경 창을 종료하지 않는다.

Human 전용 파일 실행 전 같은 SQL Editor 세션에서 다음을 먼저 실행한다.

```sql
set bohumfit.human_approved = 'BOHUMFIT-219';
```

각 파일은 독립 transaction이다. 여러 파일을 한 번에 실행하지 않는다.

## 5. 롤백

1. 오류가 난 파일의 transaction이 열려 있으면 즉시 `rollback`한다.
2. 이미 commit했다면 2단계에서 백업한 `pg_get_viewdef`, 함수 정의, policy qual/check, grants를 사용해 해당 파일 하나만 역순 복원한다.
3. 공개 뷰 문제는 기존 135/146 정의와 백업 DDL로 되돌리고 grant를 확인한다.
4. owner policy 문제는 백업한 각 테이블의 전체 policy set을 복원한다. 일부 정책만 복구하면 permissive OR 드리프트가 남을 수 있다.
5. 기본 `advisors` cutover 문제는 `grant select on public.advisors to anon, authenticated`로 임시 복구한 뒤 FitHere 코드를 원인 수정한다. 연락처 노출이 다시 열리므로 임시 복구 시간을 최소화한다.

## 6. 검증 및 미실행 확인

- 로컬 도구 조사: `psql`, Docker, Supabase CLI가 없어 실제 PostgreSQL apply/rollback은 수행할 수 없다.
- SQL 5개는 lexer 종료, 괄호, outer transaction, Human guard, 자동/수동 경로, URL/secret 패턴 정적 검사를 모두 통과했다.
- `npm run build` 통과. TypeScript와 Vite production build가 완료됐고 기존 500 kB chunk 경고만 있었다.
- `cd backend && python -m pytest -q`: **618 passed, 8 skipped**. 기준선 불변이다.
- 프로덕션 Supabase 연결/query/apply: **0**
- `src/` 변경: **0**
- `backend/` 변경: **0**
- 실DB credential/행 데이터/PII 저장: **0**

## 7. Human 결정 필요

- `connection_requests`가 단순 연락 버튼 클릭인지 실제 연결 성사인지 확정 후 RPC 조건을 승인해야 한다.
- FitHere 공개 조회를 `advisors_public`으로 옮기는 코드 변경은 별도 태스크다. 완료 전 기본 테이블 SELECT 회수 금지다.
- `advisor_profile_drafts` owner UPDATE와 `certifications` owner INSERT 범위가 현재 운영 승인 흐름과 일치하는지 policy 백업과 앱 액션을 함께 대조해야 한다.
- 실DB `pg_policies`가 218 기대와 다르면 이 SQL을 즉시 실행하지 말고 차이를 새 마이그레이션에 반영해야 한다.

## 8. 2026-07-14 후속 - analysis_history 중복 정책 정합

Human이 프로덕션에서 중복 정책 `own rows select`, `own rows insert`, `own rows delete`를 제거하고 canonical `bohumfit_history_*` 4개만 남겼다.

- S0: `rg -i "own rows" supabase/migrations/` 결과 기존 생성 SQL은 없었다. 과거 Dashboard 수동 생성 정책으로 판단한다.
- 신규 `20260714000200_bohumfit219_drop_duplicate_history_policies.sql`에 세 정책의 `drop policy if exists`를 기록했다.
- 기존 `20260714000100` 및 canonical 정책 4개는 수정하거나 drop하지 않는다.
- 이미 정리된 프로덕션에서는 세 문장이 모두 no-op이고, 오래된 환경에서만 중복 정책을 제거한다.
- SQL 정적 검사: legacy drop 이름 3개 정확 일치, canonical drop 0, transaction/괄호/secret 검사 통과.
- `npm run build` 통과(기존 500 kB chunk 경고만), backend pytest **618 passed, 8 skipped**로 기준선 불변.
- 이 후속에서도 프로덕션 Supabase 연결/query/apply는 0이다.
