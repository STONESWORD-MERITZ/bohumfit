# BOHUMFIT-195 — ④ 특약별 전후 비교표 그룹 헤더 정렬

Owner flow: Human -> Codex Windows  
Current owner: Codex

## Intent
- 고객용 컨설팅 리포트의 ④ 특약별 전후 비교표를 전/후 묶음이 대칭으로 보이게 정렬한다.
- 값, 집계, 과부족 상태 판정은 그대로 두고 표시 구조만 다듬는다.

## Scope
- 수정 허용 파일:
  - `src/pages/CoverageRemodel.tsx`
  - `backend/coverage/export_pdf.py`
  - `backend/coverage/export_excel.py`
  - `backend/tests/test_coverage_report_195.py`
  - `.agent-harness/tasks/BOHUMFIT-195-consulting-compare-group-header.md`
  - `.agent-harness/handoff.md`
- 수정 금지:
  - `backend/pipeline/`
  - 189 대분류 순서, 190 유지/해지, 191 표지, 194 ①~⑥ 순서, ⑤ 회사별/⑥ 진단 세부 로직

## Work
- 화면 ④ 특약별 비교표 `thead`만 2단 그룹 헤더로 교체한다. `tbody`는 변경하지 않는다.
- PDF ④ 특약별 비교표는 전/후 가입·상태와 증감·변화를 8칸 데이터행으로 표시하고, 전/후 그룹 헤더를 `colspan=2`로 묶는다.
- Excel `④ 전후 특약별` 시트는 전 D:E, 후 F:G 병합 그룹 헤더를 두고 전 가입·상태, 후 가입·상태를 인접 배치한다.
- 신규 테스트로 화면 정적 헤더, PDF 헤더/8칸 행, Excel 병합 헤더/행 값을 검증한다.

## Verification
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run build`
- `cd backend && python -m pytest -q`
- `cd backend && python -m pytest tests/test_coverage_report_195.py -vv`

## Handoff Requirements
- handoff 상단에 변경 파일, 검증 결과, 최종 pytest 숫자, commit hash를 기록한다.
- 실 PDF/Excel/PII 산출물은 저장·커밋하지 않는다.
