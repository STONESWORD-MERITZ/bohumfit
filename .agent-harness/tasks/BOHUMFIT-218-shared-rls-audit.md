# BOHUMFIT-218 - 공유 Supabase RLS SELECT/쓰기 정책 전수 감사 명세

Owner flow: Human -> Codex Windows -> Human
Current owner: Human
Date: 2026-07-14
Type: 조사·감사 전용(코드 0, DB 변경 0)

## 1. 목적과 결론

BOHUMFIT와 FitHere가 공유하는 Supabase `public` 스키마에서 로그인 사용자가 소유자 범위를 벗어나 다른 사용자의 개인 데이터를 조회·변경할 수 없는지 전수 확인하기 위한 감사 명세다. 실제 정책 변경은 하지 않았으며, 아래 SQL은 Human이 저트래픽 시간에 결과를 검토한 뒤 개별 실행해야 하는 감사 쿼리와 강화 초안이다.

이번 조사에서 확인된 핵심은 다음과 같다.

1. BOHUMFIT와 FitHere의 로컬 환경이 같은 Supabase URL을 가리키는 것을 값 노출 없이 확인했다.
2. 서비스 역할을 이용한 읽기 전용 OpenAPI 메타데이터 조회로 실DB `public` 객체 20개(테이블 16개, 뷰 4개)를 확인했다. 행 데이터와 키는 출력·저장하지 않았다.
3. `profiles`, `subscriptions`, `usage_logs`의 저장소 정책은 소유자 SELECT 형태다. 그러나 실DB 정책 카탈로그는 PostgREST로 노출되지 않아 `pg_policies` 실제값은 Human SQL 실행이 필요하다.
4. 가장 우선도가 높은 미확정 경계는 의료 분석 JSONB를 저장하는 `bohumfit_analysis_history`다. 실DB에는 존재하지만 생성/RLS SQL이 두 저장소에 없어 정책을 재현할 수 없다.
5. anon 읽기 스모크에서 `public.advisors` 기본 테이블 행이 실제로 조회 가능했다. 이 테이블에는 연락처 컬럼이 있으므로, 연락처를 연결 성사 시 RPC로만 제공한다는 정책과 충돌할 수 있다.
6. 공개 뷰 3개는 저장소 최종 SQL상 `security_invoker`가 아니거나 `is_published` 명시 조건이 빠져 있다. RLS를 우회해 비공개 전문가의 집계/자격 정보를 노출할 가능성이 있다.
7. 실DB 컬럼과 저장소 마이그레이션의 소유자 컬럼이 여러 곳에서 다르다. 따라서 저장소 SQL만 보고 현재 RLS가 정상이라고 확정할 수 없다.

## 2. 조사 범위와 한계

### 수행한 읽기 전용 조사

- BOHUMFIT: `AGENTS.md`, `CLAUDE.md`, 최신 handoff, BOHUMFIT-210 감사 H3, decisions 보안 정책, Supabase 마이그레이션, 앱의 Supabase 접근 경로.
- FitHere: 마이그레이션, RLS/GRANT/REVOKE, 뷰/RPC 정의, 앱의 테이블 접근 경로.
- 공유 프로젝트: 서비스 역할로 PostgREST OpenAPI 스키마 메타데이터만 조회.
- anon 스모크: 관계별 최대 1행 요청 후 상태/행 존재 여부만 기록. 응답 행 내용은 출력하거나 저장하지 않음.

### 한계

- 로컬에 Supabase CLI, `DATABASE_URL`, `SUPABASE_DB_URL`, DB 비밀번호가 없다.
- 서비스 역할 키는 PostgREST에서 RLS를 우회하지만 `pg_policies`, `pg_class`, `information_schema.role_table_grants`를 직접 조회할 수 없다.
- authenticated 사용자 2명과 admin 사용자의 실제 JWT를 사용한 교차 사용자 스모크는 수행하지 않았다. 계정 생성·세션 탈취·PII 조회를 감사 명목으로 자동 수행하지 않았다.
- 따라서 아래 표의 `실DB RLS`가 `Human SQL 필요`인 행은 미확정이다. 이 문서는 미확정을 정상으로 간주하지 않는다.

