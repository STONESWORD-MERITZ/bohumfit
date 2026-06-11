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

- 2026-06-11 `BOHUMFIT-038` - Codex - Railway Chromium install fallback implemented with `PLAYWRIGHT_BROWSERS_PATH=0`, expanded apt packages, backend start script runtime install, and LF shell script guard. Local tests/build passed; Railway Variables/log confirmation remains Human.

- 2026-06-11 `BOHUMFIT-037` - Codex - Railway/Nixpacks Playwright Chromium install configured for repo-root and backend-root deployments; report renderer now uses installed Playwright Chromium; PDF loading button nowrap fixed. tsc/lint/test/build/backend pytest passed.

- 2026-06-11 `BOHUMFIT-036` - Codex - claim estimate amount highlighted in frontend and report template; `/insurance` no longer auto-opens browser print fallback when BOHUMFIT-030 PDF generation fails. tsc/lint/test/build/backend pytest passed.

- 2026-06-11 `BOHUMFIT-035` - Codex - `/insurance` PDF button connected to BOHUMFIT-030 backend report PDF endpoint; NHIS refund amount highlighted in frontend and backend report template; report PDF regression test added. tsc/lint/test/build/backend pytest passed.

- 2026-06-11 `BOHUMFIT-034` - Codex - `/insurance` money input comma formatting, NHIS cap excess exclusion from insurance claim estimate, minimum-deductible card hidden, print path confirmed as browser print. tsc/lint/test/build/backend pytest passed.

- 2026-06-11 `BOHUMFIT-033` - Codex - `/insurance` PDF 저장을 백엔드 PDF 생성 호출에서 현재 UI 브라우저 인쇄 방식으로 전환. tsc/lint/test/build/backend pytest 통과.

