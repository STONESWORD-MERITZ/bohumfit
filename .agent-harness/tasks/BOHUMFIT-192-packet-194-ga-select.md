# BOHUMFIT-194 (패킷) — GA 마스터 목록 + 설계사 GA 선택 + 신규 GA 요청/승인

Owner flow: Claude Chat -> Cowork -> Codex
Current owner: **Human**(GA 목록 출처·승인 주체) → Cowork(구현) → Codex(검증·커밋)
선행: 193(agent_profiles·ga_agencies 스키마) + Human 결정 D4. 근거: `BOHUMFIT-192-profile-ga-logo-spec.md` §S2.

## Intent
설계사가 소속 GA 법인대리점을 **일관된 마스터 목록에서 선택**하게 한다(자유 텍스트 금지 → 표기 일관·로고 1:1 연동). 목록에 없으면 요청→관리자 승인으로 추가한다.

## Scope
- **수정 허용:**
  - `supabase/migrations/2026XXXX_ga_agencies_seed.sql` 신규 — 초기 GA 시드(Human 확정 목록). ※`ga_agencies` 테이블 자체는 193에서 생성(FK 선행).
  - `src/pages/Settings.tsx` — GA 선택 필드 결합(193에서 만든 화면에 select/combobox 추가, `agent_profiles.ga_agency_id` 저장).
  - `src/components/GaSelect.tsx` 신규(선택) — GA 검색·선택 컴포넌트 + "목록에 없음 → 추가 요청".
  - `backend/main.py` — `GET /ga-agencies`(active 목록, 인증) + `POST /ga-agencies/requests`(신규 GA 요청 적재, pending). 승인은 관리자 경로.
  - 테스트: `backend/tests/test_ga_agencies_194.py` 신규.
- **수정 금지:** `profiles`, 파이프라인, 로고 업로드/표지 로고 슬롯(195 범위), 189~191 병렬 범위.
- **보존:** `ga_agencies` 쓰기는 service-role(관리자)만(RLS에 쓰기 정책 없음). 설계사 자유 생성 금지.

## Work
- 해야 할 일:
  1. (승인 후) 초기 GA 시드 삽입(정식 법인명 `name` + 표기명 `brand_name`).
  2. GA 선택 UI: 검색/선택 → `ga_agency_id` 저장. 표지 미리보기에 brand_name 반영.
  3. 신규 GA 요청 흐름: 설계사 요청(GA명) → `status='pending'` 적재/관리자 알림 → 관리자 승인 시 `active`.
  4. 회귀 테스트: 목록 조회, 선택 저장, 요청 적재, 미선택(무소속) 케이스.
- 하지 말 것:
  - 웹에서 GA 목록/로고를 크롤링해 시드(로고는 195·§S3, 목록도 Human 확정분만).
  - 설계사에게 ga_agencies 직접 INSERT 권한 부여.
  - 로고 표시/업로드(195) 구현.

## Verification
- 자동 검증: `cd backend && python -m pytest -q`(기준선 + test_ga_agencies_194). tsc app/node. `npm run build`.
- 수동 검증: 설계사 계정에서 GA 선택 저장 → 표지 미리보기·export 표지 표기명 반영. 신규 GA 요청 → pending 적재 확인 → 관리자 승인 후 목록 노출.
- 실데이터/배포: 실 세션에서 선택→export 표지 소속 표기 육안(Human).

## Handoff Requirements
- Changed / Verified / Notes / Next.
- ★초기 GA 시드 출처·규모, 승인 주체(관리자 경로) 기록.
- 무소속/미선택 표지 표기(폴백) 동작 기록.