## 3. S0 - 실DB public 객체 인벤토리

OpenAPI 메타데이터 기준 2026-07-14 현재 객체다.

| 관계 | 유형 | 주요 소유자/공개 경계 | 저장소상 RLS/보호 근거 | 실DB 판정 |
| --- | --- | --- | --- | --- |
| `profiles` | table | `id = auth.uid()` 또는 admin; email/phone/full_name 포함 | FitHere self/admin SELECT, BOHUMFIT self SELECT가 중복 가능 | Human SQL 필요 |
| `advisors` | table | 공개 디렉터리 + `owner_id`; 연락처 포함 | 공개 승인 행 SELECT, 쓰기 service/admin 의도 | anon 기본 테이블 조회 확인, 강화 필요 |
| `reviews` | table | approved 공개, 그 외 `author_id`/admin | approved/self/admin SELECT, 작성자는 자기 INSERT | Human SQL 필요 |
| `consult_requests` | table | `requester_id`/admin | requester/admin SELECT, requester 자기 INSERT | Human SQL 필요 |
| `support_posts` | table | 공개 글 또는 `author_id`/admin | 공개/작성자/admin SELECT·작성자 쓰기 | Human SQL 필요 |
| `support_answers` | table | 상위 글 가시성 + `author_id`/admin | 상위 글 정책 연동 | Human SQL 필요 |
| `reports` | table | `reporter_id`/admin | reporter/admin SELECT, reporter 자기 INSERT | Human SQL 필요 |
| `advisor_applications` | table | 실제 `applicant_id`/admin | 저장소 정책은 과거 `profile_id` 기준 | 🔴 스키마 드리프트, 실제 qual 필수 |
| `advisor_profile_drafts` | table | `advisor_id -> advisors.owner_id`/admin | 저장소 정책은 삭제된 `profile_id`, `status` 기준 | 🔴 스키마 드리프트, 실제 qual 필수 |
| `certifications` | table | `advisor_id -> advisors.owner_id`/admin | 저장소 정책/뷰가 과거 컬럼에 의존 | 🔴 스키마 드리프트, 실제 qual 필수 |
| `connection_requests` | table | `requester_id`/admin | 저장소 초기본은 익명 INSERT·admin SELECT, 현재 anon 401 | 실제 INSERT/SELECT 정책 확인 필요 |
| `review_links` | table | 토큰 민감, 전문가 소유자/admin 또는 server-only | 저장소 정책이 실DB에 없는 컬럼을 참조 | 🔴 server-only 권장, 실제 정책 필수 |
| `contact_clicks` | table | `user_id = auth.uid()` | authenticated 자기 INSERT/SELECT | Human SQL 필요 |
| `subscriptions` | table | `user_id = auth.uid()` | 본인 SELECT, 서비스 역할 쓰기 의도 | Human SQL 필요 |
| `usage_logs` | table | `user_id = auth.uid()` | 본인 SELECT, 서비스 역할 쓰기 의도 | Human SQL 필요 |
| `bohumfit_analysis_history` | table | `user_id = auth.uid()`; `result` JSONB 의료 분석 | 저장소 생성/RLS SQL 없음, 백엔드는 service role + user_id 필터 | 🔴 최우선 미확정 |
| `advisors_public` | view | 공개 승인 전문가의 비연락처 컬럼 | `security_invoker=true`, 뷰 WHERE에는 `is_published` 누락 | 기본 정책 의존 제거 필요 |
| `advisor_review_stats` | view | 공개 집계만 | 최신 SQL이 invoker 미지정, published 필터 없음 | 🔴 RLS 우회/비공개 집계 가능 |
| `advisor_field_ratings` | view | 공개 집계만 | 최신 SQL이 invoker 미지정, published 필터 없음 | 🔴 RLS 우회/비공개 집계 가능 |
| `advisor_public_certifications` | view | 공개 승인 자격만 | `security_invoker=false`, published 필터 없음 | 🔴 RLS 우회/비공개 자격 가능 |

