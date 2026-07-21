set bohumfit.human_approved = 'BOHUMFIT-232';
-- ↑ BOHUMFIT-232 신규 표준: 세션 가드 설정을 파일 첫 줄 실행문으로 포함(별도 선행 실행 불요).
--
-- BOHUMFIT-232-01 — profiles 테이블 단위 UPDATE grant 회수 (231 (f) 후속 봉인)
-- Classification: PERMISSION CHANGE (Human 승인·직접 실행 필수).
-- NOT in supabase/migrations: 자동 마이그레이션 경로로 절대 적용하지 않는다.
--
-- [배경 — 2026-07-20 Human (f) 실측]
-- authenticated에 profiles 테이블 단위 UPDATE grant 잔존 → 231의 컬럼 revoke에도 불구하고
-- 로그인 사용자가 자기 행(RLS profiles_update_own 범위)의 전 컬럼(bohumfit_tier·role 포함)을
-- PostgREST로 직접 수정 가능. 기존부터 있던 구조로, 이번에 회수한다.
--
-- [양측 클라이언트 실측 결론 — 2026-07-21 Claude Code, BOHUMFIT-232 태스크 문서 S0 표 참조]
-- BOHUMFIT src/: profiles UPDATE/UPSERT 0건(조회만 — usePhoneGate select).
--   backend upsert(phone_verified)는 service role 경유 → grant 무관.
-- FITHERE src/: profiles 쓰기 5곳 전부 getSupabaseAdminClient(SUPABASE_SERVICE_ROLE_KEY) 경유
--   (고객 행 upsert·advisor 승격·customer 강등·탈퇴 표식·복구) → 전부 grant 무관.
-- → anon/authenticated 경로의 profiles UPDATE 실사용 0건. 따라서 열거식 재grant가 필요한
--   컬럼은 **0개**다. role은 "클라이언트 사용 없음 → 제외 확정"(스펙 분기), bohumfit_tier는
--   당연 제외. 이 파일은 회수만 수행하고 UPDATE grant를 재부여하지 않는다.
-- → 향후 클라이언트 직접 편집이 생기면 아래 형식으로 열거식 grant를 별도 태스크로 추가한다:
--   grant update (컬럼1, 컬럼2) on public.profiles to authenticated;  -- bohumfit_tier·role 금지
--
-- [실행 전 확인쿼리]
--   -- (a) 231 (f) 재확인 — 테이블 단위 UPDATE grant 현황:
--   select grantee, privilege_type from information_schema.role_table_grants
--    where table_schema='public' and table_name='profiles'
--      and grantee in ('anon','authenticated') and privilege_type='UPDATE';
--   -- (b) 컬럼 단위 UPDATE grant 현황(참고):
--   select grantee, column_name from information_schema.column_privileges
--    where table_schema='public' and table_name='profiles'
--      and grantee in ('anon','authenticated') and privilege_type='UPDATE'
--    order by grantee, column_name;
--
-- [실행 후 확인쿼리]
--   -- (c) = (a) 재실행 → 0행 기대(테이블 단위 UPDATE 잔존 0).
--   -- (d) = (b) 재실행 → 0행 기대(열거 grant 0개 — 재부여 안 함).
--   -- (e) SELECT/INSERT 등 다른 권한은 무접촉 확인:
--   select grantee, privilege_type from information_schema.role_table_grants
--    where table_schema='public' and table_name='profiles'
--      and grantee in ('anon','authenticated')
--    order by grantee, privilege_type;
--
-- [실행 후 회귀 체크리스트 — 운영 테스트 계정으로 각 1회]
--   □ FitHere: 관리자 전문가 승인(→ role advisor 반영), 계정 탈퇴 표식→복구, 프로필/전문가
--     정보 저장 동선 정상 (모두 service role 경로 — 영향 없어야 정상)
--   □ BOHUMFIT: 로그인 → 휴대폰 본인인증(phone_verified 반영) → 분석 1회 정상
--   □ 로그인 사용자 PostgREST로 자기 profiles UPDATE 시도 → 401/permission denied 확인
--     (예: patch /rest/v1/profiles?id=eq.<본인uuid> body {"display_name":"x"})
--
-- [롤백] 원상복구 한 줄(실측상 anon에는 원래 UPDATE grant가 없었음 — authenticated만 복원):
--   grant update on public.profiles to authenticated;

begin;

do $$
begin
  if current_setting('bohumfit.human_approved', true) is distinct from 'BOHUMFIT-232' then
    raise exception 'BOHUMFIT-232 Human approval setting is required';
  end if;
end
$$;

-- 드리프트 가드: 대상 테이블 존재 + 231 적용 여부 알림(bohumfit_tier 부재 시 경고만 — 이 파일은
-- 권한만 다루므로 중단하지 않되, 231-01 미실행 상태라면 실행 순서를 재확인하라는 신호다.
do $$
begin
  if to_regclass('public.profiles') is null then
    raise exception 'BOHUMFIT-232-01 drift guard: public.profiles missing';
  end if;
  if not exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'profiles' and column_name = 'bohumfit_tier'
  ) then
    raise notice 'BOHUMFIT-232-01: bohumfit_tier not found - 231-01이 아직 미실행. 이 파일 실행은 유효하나 순서를 확인할 것';
  end if;
end
$$;

-- 테이블 단위 UPDATE 회수(재실행 안전 — 없는 권한 revoke는 no-op).
-- 열거식 재grant 0개(실측 근거는 파일 머리 참조): 양쪽 앱 모두 profiles 쓰기가 service role
-- 경유라 authenticated UPDATE 실사용이 없다. RLS profiles_update_own 정책은 무접촉(잔존해도
-- grant가 없으면 도달 불가 — 향후 열거 grant 재개 시 그대로 재사용 가능).
revoke update on public.profiles from anon, authenticated;

commit;
