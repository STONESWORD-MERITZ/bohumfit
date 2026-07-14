-- BOHUMFIT-219 follow-up
-- Classification: PIN (production was already cleaned up manually by Human).
--
-- Remove the three legacy duplicate policies if an older environment still has
-- them. The canonical bohumfit_history_select/insert/update/delete_own policies
-- created by 20260714000100 are intentionally left unchanged.

begin;

drop policy if exists "own rows select"
  on public.bohumfit_analysis_history;

drop policy if exists "own rows insert"
  on public.bohumfit_analysis_history;

drop policy if exists "own rows delete"
  on public.bohumfit_analysis_history;

commit;