### 실제 컬럼과 저장소 SQL의 드리프트

서비스 역할 OpenAPI 메타데이터와 저장소 마이그레이션을 비교한 결과다.

| 관계 | 실DB 메타데이터 | 저장소 정책/코드의 오래된 전제 |
| --- | --- | --- |
| `profiles.role` | `public.user_role`: `anonymous, customer, advisor, admin, internal` | BOHUMFIT 초기 SQL은 `customer, internal`, FitHere 초기 SQL은 별도 `profile_role` |
| `advisors` | 소유자 컬럼 `owner_id` | 다수 FitHere 정책/코드는 `profile_id` 사용 |
| `advisor_applications` | 소유자 컬럼 `applicant_id` | 초기 정책은 `profile_id` 사용 |
| `advisor_profile_drafts` | `advisor_id`, `draft` 중심 | 초기 정책은 `profile_id`, `status` 사용 |
| `certifications` | `advisor_id`, `cert_name`, `issuer`, `file_path`, `is_verified` | 초기 INSERT 정책은 `status`, `masking_confirmed` 사용 |
| `review_links` | OpenAPI상 `id, advisor_id, token, expires_at, used_at, created_at` | 초기 정책은 `created_by`, `status`, `review_id` 사용 |

이 드리프트 때문에 강화 SQL은 현재 `pg_policies`, `information_schema.columns`, `pg_get_viewdef` 결과를 확보하기 전 실행하면 안 된다.

## 4. anon 읽기 스모크

anon 키로 각 관계를 최대 1행 읽고 응답 본문은 폐기했다.

| 결과 | 관계 |
| --- | --- |
| 200 + 행 존재 | `advisors`, `advisors_public`, `advisor_review_stats` |
| 200 + 현재 행 없음 | `profiles`, `reviews`, `support_posts`, `support_answers`, `certifications`, `advisor_public_certifications`, `advisor_field_ratings` |
| 401 | `advisor_applications`, `advisor_profile_drafts`, `bohumfit_analysis_history`, `connection_requests`, `consult_requests`, `contact_clicks`, `reports`, `review_links`, `subscriptions`, `usage_logs` |

주의: `200 + 현재 행 없음`은 정책이 안전하다는 증거가 아니다. 실제 테이블이 비어 있거나 RLS로 0행일 수 있으므로 정책 qual과 grant를 함께 확인해야 한다.

## 5. S1/S2 - 정책 판정 기준

### 개인 데이터 SELECT 기대값

- 직접 소유 컬럼: `profiles.id`, `*.user_id`, `requester_id`, `author_id`, `reporter_id`, `applicant_id`가 `auth.uid()`와 일치해야 한다.
- 간접 소유 컬럼: `advisor_id`는 `advisors.owner_id = auth.uid()` 조인이거나 검증된 `owns_advisor()` 함수로 제한한다.
- 관리자 예외: `public.is_admin()`만 허용하고, 함수가 현재 `profiles.role='admin'`을 읽으며 `SECURITY DEFINER SET search_path`와 최소 EXECUTE grant를 갖는지 확인한다.
- 공개 데이터: 공개 목적 컬럼만 별도 view로 제공하고 `is_active AND is_verified AND is_published`를 명시한다.
- 정책은 기본 `PERMISSIVE`이므로 같은 command 정책들이 OR로 결합된다. 안전한 정책 옆에 `USING (true)` 하나가 있으면 전체가 느슨해진다.

### 쓰기 기대값

