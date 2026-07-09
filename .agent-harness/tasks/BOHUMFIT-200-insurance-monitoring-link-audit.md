# BOHUMFIT-200 - 완전판매 모니터링 링크 전수 검수 및 경로 안내 개선

Owner flow: Human -> Codex Windows
Current owner: Human(배포 확인)

## Intent

- BOHUMFIT-199에서 추가한 완전판매/신계약 모니터링 링크 중 실제 접속 시 메인/로그인 화면으로 떨어져 현장 사용성이 낮은 항목을 전수 검수한다.
- 공개 direct link가 있는 항목은 URL을 교체하고, direct link가 막힌 보험사는 접속 경로를 화면에 고정 노출한다.
- 사용자가 언급한 메리츠, KB, 한화, 신한라이프, 흥국생명, 동양생명, ABL생명, DB생명 계열을 우선 확인하되 전체 보험사 데이터 구조가 같은 기준을 갖게 한다.

## Scope

- 수정 허용:
  - `src/pages/InsuranceLinks.tsx`
  - `backend/tests/test_insurance_links_monitoring_199.py`
  - `.agent-harness/tasks/BOHUMFIT-200-insurance-monitoring-link-audit.md`
  - `.agent-harness/handoff.md`, `.agent-harness/locks.md`
- 수정 금지:
  - `backend/pipeline/`
  - 실 PDF/엑셀/PII

## Plan

1. 현재 `monitoringUrl` 전 항목을 HTTP/공식 검색 결과로 재검수한다.
2. 한화생명/KDB생명 등 더 좋은 direct URL이 확인된 항목은 교체한다.
3. 공개 direct link가 없는 항목은 `monitoringAccess`와 `monitoringPath`를 추가해 메인/로그인 이동 후 실제 메뉴 경로를 안내한다.
4. UI 버튼/상세보기에 direct/auth/path 상태를 노출하고 경로를 복사 가능하게 한다.
5. 기존 BOHUMFIT-199 테스트를 확장해 URL 수량, 상태값, 주요 보험사 경로를 고정한다.

## Verification

- `python -m pytest backend\tests\test_insurance_links_monitoring_199.py -q`: `1 passed`.
- `npx tsc -p tsconfig.app.json --noEmit`: 통과.
- `npx tsc -p tsconfig.node.json --noEmit`: 통과.
- `npm test`: `15 passed`.
- `npm run build`: 통과. 기존 Vite chunk-size warning만 출력.
- Vite `/insurance-links` browser smoke: `http://127.0.0.1:5173/insurance-links` 렌더, 오류 오버레이 없음, 콘솔 error 0, `경로 안내`/신한라이프/DB생명 경로 문구 표시 확인.
- `cd backend; python -m pytest -q`: `563 passed, 8 skipped`.

## Notes

- 일부 보험사는 개인정보/본인인증/세션 정책상 고객별 인증 후에만 대상계약 모니터링 화면으로 이동한다. 이 경우 공개 URL을 억지로 direct로 표시하지 않고 “경로 안내”로 구분한다.
- 한화생명은 모바일 신계약 모니터링 direct URL로 교체했다.
- 흥국화재는 PC 완전판매모니터링 동의 direct URL로 교체했다.
- KDB생명은 `INLNB004M01P` 해피콜 셀프체크 URL로 교체했다.
- DB손해보험은 인증 게이트 URL로 보정했다.
- 신한라이프/ABL생명은 사이버창구 로그인 진입점 + 메뉴 경로로 보정했다.
- 메리츠화재, 한화손해보험, 흥국생명, 동양생명, DB생명 등 공개 direct URL 미확인 항목은 버튼을 `경로 안내`로 표시하고 상세 경로를 노출한다.
