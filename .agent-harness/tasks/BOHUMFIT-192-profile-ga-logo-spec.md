# BOHUMFIT-192 — 표지 프로필 연동·GA 대리점 선택·CI 로고 재구축 설계 명세

Owner flow: Claude Chat -> Cowork -> Codex
Current owner: **Human**(스키마·GA출처·로고정책 결정) → 이후 Codex(문서 커밋)
분류: 조사·설계 전용 · **코드 0** · 병렬 안전(189~191 code scope 무접촉)
조사 기준: HEAD `1f5b498`(git log 188까지, 189~191 미포함) · src/·backend 무접촉(Read/grep만)

---

## 0. 목적과 배경

191 표지(보장분석 리모델링 제안서의 표지)에 다음 3가지를 구현하기 위한 데이터·스키마·법적 요건을 조사·설계한다.

1. **프로필 자동채움** — 표지의 소속(GA)·설계사명·연락처를 설계사 계정 프로필에서 자동으로 채운다.
2. **GA 대리점 선택** — 설계사가 자신이 소속된 GA 법인대리점을 목록에서 선택한다.
3. **GA CI 로고 표시** — 선택한 GA의 CI 로고를 표지에 표시한다.

본 문서는 **설계 명세**이며 코드를 변경하지 않는다. DB 스키마 변경·GA 목록 출처·로고 제공 정책은 Human 승인 게이트다(→ `BOHUMFIT-192-human-decisions.md`). 실제 구현은 패킷 193/194/195로 분할한다.

### ★핵심 전제 (반드시 인지)

- **191 표지는 아직 HEAD에 없다.** git log는 188에서 끝나고 189~191은 병렬 Codex 배치가 진행 중이다(locks.md Active에 189 존재). 따라서 본 명세는 "병렬로 만들어질 표지가 **소비할** 데이터·슬롯 계약"으로 설계했다. 191 구현체가 확정되면 슬롯 필드명 1:1 대조가 필요하다(패킷 195).
- **공유 Supabase 인스턴스(BOHUMFIT/FitHere).** `profiles` 테이블은 두 앱이 공유한다. profiles 스키마를 바꾸면 **FitHere에도 동시 영향**을 준다. → 스키마 격리 설계 필수(§S1-2).
- **role='internal' = 설계사(내부/유료).** 표지 자동채움 대상은 설계사(agent)다. `profiles.role`이 'internal'인 계정.
- **카카오 로그인 사용자는 email이 NULL일 수 있다.** 표지 연락처에 email을 쓰려면 `auth.users`를 JOIN해야 하며, 그래도 없을 수 있으니 필수 항목으로 삼지 않는다.

---

## S0. 현행 파악

### S0-1. profiles 테이블 현황

`profiles`의 **기본 테이블(CREATE TABLE)은 마이그레이션에 없다** — Supabase 대시보드(Auth 초기 설정)에서 생성된 것으로 보인다. 마이그레이션으로 추가된 컬럼만 확인 가능하다.

| 컬럼 | 타입 | 출처 | 비고 |
|---|---|---|---|
| `id` | uuid (PK) | 기본(대시보드) | `auth.users(id)` 참조. 백필 트리거가 `insert into profiles (id)` 사용 |
| `role` | `public.user_role` enum(`customer`\|`internal`) | `20260620000000_subscription_schema.sql` | default `customer`. 설계사=`internal` |
| `phone` | text | `20260620000001_phone_verification.sql` | 1인1계정 인증용 |
| `phone_verified` | boolean | 동상 | default false |

- **없는 것:** 설계사명(이름), 소속(GA), 지점(branch), 표지용 연락처, 직급/등록번호. 표지에 넣을 필드 대부분이 **저장소가 없다.**
- **RLS:** 활성. 본인 SELECT 정책만 존재(`20260620000003_profiles_select_policy.sql`). **클라이언트 INSERT/UPDATE 경로 없음**(주석에 명시). → 프로필 편집을 붙이려면 쓰기 정책/경로 신설 필요.
- **phone unique:** `profiles_phone_verified_unique` 부분 유니크 인덱스 존재.