- INSERT: `WITH CHECK`에 소유자 식과 허용 초기상태를 모두 둔다.
- UPDATE: `USING`으로 수정 전 행의 소유권, `WITH CHECK`로 수정 후 행의 소유권을 모두 고정한다.
- DELETE: 소유자 또는 admin만 `USING`으로 허용한다. server-only 테이블은 authenticated grant 자체를 회수한다.
- `anon`에는 공개 폼으로 확정된 최소 INSERT 외 쓰기 권한을 주지 않는다. 현재 정책 결정은 민감 INSERT 회수이므로 `connection_requests`도 실제 grant를 재확인한다.

## 6. Human 실행용 감사 SQL

아래는 모두 읽기 전용이다. 결과에 UUID·정책식이 포함될 수 있으므로 안전한 운영 기록에 보관하고 저장소에는 원문 결과를 커밋하지 않는다.

### A. 테이블/뷰와 RLS 활성화 상태

```sql
select
  n.nspname as schema_name,
  c.relname as relation_name,
  case c.relkind
    when 'r' then 'table'
    when 'p' then 'partitioned_table'
    when 'v' then 'view'
    when 'm' then 'materialized_view'
    else c.relkind::text
  end as relation_type,
  c.relrowsecurity as rls_enabled,
  c.relforcerowsecurity as rls_forced,
  c.relowner::regrole as owner,
  c.reloptions
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relkind in ('r', 'p', 'v', 'm')
order by relation_type, relation_name;
```

판정: 위 16개 table은 모두 `rls_enabled=true`여야 한다. view는 RLS 대상이 아니므로 `reloptions`와 정의를 별도로 본다.

### B. 정책 전체 덤프

```sql
select
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd,
  qual,
  with_check
from pg_policies
where schemaname = 'public'
order by tablename, cmd, policyname;
```

### C. 위험 정책 자동 후보

```sql
select *
from pg_policies
where schemaname = 'public'
  and (
    coalesce(btrim(qual), '') in ('', 'true', '(true)')
    or coalesce(btrim(with_check), '') in ('true', '(true)')
    or roles @> array['public']::name[]
  )
order by tablename, cmd, policyname;
```

```sql
select tablename, cmd, count(*) as permissive_policy_count,
       string_agg(policyname, ', ' order by policyname) as policies
from pg_policies
where schemaname = 'public'
  and permissive = 'PERMISSIVE'
group by tablename, cmd
having count(*) > 1
order by tablename, cmd;
```

두 번째 결과는 즉시 취약점이라는 뜻이 아니다. 정책이 OR 결합되므로 각 qual을 함께 검토해야 한다.

### D. anon/authenticated grant

```sql
select table_name, grantee, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee in ('anon', 'authenticated')
order by table_name, grantee, privilege_type;
```

```sql
select routine_name, grantee, privilege_type
from information_schema.role_routine_grants
where routine_schema = 'public'
  and grantee in ('PUBLIC', 'anon', 'authenticated')
order by routine_name, grantee;
```

### E. 실제 컬럼/enum 확인

```sql
select table_name, ordinal_position, column_name, data_type, udt_name, is_nullable
from information_schema.columns
where table_schema = 'public'
order by table_name, ordinal_position;
```

```sql
select n.nspname as enum_schema, t.typname as enum_name,
       e.enumsortorder, e.enumlabel
from pg_type t
join pg_enum e on e.enumtypid = t.oid
join pg_namespace n on n.oid = t.typnamespace
where n.nspname = 'public'
order by t.typname, e.enumsortorder;
```

### F. 뷰의 RLS 우회 여부와 정의

```sql
select
  c.relname as view_name,
  c.relowner::regrole as owner,
  c.reloptions,
  pg_get_viewdef(c.oid, true) as view_definition
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relkind = 'v'
order by c.relname;
```

확인 대상: `advisors_public`, `advisor_review_stats`, `advisor_field_ratings`, `advisor_public_certifications`. `security_invoker=true`가 없으면 view owner 권한으로 기반 테이블 RLS가 우회될 수 있다.

### G. admin/연락처 RPC 정의와 권한

