-- BOHUMFIT-219 / F-218-01
-- Classification: PIN (expected no behavior change on the 2026-07-14 live DB).
--
-- The live project already has this table and owner-scoped RLS. This migration
-- makes that contract reproducible in source control. It intentionally does not
-- change grants: BOHUMFIT currently accesses the table through service_role, and
-- direct authenticated access remains whatever the reviewed environment grants.

begin;

create table if not exists public.bohumfit_analysis_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  label text not null,
  mode text not null,
  result jsonb not null,
  created_at timestamptz not null default now(),
  track text not null default 'saved'
);

alter table public.bohumfit_analysis_history enable row level security;

-- PostgreSQL has no CREATE POLICY IF NOT EXISTS. Add each canonical policy only
-- when its name is absent. Equivalent policies under other names are left intact
-- so this pin does not broaden or narrow the reviewed live policy set.
do $do$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'bohumfit_analysis_history'
      and policyname = 'bohumfit_history_select_own'
  ) then
    execute $sql$
      create policy bohumfit_history_select_own
      on public.bohumfit_analysis_history
      for select to authenticated
      using (user_id = auth.uid())
    $sql$;
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'bohumfit_analysis_history'
      and policyname = 'bohumfit_history_insert_own'
  ) then
    execute $sql$
      create policy bohumfit_history_insert_own
      on public.bohumfit_analysis_history
      for insert to authenticated
      with check (user_id = auth.uid())
    $sql$;
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'bohumfit_analysis_history'
      and policyname = 'bohumfit_history_update_own'
  ) then
    execute $sql$
      create policy bohumfit_history_update_own
      on public.bohumfit_analysis_history
      for update to authenticated
      using (user_id = auth.uid())
      with check (user_id = auth.uid())
    $sql$;
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'bohumfit_analysis_history'
      and policyname = 'bohumfit_history_delete_own'
  ) then
    execute $sql$
      create policy bohumfit_history_delete_own
      on public.bohumfit_analysis_history
      for delete to authenticated
      using (user_id = auth.uid())
    $sql$;
  end if;
end
$do$;

comment on table public.bohumfit_analysis_history is
  'BOHUMFIT analysis history. Owner boundary: user_id = auth.uid(); application access currently uses service_role plus an explicit user_id filter.';

commit;
