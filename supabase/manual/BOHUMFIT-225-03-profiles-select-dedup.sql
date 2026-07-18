-- BOHUMFIT-225-03 / F-218-06 재작성 (BOHUMFIT-219-03 대체 — 범위 대폭 축소)
-- Classification: HARDENING (정책 정리; Human 승인·직접 실행 필수).
-- NOT in supabase/migrations: 자동 마이그레이션 경로로 절대 적용하지 않는다.
--
-- [실측 근거 — 2026-07-17 BOHUMFIT-225-00 Q5·Q6, Human 제공]
-- 219-03이 전제한 상황과 실DB가 크게 달라, 실제 필요한 변경은 1건뿐이다.
-- 1. ★219-03은 public.is_admin()·public.owns_advisor()를 참조하지만 실DB에
--    두 함수 모두 부재(Q5 결과: get_advisor_contact·has_consult_with_advisor만 존재)
--    → 219-03을 그대로 실행했으면 42883(function does not exist)으로 실패 예정이었다.
-- 2. Q6 실측상 소유자 정책은 대부분 이미 auth.uid() 스코프로 정상이다:
--    advisor_applications(applicant_id 기준 own/admin), drafts/certifications/
--    review_links(auth.uid() = advisor_id), contact_clicks·analysis_history
--    (user_id = auth.uid(), analysis_history는 canonical 4정책 확인).
--    admin 분기도 함수가 아니라 inline EXISTS(profiles.role='admin')로 구현돼 있다.
--    → 219-03의 "전면 정책 교체"는 불필요하며, 강행 시 정상 정책을 부수는
--      위험만 있다. 이 파일은 교체하지 않는다.
-- 3. 실제 남은 문제 = profiles SELECT 중복 2건(F-218-06):
--    `profiles_select_own`과 `본인 프로필 조회` — qual이 (auth.uid() = id)로 동일한
--    permissive 중복. 정책 변경 시 한쪽만 고쳐지는 드리프트 위험 → 1개로 통합.
--    canonical로 `profiles_select_own`을 남기고 legacy 한글명 정책만 제거한다.
-- 4. 기록만(이 파일에서 변경하지 않음 — Human/Chat 결정 필요, 태스크 §실측 매핑 참조):
--    certifications 소유자 SELECT 정책 부재, connection_requests requester
--    SELECT 정책 부재, connection_requests INSERT check에 is_published 미포함,
--    drafts/certifications/review_links의 `auth.uid() = advisor_id` 의미
--    (advisors.id = 소유자 uid 전제) 확인 필요.
--
-- [실행 전 검증쿼리]
--   -- (a) 두 정책의 qual이 실제로 동일한지 최종 확인(결과 저장소 커밋 금지):
--   select policyname, cmd, roles, qual from pg_policies
--    where schemaname='public' and tablename='profiles' and cmd='SELECT'
--    order by policyname;
--   -- 기대: 2행, qual 모두 (auth.uid() = id). 다르면 실행 중단 후 재보고.
--
-- [실행 방법] 같은 SQL Editor 세션에서:
--   set bohumfit.human_approved = 'BOHUMFIT-225';
-- 그 후 이 파일 전체를 실행한다(단일 트랜잭션·재실행 안전).
--
-- [실행 후 확인쿼리]
--   -- (b) profiles SELECT 정책이 profiles_select_own 1개만 남았는지:
--   select policyname from pg_policies
--    where schemaname='public' and tablename='profiles' and cmd='SELECT';
--   -- (c) 회귀: 일반 계정 로그인 → 본인 프로필 조회 정상, 타인 프로필 0행.
--   --     BOHUMFIT 로그인/phone gate/billing, FitHere 프로필 화면 확인.
--
-- [롤백 절차]
--   1) 트랜잭션 중 오류 → 자동 abort(또는 rollback;). DB 무변경.
--   2) commit 후 문제 발생 → 제거한 legacy 정책 복원:
--      create policy "본인 프로필 조회" on public.profiles
--        for select using (auth.uid() = id);

begin;

do $$
begin
  if current_setting('bohumfit.human_approved', true) is distinct from 'BOHUMFIT-225' then
    raise exception 'BOHUMFIT-225 Human approval setting is required';
  end if;
end
$$;

-- 안전 가드: canonical 정책이 없으면 유일한 SELECT 정책을 지워버릴 수 있으므로 중단.
do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'profiles'
      and policyname = 'profiles_select_own'
      and cmd = 'SELECT'
  ) then
    raise exception 'BOHUMFIT-225-03 guard: canonical profiles_select_own missing - abort to keep at least one SELECT policy';
  end if;
end
$$;

-- 중복 legacy 정책만 제거(qual 동일 (auth.uid() = id) — Q6 실측).
drop policy if exists "본인 프로필 조회" on public.profiles;

commit;
