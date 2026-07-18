-- BOHUMFIT-225-01 / F-218-03 재작성 (BOHUMFIT-219-01 대체)
-- Classification: HARDENING (동작 변경; Human 승인·직접 실행 필수).
-- NOT in supabase/migrations: 자동 마이그레이션 경로로 절대 적용하지 않는다.
-- 공유 BOHUMFIT/FitHere DB: 저트래픽 창에서 schema/view 백업 후 실행.
--
-- [실측 근거 — 2026-07-17 BOHUMFIT-225-00 Q1~Q8, Human 제공]
-- 1. reviews.reconsult_intent는 전 스키마에 부재(Q3: 0행) → 219-01의 42703 원인.
--    이 파일은 reconsult_intent_rate 지표를 산출하지 않는다(실측 라이브 뷰에도 원래 없음).
-- 2. advisors_public: 라이브는 security_invoker=true, is_active+is_verified만 필터
--    → is_published=true 경계만 추가, 컬럼 shape 16개 유지(FitHere 화면 호환).
-- 3. 집계 뷰 3개(review_stats/field_ratings/public_certifications): 라이브는 invoker
--    미적용 + published 경계 없음 + advisors 가시성 필터 자체가 없는 것도 있음.
--    ★invoker 전환은 적용하지 않았다(Chat 지시와 다름 — 아래 근거):
--      - contact_clicks는 anon grant가 없다(218 §4 실측: anon 401).
--        invoker 전환 시 advisor_review_stats는 anon 조회가 permission denied로 실패.
--      - certifications에는 공개 SELECT 정책이 없다(Q6: insert_own·select_admin뿐).
--        invoker 전환 시 advisor_public_certifications는 전원 0행.
--      - reviews의 SELECT 정책은 미실측(Q6 범위 밖) — field_ratings도 동일 위험.
--    → 3개 뷰는 218 Draft 3·219-01과 동일한 "검토된 definer + security_barrier +
--      published 경계 + 고정 출력 컬럼" 설계를 유지한다. invoker 전환을 원하면
--      선행조건(anon grant 정비·reviews/certifications 공개 SELECT 정책 신설)이
--      필요하며 이는 Human/Chat 결정 사항이다.
--
-- [실행 전 검증쿼리 — 같은 세션에서 먼저 실행, 결과 확인 후 진행]
--   -- (a) is_published 존재(파일 내 가드로도 재확인함):
--   select 1 from information_schema.columns
--    where table_schema='public' and table_name='advisors' and column_name='is_published';
--   -- (b) 변경 전후 행수 비교 기준 확보(비공개 전문가 제외분 예상치):
--   select count(*) as before_public from public.advisors_public;
--   select count(*) as after_expected from public.advisors
--    where is_active and is_verified and is_published;
--   select count(*) as certs_before from public.advisor_public_certifications;
--   select count(*) as certs_after_expected
--     from public.certifications c join public.advisors a on a.id = c.advisor_id
--    where c.is_verified and a.is_active and a.is_verified and a.is_published;
--
-- [실행 방법] 같은 SQL Editor 세션에서:
--   set bohumfit.human_approved = 'BOHUMFIT-225';
-- 그 후 이 파일 전체를 실행한다(단일 트랜잭션·재실행 안전).
--
-- [실행 후 확인쿼리]
--   -- (c) 4개 뷰 모두 is_published=false 전문가 0행(모두 false여야 함):
--   select exists(select 1 from public.advisors_public p
--     join public.advisors a on a.id = p.id where a.is_published = false) as leak_public;
--   select exists(select 1 from public.advisor_review_stats s
--     join public.advisors a on a.id = s.advisor_id where a.is_published = false) as leak_stats;
--   select exists(select 1 from public.advisor_field_ratings f
--     join public.advisors a on a.id = f.advisor_id where a.is_published = false) as leak_fields;
--   select exists(select 1 from public.advisor_public_certifications c
--     join public.advisors a on a.id = c.advisor_id where a.is_published = false) as leak_certs;
--   -- (d) 뷰 옵션 확인(advisors_public=invoker+barrier, 나머지 3개=barrier):
--   select c.relname, c.reloptions from pg_class c
--     join pg_namespace n on n.oid = c.relnamespace
--    where n.nspname='public' and c.relkind='v' and c.relname like 'advisor%';
--   -- (e) FitHere 공개 목록/상세/평점/자격 화면 + 비공개 전문가 미노출 회귀 확인.
--
-- [롤백 절차]
--   1) 트랜잭션 중 오류 → 자동 abort(또는 rollback;). DB 무변경.
--   2) commit 후 문제 발생 → Human이 보관 중인 225-00 Q1 결과(라이브 뷰 정의 원문)로
--      해당 뷰만 create or replace 복원. 복원 후 위 (d)로 reloptions 원상 확인.
--      (Q1 원문은 저장소에 커밋하지 않는다 — 218 §6 보관 규칙.)

