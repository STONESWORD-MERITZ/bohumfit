# BOHUMFIT-017: 처방 PDF 오분류 잔존 여부 진단

## Owner
- Codex

## Status
- Completed

## Type
- Diagnosis only

## Context
- PROGRESS 백로그에 "처방 PDF 오분류 보정 (P1, 헤더 OCR 누락 시 페이지 텍스트 신호 신뢰)" 항목이 남아 있다.
- `backend/pipeline/pdf_parser.py`는 이미 `헤더 강신호 -> 본문 신호 fallback -> 약신호 헤더는 본문에 양보` 흐름을 구현한 것으로 보인다.
- 이번 태스크는 실제 수정 필요성이 남았는지 읽기 전용으로 확인한다.

## Scope
- Read-only investigation:
  - `backend/pipeline/pdf_parser.py`
  - `backend/tests/`
  - `.agent-harness/handoff.md`
- No code changes.
- No lock added.
- No commit.

## Investigation
- `detect_file_type`, `_strong_header_ftype`, `_detect_ftype_by_page_text`, `_resolve_ftype` 흐름 확인.
- 처방 PDF가 진료내역(`detail`/`basic`)으로 오분류될 수 있는 잔존 경로 확인.
- 헤더 OCR이 약신호 또는 진료내역 신호를 잘못 잡는 경우 본문 신호 우선 여부 확인.
- 기존 처방 PDF 분류 회귀 테스트 커버리지 확인.
- 가능하면 임시 인라인 호출로 분류 함수 재현 확인.

## Verification
- `cd backend && python -m pytest -q`

## Expected Output
- 현재 커버되는 케이스와 미커버 케이스 정리.
- 실제 오분류 재현 여부와 입력 조건 정리.
- 추가 작업 불필요 또는 후속 수정 태스크 제안.