### S0-2. 프로필 편집 UI / 데이터 수집 현황

- **프로필 편집 화면 부재.** `/settings`·`/profile`·`/account`·`/mypage` 라우트 없음(grep 0).
- **Signup(`src/pages/Signup.tsx`)이 수집하는 것:** email, password, phone뿐. 약관/개인정보/민감정보 동의 체크. **설계사명·소속·회사 미수집.**
  - ※ 현재 Signup의 휴대폰 "인증"은 클라이언트 목업이다(`requestPhoneVerify` → `setPhoneVerified(true)`, 실제 SMS 검증 없음). 표지 연락처를 phone에서 끌어올 경우 이 목업 사실을 인지해야 한다(패킷 193 Note).
- **설계사명 후보 소스:** 현재로선 `auth.users.user_metadata`의 소셜 표시명(카카오/구글) 정도. profiles에는 없음.

### S0-3. 표지(191) 현황과 입력 필드 갭

현재 보장분석 PDF(`backend/coverage/export_pdf.py`)에는 **표지가 없다.** 상단 헤더만 존재:

- `.brand`: 고정 BohumFit 브랜드(`logo-mark "ㅍ"` + 워드마크 "BohumFit / 보험핏 · 보장분석 리모델링").
- `.head-meta`: 고객명(+나이) + 작성일.

즉 현재 출력물에는 **소속(GA)·설계사명·연락처·GA 로고가 전혀 없다.** 191이 표지를 추가하는 중이며, 표지가 필요로 하는 필드(아래)는 전부 신규 데이터다.

| 표지 필드 | 현재 저장/제공 여부 | 갭 |
|---|---|---|
| 설계사명 | ✗ (profiles에 없음) | 스키마+수집 필요 |
| 소속(GA) 법인명/표기명 | ✗ | GA 마스터+선택 필요 |
| 지점/사업부(선택) | ✗ | 스키마 필요(선택) |
| 연락처(전화) | △ (phone은 인증용, 표지용과 다를 수 있음) | 표지용 연락처 정의 필요 |
| 연락처(email) | △ (카카오는 NULL 가능) | auth.users JOIN·폴백 필요 |
| GA CI 로고 | ✗ (스토리지 미사용) | 업로드/스토리지/슬롯 필요 |

### S0-4. export 경로·인증·서버측 프로필 조회 가능성

- 엔드포인트 `POST /coverage/export/pdf`(`backend/main.py` L1382~): `verify_jwt` 의존성으로 **user_id 확보**, body는 analysis payload(before/final). → 서버는 요청자를 안다.
- 렌더: `generate_coverage_pdf(payload)` → `export_pdf.build_coverage_html` → 헤드리스 Chromium. **응답 스트림 전용, 서버 미저장(no-store, PII 미저장).**
- ★**백엔드는 이미 service-role Supabase admin 클라이언트를 가진다**(`_get_supabase_admin()`, `SUPABASE_SERVICE_ROLE_KEY`). 빌링 게이트가 이 클라로 `profiles.role`을 조회한다(L466~). → **표지 자동채움을 서버측 profiles/agent_profiles 조회로 안전하게 구현할 수 있다**(클라 입력 신뢰 불필요).

### S0-5. 스토리지 현황

- **Supabase Storage 버킷 사용처 0**(`storage.from`/`.upload` grep 0). 로고 업로드는 **신규 스토리지 패턴 도입**이다.
- 기존 로고 자산은 전부 repo 정적 파일: `backend/assets/brand/bohumfit_logo.svg`·`_white.svg`(리포트 PDF가 base64 data-URI로 임베드 — BOHUMFIT-051 패턴), `brand/`(favicon·fithere-logo-*), `public/`.
- ★재사용 가능한 패턴: BOHUMFIT-051이 SVG를 읽어 base64 data-URI로 PDF에 임베드하는 방식을 이미 검증함. GA 로고도 동일 임베드 방식을 쓰면 Chromium 렌더에서 외부 요청 없이 안정적으로 표시된다.

