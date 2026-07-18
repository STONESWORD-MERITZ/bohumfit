-- BOHUMFIT-225-04 / F-218-02 재작성 (BOHUMFIT-219-04 대체)
-- Classification: HARDENING (동작 변경; ★FitHere 코드 전환 전 실행 금지 — BLOCKED).
-- NOT in supabase/migrations: 자동 마이그레이션 경로로 절대 적용하지 않는다.
--
-- ★★ 선행 조건(미충족 시 실행 금지) ★★
-- FitHere가 현재 public.advisors를 select('*')로 직접 조회한다. 공개 목록/상세를
-- advisors_public 호환 경로로 전환·배포·검증한 뒤에만 이 파일을 실행한다.
-- 선행 없이 실행하면 FitHere 공개 전문가 목록/상세가 즉시 깨진다.
-- 또한 authenticated SELECT도 회수되므로, advisor 본인이 자기 advisors 행을
-- 직접 읽는 워크스페이스 경로가 있다면 그 경로의 대체(RPC/뷰)도 선행돼야 한다.
--
-- [실측 근거 — 2026-07-17 BOHUMFIT-225-00 / 218 §4, Human 제공]
-- 1. advisors 기본 테이블에 연락처 3컬럼(contact_phone, contact_kakao_openchat,
--    contact_kakao_channel)이 있고, anon 스모크에서 기본 테이블 행 조회가 성공했다
--    (218 §4). RLS는 행만 제한하고 컬럼을 숨기지 않으므로, SELECT grant가 남아
--    있는 한 RPC(225-02)를 우회한 연락처 직접 조회가 가능하다.
-- 2. 225-01 적용 후 advisors_public이 is_published 경계 포함 공개 표면이 된다.
--    이 파일은 그 표면으로의 일원화(기본 테이블 SELECT 회수)만 수행한다.
-- 3. 219-04와 실질 동일 내용 — 세션 가드 키 갱신('BOHUMFIT-225')·가드/확인쿼리
--    보강만. 드리프트 없음을 실측으로 확인했다.
--
-- [실행 전 검증쿼리]
--   -- (a) 현재 grant 백업(롤백 기준):
--   select table_name, grantee, privilege_type
--     from information_schema.role_table_grants
--    where table_schema='public' and table_name in ('advisors','advisors_public')
--      and grantee in ('anon','authenticated')
--    order by table_name, grantee, privilege_type;
--   -- (b) FitHere 배포본이 advisors 직접 SELECT를 더 이상 호출하지 않는지
--   --     (코드 릴리스 확인 + 네트워크 탭에서 /rest/v1/advisors? 직접 호출 0건).
--
-- [실행 방법] 같은 SQL Editor 세션에서:
--   set bohumfit.human_approved = 'BOHUMFIT-225';
-- 그 후 이 파일 전체를 실행한다(단일 트랜잭션·재실행 안전).
--
-- [실행 후 확인쿼리]
--   -- (c) advisors에 anon/authenticated SELECT가 없는지, advisors_public에는 있는지:
--   select table_name, grantee, privilege_type
--     from information_schema.role_table_grants
--    where table_schema='public' and table_name in ('advisors','advisors_public')
--      and grantee in ('anon','authenticated')
--    order by table_name, grantee, privilege_type;
--   -- (d) anon 키로 /rest/v1/advisors?limit=1 → 401/permission denied,
--   --     /rest/v1/advisors_public?limit=1 → 200 확인.
--   -- (e) FitHere 공개 목록/상세/연결, advisor 워크스페이스, admin 흐름 회귀 확인.
--
-- [롤백 절차]
--   1) 트랜잭션 중 오류 → 자동 abort(또는 rollback;). DB 무변경.
--   2) commit 후 장애 → 임시 복구:
--      grant select on public.advisors to anon, authenticated;
--      연락처 노출이 다시 열리므로 복구 시간을 최소화하고, FitHere 코드 원인을
--      수정한 뒤 재실행한다(219 §5-5 원칙 준용).

begin;

do $$
begin
  if current_setting('bohumfit.human_approved', true) is distinct from 'BOHUMFIT-225' then
    raise exception 'BOHUMFIT-225 Human approval setting is required';
  end if;
end
$$;

-- 드리프트 가드: 공개 표면(advisors_public)이 없으면 회수는 즉시 장애다.
do $$
begin
  if to_regclass('public.advisors_public') is null then
    raise exception 'BOHUMFIT-225-04 drift guard: public.advisors_public missing - run 225-01 first';
  end if;
end
$$;

revoke select on public.advisors from anon, authenticated;
grant select on public.advisors_public to anon, authenticated;

commit;
