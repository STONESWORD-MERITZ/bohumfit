# BOHUMFIT-026 — "추가검사 의심" 과검 진단 (진단 전용 · 코드 수정 없음)

- Owner: Cowork (진단) — 읽기 전용. 코드/커밋 없음.
- 생성: 2026-06-07
- 목적: 건강체 Q2 "추가검사·재검사 의심" 판정이 너무 넓게 잡히는지 진단하고 수정 방향 제안.
- 범위: 읽기만 — `backend/pipeline/ai_judgment.py`, `backend/filters.py`, `backend/analyzer.py`, `backend/pipeline/result_builder.py`, `backend/pipeline/helpers.py`, `backend/pipeline/disease_aggregator.py`. 잠금 미추가(read-only).

## 확정 정의 (진단 기준)
추가검사/재검사로 '보는' 것: 선행 검사 결과에 따라 후속 검사가 필요해진 경우(추가검사=다른 종류 추가, 재검사=같은 검사 재시행).
'안 보는' 것: 단순 정기검진/추적관찰, 같은 날 일련의 동시·연속 검사(한 진단 과정), 병증변화·치료 없이 진행되는 정기검사.
판정 4기준: ①선행검사 존재 ②결과로 후속검사 필요해졌나 ③단순 추적관찰인가 ④같은 날 일련검사인가.

## 산출물
상세 진단·수정방향은 `.agent-harness/handoff.md` 2026-06-07 BOHUMFIT-026 항목 참조.

## 검증
- 코드 수정 없음. `cd backend && python -m pytest -q` 기준선 = 156 passed, 7 skipped (클린).
- 임시 확인 스크립트(/tmp/diag_gate.py)는 비저장(커밋 안 함).

## 후속 제안
- 구현 태스크: **BOHUMFIT-027-additional-test-narrowing** (가 프롬프트 + 나 결정론 보조 제외 조합).