### S0-6. 갭 요약

표지 자동채움을 위해 신설이 필요한 것: (1) 설계사 프로필 필드 저장소, (2) 프로필 편집 UI + 쓰기 경로/RLS, (3) GA 마스터 목록 + 선택, (4) 로고 스토리지 + 업로드/검수, (5) 표지 슬롯 주입(서버측 권장). 이 중 (1)(3)(5)의 스키마·정책은 Human 게이트.

---

## S1. 프로필 연동 설계

### S1-1. 표지에 채울 필드 정의

| 표지 슬롯 | 소스 필드 | 필수 | 폴백 |
|---|---|---|---|
| 설계사명 | `agent_name` | 필수 | 없으면 표지 발행 차단 or 공란 경고 |
| 소속(표기명) | `ga_agencies.brand_name`(선택된 GA) | 필수 | 공란 시 "무소속/개인" 텍스트 |
| 지점·사업부 | `branch` | 선택 | 생략 |
| 직급 | `agent_title` | 선택 | 생략 |
| 연락처(전화) | `contact_phone`(없으면 `profiles.phone`) | 권장 | 생략 |
| 연락처(email) | `contact_email`(없으면 auth.users.email) | 선택 | 카카오 NULL이면 생략 |
| 설계사 등록번호 | `agent_reg_no` | 선택 | 컴플라이언스 필요 시 노출 |
| GA CI 로고 | `ga_agencies.logo_path`(Storage) | 선택 | 없으면 brand_name **텍스트 폴백**(§S3-4) |

### S1-2. profiles 스키마 추가안 (★DB 변경 — Human 승인 필요, 제안만)

공유 인스턴스 리스크(FitHere 동시 영향) 때문에 **두 가지 안**을 제시하고 **안 B를 권장**한다.

**안 A — profiles에 nullable 컬럼 추가(단순):**

```sql
-- ※ 제안. 실행은 Human 승인 후.
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS agent_name    text,
  ADD COLUMN IF NOT EXISTS ga_agency_id  uuid REFERENCES public.ga_agencies(id),
  ADD COLUMN IF NOT EXISTS branch        text,
  ADD COLUMN IF NOT EXISTS agent_title   text,
  ADD COLUMN IF NOT EXISTS contact_phone text,
  ADD COLUMN IF NOT EXISTS contact_email text,
  ADD COLUMN IF NOT EXISTS agent_reg_no  text;
```
- 장점: 조인 없이 단순. 단점: **공유 profiles 오염**(FitHere가 모르는 컬럼 증가), 관심사 혼재.

**안 B — BOHUMFIT 전용 1:1 테이블 신설(권장):**

```sql
-- ※ 제안. 실행은 Human 승인 후.
CREATE TABLE IF NOT EXISTS public.agent_profiles (
  user_id       uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  agent_name    text,
  ga_agency_id  uuid REFERENCES public.ga_agencies(id),
  branch        text,
  agent_title   text,
  contact_phone text,
  contact_email text,
  agent_reg_no  text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.agent_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "본인 설계사 프로필 조회" ON public.agent_profiles
  FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "본인 설계사 프로필 수정" ON public.agent_profiles
  FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "본인 설계사 프로필 생성" ON public.agent_profiles
  FOR INSERT WITH CHECK (auth.uid() = user_id);
-- updated_at 트리거는 기존 public.set_updated_at() 재사용
```
- 장점: **공유 profiles 무변경**(FitHere 격리), 관심사 분리, 편집 쓰기 경로를 profiles와 분리(profiles는 여전히 읽기전용 정책 유지). 단점: 조인 1회 추가(서버 service-role 조회라 부담 없음).
- **권장:** 안 B. 이유 = 공유 인스턴스 리스크 최소화 + profiles의 "클라 쓰기 경로 없음" 보안 불변량 보존.