```sql
select
  n.nspname as schema_name,
  p.proname,
  p.prosecdef as security_definer,
  p.proconfig,
  p.proacl,
  pg_get_functiondef(p.oid) as definition
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.proname in (
    'current_profile_role', 'is_admin', 'owns_advisor',
    'has_consult_with_advisor', 'get_advisor_contact'
  )
order by p.proname;
```

### H. Storage 보조 감사

```sql
select id, name, public, file_size_limit, allowed_mime_types
from storage.buckets
order by id;

select policyname, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'storage' and tablename = 'objects'
order by policyname;
```

자격증 버킷은 private여야 하고, 경로의 advisor 소유자 또는 admin만 접근해야 한다.

### I. authenticated 교차 소유자 읽기 카나리

운영 데이터 원문을 출력하지 않고 boolean만 확인한다. `USER_A_UUID`는 일반 사용자, `ADMIN_UUID`는 실제 admin 계정으로 교체한다.

```sql
begin;
select set_config(
  'request.jwt.claims',
  json_build_object('sub', 'USER_A_UUID', 'role', 'authenticated')::text,
  true
);
set local role authenticated;

select auth.uid() as simulated_uid;
select exists(select 1 from public.profiles where id <> auth.uid())
  as profiles_cross_owner_visible;
select exists(select 1 from public.subscriptions where user_id <> auth.uid())
  as subscriptions_cross_owner_visible;
select exists(select 1 from public.usage_logs where user_id <> auth.uid())
  as usage_logs_cross_owner_visible;
select exists(select 1 from public.bohumfit_analysis_history where user_id <> auth.uid())
  as history_cross_owner_visible;
select exists(select 1 from public.consult_requests where requester_id <> auth.uid())
  as consult_cross_owner_visible;
select exists(select 1 from public.contact_clicks where user_id is distinct from auth.uid())
  as contact_clicks_cross_owner_visible;
select exists(select 1 from public.advisor_applications where applicant_id <> auth.uid())
  as application_cross_owner_visible;

rollback;
```

모든 결과가 `false`여야 한다. admin 카나리는 같은 방식으로 `ADMIN_UUID`를 사용하되, 정책상 필요한 관리 행이 보이는지 별도 확인한다. SQL Editor 역할 전환 권한이 제한되면 JWT를 가진 테스트 계정 A/B로 PostgREST에서 같은 boolean/count 검사를 수행한다.

## 7. 발견 사항

### F-218-01 🔴 `bohumfit_analysis_history` RLS 원본 부재

- 실DB에는 `user_id`, `result jsonb`를 가진 테이블이 있다.
- BOHUMFIT 백엔드는 service role로 접근하면서 모든 쿼리에 `user_id` 필터를 적용한다. 이것은 앱 경로 방어로는 좋지만 service role이 RLS를 우회하므로 DB 정책의 증거는 아니다.
- authenticated가 직접 PostgREST를 호출했을 때 타인 행을 볼 수 없는지는 현재 확인할 수 없다.
- 조치: A~D/I 쿼리로 실제 RLS/grant를 확인하고, backend-only 원칙이면 anon/authenticated grant를 모두 회수한다.

### F-218-02 🔴 기본 `advisors` 테이블의 연락처 컬럼 노출 경계

- 실DB `advisors`에는 `contact_phone`, `contact_kakao_openchat`, `contact_kakao_channel`이 있다.
- anon 스모크에서 기본 테이블 행 조회가 성공했다. RLS는 행을 제한할 뿐 같은 행의 민감 컬럼을 숨기지 않는다.
- 따라서 공개 승인 행이라도 기본 테이블 SELECT grant가 유지되면 RPC를 거치지 않고 연락처를 직접 요청할 수 있다.
- 조치: 공개 읽기를 `advisors_public`으로 전환하고 기본 테이블 SELECT를 회수하거나, 공개 안전 컬럼에만 column-level grant를 부여한다. 양쪽 앱 쿼리 회귀를 먼저 확인해야 한다.

