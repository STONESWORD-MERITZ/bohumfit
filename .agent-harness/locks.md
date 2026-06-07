# Locks

Use this file to record active Codex file ownership during a task.

## Active

- none

## Rules

- New work is Codex-only unless the user explicitly assigns another owner.
- Add active locks before editing task-scoped files.
- Release locks when the task is complete, blocked, or handed back to the user.
- Keep this file operational and short. Historical lock detail lives in git history and `handoff.md`.

## Released

- 2026-06-07 `SURIT-025` - Codex - Windows authority verification completed for insurance print/PDF output; Chrome print-media PDF render passed; locks remain released.
- 2026-06-06 `SURIT-025` - Cowork - 실손 리포트 PDF 출력(브라우저 인쇄 + @media print, 새 의존성 없음) 구현 완료. Windows 원본 JSX 균형·백엔드 §4-1 일관성(COPAY_RATE_VERIFIED) 확인. in-sandbox tsc/build 는 마운트 truncation 으로 차단 → Codex(Windows) 검증·푸시 대기로 잠금 해제. calculator.py 미수정(이미 정합), 무관 변경 filters.py 미수정.
- 2026-06-07 `SURIT-024` - Codex - copay-rate draft marker finalized without numeric changes; locks released.
- 2026-06-06 `SURIT-023` - Codex - Windows authority verification completed and scoped publish prepared; no active locks remained.
- 2026-06-06 `SURIT-023` - Cowork - 실손 청구 2단계(§4-2 세대별 합산범위 확정 + 급여 surfacing + 실손 탭 UI) 구현 완료. §4-2 로직 독립 검증·Windows 원본 정합 확인. in-sandbox pytest/tsc/build 는 마운트 truncation 으로 차단 → Codex(Windows) 검증·푸시 대기로 잠금 해제. 범위 확장 `backend/analyzer.py`·`backend/main.py`(additive surfacing, 고지 로직 불변) 포함. 무관 변경 `backend/filters.py` 미수정.
- 2026-06-06 `SURIT-022` - Cowork - 실손 청구 안내 1단계(수치 상수+계산 모듈+데이터 진단) 구현 완료, 검증 통과(pytest 156p/7s, tsc app·node, vite build). Codex 검증·푸시 대기로 잠금 해제. (무관 변경 backend/filters.py 는 미수정)
- 2026-06-01 `SURIT-021` - Codex - backend Sentry PII hardening completed; locks released.
- 2026-05-31 `SURIT-018` - Codex - prescription PDF page signal hardening completed; locks released.
- 2026-05-30 `SURIT-016` - Codex - backend direct dependency pins verified against current passing versions; clean venv install and pytest passed; locks released.
- 2026-05-30 `BOHUMFIT-002` - Codex - git remote switched to bohumfit and package name cleanup completed; locks released.
- 2026-05-30 `BOHUMFIT-001` - Codex - rebrand audit completed; runtime files unchanged; locks released.
- 2026-05-30 `SURIT-013` - Codex - Q3 medication daily-max accumulation, BUG-012 PDF verification, and `_build_health` dead-code removal completed; locks released.
- 2026-05-30 `SURIT-LAUNCH-002` - Codex - BOHUMFIT.ai final open trust/legal placeholder cleanup completed; locks released.
- 2026-05-30 `SURIT-LAUNCH-001` - Codex - BOHUMFIT.ai open-prep implementation completed; locks released.
- 2026-05-30 `SURIT-BUG-014` - Codex - clinical review scope/completeness fixed; locks released.
- 2026-05-30 `SURIT-BUG-013` - Codex - question-specific disclosure display completed; locks released.
- 2026-05-30 `SURIT-PROGRESS-001` - Codex - progress determinism plan updated; locks released.
- 2026-05-30 `SURIT-HARNESS-CODEX-ONLY` - Codex - final check/plan/publish completed; locks released.
- 2026-05-30 `SURIT-HARNESS-CODEX-ONLY` - Codex - documentation cleanup completed; locks released.
