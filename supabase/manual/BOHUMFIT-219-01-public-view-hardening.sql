-- [SUPERSEDED by BOHUMFIT-225-01-public-view-hardening.sql] 2026-07-17 — 실행 금지.
-- 2026-07-14 감사 시점 메타데이터 기준이라 실DB와 드리프트: reviews.reconsult_intent
-- 삭제(42703 실측, 2026-07-17 실행 시도 롤백). 이 파일은 이력 보존용.
-- BOHUMFIT-219 / F-218-03
-- Classification: HARDENING (behavior change; Human approval required).
-- NOT in supabase/migrations: never apply through an automatic migration run.
-- Shared BOHUMFIT/FitHere DB: run at low traffic after schema/view backups.
--
-- Before running in the same SQL Editor session:
--   set bohumfit.human_approved = 'BOHUMFIT-219';

begin;

do $$
begin
  if current_setting('bohumfit.human_approved', true) is distinct from 'BOHUMFIT-219' then
    raise exception 'BOHUMFIT-219 Human approval setting is required';
  end if;
end
$$;

-- Public profile surface: invoker RLS plus an explicit publication boundary.
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

-- Aggregate views stay security-definer so private source tables do not turn
-- public metrics into zero rows. Their output is constrained to published
-- advisors and the existing public aggregate columns.
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
  round(
    100.0 * count(case when r.reconsult_intent = true then 1 else null end)::numeric
      / nullif(count(r.id), 0)::numeric,
    1
  ) as reconsult_intent_rate,
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

grant select on public.advisors_public to anon, authenticated;
grant select on public.advisor_review_stats to anon, authenticated;
grant select on public.advisor_field_ratings to anon, authenticated;
grant select on public.advisor_public_certifications to anon, authenticated;

commit;