### F-218-03 🔴 공개 집계/자격 뷰의 RLS 우회 가능성

- 최신 `advisor_review_stats`, `advisor_field_ratings` SQL은 `security_invoker`를 지정하지 않고 `is_published`를 필터하지 않는다.
- `advisor_public_certifications`는 저장소 SQL에서 `security_invoker=false`이며 `is_published`가 없다.
- 공개 뷰가 owner 권한으로 실행되면 비공개 전문가의 식별자·집계·자격 정보가 노출될 수 있다.
- 조치: 실제 `pg_get_viewdef`를 백업한 뒤 published 조건을 명시하고, invoker 또는 최소 컬럼의 검토된 definer view로 재작성한다.

### F-218-04 🔴 `get_advisor_contact` RPC의 연결 성사 조건 부재

- 저장소 정의는 `authenticated`, `is_active`, `is_verified`만 확인한다.
- `is_published` 및 현재 사용자의 `connection_requests` 존재 여부를 확인하지 않는다.
- 조치: 공개 승인 + 본인 연결 기록을 함께 확인하도록 강화하고 PUBLIC/anon EXECUTE를 회수한다.

### F-218-05 🔴 실DB/마이그레이션 소유자 컬럼 드리프트

- `owner_id/profile_id`, `applicant_id/profile_id`, draft/review_link 컬럼이 다르다.
- 오래된 정책을 그대로 재실행하면 실패하거나 잘못된 소유자 스코프를 만들 수 있다.
- 조치: E/B/F 결과를 현재 기준선으로 승인한 후 실제 컬럼명으로 새 migration을 작성한다. 재구성 파일을 운영의 유일한 진실로 취급하지 않는다.

### F-218-06 🟡 `profiles` SELECT 정책 중복 가능성

- FitHere `profiles_select_self_or_admin`과 BOHUMFIT `본인 프로필 조회`가 함께 있으면 permissive OR로 결합된다.
- 두 식 자체는 self/admin 범위라 즉시 노출은 아니지만, 정책 변경 시 한쪽만 고쳐져 드리프트할 수 있다.
- 조치: 실제 B 결과 확인 후 self/admin 정책 하나로 통합한다.

### F-218-07 🟡 broad authenticated grant는 RLS 정확성에 전적으로 의존

- 초기 SQL은 여러 테이블에 authenticated SELECT/INSERT/UPDATE/DELETE를 넓게 grant한다.
- RLS가 켜져 있고 모든 command 정책이 정확하면 동작하지만, 한 테이블의 RLS off 또는 `true` 정책이 곧 전체 노출/변조로 이어진다.
- 조치: 앱이 server-only로 사용하는 테이블은 grant 자체를 회수하고, 직접 접근 테이블만 최소 privilege를 유지한다.

## 8. 강화 SQL 초안(Human 검토 후 개별 실행)

아래는 한 번에 실행할 배치가 아니다. 반드시 6절 A~G 결과와 양쪽 앱 호출 경로를 대조하고, 각 항목을 별도 transaction으로 적용한다.

### Draft 1 - BOHUMFIT 히스토리를 backend-only로 잠금

```sql
begin;

alter table public.bohumfit_analysis_history enable row level security;
revoke all on public.bohumfit_analysis_history from anon, authenticated;

-- 정책은 미래에 authenticated direct access를 다시 grant할 때도 소유자 경계를 유지하는 방어층이다.
drop policy if exists bohumfit_history_select_own on public.bohumfit_analysis_history;
drop policy if exists bohumfit_history_insert_own on public.bohumfit_analysis_history;
drop policy if exists bohumfit_history_update_own on public.bohumfit_analysis_history;
drop policy if exists bohumfit_history_delete_own on public.bohumfit_analysis_history;

create policy bohumfit_history_select_own
on public.bohumfit_analysis_history for select to authenticated
using (user_id = auth.uid());

create policy bohumfit_history_insert_own
on public.bohumfit_analysis_history for insert to authenticated
with check (user_id = auth.uid());

create policy bohumfit_history_update_own
on public.bohumfit_analysis_history for update to authenticated
using (user_id = auth.uid()) with check (user_id = auth.uid());

create policy bohumfit_history_delete_own
on public.bohumfit_analysis_history for delete to authenticated
using (user_id = auth.uid());

commit;
```

