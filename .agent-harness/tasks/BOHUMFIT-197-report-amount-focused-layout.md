# BOHUMFIT-197 - 리포트 보장금액 중심 레이아웃 정리

Owner flow: Human -> Codex Windows
Current owner: Codex

## Intent

고객용 보장분석 리포트와 화면에서 신규가입 제안서/특약별 비교/회사별 세부 표가 상태 판정 문구보다 **보장금액 자체**에 집중되도록 정리한다.

## Scope

수정 허용:

- `src/pages/CoverageRemodel.tsx`
- `backend/coverage/export_pdf.py`
- `backend/coverage/export_excel.py`
- 관련 회귀 테스트

수정 금지:

- `backend/pipeline/`
- 보장금액 계산/집계 로직
- 실 PDF/엑셀/PII 저장 또는 커밋

## Changes

- ③ 신규가입 제안서 영역에서 `수기 입력`, `수기 입력 담보` 표현을 `핵심 보장금액` 중심 문구로 교체.
- ④ 특약별 보장 비교에서 `충분`, `부족`, `미가입`, `부족 -> 충분` 등 상태/변화 컬럼을 제거하고 `전 보장금액`, `후 보장금액`, `증감`만 표시.
- ⑤ 회사별 보장 세부 매트릭스에서 회사명과 월보험료를 한 셀 줄바꿈이 아니라 헤더 2행으로 분리.
- PDF 섹션마다 구분선과 여백을 추가해 문단 구분을 명확히 함.
- PDF 표지 높이 과다로 생기던 빈 페이지를 함께 정리.

## Verification

- `python -m pytest backend\tests\test_coverage_report_191.py backend\tests\test_coverage_report_194.py backend\tests\test_coverage_report_195.py backend\tests\test_coverage_compare_188.py -q`: `13 passed`
- `npx tsc -p tsconfig.app.json --noEmit`: 통과
- `npx tsc -p tsconfig.node.json --noEmit`: 통과
- `npm run build`: 통과, 기존 Vite chunk-size warning만 출력
- `cd backend; python -m pytest -q`: `561 passed, 8 skipped`
- PDF visual smoke: 임시 합성 리포트 PDF 생성 후 Poppler PNG 렌더 확인. 빈 페이지 없음, ③ 핵심 보장금액, ④ 금액 중심 표, ⑤ 회사명/보험료 헤더 분리 확인.

## Notes

- `backend/pipeline/` 무접촉.
- 생성한 `tmp/pdfs/coverage_layout_check*` 임시 산출물은 삭제했고 커밋하지 않는다.
