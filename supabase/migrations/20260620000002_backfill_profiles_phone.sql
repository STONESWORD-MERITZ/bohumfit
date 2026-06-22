-- BOHUMFIT-085: 휴대폰 인증 게이트 실동작 — profiles 행 백필 + 신규 가입 트리거 보강.
-- ★ 이 SQL은 Human이 Supabase SQL 에디터에서 직접 실행해야 적용됩니다(저장소 마이그레이션 자동 실행 아님).
-- 목적: profiles 행이 없는 기존/소셜 계정이 휴대폰 인증 게이트를 그냥 통과하던 버그 차단.

-- 1) 신규 가입(이메일·OAuth 소셜 포함) 시 profiles 행 자동 생성.
--    auth.users INSERT마다 발화 → 소셜(카카오·구글) 최초 로그인에도 행을 보장.
--    phone_verified 는 컬럼 기본값 false 로 들어가 게이트가 동작한다. 멱등(ON CONFLICT DO NOTHING).
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id)
  values (new.id)
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- 2) 기존 계정 백필: profiles 행이 없는 auth.users 전체에 행 생성.
--    role(기본 'customer')·phone_verified(기본 false)는 컬럼 기본값으로 채워진다. 멱등.
insert into public.profiles (id)
select u.id
from auth.users u
where not exists (
  select 1 from public.profiles p where p.id = u.id
)
on conflict (id) do nothing;