정책만으로 privilege가 생기지 않는다. 현재 backend service role 경로만 쓴다면 authenticated grant는 복구하지 않는다.

### Draft 2 - 연락처를 기본 테이블에서 분리

권장 순서: FitHere 공개 조회를 `advisors_public`으로 전환·검증한 뒤 grant를 회수한다.

```sql
begin;

revoke select on public.advisors from anon, authenticated;
grant select on public.advisors_public to anon, authenticated;

commit;
```

기존 코드가 기본 테이블을 직접 읽으므로 선행 코드 배포 없이 실행하면 장애가 난다. 대안은 기본 테이블의 안전 컬럼만 column-level grant하는 것이지만, 실제 쿼리 컬럼 전수 대조 후 작성해야 한다.

### Draft 3 - 공개 뷰 published 경계

먼저 현재 정의를 `pg_get_viewdef`로 백업한다. 아래 원칙으로 각 뷰를 재작성한다.

```sql
-- advisors_public: security_invoker + 명시적 3조건
create or replace view public.advisors_public
with (security_invoker = true, security_barrier = true) as
select
  id, full_name, title, bio, photo_url, specialty, life_stage,
  financial_goal, affiliation, region, consulting_style, target_clients,
  is_verified, is_active, created_at, updated_at
from public.advisors
where is_active = true
  and is_verified = true
  and is_published = true;
```

`advisor_review_stats`, `advisor_field_ratings`, `advisor_public_certifications`는 현재 집계 산식을 그대로 복사하되 다음 조건을 모두 만족시킨다.

- `advisors`를 join하고 `a.is_active AND a.is_verified AND a.is_published`를 명시한다.
- 공개 컬럼은 advisor id와 비식별 집계/검증된 자격명만 둔다.
- `security_invoker=true`로 바꾸면 contact_clicks 등 비공개 원천이 anon에게 0행이 되어 지표가 달라질 수 있으므로, 지표 의미를 유지하려면 검토된 `security_invoker=false, security_barrier=true` 집계 뷰를 사용하되 published 필터와 출력 컬럼을 고정한다.
- 변경 후 FitHere 공개 목록/상세/통계와 비공개 전문가 미노출을 함께 확인한다.

### Draft 4 - 연락처 RPC

실DB 연락처 컬럼명을 E 결과로 확인한 뒤 적용한다.

```sql
create or replace function public.get_advisor_contact(p_advisor_id uuid)
returns table (
  contact_phone text,
  contact_kakao_openchat text,
  contact_kakao_channel text
)
language sql
security definer
set search_path = public, pg_temp
as $$
  select a.contact_phone, a.contact_kakao_openchat, a.contact_kakao_channel
  from public.advisors a
  where a.id = p_advisor_id
    and a.is_active = true
    and a.is_verified = true
    and a.is_published = true
    and auth.uid() is not null
    and exists (
      select 1
      from public.connection_requests cr
      where cr.advisor_id = a.id
        and cr.requester_id = auth.uid()
    );
$$;

revoke all on function public.get_advisor_contact(uuid) from public, anon;
grant execute on function public.get_advisor_contact(uuid) to authenticated;
```

`connection_requests` 생성과 RPC 호출 순서가 현재 UX와 맞는지 먼저 확인한다. “연결 성사”가 단순 버튼 클릭과 다른 의미라면 별도 상태 컬럼/RPC 정책은 Human 제품 결정이 필요하다.

### Draft 5 - 드리프트 테이블의 현재 컬럼 기준 owner policy

정책 이름과 기존 정책을 B 결과로 확인한 뒤 교체한다. 아래는 qual 템플릿이다.

