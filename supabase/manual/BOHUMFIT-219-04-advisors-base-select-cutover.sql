-- BOHUMFIT-219 / F-218-02
-- Classification: HARDENING (behavior change; BLOCKED until FitHere cutover).
-- NOT in supabase/migrations: never apply through an automatic migration run.
--
-- FitHere currently queries public.advisors with select('*'). Deploy and verify
-- an advisors_public-compatible read path before running this file. Applying it
-- first will break the public advisor list/detail flow.
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

revoke select on public.advisors from anon, authenticated;
grant select on public.advisors_public to anon, authenticated;

commit;
