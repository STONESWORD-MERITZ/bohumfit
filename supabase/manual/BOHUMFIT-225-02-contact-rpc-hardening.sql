-- BOHUMFIT-225-02 / F-218-04 재작성 (BOHUMFIT-219-02 대체)
-- Classification: HARDENING (동작 변경; Human 승인·직접 실행 필수).
-- NOT in supabase/migrations: 자동 마이그레이션 경로로 절대 적용하지 않는다.
-- 공유 BOHUMFIT/FitHere DB: 저트래픽 창에서 함수 정의 백업(Q5) 후 실행.
--
-- [실측 근거 — 2026-07-17 BOHUMFIT-225-00 Q5, Human 제공]
-- 1. 라이브 get_advisor_contact는 is_active+is_verified+auth.uid() NOT NULL만 확인.
--    is_published 경계와 연결기록 조건이 없어, 로그인만 하면 어떤 활성 전문가의
--    연락처든 RPC로 조회 가능(F-218-04 미해결 상태 확인).
-- 2. 라이브에 has_consult_with_advisor(uuid)가 이미 존재(definer,
--    consult_requests OR connection_requests의 requester_id = auth.uid() 확인)
--    → 219-02의 connection_requests 단독 EXISTS 대신 이 함수를 재사용한다
--    (Chat 지시 반영; consult 경로도 연결기록으로 인정 — 제품 의미는 Human이
--    219 §7 "연결 성사" 결정과 함께 최종 확인).
-- 3. 라이브 proacl상 anon에 EXECUTE가 있다 → 회수한다(authenticated만 유지).
-- 4. search_path를 'public' 단독에서 public, pg_temp로 보강(219-02 설계 유지).
-- ※ has_consult_with_advisor 자체의 PUBLIC/anon EXECUTE도 라이브에 존재하나
--    이 파일 범위 밖 — 기록만(태스크 §실측 매핑 참조), 변경은 Human 결정.
--
-- [실행 전 검증쿼리]
--   -- (a) 현 함수 정의 백업(결과는 저장소 커밋 금지):
--   select pg_get_functiondef('public.get_advisor_contact(uuid)'::regprocedure);
--   -- (b) 의존 함수 존재:
--   select to_regprocedure('public.has_consult_with_advisor(uuid)');
--
-- [실행 방법] 같은 SQL Editor 세션에서:
--   set bohumfit.human_approved = 'BOHUMFIT-225';
-- 그 후 이 파일 전체를 실행한다(단일 트랜잭션·재실행 안전).
--
-- [실행 후 확인쿼리]
--   -- (c) 새 정의에 is_published·has_consult_with_advisor 포함 확인:
--   select pg_get_functiondef('public.get_advisor_contact(uuid)'::regprocedure);
--   -- (d) EXECUTE 권한: anon 없음, authenticated 있음:
--   select routine_name, grantee, privilege_type
--     from information_schema.role_routine_grants
--    where routine_schema='public' and routine_name='get_advisor_contact';
--   -- (e) 동작: 연결기록 없는 테스트 계정 → 0행 / 본인 연결기록 생성 후 → 1행 /
--   --     is_published=false 전문가 → 연결기록 있어도 0행. (운영 테스트 계정만 사용)
--
-- [롤백 절차]
--   1) 트랜잭션 중 오류 → 자동 abort(또는 rollback;). DB 무변경.
--   2) commit 후 문제 발생 → (a)에서 백업한 정의로 create or replace 복원 후,
--      필요 시 grant execute on function public.get_advisor_contact(uuid) to anon;
--      (구 권한 복원은 노출 재개이므로 복원 시간 최소화 — 219 §5 원칙 준용.)

begin;

do $$
begin
  if current_setting('bohumfit.human_approved', true) is distinct from 'BOHUMFIT-225' then
    raise exception 'BOHUMFIT-225 Human approval setting is required';
  end if;
end
$$;

-- 드리프트 가드: 참조 대상이 실DB에 없으면 재정의 전에 즉시 실패시킨다.
do $$
begin
  if to_regprocedure('public.has_consult_with_advisor(uuid)') is null then
    raise exception 'BOHUMFIT-225-02 drift guard: public.has_consult_with_advisor(uuid) missing';
  end if;
  if exists (
    select 1
    from (values ('contact_phone'), ('contact_kakao_openchat'),
                 ('contact_kakao_channel'), ('is_published')) as need(col)
    where not exists (
      select 1 from information_schema.columns ic
      where ic.table_schema = 'public'
        and ic.table_name = 'advisors'
        and ic.column_name = need.col
    )
  ) then
    raise exception 'BOHUMFIT-225-02 drift guard: advisors contact/is_published column missing - rerun 225-00';
  end if;
end
$$;

-- 연락처 RPC: 공개 승인(is_published) + 본인 연결기록(has_consult_with_advisor)
-- 이 모두 있을 때만 반환. 반환 컬럼 shape는 라이브와 동일(3컬럼).
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
    and public.has_consult_with_advisor(p_advisor_id);
$$;

revoke all on function public.get_advisor_contact(uuid) from public, anon;
grant execute on function public.get_advisor_contact(uuid) to authenticated;

commit;