```sql
-- advisor_applications
using (applicant_id = auth.uid() or public.is_admin())
with check (applicant_id = auth.uid() or public.is_admin())

-- advisor_profile_drafts / certifications
using (
  public.is_admin()
  or exists (
    select 1 from public.advisors a
    where a.id = advisor_id and a.owner_id = auth.uid()
  )
)

-- connection_requests
using (requester_id = auth.uid() or public.is_admin())
with check (requester_id = auth.uid())

-- contact_clicks
using (user_id = auth.uid() or public.is_admin())
with check (user_id = auth.uid())
```

`review_links`는 토큰 테이블이므로 앱이 service role만 사용한다면 다음이 더 단순하고 안전하다.

```sql
revoke all on public.review_links from anon, authenticated;
```

### Draft 6 - profiles 중복 SELECT 정책 통합

실제 정책 목록에서 두 정책이 모두 존재하고 `profiles_select_self_or_admin`이 아래 식과 일치할 때만 중복을 제거한다.

```sql
begin;

drop policy if exists "본인 프로필 조회" on public.profiles;
drop policy if exists profiles_select_self_or_admin on public.profiles;

create policy profiles_select_self_or_admin
on public.profiles for select to authenticated
using (id = auth.uid() or public.is_admin());

commit;
```

## 9. Human 실행 절차

1. 저트래픽 시간대를 잡고 BOHUMFIT/Railway와 FitHere/Vercel 운영 담당자에게 변경 창을 공유한다.
2. Supabase Dashboard에서 schema-only 백업과 6절 A~H 결과를 보관한다. UUID·정책 원문이 포함된 결과는 저장소에 커밋하지 않는다.
3. 일반 사용자 A/B, advisor, admin 테스트 계정을 준비한다. 실제 고객 데이터 대신 운영 테스트 계정을 사용한다.
4. 먼저 읽기 전용 A~I를 실행해 `rls_enabled`, 정책 qual, grant, 실제 컬럼, view option, function ACL을 확정한다.
5. F-218-01부터 한 항목씩 별도 transaction으로 적용한다. 여러 정책/뷰/RPC를 한 번에 바꾸지 않는다.
6. 변경 직후 BOHUMFIT에서 로그인, phone gate, billing/status, 분석, 히스토리 저장·목록·삭제를 확인한다.
7. FitHere에서 공개 전문가 목록/상세, 연락처 연결, 신청, 상담 요청, 후기, 고객센터, advisor workspace, admin queue를 확인한다.
8. 사용자 A JWT로 B의 개인 행이 0건인지, advisor가 다른 advisor의 draft/cert/link를 읽거나 변경할 수 없는지, admin만 관리 범위를 볼 수 있는지 확인한다.
9. 오류가 나면 해당 transaction을 rollback하고 캡처한 DDL/정책 기준으로 복구한다. 공유 DB이므로 한쪽 앱만 정상인 상태로 종료하지 않는다.

## 10. 완료 기준

- public table 16개의 `rls_enabled=true`가 확인됨.
- 개인 데이터 SELECT가 owner/admin 범위이며 `true` 또는 과다 OR 정책이 없음.
- INSERT/UPDATE/DELETE에 소유자 `WITH CHECK`가 있거나 server-only grant가 회수됨.
- `bohumfit_analysis_history`가 backend-only 또는 owner RLS로 확정됨.
- 기본 `advisors` 연락처를 anon/authenticated가 직접 읽지 못하고 검증된 RPC만 사용함.
- 공개 뷰가 비공개 전문가(`is_published=false`) 데이터를 노출하지 않음.
- BOHUMFIT와 FitHere의 핵심 흐름이 모두 회귀 없이 통과함.

## 11. 이번 태스크 변경 금지 확인

- Supabase SQL 실행/정책 변경: 0
- `src/` 변경: 0
- `backend/` 변경: 0
- 실제 행 데이터·PII 출력/저장: 0
- 키·시크릿 출력/저장: 0
