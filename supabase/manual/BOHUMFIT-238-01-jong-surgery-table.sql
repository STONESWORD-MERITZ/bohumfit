set bohumfit.human_approved = 'BOHUMFIT-238';
-- ↑ 세션 가드(파일 첫 줄 실행문 — 232 신규 표준). 이 파일 전체를 한 번에 실행한다.
--
-- BOHUMFIT-238-01 — 종수술비 5종→1~5종 표준 환산표 시딩 (Human 실행용)
-- Classification: DATA SEED (신규 조회 전용 테이블; Human 승인·직접 실행 필수).
-- NOT in supabase/migrations: 자동 마이그레이션 경로로 절대 적용하지 않는다.
--
-- [배경] 원문에 종별 금액 없이 "5종 기준 최대금액"만 표기된 종수술비 담보를 표준
-- 환산표로 1~5종 세팅한다(2026-07-21 Human 확정·판독 검증 완료 표). 표는 상품별로
-- 정확하지 않은 "표준 환산 기준"이며 산출 화면·문서에 문구가 병기된다.
-- 백엔드는 이 테이블을 service role로 읽고, 미존재·실패 시 코드 내장 기본표
-- (coverage/jong_surgery.py DEFAULT_JONG_TABLE — 값 동일)로 fallback한다.
-- ★표 값을 수정하면 백엔드 재시작(캐시) 후 반영되고, 내장 기본표와 달라질 수 있음을
--   기록할 것(내장표는 배포 시점 스냅샷).
--
-- [실행 전 확인쿼리]
--   select to_regclass('public.jong_surgery_conversion');  -- 기존재 여부(재실행 안전)
--
-- [실행 후 확인쿼리]
--   -- (a) 10행·값 검수:
--   select * from public.jong_surgery_conversion order by base_man;
--   -- (b) 권한: anon/authenticated는 SELECT만(232 봉인 정합 — 공개 읽기 허용 테이블):
--   select grantee, privilege_type from information_schema.role_table_grants
--    where table_schema='public' and table_name='jong_surgery_conversion'
--      and grantee in ('anon','authenticated');
--
-- [롤백] drop table if exists public.jong_surgery_conversion;
--   (백엔드는 내장 기본표로 자동 fallback — 장애 없음)

begin;

do $$
begin
  if current_setting('bohumfit.human_approved', true) is distinct from 'BOHUMFIT-238' then
    raise exception 'BOHUMFIT-238 Human approval setting is required';
  end if;
end
$$;

create table if not exists public.jong_surgery_conversion (
  base_man  integer primary key,
  tier1_man integer not null,
  tier2_man integer not null,
  tier3_man integer not null,
  tier4_man integer not null,
  tier5_man integer not null,
  updated_at timestamptz not null default now()
);

alter table public.jong_surgery_conversion enable row level security;

drop policy if exists jong_surgery_conversion_read_all on public.jong_surgery_conversion;
create policy jong_surgery_conversion_read_all
on public.jong_surgery_conversion for select
using (true);

revoke all on public.jong_surgery_conversion from anon, authenticated;
grant select on public.jong_surgery_conversion to anon, authenticated;

-- Human 확정표(만원 단위) — 재실행 시 값 갱신(on conflict update: Human이 표를 고칠 때 재실행).
insert into public.jong_surgery_conversion
  (base_man, tier1_man, tier2_man, tier3_man, tier4_man, tier5_man)
values
  (100,  5, 10, 15,  50,  100),
  (200,  5, 10, 15,  50,  200),
  (300, 10, 30, 50, 100,  300),
  (400, 10, 30, 50, 100,  400),
  (500, 10, 30, 50, 100,  500),
  (600, 20, 30, 40, 150,  600),
  (700, 20, 30, 40, 150,  700),
  (800, 20, 50, 100, 500,  800),
  (900, 20, 50, 100, 500,  900),
  (1000, 20, 50, 100, 500, 1000)
on conflict (base_man) do update set
  tier1_man = excluded.tier1_man,
  tier2_man = excluded.tier2_man,
  tier3_man = excluded.tier3_man,
  tier4_man = excluded.tier4_man,
  tier5_man = excluded.tier5_man,
  updated_at = now();

commit;
