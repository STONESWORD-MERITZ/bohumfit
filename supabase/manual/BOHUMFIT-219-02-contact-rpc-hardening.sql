-- [SUPERSEDED by BOHUMFIT-225-02-contact-rpc-hardening.sql] 2026-07-17 — 실행 금지.
-- 실DB에 has_consult_with_advisor(uuid)가 이미 존재해(225-00 Q5 실측) 연결기록
-- 조건을 그 함수 재사용으로 재작성했다. 이 파일은 이력 보존용.
-- BOHUMFIT-219 / F-218-04
-- Classification: HARDENING (behavior change; Human approval required).
-- NOT in supabase/migrations: never apply through an automatic migration run.
-- Shared BOHUMFIT/FitHere DB: verify the meaning and creation timing of a
-- connection_requests row before applying at low traffic.
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

create or replace function public.get_advisor_contact(p_advisor_id uuid)
returns table (
  contact_phone text,
  contact_kakao_openchat text,
  contact_kakao_channel text
)
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select
    a.contact_phone,
    a.contact_kakao_openchat,
    a.contact_kakao_channel
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

commit;
