# SURIT-018: 처방 PDF 타입 분류 page 신호 견고화

## Owner
- Codex

## Status
- Completed

## Type
- Bug fix / parser classification

## Context
- SURIT-017 진단에서 처방 PDF 오분류 잔존 경로 2개를 확인했다.
- 버그1: `_resolve_ftype`이 강한 detail/basic 헤더 신호를 본문 `pharma` 신호보다 우선해 처방 PDF를 진료내역으로 오분류할 수 있다.
- 버그2: `parse_single_pdf`가 `page_ftype`을 첫 페이지에서만 계산해 모든 페이지 테이블에 적용한다.

## Scope
- `backend/pipeline/pdf_parser.py`
- `backend/tests/test_pdf_parser.py`
- `.agent-harness/tasks/SURIT-018-pdf-ftype-page-signal-hardening.md`
- `.agent-harness/handoff.md`
- `.agent-harness/locks.md`

## Work
- `_resolve_ftype`에서 `page_ftype == "pharma"`이고 강한 헤더가 `detail` 또는 `basic`인 경우에만 본문 `pharma`를 우선한다.
- 헤더가 `pharma` 강신호인 경우 및 본문이 `detail`/`basic`인 경우는 기존 동작을 유지한다.
- 비-NHIS PDF 표 파싱 루프에서 `page_ftype`을 페이지별로 계산한다.
- 회귀 테스트를 추가한다.

## Constraints
- `_strong_header_ftype` 키워드·우선순위 변경 금지.
- `detect_file_type` 휴리스틱 변경 금지.
- 본문 `detail`/`basic`이 헤더를 이기는 일반화 금지.
- 분류 외 레코드 추출·`row_is_junk` 등 변경 금지.

## Verification
- `cd backend && python -m pytest -q`
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run build`

## Expected Result
- 처방조제 본문 신호가 있는 페이지에서 detail/basic 헤더 OCR 오염으로 처방 PDF가 진료내역으로 굳지 않는다.
- 합본 PDF에서 뒤쪽 처방 페이지는 뒤쪽 페이지 본문 신호로 `pharma` 분류된다.
