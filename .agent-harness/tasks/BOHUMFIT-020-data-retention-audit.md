# BOHUMFIT-020: 데이터 파기·잔류 경로 진단

## Owner
- Codex

## Status
- Completed

## Type
- Diagnosis only

## Context
- BOHUMFIT-019에서 BOHUMFIT은 Supabase를 인증 전용으로 쓰며 진료기록·분석결과를 DB/Storage에 저장하지 않는 것으로 확인했다.
- 따라서 업로드 PDF와 추출 진료정보가 메모리, 디스크, 로그, Sentry, Gemini, 응답 경로에서 어디에 남는지 진단한다.

## Scope
- Read-only investigation:
  - `backend/main.py`
  - `backend/analyzer.py`
  - `backend/pipeline/`
  - `src/pages/Disclosure.tsx`
  - Sentry 설정 관련 파일
  - `.agent-harness/handoff.md`
- No runtime code changes.
- No lock added.
- No commit.

## Investigation
- PDF 메모리 처리 및 해제 경로 확인.
- PDF/중간결과 디스크 임시파일 저장 여부 확인.
- 로그/print/error message에 진료기록 원문·PII가 찍히는지 확인.
- Sentry before_send/PII scrub 설정 확인.
- Gemini API로 전송되는 진료정보 범위와 식별정보 포함 가능성 확인.
- 응답이 인증된 사용자에게만 전달되는 구조인지 확인.

## Verification
- `cd backend && python -m pytest -q`

## Expected Output
- 업로드 -> 처리 -> 응답 -> 파기 데이터 흐름 정리.
- 디스크/로그/Sentry PII 잔류 위험 판정.
- Gemini 위탁 전송 항목 정리.
- 후속 수정 태스크 필요 여부 결론.