begin;

do $$
begin
  if current_setting('bohumfit.human_approved', true) is distinct from 'BOHUMFIT-225' then
    raise exception 'BOHUMFIT-225 Human approval setting is required';
  end if;
end
$$;

-- 드리프트 가드: 참조 컬럼이 실DB에 없으면 뷰 재정의 전에 즉시 실패시킨다.
do $$
declare
  missing text;
begin
  select string_agg(need.col, ', ') into missing
  from (values
    ('advisors',       'is_published'),
    ('reviews',        'rating'),
    ('reviews',        'status'),
    ('reviews',        'author_id'),
    ('reviews',        'field_tags'),
    ('certifications', 'cert_name'),
    ('certifications', 'issuer'),
    ('certifications', 'is_verified'),
    ('contact_clicks', 'user_id'),
    ('contact_clicks', 'advisor_id')
  ) as need(tbl, col)
  where not exists (
    select 1 from information_schema.columns ic
    where ic.table_schema = 'public'
      and ic.table_name = need.tbl
      and ic.column_name = need.col
  );
  if missing is not null then
    raise exception 'BOHUMFIT-225-01 drift guard: missing column(s) [%] - rerun 225-00 checks first', missing;
  end if;
end
$$;

-- 1) advisors_public: 라이브 정의(invoker=true, 컬럼 16개) 유지 + is_published 경계 추가.
create or replace view public.advisors_public
with (security_invoker = true, security_barrier = true) as
select
  id,
  full_name,
  title,
  bio,
  photo_url,
  specialty,
  life_stage,
  financial_goal,
  affiliation,
  region,
  consulting_style,
  target_clients,
  is_verified,
  is_active,
  created_at,
  updated_at
from public.advisors
where is_active = true
  and is_verified = true
  and is_published = true;

-- 2) advisor_review_stats: 라이브 정의 기준(컬럼 6개 동일 — reconsult_intent_rate 미산출)
--    + published 경계. definer 유지(파일 머리 실측 근거 참조), barrier 명시.
create or replace view public.advisor_review_stats
with (security_invoker = false, security_barrier = true) as
select
  a.id as advisor_id,
  count(r.id) as review_count,
  round(avg(r.rating), 2) as avg_rating,
  round(
    100.0 * count(case when r.rating >= 4 then 1 else null end)::numeric
      / nullif(count(r.id), 0)::numeric,
    1
  ) as satisfaction_rate,
  count(case when cc.user_id is not null then 1 else null end) as verified_review_count,
  round(avg(case when cc.user_id is not null then r.rating else null end), 2)
    as verified_avg_rating
from public.advisors a
left join public.reviews r
  on r.advisor_id = a.id
 and r.status = 'approved'::text
left join lateral (
  select distinct c.user_id
  from public.contact_clicks c
  where c.advisor_id = r.advisor_id
    and c.user_id = r.author_id
  limit 1
) cc on true
where a.is_active = true
  and a.is_verified = true
  and a.is_published = true
group by a.id;

-- 3) advisor_field_ratings: 라이브 정의에는 advisors 가시성 필터가 전혀 없다.
--    advisors join + published 경계 추가. definer 유지, barrier 명시.
create or replace view public.advisor_field_ratings
with (security_invoker = false, security_barrier = true) as
select
  r.advisor_id,
  tag.field_tag,
  count(r.id) as review_count,
  round(avg(r.rating), 2) as avg_rating
from public.reviews r
join public.advisors a on a.id = r.advisor_id
cross join lateral unnest(
  case when r.field_tags is null then array[]::text[] else r.field_tags end
) as tag(field_tag)
where r.status = 'approved'::text
  and a.is_active = true
  and a.is_verified = true
  and a.is_published = true
group by r.advisor_id, tag.field_tag;

-- 4) advisor_public_certifications: 라이브 정의에는 advisors join 자체가 없어
--    비공개 전문가의 자격도 노출된다. join + published 경계 추가. definer 유지.
create or replace view public.advisor_public_certifications
with (security_invoker = false, security_barrier = true) as
select
  c.advisor_id,
  c.cert_name,
  c.issuer,
  c.is_verified
from public.certifications c
join public.advisors a on a.id = c.advisor_id
where c.is_verified = true
  and a.is_active = true
  and a.is_verified = true
  and a.is_published = true;

-- 공개 소비 경로 유지(현행 grant 재명시 — 무변경이어도 재실행 안전).
grant select on public.advisors_public to anon, authenticated;
grant select on public.advisor_review_stats to anon, authenticated;
grant select on public.advisor_field_ratings to anon, authenticated;
grant select on public.advisor_public_certifications to anon, authenticated;

commit;
