# BOHUMFIT-198 - 핵심 보장금액 접힘 UI + 컨설팅 전 진단 세부 제거

Owner flow: Human -> Codex Windows  
Current owner: Codex

## Intent

- ③ 신규가입 제안서 영역에서 `핵심 보장금액` 전체 편집폼이 처음부터 모두 펼쳐져 화면을 길게 만드는 문제를 줄인다.
- 사용자는 요약만 먼저 보고, 필요할 때 `펼치기`로 보험사/상품/보험료/보장금액 편집폼을 열어 보완할 수 있어야 한다.
- ④ 전/후 보장금액 비교는 대분류별 표마다 금액 컬럼 위치가 같아야 한다.
- ⑥ `컨설팅 전 진단 세부`는 화면/PDF/Excel 산출물에서 제외한다.

## Scope

- 수정 허용:
  - `src/pages/CoverageRemodel.tsx`
  - `backend/coverage/export_pdf.py`
  - `backend/coverage/export_excel.py`
  - 관련 coverage report/export 테스트
  - `.agent-harness/handoff.md`, `.agent-harness/locks.md`, `.agent-harness/verify.md`, `CLAUDE.md`
- 수정 금지:
  - `backend/pipeline/`
  - 실 PDF/엑셀/PII 저장 또는 커밋

## Changed

- ③ `핵심 보장금액` 제안 카드를 기본 접힘 요약 카드로 변경.
  - 파싱 결과는 접힘 상태로 시작.
  - 수기 `추가` 및 파싱 실패 fallback은 입력 편의를 위해 펼침 상태로 시작.
  - 접힘 카드에 보험사, 상품명, 월보험료, 만기, 핵심 보장금액 preview를 표시.
- ④ 특약별 보장 비교 화면 표에 `table-fixed`와 동일 `colgroup`을 적용해 대분류별 전/후/증감 열 위치를 고정.
- ⑥ `컨설팅 전 진단 세부`를 화면에서 제거.
- PDF/Excel 산출물에서 ⑥ 진단 세부 섹션/시트와 전용 계산 제거.
- 테스트 기대값을 ①~⑤ 리포트 구조와 접힘 UI/고정 컬럼 기준으로 갱신.

## Verification

- `python -m pytest backend\tests\test_coverage_export_181.py backend\tests\test_coverage_report_194.py backend\tests\test_coverage_report_195.py backend\tests\test_coverage_compare_188.py -q`: `15 passed`.
- `npm test`: `15 passed`.
- `npx tsc -p tsconfig.app.json --noEmit`: 통과.
- `npx tsc -p tsconfig.node.json --noEmit`: 통과.
- `npm run build`: 통과. 기존 Vite chunk-size warning만 출력.
- Vite dev smoke: `http://127.0.0.1:5181/coverage-compare` 응답 200 및 `<div id="root">` 확인 후 서버 종료.
- `cd backend; python -m pytest -q`: `562 passed, 8 skipped`.
- `git diff --check`: 통과(LF→CRLF warning만 출력).
- PDF visual smoke: 합성 리포트 PDF 생성 후 Poppler PNG 3페이지 렌더 확인.
  - ②/③/④/⑤만 표시되고 ⑥ 섹션 없음.
  - ④ 대분류별 요약/특약별 비교 표 금액 열 정렬 정상.
  - ⑤ 회사별 세부 표 잘림/겹침 없음.

## Notes

- `backend/pipeline/` 무접촉.
- 실 PDF/엑셀/PII 미저장·미커밋.
- Poppler 번들에는 `pdftoppm.exe`만 있어 텍스트 추출 확인은 생략. HTML 테스트에서 ⑥ 미포함을 검증하고 PNG 렌더로 시각 확인했다.