> 어느 안이든 `ga_agencies` 마스터 테이블(§S2)이 선행 전제다.

### S1-3. 자동채움 데이터 소스 방식 — 서버측 주입 권장

두 경로가 같은 원본을 읽게 설계한다.

- **PDF 표지(권위):** `/coverage/export/pdf`에서 백엔드가 **service-role로 user_id→agent_profiles(+ga_agencies+로고) 조회 후 표지 HTML에 주입.** 클라가 보낸 표지 텍스트를 신뢰하지 않음(위·변조 방지, 브랜딩 서버 권위). 표지가 backend 렌더면 이 방식이 자연스럽다.
- **화면 미리보기:** `CoverageRemodel.tsx`가 Supabase 클라로 본인 agent_profiles를 조회해 동일 정보를 표지 미리보기에 표시.
- ★191 표지가 **프런트 렌더**인지 **백엔드 HTML**인지 확정되면 주입 지점을 맞춘다. export_pdf.py가 backend HTML→PDF이므로 표지도 backend 섹션일 가능성이 높다(패킷 195에서 대조).

### S1-4. 공유 인스턴스·role·카카오 주의(명세 반영)

- 자동채움/편집 UI는 `role='internal'` 계정에만 노출(고객 계정 제외).
- email 표지 표기는 `auth.users` JOIN 필요(카카오 NULL 가능) → 필수 아님, 없으면 생략.
- agent_profiles(안 B)는 BOHUMFIT 전용 → FitHere는 이 테이블을 모른 채 정상 동작.

---

## S2. GA 목록 관리

### S2-1. 선택 방식 — 마스터 테이블 권장

| 방식 | 설명 | 판정 |
|---|---|---|
| 자유 텍스트 입력 | 설계사가 소속 GA를 직접 타이핑 | ✗ 표기 불일치·로고 연동 불가 |
| **마스터 테이블 선택(권장)** | `ga_agencies`에서 선택, `ga_agency_id` FK | ✓ 표기 일관·로고 1:1·운영 관리 |
| 하드코딩 리스트(프런트 상수) | 코드 배열 | △ 초기 간편하나 추가마다 배포 필요 |

→ **`ga_agencies` 마스터 테이블 + FK 선택**을 권장. 로고(§S3)를 GA에 1:1로 붙일 수 있고, 신규 추가가 데이터 작업(무배포)이 된다.

### S2-2. ga_agencies 마스터 테이블안 (★Human 승인)

```sql
-- ※ 제안. 실행은 Human 승인 후.
CREATE TABLE IF NOT EXISTS public.ga_agencies (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text NOT NULL,           -- 정식 법인명(등록 명칭)
  brand_name  text NOT NULL,           -- 표지 표기명(줄임/브랜드)
  logo_path   text,                    -- Storage 경로(없으면 텍스트 폴백)
  logo_status text NOT NULL DEFAULT 'none',  -- none | pending | approved
  status      text NOT NULL DEFAULT 'active', -- active | hidden | pending
  sort_order  integer NOT NULL DEFAULT 100,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.ga_agencies ENABLE ROW LEVEL SECURITY;
-- 로그인 사용자 읽기 허용(선택 목록 표시용), 쓰기는 service-role(관리자)만
CREATE POLICY "GA 목록 조회" ON public.ga_agencies
  FOR SELECT USING (auth.role() = 'authenticated');
```

- 쓰기(INSERT/UPDATE)는 RLS 정책을 두지 않아 **service-role(관리자 경로)만** 가능 → 설계사가 임의로 GA를 만들지 못함.

