-- BOHUMFIT-231-01 — profiles.bohumfit_tier 신설 + role 기준 1회 백필 + 자기승격 봉인
-- Classification: SCHEMA CHANGE (추가 전용; Human 승인·직접 실행 필수).
-- NOT in supabase/migrations: 자동 마이그레이션 경로로 절대 적용하지 않는다.
-- 공유 BOHUMFIT/FitHere DB — 추가 전용 설계라 FitHere는 무변경·무영향(컬럼 1개 추가뿐,
-- role 컬럼·enum·기존 정책 무접촉).
--
-- ★★ 배포 순서 (역순 금지) ★★
-- 1) 이 SQL 실행 → 2) 실행 후 확인쿼리 → 3) BOHUMFIT-231 코드 push(Railway 자동 배포).
-- 역순(코드 먼저 배포) 시: 게이트가 bohumfit_tier 조회에 실패해 전원 customer(fail-closed)로
-- 동작한다 — 데이터 노출은 없지만 admin/내근직이 일시적으로 5회 제한을 받는다.
-- (이 안전망은 backend 테스트 test_missing_tier_column_fails_closed_to_customer로 보증)
--
-- [배경] profiles.role을 두 서비스가 다른 의미로 공유(보험핏=분석 등급, FitHere=advisor 신분).
-- 내근직이 FitHere 전문가 등록 시 role→advisor 전환 → 212 게이트 미인식 → 5회 제한 오적용
-- (hssong302984 사례 확정). 분석 등급을 bohumfit_tier로 분리하고 role은 FitHere 전용화한다.
--
-- [실행 전 확인쿼리]
--   -- (a) 현재 role 분포(백필 예상치 산출):
--   select role, count(*) from public.profiles group by role order by role;
--   -- (b) bohumfit_tier 기존재 여부(재실행 판단):
--   select 1 from information_schema.columns
--    where table_schema='public' and table_name='profiles' and column_name='bohumfit_tier';
--
-- [실행 방법] 같은 SQL Editor 세션에서:
--   set bohumfit.human_approved = 'BOHUMFIT-231';
-- 그 후 이 파일 전체를 실행한다(단일 트랜잭션·재실행 안전 — 재실행 시 백필은 건너뜀).
--
-- [실행 후 확인쿼리]
--   -- (c) tier 분포:
--   select bohumfit_tier, count(*) from public.profiles group by bohumfit_tier order by 1;
--   -- (d) role × tier 크로스탭(백필 검증 — admin→admin, internal→internal, 그 외→customer):
--   select role, bohumfit_tier, count(*) from public.profiles group by role, bohumfit_tier order by 1, 2;
--   -- (e) 컬럼 단위 UPDATE 권한 확인(bohumfit_tier가 anon/authenticated에 없어야 함):
--   select grantee, column_name, privilege_type from information_schema.column_privileges
--    where table_schema='public' and table_name='profiles'
--      and grantee in ('anon','authenticated') and privilege_type='UPDATE'
--    order by grantee, column_name;
--   -- (f) ★테이블 단위 UPDATE grant 잔존 확인(아래 '봉인 한계' 참조):
--   select grantee, privilege_type from information_schema.role_table_grants
--    where table_schema='public' and table_name='profiles'
--      and grantee in ('anon','authenticated') and privilege_type='UPDATE';
--
-- [★봉인 한계 — Human 확인 필요]
-- PostgreSQL에서 `revoke update (컬럼)`은 컬럼 단위 grant만 회수한다. (f)에서
-- 테이블 단위 UPDATE grant가 잔존하면 그 grant로 여전히 bohumfit_tier를 수정할 수 있다
-- (RLS의 profiles_update_own은 행 범위만 제한 — 컬럼은 못 막음).
-- (f) 결과가 비어 있지 않으면: 테이블 UPDATE를 회수하고 앱이 실제 수정하는 컬럼만
-- 열거식 grant하는 후속 SQL이 필요하다(양쪽 앱의 profiles UPDATE 사용 컬럼 실측 선행 —
-- FitHere 회귀 위험이 있어 이 파일에 포함하지 않음. Human/Chat 결정).
--
-- [롤백 절차]
--   1) 트랜잭션 중 오류 → 자동 abort(또는 rollback;). DB 무변경.
--   2) commit 후 되돌리려면: alter table public.profiles drop column if exists bohumfit_tier;
--      (231 코드가 이미 배포된 상태라면 드랍 후 게이트는 전원 customer(fail-closed)로 동작 —
--       코드도 함께 롤백하거나 재실행으로 복구할 것.)

begin;

do $$
begin
  if current_setting('bohumfit.human_approved', true) is distinct from 'BOHUMFIT-231' then
    raise exception 'BOHUMFIT-231 Human approval setting is required';
  end if;
end
$$;

-- 드리프트 가드 + 컬럼 신설 + 1회 백필(신설된 경우에만 — 재실행 시 기존 tier 값을 덮지 않음).
do $$
declare
  col_existed boolean;
  backfilled integer;
begin
  if to_regclass('public.profiles') is null then
    raise exception 'BOHUMFIT-231-01 drift guard: public.profiles missing';
  end if;
  if not exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'profiles' and column_name = 'role'
  ) then
    raise exception 'BOHUMFIT-231-01 drift guard: profiles.role missing - backfill source absent';
  end if;

  select exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'profiles' and column_name = 'bohumfit_tier'
  ) into col_existed;

  if col_existed then
    raise notice 'BOHUMFIT-231-01: bohumfit_tier already exists - creation/backfill skipped (idempotent re-run)';
  else
    execute $ddl$
      alter table public.profiles
        add column bohumfit_tier text not null default 'customer'
        constraint profiles_bohumfit_tier_check
        check (bohumfit_tier in ('admin', 'internal', 'customer'))
    $ddl$;

    -- 백필: 컬럼 신설 직후 1회만. role=admin→admin, role=internal→internal, 그 외(customer·advisor 등)는
    -- default 'customer' 유지. 이후 등급 변경은 role과 무관하게 bohumfit_tier만 갱신한다(운영 절차 표준).
    update public.profiles
       set bohumfit_tier = role::text
     where role::text in ('admin', 'internal');
    get diagnostics backfilled = row_count;
    raise notice 'BOHUMFIT-231-01: bohumfit_tier created; backfilled % row(s) from role', backfilled;
  end if;
end
$$;

-- 자기승격 봉인: 컬럼 단위 UPDATE 권한 회수(재실행 안전 — 없는 권한 revoke는 no-op).
-- ★위 "[봉인 한계]" 참조: 테이블 단위 UPDATE grant가 잔존하면 이 문장만으로는 불충분 —
--   실행 후 (f) 확인쿼리로 잔존 여부를 반드시 확인한다.
revoke update (bohumfit_tier) on public.profiles from anon, authenticated;

commit;
