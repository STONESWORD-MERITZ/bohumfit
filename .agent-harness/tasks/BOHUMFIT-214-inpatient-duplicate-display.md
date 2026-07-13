# BOHUMFIT-214 - 입원 판정 라인 중복 제거

Owner flow: Human -> Codex Windows
Current owner: Human

## Intent
- 고지 결과에서 입원은 상단 `입원기간` 블록에 회차별 상세와 안내가 이미 있으므로, 하단 판정 칩/라인의 `입원 N일/N회` 중복 표시를 제거한다.
- 수술, 통원, 투약처럼 별도 상단 상세가 없는 항목은 기존 하단 표시를 유지한다.

## Scope
- 수정 허용:
  - `src/pages/Disclosure.tsx`
  - `backend/main.py`
  - `backend/templates/report_disclosure.html`
  - 관련 backend/frontend 테스트
  - harness docs
- 수정 금지:
  - `backend/filters.py` 및 판정 로직/임계
  - `backend/coverage/`
  - DB/auth/payment core
  - 실 PDF/PII 커밋

## Work
- 화면: `입원기간` 블록은 유지하고 하단 metric chip에서 입원 일수/회수만 제거한다.
- 복사문: 입원 회차별 줄은 유지하되 하단 detail의 입원 판정 문구 중복은 제거한다.
- PDF: 입원 근거 블록은 유지하고 하단 metric chip에서 입원 일수/회수만 제거한다.
- 판정 대상 코드집합·분석 결과 구조는 변경하지 않는다.

## Verification
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run build`
- `cd backend && python -m pytest -q`
- 관련 205/213/214 표시 테스트

## Handoff Requirements
- Changed / Verified / Notes / Commit hash / pytest 숫자를 handoff 상단에 기록한다.
- scope 파일만 stage하고 실 PDF/PII는 stage하지 않는다.

## Result
- 화면/복사문/PDF에서 입원-only 하단 판정 중복을 제거했다.
- 화면: 상단 `입원기간` 블록은 유지하고 하단 `입원 N일/N회` 칩은 숨김.
- 복사문: 회차별 입원 줄은 유지하고 바로 아래 `N년이내 입원 (N일)` detail 중복은 숨김.
- PDF: `입원 근거` 블록은 유지하고 하단 입원 칩/detail 중복은 숨김.
- 판정 payload와 코드집합, `backend/filters.py`는 변경하지 않았다.

## Verified
- `npx tsc -p tsconfig.app.json --noEmit` passed.
- `npx tsc -p tsconfig.node.json --noEmit` passed.
- `npm run lint` passed.
- `npm test` passed: `25 passed`.
- `npm run build` passed, existing Vite chunk warning only.
- `python -m py_compile main.py pipeline\report_pdf.py` passed.
- `python -m pytest tests/test_inpatient_display_214.py tests/test_kakao_inpatient_205.py tests/test_evidence_213.py tests/test_report_pdf_q1q5.py -vv` passed: `22 passed`.
- `python -m pytest -q` passed: `611 passed, 8 skipped`.
- Read-only real PDF smoke: Seok Jiwon 3 PDFs parsed `basic 68/detail 770/pharma 181`, parse_errors 0; inpatient periods/evidence remained and PDF inpatient chip was absent. Lee Mi-suk 3 text PDFs parsed `basic 247/detail 1698/pharma 803`, parse_errors 0; duplicate inpatient detail absent.
