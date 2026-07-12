# BOHUMFIT-211 Coverage Parity + GA Placeholder Cleanup

Owner flow: Human -> Codex Windows
Current owner: Codex

## Intent
- FABLE 마감 전 취지2 신뢰 경계를 강화한다.
- 프런트 표시용 후 집계 캐시가 백엔드 권위 집계와 같은 결과를 내는지 테스트로 보증한다.
- 고객 산출물에 `GA LOGO`, `슬롯 준비` 같은 내부 플레이스홀더가 노출되지 않게 한다.

## Scope
- 수정 허용:
  - `src/pages/CoverageRemodel.tsx`
  - 프런트 테스트/테스트 픽스처
  - `backend/coverage/export_pdf.py`
  - `backend/coverage/export_excel.py`
  - backend coverage export/parity tests
  - harness task/handoff/locks
- 수정 금지:
  - `backend/pipeline/`
  - DB/RLS/Supabase/auth
  - coverage 계산 규칙 자체
  - 신규 프로필/agent_profiles 스키마

## Work
- 프런트 후 집계 path가 display cache임을 코드 주석으로 명시한다.
- 동일 입력에 대해 프런트 `buildAfterResult`와 백엔드 `build_after_analysis` 결과가 일치하는 패리티 테스트를 추가한다.
- PDF/Excel export의 GA/로고 placeholder를 회사명 텍스트 폴백 또는 빈 처리로 교체한다.

## Verification
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm test`
- `npm run build`
- `cd backend && python -m pytest -q`
- 신규 패리티 테스트가 실제 프런트=백엔드 결과를 비교하는지 확인.

## Handoff Requirements
- 변경 파일과 계산 규칙 무변경 사실.
- 신규 테스트와 전체 검증 결과.
- backend pytest 최종 숫자.
- commit hash and push result.

## Result
- `CoverageRemodel.tsx`의 `[후]` 산출 display cache를 `src/lib/coverageAfterDisplayCache.ts`로 분리하고, 백엔드 `coverage.compare.build_after_analysis`가 권위임을 코드 주석으로 명시했다.
- 합성 fixture `backend/tests/fixtures/coverage_after_parity_211.json`로 해지 계약, 신규 제안, 합산 담보, 대표값(max) 담보, 신규 미매핑 담보를 포함한 패리티 케이스를 고정했다.
- `backend/tests/test_coverage_parity_211.py`는 백엔드 결과를 정규화한 뒤 `BOHUMFIT_PARITY_EXPECTED`로 Vitest에 넘겨 프런트 display cache 결과와 동일한지 검증한다.
- PDF/Excel 표지에서 `GA LOGO`, `GA 로고`, `슬롯 준비` placeholder가 고객 산출물에 노출되지 않도록 소속명/설계사명 fallback으로 정리했다.
- `backend/pipeline/`, DB/auth, coverage 계산 규칙(`compare.py`, `aggregator.py`, service/parser/registry)은 변경하지 않았다.

## Verified
- `npx tsc -p tsconfig.app.json --noEmit` — passed.
- `npx tsc -p tsconfig.node.json --noEmit` — passed.
- `npm run lint` — passed.
- `npm test` — `7` files, `25 passed`.
- `npm run build` — passed, 기존 Vite 500kB chunk warning만 발생.
- `cd backend && python -m pytest tests/test_coverage_parity_211.py -vv` — `1 passed`.
- `cd backend && python -m pytest tests/test_coverage_report_191.py -vv` — `3 passed`.
- `cd backend && python -m pytest -q` — `593 passed, 8 skipped`.
