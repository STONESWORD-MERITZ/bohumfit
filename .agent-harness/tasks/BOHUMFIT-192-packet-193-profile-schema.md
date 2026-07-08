# BOHUMFIT-193 (패킷) — 설계사 프로필 스키마 + 편집 UI + 표지 자동채움

Owner flow: Claude Chat -> Cowork -> Codex
Current owner: **Human**(스키마 승인) → Cowork(구현) → Codex(검증·커밋)
선행: `BOHUMFIT-192-*` 명세 + Human 결정 D1·D2·D3·D8. 상세 근거: `BOHUMFIT-192-profile-ga-logo-spec.md` §S0·S1.

## Intent
설계사(role='internal')가 자신의 소속·이름·연락처를 저장·편집할 수 있게 하고, 191 표지에 이 정보가 자동으로 채워지도록 데이터 계층을 만든다. 지금은 저장소도 편집 UI도 없다.

## Scope
- **수정 허용:**
  - (Human 승인 후) `supabase/migrations/2026XXXX_agent_profiles.sql` 신규 — `agent_profiles`(안 B 권장) + RLS. `ga_agencies`는 194 선행이나 FK 때문에 여기서 함께 생성 가능(D1 결정에 따름).
  - `src/pages/Settings.tsx` 신규 — 설계사 프로필 편집(설계사명·지점·직급·연락처; GA 선택은 194에서 결합).
  - `src/App.tsx` — `/settings` ProtectedRoute 추가(1줄 수준).
  - `src/components/Layout.tsx` — 로그인 설계사 메뉴에 "설정" 진입(소형).
  - `backend/coverage/export_pdf.py` 또는 신규 `backend/coverage/cover.py` — 표지 자동채움 주입(서버측). ★191 표지 구현체 확정 후 슬롯 맞춤.
  - `backend/main.py` — `/coverage/export/pdf`에서 user_id→agent_profiles 조회(service-role) 주입. 필요 시 `GET /me/agent-profile`·`PATCH /me/agent-profile` 신설(또는 클라 직접 Supabase 사용).
  - 테스트: `backend/tests/test_agent_profile_193.py` 신규.
- **수정 금지:** `profiles` 테이블(안 B 채택 시 무변경), 고지의무/실손 파이프라인(`backend/pipeline/*`, `backend/filters.py`), 189~191 병렬 배치 범위(`backend/coverage/constants.py`, `CoverageRemodel.tsx` 정렬 경로 — 충돌 회피).
- **보존:** profiles의 "클라 INSERT/UPDATE 경로 없음" 보안(agent_profiles로 분리). export의 no-store·PII 미저장.

## Work
- 해야 할 일:
  1. (승인 후) `agent_profiles` 마이그레이션 + RLS(본인 SELECT/INSERT/UPDATE).
  2. 설정 화면: 설계사명·지점·직급·contact_phone·contact_email 입력/저장. role='internal'만 접근(고객은 안내/차단).
  3. 표지 자동채움: export 시 서버가 agent_profiles 조회 → 표지 슬롯 주입. 값 없으면 §S3-4/§S1-1 폴백.
  4. 회귀 테스트: 프로필 없음/부분입력/카카오 email NULL 케이스.
- 하지 말 것:
  - Human 승인 전 마이그레이션 실행.
  - `profiles` 컬럼 추가(안 B 채택 시). 안 A 채택 시에도 FitHere 영향 재확인 후에만.
  - GA 선택·로고(194·195 범위) 여기서 구현.
  - 191 표지 슬롯을 추측으로 확정(구현체 대조 전이면 주입 지점 TODO로 격리).

## Verification
- 자동 검증: `cd backend && python -m pytest -q`(기준선 유지 + test_agent_profile_193 통과). `npx tsc -p tsconfig.app.json --noEmit`·`tsconfig.node.json`. `npm run build`.
- 수동 검증: 설계사 계정으로 `/settings` 저장 → export PDF 표지에 반영. 고객 계정은 설정 비노출/차단. 프로필 미입력 시 표지 폴백 정상.
- 실데이터/배포: 실 로그인 세션에서 문건주 PDF export → 표지 자동채움 육안(Human).

## Handoff Requirements
- Changed / Verified / Notes / Next 표준 기록.
- ★스키마 미승인이면 코드 미실행 사유 handoff 명시(명세만).
- ★191 표지 슬롯 대조 결과(주입 지점 확정/보류) 기록.
