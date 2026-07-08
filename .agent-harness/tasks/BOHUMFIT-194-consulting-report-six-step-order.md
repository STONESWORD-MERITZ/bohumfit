# BOHUMFIT-194 — 컨설팅 리포트·화면 6단계 순서 재편

Owner flow: Claude Chat -> Codex
Current owner: Codex

## Intent
- 고객용 PDF 리포트와 설계사용 화면 흐름을 같은 6단계 정본 순서로 맞춘다.
- 고객에게는 표지 → 계약 처리 → 신규제안 → 특약별 전후 → 회사별 전후 → 전 진단 세부 순서로 읽히게 하고, 설계사 화면도 같은 순서로 조작하게 한다.

## Scope
- 수정 허용:
  - `src/pages/CoverageRemodel.tsx`
  - `backend/coverage/export_pdf.py`
  - `backend/coverage/export_excel.py`
  - `backend/tests/test_coverage_report_194.py`
  - 기존 Excel sheet order 기대값 보정 테스트
  - `.agent-harness/handoff.md`, `.agent-harness/locks.md`
- 수정 금지:
  - `backend/pipeline/`
  - BOHUMFIT-193 파서 신규 구현
  - 실 PDF·엑셀·PII 산출물 저장/커밋

## Work
1. 6단계 순서로 화면과 PDF 본문을 재배치한다.
2. 유지/해지는 드롭다운 대신 계약 목록 인라인 체크로 처리한다.
3. 신규가입 제안서 PDF 업로드 슬롯을 만들되, 실제 파싱은 구현하지 않고 현행 수기 입력 경로만 연결한다.
4. 최종 전 VS 후를 특약별 비교와 회사별 세부 비교로 분리한다.
5. 컨설팅 전 진단 세부는 말미 참고자료 섹션으로 이동한다.
6. Excel 시트 순서도 6단계와 맞춘다.

## Acceptance
- 화면 순서: ① 표지 → ② 컨설팅 전 계약 → ③ 신규가입 제안서 → ④ 특약별 전후 → ⑤ 회사별 전후 → ⑥ 전 진단 세부.
- PDF HTML 본문도 같은 순서다.
- Excel 컨설팅 결과 시트 순서도 같은 6단계다.
- ③ 업로드 슬롯은 BOHUMFIT-193 TODO만 남기고 파서 구현을 하지 않는다.
- 189 대분류 순서, 190 유지/해지 계산, 191 표지, `[전]` 파싱 회귀를 깨지 않는다.

## Verification
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run build`
- `cd backend && python -m pytest -q`
- `cd backend && python -m pytest tests/test_coverage_report_194.py -vv`
