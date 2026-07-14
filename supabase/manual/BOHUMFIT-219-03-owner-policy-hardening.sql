-- BOHUMFIT-219 / F-218-01, F-218-05, F-218-06, F-218-07
-- Classification: HARDENING (behavior change; Human approval required).
-- NOT in supabase/migrations: never apply through an automatic migration run.
-- Shared BOHUMFIT/FitHere DB: this replaces policy sets on drifted tables.
-- Back up pg_policies and test every FitHere owner/admin flow first.
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

-- Canonical indirect owner check uses the live owner_id column.
create or replace function public.owns_advisor(target_advisor_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select exists (
    select 1
    from public.advisors a
    where a.id = target_advisor_id
      and a.owner_id = auth.uid()
  );
$$;

revoke all on function public.owns_advisor(uuid) from public, anon;
grant execute on function public.owns_advisor(uuid) to authenticated;

alter table public.advisor_applications enable row level security;
alter table public.advisor_profile_drafts enable row level security;
alter table public.certifications enable row level security;
alter table public.connection_requests enable row level security;
alter table public.contact_clicks enable row level security;
alter table public.review_links enable row level security;

-- Replace complete policy sets so stale profile_id/status/created_by policies
-- cannot remain permissive OR branches. This is why Human review is mandatory.
do $$
declare
  target_table text;
  pol record;
begin
  foreach target_table in array array[
    'advisor_applications',
    'advisor_profile_drafts',
    'certifications',
    'connection_requests',
    'contact_clicks',
    'review_links'
  ]
  loop
    for pol in
      select policyname
      from pg_policies
      where schemaname = 'public' and tablename = target_table
    loop
      execute format('drop policy if exists %I on public.%I', pol.policyname, target_table);
    end loop;
  end loop;
end
$$;

create policy advisor_applications_select_own_or_admin
on public.advisor_applications for select to authenticated
using (applicant_id = auth.uid() or public.is_admin());

create policy advisor_applications_insert_own
on public.advisor_applications for insert to authenticated
with check (applicant_id = auth.uid());

create policy advisor_applications_update_admin
on public.advisor_applications for update to authenticated
using (public.is_admin()) with check (public.is_admin());

create policy advisor_applications_delete_admin
on public.advisor_applications for delete to authenticated
using (public.is_admin());

create policy advisor_drafts_select_owner_or_admin
on public.advisor_profile_drafts for select to authenticated
using (public.owns_advisor(advisor_id) or public.is_admin());

create policy advisor_drafts_insert_owner
on public.advisor_profile_drafts for insert to authenticated
with check (public.owns_advisor(advisor_id));

create policy advisor_drafts_update_owner_or_admin
on public.advisor_profile_drafts for update to authenticated
using (public.owns_advisor(advisor_id) or public.is_admin())
with check (public.owns_advisor(advisor_id) or public.is_admin());

create policy advisor_drafts_delete_admin
on public.advisor_profile_drafts for delete to authenticated
using (public.is_admin());

create policy certifications_select_owner_or_admin
on public.certifications for select to authenticated
using (public.owns_advisor(advisor_id) or public.is_admin());

create policy certifications_insert_owner
on public.certifications for insert to authenticated
with check (public.owns_advisor(advisor_id));

create policy certifications_update_admin
on public.certifications for update to authenticated
using (public.is_admin()) with check (public.is_admin());

create policy certifications_delete_admin
on public.certifications for delete to authenticated
using (public.is_admin());

create policy connection_requests_select_own_or_admin
on public.connection_requests for select to authenticated
using (requester_id = auth.uid() or public.is_admin());

create policy connection_requests_insert_own_published
on public.connection_requests for insert to authenticated
with check (
  requester_id = auth.uid()
  and exists (
    select 1 from public.advisors a
    where a.id = advisor_id
      and a.is_active = true
      and a.is_verified = true
      and a.is_published = true
  )
);

create policy connection_requests_delete_admin
on public.connection_requests for delete to authenticated
using (public.is_admin());

create policy contact_clicks_select_own_or_admin
on public.contact_clicks for select to authenticated
using (user_id = auth.uid() or public.is_admin());

create policy contact_clicks_insert_own
on public.contact_clicks for insert to authenticated
with check (user_id = auth.uid());

create policy contact_clicks_delete_admin
on public.contact_clicks for delete to authenticated
using (public.is_admin());

-- review_links live columns no longer include created_by/status/review_id.
-- Keep it server-only; service_role bypasses RLS for reviewed server actions.
revoke all on public.review_links from anon, authenticated;
grant all on public.review_links to service_role;

revoke all on public.advisor_applications from anon, authenticated;
grant select, insert, update, delete on public.advisor_applications to authenticated;
revoke all on public.advisor_profile_drafts from anon, authenticated;
grant select, insert, update, delete on public.advisor_profile_drafts to authenticated;
revoke all on public.certifications from anon, authenticated;
grant select, insert, update, delete on public.certifications to authenticated;
revoke all on public.connection_requests from anon, authenticated;
grant select, insert, delete on public.connection_requests to authenticated;
revoke all on public.contact_clicks from anon, authenticated;
grant select, insert, delete on public.contact_clicks to authenticated;

-- Consolidate duplicate permissive SELECT policies without touching profile
-- INSERT/UPDATE policies or the role-change trigger.
do $$
declare
  pol record;
begin
  for pol in
    select policyname
    from pg_policies
    where schemaname = 'public'
      and tablename = 'profiles'
      and cmd = 'SELECT'
  loop
    execute format('drop policy if exists %I on public.profiles', pol.policyname);
  end loop;
end
$$;

create policy profiles_select_self_or_admin
on public.profiles for select to authenticated
using (id = auth.uid() or public.is_admin());

-- BOHUMFIT history is backend-only today. Owner RLS remains as defense in depth
-- if direct access is deliberately granted later.
revoke all on public.bohumfit_analysis_history from anon, authenticated;

commit;
