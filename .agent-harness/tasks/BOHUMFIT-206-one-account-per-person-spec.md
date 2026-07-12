# BOHUMFIT-206 "1인 1계정" 설계 명세 — SMS OTP 서버검증 + 본인인증 번호 유일 키

Owner flow: Claude Chat -> Cowork(조사·설계) -> Codex(문서 커밋)
Current owner: Codex (문서만 stage/commit/push — 코드 게이트 불필요)
성격: **조사·설계 전용(코드 0)**. src/·backend/ 무접촉(읽기만).

> ⚠️ **[스펙 변경 예고]** 본 설계는 BOHUMFIT-097 완화 결정("번호 소유 확인 수준, 중복 hard-block 제거,
> 1인 1계정은 이메일 기준")을 **재강화**하는 방향이다(중복 번호 가입 차단 복원 + 실제 OTP 검증).
> 구현 태스크(207~209) 착수 시 태스크 파일에 "[스펙 변경]"을 명시하고 `decisions.md`에 동시 기록해야 한다.
> 본 문서는 제안이며 스키마·비용·정책의 최종 결정은 Human 게이트다.

## Intent

모든 가입 경로(이메일·카카오·구글)가 **본인인증된 휴대폰 번호를 유일 키**로 거치게 하고,
중복 번호 가입을 차단한다. 현재 휴대폰 인증이 클라이언트 목업(번호만 넣으면 통과)인 문제를
서버측 SMS OTP 검증으로 교체한다. 목표 효과: 무한 계정 생성(무료 체험 어뷰징) 차단,
민감정보(병력) 서비스의 계정 신뢰 기반 확보.

---

## S0 현행 실사 (2026-07-12, 저장소 읽기 전용 — 커밋 확정은 Codex `git show HEAD:` 대조)

### S0-1. 가입 플로우 3경로

| 경로 | 진입 | 흐름 | 폰인증 접점 |
|---|---|---|---|
| 이메일 | `src/pages/Signup.tsx` | `supabase.auth.signUp`(hCaptcha 키 있으면 captchaToken) → 인증 메일 → 로그인 | 가입 화면에 "휴대폰 본인인증(필수)" UI가 있으나 **완전 목업**(아래 S0-2) |
| 카카오 | `Signup.tsx`/`Login.tsx` `signInWithOAuth({provider:"kakao"})` (BOHUMFIT-204: OAuth가 주 경로) | 첫 로그인 시 `auth.users` INSERT → `handle_new_user` 트리거로 `profiles` 행 생성(phone_verified=false) | 로그인 후 게이트에서만 |
| 구글 | 〃 `google` | 〃 | 〃 |

공통 게이트(클라이언트): `src/components/ProtectedRoute.tsx` + `src/lib/usePhoneGate.tsx`(공개 랜딩 `/`)가
`profiles.phone_verified`를 조회해 미인증이면 `/phone-verify`로 보냄(086 판정 로직 `src/lib/phoneGate.ts`,
행 없음=미인증, `role='internal'` 우회, 조회 오류만 deploy-safe 통과).

### S0-2. 휴대폰 인증 목업 위치 (2곳)

1. **클라 목업(가입 화면)**: `src/pages/Signup.tsx` L29-37 `requestPhoneVerify()` —
   10자리 이상이면 `setPhoneVerified(true)`. **서버 전송·검증·저장 전혀 없음**(번호는 가입 시 어디에도 저장 안 됨).
   가입 버튼 활성화 조건일 뿐이며, 실제 게이트는 로그인 후 별도로 다시 인증을 요구한다(UX 이중 부담 + 가짜 안심).
2. **서버 스텁(실제 마킹 지점)**: `backend/main.py` L832-861 `POST /auth/verify-phone` (BOHUMFIT-074 스텁) —
   JWT 필수, hCaptcha 조건부(`HCAPTCHA_SECRET` 있을 때만), 레이트리밋(user 10/min + IP `5/minute,20/hour`).
   받은 번호를 **아무 검증 없이** `profiles.upsert({id, phone, phone_verified: true})`.
   ⚠️ 잠재 결함: upsert 예외를 `logger.warning`으로 삼키고 `{"verified": true}`를 반환 —
   DB unique 위반 등 실패 시 사용자는 "완료" 메시지를 보지만 게이트는 계속 미인증(무한 루프 소지). 207에서 수정.

### S0-3. `profiles.phone` / `phone_verified` 컬럼·인덱스 상태

- `supabase/migrations/20260620000001_phone_verification.sql`(074): `phone TEXT`, `phone_verified BOOLEAN NOT NULL DEFAULT false` 추가.
- `...02_backfill_profiles_phone.sql`(085): `handle_new_user()` 트리거(auth.users INSERT→profiles 행) + 기존 계정 백필.
- `...03_profiles_select_policy.sql`(086): RLS 활성 + 본인 SELECT 정책(클라 게이트 판정용).
- `...04_phone_unique.sql`(088): 부분 UNIQUE 인덱스 `profiles_phone_verified_unique ON profiles(phone) WHERE phone_verified=true AND phone IS NOT NULL`.
- ★ 마이그레이션은 전부 **Human 수동 실행** 방식. 097 결정(decisions.md L108)이 "088 인덱스 제거 필요(Human SQL)"를
  남겼으나 **실행 여부 기록 없음 → 현재 DB에 인덱스가 있는지 불명**. 208 착수 전 확인 필수:
  ```sql
  select indexname from pg_indexes where schemaname='public' and tablename='profiles';
  select phone, count(*) from public.profiles
   where phone_verified = true and phone is not null group by phone having count(*) > 1;
  ```
- 앱단 중복 차단은 097에서 제거됨(`backend/phone_guard.py`는 미사용 보존, `PhoneVerify.tsx`의 409 처리 분기는 잔존).

### S0-4. SMS 발송(sms_provider)·Supabase 폰 설정

- 저장소 전체에 Twilio/SMS/OTP 연동 코드·환경변수 **0건**(`.env.example`에 Supabase·hCaptcha 키만).
- Supabase Auth의 Phone provider(=대시보드 Authentication→Sign In/Up→Phone: enable 여부, `sms_provider`,
  OTP 만료/길이, **phone_autoconfirm**)는 저장소 밖 설정이라 **코드로 확인 불가 — Human이 대시보드에서 확인**.
  - ★ `phone_autoconfirm`이 ON이면 OTP 없이 즉시 확인 처리되어 목업과 다름없음 → 도입 시 **반드시 OFF**.
- 결제는 토스페이먼츠 기사용(`backend/tosspayments.py`) — 087 문서의 "토스 생태계 일원화" 논거와 연결.

### S0-5. 서버측 강제 부재 (게이트는 클라이언트뿐)

`backend/main.py`의 보호 API(analyze L1554, coverage L1369, history, billing 등)는 전부 `verify_jwt`만 요구 —
**`phone_verified` 검사가 없다.** 즉 유효 JWT만 있으면 `/phone-verify`를 안 거치고 API 직접 호출 가능
(구글 계정 무한 생성 → 클라 게이트 무시 → 무료 분석 체험 어뷰징이 현재도 성립). 204의 IP 레이트리밋이 유일한 완화.
→ S3에서 서버측 의존성(`require_verified_phone`)을 신설한다.

### S0-6. 기존 산출물 연결

- `docs/identity-verification-plan.md`(087): PASS/CI 기반 실본인확인 조사·추천(포트원 1순위, 비용은 견적 필요).
  CI 기반이 "진짜 1인 1계정"의 종착지라는 결론 — 본 206은 그 **전 단계(번호 소유 확인 강화)**로 위치.
- 공유 Supabase 주의(decisions.md L137-139): BOHUMFIT/FitHere가 인스턴스·일부 데이터 경계 공유.
  RLS/인덱스/트리거 변경은 양쪽 앱 검토 + 저트래픽 시간대 + 승인 운영자 실행.
  ★ **auth.users·profiles를 FitHere와 공유하는지가 유일성 경계를 결정** — Human 확인 필수(아래 S2·Human 목록).

---

## S1 SMS OTP 설계 — 번호 입력 → SMS 코드 발송 → 서버 검증 → phone_verified=true

공통 원칙: **클라 목업 제거, 검증의 진실원천은 서버(또는 Supabase Auth)**. 클라이언트가 "인증됨"을
자가 신고하는 어떤 경로도 남기지 않는다. 발송·검증 모두 레이트리밋 + (키 있으면) hCaptcha 유지.

### 옵션 A — Supabase Auth Phone provider 활용 (권장 1안)

- 설정(코드 아님, 대시보드): Phone provider enable + `sms_provider`(Twilio Verify 권장 — OTP 생성·재발송·
  만료를 Twilio가 관리) + `phone_autoconfirm` **OFF** + OTP rate limit 확인.
- 흐름(이미 로그인된 계정에 번호를 붙이는 **phone_change** 흐름 — 3경로 공통 게이트와 정합):
  1. `/phone-verify`에서 번호 입력 → `supabase.auth.updateUser({ phone: '+82...' })` → Supabase가 SMS OTP 발송
  2. 코드 입력 → `supabase.auth.verifyOtp({ phone, token, type: 'phone_change' })`
  3. 성공 시 `auth.users.phone` 확정 + `phone_confirmed_at` 세팅(Supabase가 관리)
  4. 프런트가 `POST /auth/verify-phone` 호출 → **서버가 Supabase Admin으로 `auth.users`의
     `phone`/`phone_confirmed_at`을 직접 조회·대조한 뒤에만** `profiles.phone/phone_verified=true` 동기화
     (클라 자유 텍스트 번호를 믿는 현행 계약 폐기 — 서버가 auth 원본에서 읽는다)
- 장점: OTP 저장·만료·브루트포스 방어를 Supabase/Twilio가 처리(자체 OTP 테이블 불필요),
  `auth.users.phone`은 **Supabase 프로젝트 수준에서 이미 유일** → S2 유일성의 1차 방어를 공짜로 획득.
  supabase-js `^2.105.1`(현행)로 충분.
- 단점/확인 필요: ① Twilio 한국(+82) SMS 단가·전달률·**국내 발신번호 사전등록제 대응** —
  변동 값이라 본 문서에 수치 확정 기재하지 않음, **Human 견적·규제 확인 필수**.
  ② 공유 프로젝트면 유일성 경계가 "BOHUMFIT+FitHere 합산"이 됨(S2).
  ③ SMS 국제 발송 경유 시 지연·스팸함 이슈 가능 — 파일럿 테스트 항목.

### 옵션 B — 커스텀 OTP (FastAPI + 국내 SMS 사업자)

- 신규 테이블(★Human 승인): `phone_verifications(id, user_id, phone, code_hash, expires_at, attempts, verified_at, created_at)`
  — 코드 원문 저장 금지(해시), 만료 3~5분, 시도 5회 제한, 재발송 쿨다운 60초.
- 신규 엔드포인트: `POST /auth/phone/request-otp`(발송) / `POST /auth/phone/verify-otp`(검증→profiles 마킹).
  기존 slowapi(user+IP)·hCaptcha 패턴 재사용. 발송 실패·만료·초과는 명확한 409/429/400 한국어 응답.
- SMS 사업자: 국내(솔라피/알리고/NHN Cloud 등 — 발신번호 등록 용이, 국내 단가 우위 일반적이나 **수치는 견적 필요**).
- 장점: 국내 발송 현실(전달률·발신번호·단가) 대응 유연, 정책(쿨다운·차단) 자유.
- 단점: OTP 보안 구현·운영 부담 자체 부담, 테이블 추가(Human), 코드량 최대.

### 권장

**A(Supabase+Twilio Verify)를 1차 채택**하되, `/auth/verify-phone`의 서버 계약을
"인증 수단이 무엇이든 → 서버가 원천 확인 → profiles 마킹" 인터페이스로 유지해
Twilio 비용·전달률 문제가 확인되면 B(국내 사업자)로 교체 가능하게 한다.
단 **Twilio 한국 발신 비용은 Human 결정 항목**이므로 A/B 최종 선택은 견적 후 확정.

---

## S2 번호 유일성 — 본인인증된 번호 = 계정당 유일 키

### 유니크 제약 위치 옵션 (★스키마 변경은 전부 Human 승인 — 본 문서는 제안만)

| 안 | 내용 | 장점 | 단점/리스크 |
|---|---|---|---|
| ① `auth.users.phone` (옵션 A 부산물) | Supabase가 프로젝트 수준 유일 보장 | 추가 스키마 0 | **FitHere와 auth 공유 시 두 앱 합산 유일** — 정책 의도 확인 필요. Supabase 내부 정책이라 세밀 제어 불가 |
| ② `profiles` 부분 UNIQUE 인덱스(088 재사용) | `ON profiles(phone) WHERE phone_verified=true AND phone IS NOT NULL` — SQL 이미 저장소에 있음(`...04_phone_unique.sql`) | 즉시 적용 가능·멱등·검증된 SQL | profiles를 FitHere가 공유하는지 확인 필요. 097이 요청한 drop 실행 여부부터 확인 |
| ③ 별도 `verified_phones` 테이블 | `phone PK(정규화 E.164), user_id UNIQUE, method('sms_otp'/'pass_ci'), ci_hash NULL, verified_at, released_at NULL` | 이력·번호변경(soft-release)·앱 스코프 컬럼·CI 확장(087) 대비 최적 | 신규 테이블+RLS+조인 — 가장 큰 변경. New Table Checklist(decisions.md) 적용 필요 |

**권장 조합**: 단기 = ②(+옵션 A면 ①이 자동 동반). 장기(PASS/CI 도입 시) = ③으로 승격해 `ci_hash` 수용.
어느 안이든 **번호 정규화 규칙**을 서버 단일 함수로 통일: 숫자만 추출 → `010XXXXXXXX` ↔ `+8210XXXXXXXX`
변환 일원화(현행 profiles.phone은 자유 형식 → 208에서 기존 데이터 정규화 스크립트 제안 포함).

### 충돌 처리(중복 번호 가입 차단)

- verify 시점에 동일 정규화 번호의 `phone_verified=true` **타 계정** 존재 → `409` + 한국어 안내
  ("이미 인증에 사용된 번호입니다…") — `backend/phone_guard.py`(보존 모듈)·`PhoneVerify.tsx` 409 분기 재활성.
  `role='internal'` 우회는 기존 정책 유지.
- DB 인덱스는 최후 방어선, 앱 검사는 UX용 — 097이 겪은 "정상 신규 가입 차단 버그"의 원인이었던
  **선점 목업 데이터**가 재발하지 않도록, 208 적용 전에 기존 `phone_verified=true` 행 전수 점검(아래 순서 근거).
- 번호 변경 플로우(권장·후속): 새 번호 OTP 성공 시 이전 번호 해제(②안: 구 행 phone_verified 유지 문제 없음 —
  같은 계정 갱신, ③안: released_at 마킹). 계정 탈퇴 시 번호 해제 정책 포함.

### 공유 Supabase(BOHUMFIT/FitHere) 영향 — 적용 전 필수 확인

- `profiles`(그리고 auth.users)를 FitHere가 **함께 쓰는지** Human 확인. 함께 쓴다면:
  유일성 경계(두 앱 합산인지/앱별인지) 결정, 인덱스 생성은 **저트래픽 시간대 + 양쪽 앱 핵심 흐름 사전·사후 확인**
  (decisions.md 공유 Supabase 절차 준수). 앱별 유일이 필요하면 ③안에 `app` 컬럼을 두는 변형 제시.

---

## S3 경로별 강제

| 경로 | 설계 |
|---|---|
| 이메일 가입 | **Signup.tsx의 목업 폰 UI 제거**(서버 미전송 가짜 단계 — 혼란·허위 안심만 유발). 가입은 이메일+약관만으로 가볍게, OTP는 로그인 직후 게이트(`/phone-verify`)에서 1회 필수. *가입 화면에서 OTP까지 끝내는 안은 비로그인 상태 SMS 발송 남용(요금·스미싱 악용) 위험이 커서 비권장 — 게이트 일원화가 안전.* |
| 카카오 | 게이트 동일 적용. 카카오 계정이 전화번호 기반이라도 Supabase로 넘어오는 정보에 검증된 번호·CI가 없으므로 **OTP 이중확인 권장**(코드 단순·예외 없음). 면제 여부는 Human 결정(면제 시 카카오만 무한생성 구멍 잔존). |
| 구글 | **OTP 강제 — 무한 생성 차단의 핵심**(구글 계정은 무한 생성 가능). 게이트 동일. |
| **서버측 강제(신설)** | `require_verified_phone` FastAPI 의존성: `verify_jwt` 뒤에 `profiles.phone_verified` 확인(admin 클라이언트, `role='internal'` 우회), 미인증이면 403 + 안내. 적용 대상: `/analyze`, `/coverage/analyze`, `/history/*`, `/report/*` 등 **비용·민감정보 API 전부**(공개/헬스/빌링 조회는 제외 검토). 클라 게이트는 UX, 서버 의존성이 실제 방어선. per-request 조회 부하는 낮음(단일 PK 조회)이나 필요 시 짧은 TTL 캐시. |
| 미인증 상태 이용 범위 | 현행 클라 게이트 유지(로그인 필수 화면 전부) + 위 서버 의존성. 공개 페이지(가이드·링크·샘플)는 영향 없음. |

---

## S4 PASS(CI) 확장 여지 — 지금은 SMS OTP로 충분, 접합점만 고정

- SMS OTP는 "**번호 소유** 확인"까지다. 타인 명의 번호·선불폰 우회, 명의도용 차단은
  **CI(연계정보) 기반 실본인확인**(087 문서: 포트원 통합/휴대폰 본인인증 추천, 계약·견적 Human)에서 완성.
- 접합점(207~209 구현 시 지켜둘 것):
  1. `/auth/verify-phone`(또는 후속 verify-otp)의 서버 계약을 "수단 → 서버 원천 확인 → profiles 마킹"으로 유지
     → PASS 도입 시 같은 자리에서 CI 콜백 검증으로 교체(087 §3.1 흐름).
  2. 유일 키 저장소(②/③안)에 `method`('sms_otp'→'pass_ci')와 `ci_hash`(③안) 자리를 예약 —
     도입 시 유일성 기준을 번호 → CI로 승격.
  3. `PhoneVerify.tsx`는 "인증 수단 카드" 구조로 두어 SMS OTP ↔ PASS 버튼 교체만으로 전환.
- 도입 시점·예산은 Human(사업자 승인·대행사 계약 선행 — 087 선행조건 체크리스트 참조).

---

## S5 구현 분할 (순차)

| 태스크 | 내용 | 선행 조건 |
|---|---|---|
| **BOHUMFIT-207** OTP 서버검증 | 제공자 결정 반영(A: 대시보드 설정+phone_change 연동 / B: phone_verifications+발송·검증 API). `/auth/verify-phone`을 "서버 원천 확인" 계약으로 재작성 + **예외 삼킴(silent success) 수정**, Signup 목업 UI 제거, PhoneVerify OTP 입력 UI(발송→입력→재발송 쿨다운), 실패·만료·한도 한국어 응답, 회귀 테스트 | Human: S1 제공자·비용 결정, 대시보드 설정(autoconfirm OFF) 또는 SMS 계약 |
| **BOHUMFIT-208** 번호 유일 제약 | 정규화 함수 + 기존 데이터 점검·정리 절차 → 유니크 제약 적용(② 인덱스 SQL 제안, 실행은 Human) → 서버 409 복원(phone_guard 재활성) + 프런트 안내. **[스펙 변경] 표기 + decisions.md 기록**(097 재강화) | 207 완료(아래 순서 근거), Human: 인덱스 현존 확인·중복 정리·공유 Supabase 절차 |
| **BOHUMFIT-209** 경로별 강제 | `require_verified_phone` 서버 의존성 + 적용 엔드포인트 확정·적용 + 클라 게이트 정합(403 수신 시 /phone-verify 유도) + 회귀 테스트(미인증 403·internal 우회·공개 API 무영향) | 207 완료(실OTP 없이 서버 강제만 먼저 켜면 기존 미인증 사용자 전면 차단 혼란) |
| (후속) BOHUMFIT-210 | 번호 변경·해제 플로우(soft-release), 탈퇴 시 해제 | 208 |
| (후속) BOHUMFIT-211 | PASS/CI 실연동(087 계획 실행, 유일 키 CI 승격) | 사업자 승인·계약(Human) |

**순서 근거**: 208(유니크)을 207(실OTP)보다 먼저 켜면 **목업 인증으로 임의 번호를 선점**하는 어뷰징이
가능해지고(097 버그 재발 형태), 209(서버 강제)를 207보다 먼저 켜면 실인증 수단이 없는 상태로
기존 사용자가 잠긴다. 따라서 207 → 208 → 209 고정.

---

## Human 결정 필요 목록

1. **유니크 제약 위치**: ②profiles 부분 인덱스(단기 권장) / ③verified_phones 테이블(장기) / ①auth.users 의존 —
   그리고 **FitHere와 auth.users·profiles 공유 여부 + 유일성 경계(두 앱 합산 vs 앱별)** 확인.
2. **SMS 제공자·비용**: Twilio 한국 발신 단가·발신번호 사전등록 대응 vs 국내 사업자(솔라피 등) 견적 비교
   (본 문서는 단가 수치를 확정 기재하지 않음 — 조사 시점 변동값).
3. **카카오 경로 OTP 이중확인 여부**(권장: 적용).
4. **PASS(CI) 도입 시점·예산**(087 선행조건: 사업자 승인·대행사 계약).
5. **사전 DB 확인·정리**: `profiles_phone_verified_unique` 현존 여부(097 drop 실행됐는지),
   `phone_verified=true` 중복·목업 데이터 전수 점검 및 정리 방침(기존 사용자 재인증 요구 여부 포함).
6. Supabase 대시보드: Phone provider 활성화, `sms_provider` 설정, **phone_autoconfirm OFF** 확인.
7. 097 완화 스펙의 재강화([스펙 변경]) 승인.

## 산출·검증·커밋

- 산출물: 본 문서 1개(코드 0, src/·backend/ 무접촉). 빌드·테스트 게이트 불필요(마크다운 정합만).
- Codex: `git status --short -uall` 확인 → 본 문서 + handoff/locks만 stage →
  커밋 메시지: `docs(BOHUMFIT-206): 1인 1계정(SMS OTP + 번호 유일성) 설계 명세` → push.
