# BOHUMFIT-217 - 판정라인 수술만 + 입원 배지 3개 + 조회기간 연동

Owner flow: Human -> Codex Windows
Current owner: Human

## Intent
- 214 후 화면 확인 결과, Q2 결과 카드 판정라인에 입원 회차 문구가 아직 남아 상단 입원기간 블록과 중복된다.
- 조회기간 변경 시 배지·입원기간·진료기간은 필터되지만 판정라인 텍스트는 필터되지 않아 화면 안에서 불일치가 생긴다.
- 입원 신호는 상단 입원기간 블록과 배지 `[입원 총 N회] [합산 N일]`로 보여주고, 판정라인은 수술 내역만 남긴다.

## Scope
- 수정 허용:
  - `src/pages/Disclosure.tsx`
  - `src/lib/disclosureWindow.ts`
  - `src/lib/disclosureMemo.ts`
  - `backend/main.py`
  - `backend/pipeline/report_pdf.py`
  - `backend/templates/report_disclosure.html`
  - 관련 테스트와 harness 문서
- 수정 금지:
  - `backend/filters.py` 판정·임계·코드집합
  - `backend/pipeline/`의 판정 로직
  - `backend/coverage/`
  - DB/auth/payment core
  - 실 PDF/PII 커밋

## Work
- S0: 판정라인 생성 위치와 215 조회기간 필터가 판정라인 detail에 미적용된 원인을 확인한다.
- S1: 화면·복사문·PDF 판정라인에서 입원 회차 문구를 제거하고 수술 텍스트만 유지한다.
- S2: 화면 배지를 `[입원 총 N회] [합산 N일] [수술 N건]`으로 표시한다.
- S3: 조회기간 필터가 판정라인 수술 텍스트와 배지 숫자에 같이 반영되도록 표시 레이어를 보정한다.
- S4: 215 정책 유지: 화면·복사문은 선택 조회기간 축소, PDF는 10년 전체 보존.

## Verification
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run lint`
- `npm test`
- `npm run build`
- `cd backend && python -m pytest -q`
- 관련 신규/회귀 테스트 `-vv`

## Result
- 화면/복사문/PDF 표시 레이어에서 판정라인은 입원 세그먼트를 제거하고 현재 조회기간 payload의 수술/통원/투약만 남기도록 정리했다.
- 화면 배지는 `입원 총 N회`, `합산 N일`, `수술 N건`으로 표시한다. 조회기간 필터가 수술 근거를 제거하면 수술 배지와 판정라인 텍스트도 함께 제거된다.
- PDF는 BOHUMFIT-215 정책대로 10년 전체 reports를 보존하되, 고객 산출물의 중복 입원 detail/chip만 정리했다.
- `backend/filters.py`, 판정 임계/코드집합, coverage, DB/auth/payment는 변경하지 않았다.

## Verified
- `npx tsc -p tsconfig.app.json --noEmit` passed.
- `npx tsc -p tsconfig.node.json --noEmit` passed.
- `npm run lint` passed.
- `npm test` passed: `36 passed`.
- `npm run build` passed, existing Vite chunk warning only.
- `cd backend && python -m py_compile main.py pipeline\report_pdf.py` passed.
- `cd backend && python -m pytest tests\test_disclosure_window_215.py tests\test_inpatient_display_214.py -vv` passed: `6 passed`.
- `cd backend && python -m pytest -q` passed: `618 passed, 8 skipped`.
- Read-only real PDF smoke passed without outputting or staging PII: local Seok fixture parsed `basic 68`, Q2 inpatient periods `3`, days `[4, 9, 10]`, parse errors `0`; local Lee fixture parsed `basic 349`, parse errors `0`.
