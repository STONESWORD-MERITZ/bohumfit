# BOHUMFIT-195 (패킷) — GA CI 로고 업로드/스토리지 + 표지 슬롯 연동 + 텍스트 폴백

Owner flow: Claude Chat -> Cowork -> Codex
Current owner: **Human**(로고 제공/사용 승낙 정책·191 슬롯) → Cowork(구현) → Codex(검증·커밋)
선행: 194(ga_agencies 운영) + **191 표지 슬롯 확정** + Human 결정 D5·D6·D7. 근거: `BOHUMFIT-192-profile-ga-logo-spec.md` §S3.

## Intent
선택된 GA의 **정식 제공 CI 로고**를 표지에 표시한다. 로고가 없으면 표기명 텍스트로 폴백한다. 로고는 각 GA의 등록상표이므로 **웹 수집 금지·정식 제공 파일만·관리자 업로드만**의 법적 정책을 코드/운영으로 강제한다.

## Scope
- **수정 허용:**
  - Supabase Storage 신규 버킷 `ga-logos`(비공개 권장) — 콘솔/마이그레이션(Human 승인).
  - `backend/main.py` — (관리자) 로고 업로드/검수 경로 `POST /admin/ga-agencies/{id}/logo`(service-role, 형식/크기 검증) + `ga_agencies.logo_path`·`logo_status` 갱신.
  - `backend/coverage/export_pdf.py` 또는 `backend/coverage/cover.py`(193 신설분) — 표지 로고 슬롯: Storage 로고 → **base64 data-URI 임베드**(BOHUMFIT-051 패턴), 없거나 `logo_status!='approved'`면 **brand_name 텍스트 폴백**.
  - 테스트: `backend/tests/test_ga_logo_195.py` 신규(임베드 성공·폴백·미승인).
- **수정 금지:** 설계사 업로드 경로(관리자만), `profiles`, 파이프라인, 189~191 병렬 범위. GA 목록/선택(194).
- **보존:** export no-store·PII 미저장. 로고 미보유=정상(폴백).

## Work
- 해야 할 일:
  1. (승인 후) `ga-logos` 버킷 생성. 형식(SVG 1순위/PNG 투명 2순위)·크기(≤1MB) 검증.
  2. 관리자 업로드/검수 경로: 정식 파일 수령 후 업로드 → `logo_path` 설정·`logo_status='approved'`.
  3. 표지 슬롯: 로고 data-URI 임베드(191 표지 슬롯 규격 대조 — 위치·max-height·여백). 폴백 텍스트 스타일.
  4. 테스트: 승인 로고 임베드/미승인·미보유 폴백/잘못된 형식 거부.
- 하지 말 것:
  - **웹에서 로고를 수집·트레이싱·재현.** 검색 이미지/스크린샷 금지.
  - 설계사 임의 이미지 업로드를 GA 로고로 지정.
  - 사용 승낙 없는 로고 등록. (승낙 근거 운영 기록 병행)
  - 191 표지 슬롯을 추측 확정(구현체 확정 전이면 슬롯 좌표 TODO 격리).

## Verification
- 자동 검증: `cd backend && python -m pytest -q`(기준선 + test_ga_logo_195). tsc app/node. `npm run build`.
- 수동 검증: 승인 로고 GA로 export → 표지에 로고 표시. 미보유/미승인 GA → 텍스트 폴백. 형식 위반 업로드 거부.
- 실데이터/배포: 실 세션 문건주 PDF export → 로고/폴백 육안(Human). 실 Chromium 렌더 로고 선명도 확인(Codex 로컬).

## Handoff Requirements
- Changed / Verified / Notes / Next.
- ★법적 정책 준수 명시: 정식 제공 파일만·관리자 업로드만·웹수집 0·사용 승낙 근거 보관.
- ★191 표지 로고 슬롯 대조 결과(좌표·크기 확정/보류) 기록.
- 폴백(텍스트) 동작·미승인 로고 처리 기록.