- 2026-06-11 `BOHUMFIT-032` - Codex - `/insurance` 최소공제 사용자 입력 UI 제거, 자동 최소공제 추정 적용, PDF 저장 버튼 연결 완료. tsc/lint/test/build/backend pytest 통과.
- 2026-06-11 `BOHUMFIT-030/031` - Codex - Windows authority verification and 031 reconciliation completed. Frontend gates passed, report PDF tests 16 passed with skip 0 after Playwright Chromium install, full backend suite 201 passed/7 skipped. User gate required overall pytest skip 0, so commit/push held; locks released for Human decision.
- 2026-06-11 `BOHUMFIT-030` - Cowork - 백엔드 리포트 PDF(고지/실손 분리) 구현 완료. 범위: `backend/pipeline/report_pdf.py`·`backend/templates/report_disclosure.html`·`report_insurance.html`·`backend/tests/test_report_pdf.py`(신규), `backend/main.py`(`POST /api/report/pdf` 추가)·`backend/requirements.txt`(jinja2/playwright 고정), 태스크/handoff/locks. 콘텐츠 수정 6건 반영·산출물 구 브랜드명 0건·금액 passthrough(재계산 0)·휘발 처리. /tmp pytest 15p/1s + 엔드포인트 스텁 하네스 + PDF 2종 육안 통과. **031 차단 원인 2건(sec.items TypeError, 템플릿 주석 구 브랜드명) 해결됨** → Codex(Windows) 전체 pytest(스킵 0 확인)·커밋·푸시 대기로 잠금 해제(ENV-MOUNT-NOTES 준수, 마운트 git 미실행). 결정 3건 handoff 기록.
- 2026-06-11 `BOHUMFIT-031` - Codex - 통제 리네임 A 범위 적용 및 검증 시도 후 해제. 030 잠금 파일(`backend/pipeline/report_pdf.py`, templates, `backend/main.py`, `backend/requirements.txt`, `backend/tests/test_report_pdf.py`, 030 task)은 수정/스테이징 제외. 전체 backend pytest는 030 리포트 템플릿 실패로 gate 미통과 → commit/push 보류.
- 2026-06-08 `BOHUMFIT-029` - Cowork - 독립 실손 예상 보험금 계산기(수기/PDF 모드) 구현 완료. 범위: `src/lib/insuranceCalc.ts`(신규, 검증 미러 verbatim 추출)·`src/pages/InsuranceCalculator.tsx`(신규)·`src/App.tsx`(라우트)·`src/components/Layout.tsx`(네비). Disclosure.tsx·backend **무변경**(회귀 0). 미러 일치 /tmp node 검증(backend BOHUMFIT-028 참조값 일치)·신규 파일 온전 동기화·React.ReactNode tsc 이슈 선수정. in-sandbox tsc/build 는 마운트 truncated Disclosure 로 차단 → Codex(Windows) 검증·커밋·푸시 대기로 잠금 해제(ENV-MOUNT-NOTES 준수, 마운트 git 미실행). 결정 3건 handoff 기록.
- 2026-06-09 `BOHUMFIT-028` - Codex - Windows authority verification completed; stale `.git/index.lock` removed after writer exited; pytest/tsc/build and backend-vs-TS mirror comparison passed; locks remain released.
- 2026-06-08 `BOHUMFIT-028` - Cowork - 실손 최소공제(정액↔정률 max) + 의원 자동분류 구현 완료(additive, 기존 ①②③ 불변). 범위: `backend/insurance/constants.py`(§4-4)·`calculator.py`(§6-1 함수 4종)·`tests/test_min_deductible.py`(14케이스)·`src/pages/Disclosure.tsx`(TS미러+①-b)·설계문서 v4. 백엔드 산식 9건 독립 검증·Windows 원본 정합 확인. in-sandbox pytest/tsc 는 마운트 truncation 으로 차단 → Codex(Windows) 검증·푸시 대기로 잠금 해제(Active 미점유 — 작업 중 기록 누락, 변경범위 위와 같음). 백엔드-TS 미러 일치(케이스10) Codex 대조 요망.
- 2026-06-08 `BOHUMFIT-027` - Codex - Windows authority verification completed; stale `.git/index.lock` removed after `write-tree` exited; pytest/tsc/build and O Seongsim PDF mock check passed; locks remain released.
- 2026-06-07 `BOHUMFIT-027` - Cowork - 추가검사·재검사 판정 정교화(B q2_suspicion 검사근거 게이팅 + 가 프롬프트 4기준/103↔105 해소 + 나 same-day collapse) 구현 완료. (나)+(B) 핵심 로직 독립 검증 8건·Windows 원본 정합·기존 통합테스트 회귀 없음 확인. ai_judgment parse OK. 전체 pytest 는 analyzer 마운트 truncation 으로 차단 → Codex(Windows) 검증·푸시 대기로 잠금 해제. 과소 방지 설계결정(같은날 다종·교차일 추적관찰은 결정론 보존 + Gemini 판단)은 handoff 기록. filters/result_builder 미수정.
- 2026-06-07 `BOHUMFIT-025` - Codex - Windows authority verification completed for insurance print/PDF output; Chrome print-media PDF render passed; locks remain released.
- 2026-06-06 `BOHUMFIT-025` - Cowork - 실손 리포트 PDF 출력(브라우저 인쇄 + @media print, 새 의존성 없음) 구현 완료. Windows 원본 JSX 균형·백엔드 §4-1 일관성(COPAY_RATE_VERIFIED) 확인. in-sandbox tsc/build 는 마운트 truncation 으로 차단 → Codex(Windows) 검증·푸시 대기로 잠금 해제. calculator.py 미수정(이미 정합), 무관 변경 filters.py 미수정.
- 2026-06-07 `BOHUMFIT-024` - Codex - copay-rate draft marker finalized without numeric changes; locks released.
- 2026-06-06 `BOHUMFIT-023` - Codex - Windows authority verification completed and scoped publish prepared; no active locks remained.
- 2026-06-06 `BOHUMFIT-023` - Cowork - 실손 청구 2단계(§4-2 세대별 합산범위 확정 + 급여 surfacing + 실손 탭 UI) 구현 완료. §4-2 로직 독립 검증·Windows 원본 정합 확인. in-sandbox pytest/tsc/build 는 마운트 truncation 으로 차단 → Codex(Windows) 검증·푸시 대기로 잠금 해제. 범위 확장 `backend/analyzer.py`·`backend/main.py`(additive surfacing, 고지 로직 불변) 포함. 무관 변경 `backend/filters.py` 미수정.
- 2026-06-06 `BOHUMFIT-022` - Cowork - 실손 청구 안내 1단계(수치 상수+계산 모듈+데이터 진단) 구현 완료, 검증 통과(pytest 156p/7s, tsc app·node, vite build). Codex 검증·푸시 대기로 잠금 해제. (무관 변경 backend/filters.py 는 미수정)
- 2026-06-01 `BOHUMFIT-021` - Codex - backend Sentry PII hardening completed; locks released.
- 2026-05-31 `BOHUMFIT-018` - Codex - prescription PDF page signal hardening completed; locks released.
- 2026-05-30 `BOHUMFIT-016` - Codex - backend direct dependency pins verified against current passing versions; clean venv install and pytest passed; locks released.
- 2026-05-30 `BOHUMFIT-002` - Codex - git remote switched to bohumfit and package name cleanup completed; locks released.
- 2026-05-30 `BOHUMFIT-001` - Codex - rebrand audit completed; runtime files unchanged; locks released.
- 2026-05-30 `BOHUMFIT-013` - Codex - Q3 medication daily-max accumulation, BUG-012 PDF verification, and `_build_health` dead-code removal completed; locks released.
- 2026-05-30 `BOHUMFIT-LAUNCH-002` - Codex - BOHUMFIT.ai final open trust/legal placeholder cleanup completed; locks released.
- 2026-05-30 `BOHUMFIT-LAUNCH-001` - Codex - BOHUMFIT.ai open-prep implementation completed; locks released.
- 2026-05-30 `BOHUMFIT-BUG-014` - Codex - clinical review scope/completeness fixed; locks released.
- 2026-05-30 `BOHUMFIT-BUG-013` - Codex - question-specific disclosure display completed; locks released.
- 2026-05-30 `BOHUMFIT-PROGRESS-001` - Codex - progress determinism plan updated; locks released.
- 2026-05-30 `BOHUMFIT-HARNESS-CODEX-ONLY` - Codex - final check/plan/publish completed; locks released.
- 2026-05-30 `BOHUMFIT-HARNESS-CODEX-ONLY` - Codex - documentation cleanup completed; locks released.
