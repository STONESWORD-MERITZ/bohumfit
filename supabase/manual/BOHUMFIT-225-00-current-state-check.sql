-- BOHUMFIT-225 / S0 - 실DB 현재 상태 확인 쿼리 세트 (219-01~04 재작성 전 필수)
-- Classification: READ-ONLY (스키마 메타데이터만 조회; 어떤 객체도 변경하지 않음).
-- 배경: 219-01 실행 시도에서 "column r.reconsult_intent does not exist" (42703)로
--       트랜잭션이 롤백됐다(DB 무변경). 219-01~04는 218 감사(2026-07-14) 시점
--       메타데이터 기준이므로, 그 이후 FitHere 측 변경(FITHERE-158~162 추정)과의
--       드리프트를 실측으로 확정한 뒤에만 재작성한다.
--
-- 실행 방법: Supabase SQL Editor에서 Q1부터 Q8까지 순서대로 개별 실행하고,
--            각 결과를 그대로 복사해 Claude Chat/Code에 전달한다.
-- 주의: 결과는 스키마 메타데이터(컬럼명·뷰 정의·정책식·grant)다. 행 데이터·PII는
--       조회하지 않는다. 정책식/뷰 정의 원문 결과는 저장소에 커밋하지 않는다
--       (218 §6 보관 규칙과 동일 — 안전한 운영 기록에 보관).
-- 세션 가드 불필요: 전부 읽기 전용이므로 bohumfit.human_approved 설정 없이 실행 가능.

-- =====================================================================
-- Q1. 공개 뷰 4개의 현재 정의와 옵션 (219-01 재작성의 기준선)
--     reloptions에 security_invoker/security_barrier 여부가 나온다.
-- =====================================================================
select
  c.relname as view_name,
  c.relowner::regrole as owner,
  c.reloptions,
  pg_get_viewdef(c.oid, true) as view_definition
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relkind = 'v'
  and c.relname in (
    'advisors_public',
    'advisor_review_stats',
    'advisor_field_ratings',
    'advisor_public_certifications'
  )
order by c.relname;

-- =====================================================================
-- Q2. 219-01~04가 참조하는 테이블의 현재 컬럼 전체
--     (advisors의 is_published/연락처 3컬럼, reviews의 rating/status/author_id/
--      field_tags, certifications의 cert_name/issuer/is_verified 존재를 여기서 확정)
-- =====================================================================
select table_name, ordinal_position, column_name, data_type, udt_name, is_nullable
from information_schema.columns
where table_schema = 'public'
  and table_name in (
    'advisors',
    'reviews',
    'contact_clicks',
    'certifications',
    'connection_requests',
    'advisor_applications',
    'advisor_profile_drafts',
    'review_links',
    'profiles',
    'bohumfit_analysis_history'
  )
order by table_name, ordinal_position;

-- =====================================================================
-- Q3. reconsult_intent(및 유사 명칭)의 현재 존재 위치 — 42703의 원인 확정
--     결과 0행이면 컬럼이 삭제된 것, 다른 테이블/컬럼명으로 나오면 이동/개명된 것.
-- =====================================================================
select table_schema, table_name, column_name, data_type
from information_schema.columns
where column_name ilike '%reconsult%'
   or column_name ilike '%re_consult%'
   or column_name ilike '%revisit%'
order by table_schema, table_name, column_name;

-- =====================================================================
-- Q4. reviews 테이블에 219-01 집계가 전제하는 값이 실제로 있는지
--     (status enum/체크 값 — 'approved' 문자열 전제 검증. 행 데이터 아님)
-- =====================================================================
select n.nspname as enum_schema, t.typname as enum_name,
       e.enumsortorder, e.enumlabel
from pg_type t
join pg_enum e on e.enumtypid = t.oid
join pg_namespace n on n.oid = t.typnamespace
where n.nspname = 'public'
order by t.typname, e.enumsortorder;

-- =====================================================================
-- Q5. 관련 함수의 현재 정의 (219-02·03 재작성의 기준선)
-- =====================================================================
select
  p.proname,
  p.prosecdef as security_definer,
  p.proconfig,
  p.proacl,
  pg_get_functiondef(p.oid) as definition
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.proname in (
    'get_advisor_contact',
    'owns_advisor',
    'is_admin',
    'current_profile_role',
    'has_consult_with_advisor'
  )
order by p.proname;

-- =====================================================================
-- Q6. 219-03 대상 테이블의 현재 정책 전체 (교체 전 기준선·백업용)
--     ※ 결과에 정책식이 포함된다 — 저장소 커밋 금지, 안전한 기록에 보관.
-- =====================================================================
select tablename, policyname, permissive, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'public'
  and tablename in (
    'advisor_applications',
    'advisor_profile_drafts',
    'certifications',
    'connection_requests',
    'contact_clicks',
    'review_links',
    'profiles',
    'bohumfit_analysis_history'
  )
order by tablename, cmd, policyname;

-- =====================================================================
-- Q7. 관련 테이블·뷰의 anon/authenticated grant 현재값 (219-03·04 기준선)
-- =====================================================================
select table_name, grantee, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee in ('anon', 'authenticated')
  and table_name in (
    'advisors',
    'advisors_public',
    'advisor_review_stats',
    'advisor_field_ratings',
    'advisor_public_certifications',
    'reviews',
    'contact_clicks',
    'certifications',
    'connection_requests',
    'advisor_applications',
    'advisor_profile_drafts',
    'review_links',
    'profiles',
    'bohumfit_analysis_history'
  )
order by table_name, grantee, privilege_type;

-- =====================================================================
-- Q8. 대상 테이블 RLS 활성화 상태 (219-03의 enable row level security 전제 확인)
-- =====================================================================
select
  c.relname as relation_name,
  c.relrowsecurity as rls_enabled,
  c.relforcerowsecurity as rls_forced
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relkind = 'r'
  and c.relname in (
    'advisors',
    'reviews',
    'contact_clicks',
    'certifications',
    'connection_requests',
    'advisor_applications',
    'advisor_profile_drafts',
    'review_links',
    'profiles',
    'bohumfit_analysis_history'
  )
order by c.relname;

-- =====================================================================
-- 끝. Q1~Q8 결과 확보 후: 219-01~04 재작성(BOHUMFIT-225 S1·S2)으로 진행.
-- 재작성 완료 전까지 기존 219-01~04 파일은 실행 금지.
-- =====================================================================