### S2-3. 초기 GA 목록 수집 출처 (★Human 결정)

초기 시드 목록의 출처는 Human이 정한다. 후보:

1. **운영자 큐레이션(권장 시작점):** 서비스가 실제로 상대하는 GA(설계사 사용자 소속)만 수기 시드. 소수로 시작해 요청 시 확장.
2. 공개 등록 정보 참조: 금융소비자정보포털/협회의 법인보험대리점 등록 명칭을 참고해 `name`(정식 법인명) 정확도 확보. ※로고는 별개(§S3, 웹 수집 금지).
3. 온보딩 수집: 설계사 가입/편집 시 "소속 GA가 목록에 없으면 요청" → 관리자 승인 후 추가(§S2-4).

> 권장: 1번으로 소규모 시드 → 3번 운영 흐름으로 점증. 2번은 법인명 표기 정확도 확보용 참조로만.

### S2-4. 신규 GA 추가 운영 흐름

```
설계사: 목록에서 "소속 GA 없음 → 추가 요청"(GA명 입력)
  → ga_agencies(status='pending')에 요청 적재 or 관리자 알림
  → 관리자: 법인명/표기명 확정 + (로고는 §S3 정식 파일 수령 후) 승인
  → status='active', 목록 노출 → 설계사 선택 가능
```

- 설계사에게 자유 생성 권한을 주지 않는다(중복·오표기 방지). 요청→승인 게이트.

---

## S3. CI 로고 (★법적 요건 포함)

### S3-1. 법적 요건 — 상표·저작권

- **GA CI 로고는 각 법인의 등록상표(IP)다.** 무단 사용·수정·재현은 상표권/저작권 침해 소지가 있다.
- **웹에서 수집·크롤링·재현 금지.** 검색으로 찾은 이미지, 스크린샷, 벡터 트레이싱 등 **어떤 우회 수집도 금지.**
- 로고는 **각 GA가 공식적으로 제공한 파일만** 사용한다(사용 승낙 포함).

### S3-2. "정식 제공 파일만" 정책 (명세 명시)

- 각 GA로부터 **로고 원본 파일 + 표지·제안서 내 사용 승낙**을 서면/이메일로 수령한 경우에만 등록한다.
- 업로드는 **관리자(운영) 경로**로 한정한다. 설계사가 임의 이미지를 올려 GA 로고로 지정하지 못하게 한다(오용·침해 차단).
- 미보유 GA는 로고 없이 운영하고 **텍스트 폴백**을 쓴다(§S3-4). "로고 없음"은 정상 상태다.
- 로고 사용 승낙의 근거(수령일·연락처·범위)를 운영 기록으로 남긴다(감사 대비).

### S3-3. 저장 위치·형식·크기

| 항목 | 권장 |
|---|---|
| 저장 위치 | Supabase Storage 신규 버킷 `ga-logos`(비공개 권장, service-role 읽기 → 서버가 표지에 임베드). 경로 예: `ga-logos/{ga_agency_id}.svg` |
| 형식 | **SVG 1순위**(벡터, PDF에서 선명), **PNG(투명배경) 2순위**. JPG 지양(투명 불가) |
| 크기 | 파일 ≤ 1MB. 표지 슬롯 기준 가로 약 240~360px 상당(래스터면 2x), 가로형 로고 우선 |
| 색/버전 | 컬러 원본 + (가능 시) 단색/화이트 버전. 표지 배경이 밝으므로 컬러본이 기본 |
| 메타 | `ga_agencies.logo_path`, `logo_status`(pending→approved) |

### S3-4. 표지 슬롯 연동·텍스트 폴백

