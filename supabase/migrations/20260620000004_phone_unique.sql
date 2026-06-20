-- BOHUMFIT-088: 휴대폰 번호 중복가입 임시 방어 — 부분 UNIQUE 인덱스.
-- ★ 이 SQL은 Human이 Supabase SQL 에디터에서 직접 실행해야 적용됩니다(저장소 마이그레이션 자동 실행 아님).
-- 임시방편: 사용자가 번호를 직접 입력하는 스텁 구조라 "다른 번호 입력"으로는 우회 가능.
--   동일 번호 재사용만 차단한다. 진짜 1인 1계정은 087(CI 기반 본인확인)에서 완성.
--
-- ⚠ 이미 같은 번호로 phone_verified=true 인 중복 행이 있으면 아래 인덱스 생성이 실패합니다.
--    그 경우 Human이 중복을 먼저 정리(한 계정만 유지)한 뒤 재실행하세요.
--    중복 확인 예시:
--      select phone, count(*) from public.profiles
--      where phone_verified = true and phone is not null
--      group by phone having count(*) > 1;

-- phone_verified=true 이고 phone IS NOT NULL 인 행에 한해 phone 유일. 멱등(IF NOT EXISTS).
create unique index if not exists profiles_phone_verified_unique
  on public.profiles (phone)
  where phone_verified = true and phone is not null;
