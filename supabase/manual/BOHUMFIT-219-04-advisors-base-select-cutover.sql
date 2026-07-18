-- [SUPERSEDED by BOHUMFIT-225-04-advisors-base-select-cutover.sql] 2026-07-17 — 실행 금지.
-- 내용 실질 동일(드리프트 없음 실측 확인). 세션 가드 키 갱신('BOHUMFIT-225')과
-- 드리프트 가드·전후 확인쿼리 보강본이 225-04다. 이 파일은 이력 보존용.
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
