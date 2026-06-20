-- BOHUMFIT-086: profiles 본인 SELECT 정책 — 클라이언트(anon 키)가 자기 phone_verified를 읽도록 보장.
-- ★ 이 SQL은 Human이 Supabase SQL 에디터에서 직접 실행해야 적용됩니다(저장소 마이그레이션 자동 실행 아님).
-- 배경: subscriptions/usage_logs에는 본인 SELECT 정책이 있으나 profiles에는 없었음.
--   profiles에 RLS가 켜져 있고 정책이 없으면, 클라이언트가 자기 행을 못 읽어(빈 결과) 게이트 판정이
--   어긋난다(특히 인증 후 phone_verified=true 를 못 읽어 /phone-verify 에 머무는 루프).
-- 안전성: 백엔드는 서비스롤로 RLS를 우회하므로 영향 없음. 클라이언트는 ProtectedRoute/PhoneGate의
--   본인 행 SELECT만 수행(코드 전수 확인). profiles에 대한 클라이언트 INSERT/UPDATE 경로 없음.

-- RLS 활성화(이미 켜져 있으면 무해). 보안 기본값.
alter table public.profiles enable row level security;

-- 멱등: 기존 동일 정책 제거 후 재생성.
drop policy if exists "본인 프로필 조회" on public.profiles;
create policy "본인 프로필 조회" on public.profiles
  for select using (auth.uid() = id);
