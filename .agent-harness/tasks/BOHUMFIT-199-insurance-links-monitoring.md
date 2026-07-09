# BOHUMFIT-199 - 보험사 링크 완전판매 모니터링 추가

Owner flow: Human -> Codex Windows
Current owner: Codex

## Intent

- 기존 `보험사 링크` 화면에 완전판매 모니터링 / 신계약 모니터링 / 해피콜 / e모니터링 바로가기를 추가한다.
- 사용자가 제공한 2026-07-07 링크 목록을 기준으로 채우고, 공개 직접 URL이 확인되지 않는 보험사는 공식 홈페이지/로그인 경유 비고를 남긴다.
- 공제회사 항목은 일반 보험사 신계약 완전판매 모니터링 공개 URL 대상과 성격이 달라 직접 링크를 두지 않는다.

## Scope

- 수정 허용:
  - `src/pages/InsuranceLinks.tsx`
  - `backend/tests/test_insurance_links_monitoring_199.py`
  - `.agent-harness/tasks/BOHUMFIT-199-insurance-links-monitoring.md`
  - `.agent-harness/handoff.md`, `.agent-harness/locks.md`, `.agent-harness/verify.md`, `CLAUDE.md`
- 수정 금지:
  - `backend/pipeline/`
  - 고객 실 PDF/엑셀/PII

## Plan

1. 기존 보험사 링크 데이터 44개 항목을 점검한다.
2. 손해/생명보험 38개 항목에 `monitoringUrl`/`monitoringNote`를 추가한다.
3. 공제회사 6개 항목은 `monitoringNote`만 남기고 버튼은 비활성으로 둔다.
4. 카드 액션에 `완전판매` 버튼을 추가하고, 상세보기에는 URL/비고를 노출한다.
5. 소스 회귀 테스트와 프론트/백엔드 검증을 수행한다.

## Verification

- `python -m pytest backend\tests\test_insurance_links_monitoring_199.py -q`: `1 passed`.
- `npx tsc -p tsconfig.app.json --noEmit`: 통과.
- `npx tsc -p tsconfig.node.json --noEmit`: 통과.
- `npm test`: `15 passed`.
- `npm run build`: 통과. 기존 Vite chunk-size warning만 출력.
- Vite `/insurance-links` route smoke: `http://127.0.0.1:5182/insurance-links` 200 및 root div 확인 후 서버 종료.
- `cd backend; python -m pytest -q`: `563 passed, 8 skipped`.
- `git diff --check`: 통과. LF/CRLF warning만 출력.

## Notes

- 공식 검색으로 일부 대표 URL을 재확인했다: 한화생명 신계약모니터링, 교보생명 모니터링 대상 계약 목록, 삼성화재 완전판매모니터링, DB손해보험/AIG/NH농협손해보험 완전판매모니터링 등.
- 공개 직접 URL이 없는 보험사는 “공개 직접 URL 미확인” 비고로 구분한다.