- **임베드 방식:** BOHUMFIT-051 패턴 재사용 — 서버가 Storage에서 로고 바이트를 읽어 **base64 data-URI로 표지 HTML에 인라인** → Chromium 렌더 시 외부 요청 없음(안정·빠름).
- **슬롯 규격(191 표지와 대조 필요):** 표지 상단(또는 지정 로고 영역)에 GA 로고. `max-height` 고정(예 48~64px), 가로 비율 유지, 여백 규칙.
- **텍스트 폴백:** `logo_path`가 없거나 `logo_status != 'approved'`면 로고 대신 `ga_agencies.brand_name`을 **워드마크 텍스트**로 표기(폰트·크기 규칙). 폴백은 오류가 아니라 기본 동작.
- **BohumFit 브랜드와 공존:** 표지의 BohumFit 워드마크(도구 제공사)와 GA 로고(설계사 소속)의 위치/우선순위를 191 표지 디자인에 맞춰 정의(예: BohumFit=푸터/소형, GA=표지 헤더). → Human/디자인 확인 항목.

### S3-5. 로고 운영(업로드·검수) 흐름

```
GA로부터 공식 로고 파일 + 사용 승낙 수령
  → 관리자: 형식/크기/투명배경 검수 → ga-logos 버킷 업로드
  → ga_agencies.logo_path 설정, logo_status='approved'
  → 표지에서 자동 표시. 문제 시 logo_status='pending'로 내려 텍스트 폴백.
```

---

## S4. 구현 분할 (193+)

의존 순서: **193(프로필 스키마·자동채움) → 194(GA 선택) → 195(로고)**. GA 마스터(`ga_agencies`)는 193/194 공통 전제라 193의 스키마 승인에 포함해 함께 확정한다.

| 패킷 | 범위 | 선행 | Human 게이트 | 산출물 |
|---|---|---|---|---|
| **193** `packet-193-profile-schema` | agent_profiles(안 B) + ga_agencies 스키마 확정, 프로필 편집 UI(설계사명·연락처 등), 표지 자동채움(서버측 주입) | 스키마 승인 | ✅ DB 스키마(안 A/B), 표지 데이터 소스 방식 | 마이그레이션(승인 후)·`/settings`(agent)·export 주입 |
| **194** `packet-194-ga-select` | ga_agencies 시드 + 설계사 GA 선택 UI + 신규 GA 요청→승인 흐름 | 193 스키마 | ✅ 초기 GA 목록 출처·관리 주체 | GA 선택 컴포넌트·요청/승인 경로 |
| **195** `packet-195-logo-upload` | ga-logos 버킷 + 관리자 업로드/검수 + 표지 슬롯 임베드 + 텍스트 폴백 | 194 GA + 191 표지 슬롯 확정 | ✅ 로고 제공/사용 승낙 정책 | 업로드/검수 경로·표지 로고 슬롯(대조)·폴백 |

각 패킷 상세는 `BOHUMFIT-192-packet-193/194/195-*.md` 참조. Human 결정 항목은 `BOHUMFIT-192-human-decisions.md`에 집약.

---

## 부록. 조사 근거(파일)

- `supabase/migrations/20260620000000_subscription_schema.sql`(role enum·subscriptions), `..._phone_verification.sql`(phone), `..._backfill_profiles_phone.sql`(profiles insert 트리거), `..._profiles_select_policy.sql`(본인 SELECT·클라 쓰기 없음).
- `src/pages/Signup.tsx`(email/pw/phone만·휴대폰 인증 목업), `src/lib/AuthContext.tsx`(세션·카카오 로그아웃).
- `backend/main.py`(`/coverage/export/pdf` verify_jwt L1382~, `_get_supabase_admin` service-role L466~/489~).
- `backend/coverage/export_pdf.py`(현행 헤더=BohumFit 브랜드+고객명/작성일, 표지 없음, base64 임베드 여지).
- 스토리지: `storage.from`/`.upload` grep 0. 로고 정적 자산: `backend/assets/brand/`, `brand/`, `public/`.
- git log: HEAD `1f5b498`(188까지), 189~191 미포함. locks.md Active: `BOHUMFIT-189`(병렬).
