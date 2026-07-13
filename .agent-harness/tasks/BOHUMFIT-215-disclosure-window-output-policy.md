# BOHUMFIT-215 - 조회기간 필터(화면·복사문 축소, PDF 전체보존)

Owner flow: Human -> Codex Windows
Current owner: Human

## Intent
- 설계사가 선택한 조회기간 N년을 화면과 복사문에 실제 반영한다.
- PDF는 고지 누락 방지를 위해 10년치 전체 병력을 보존하되, 선택 N년 고지라는 헤더만 표시한다.

## Scope
- 수정 허용:
  - `src/pages/Disclosure.tsx`
  - `src/lib/disclosureWindow.ts`
  - 필요 시 신규 memo helper/test
  - `backend/pipeline/report_pdf.py`
  - `backend/templates/report_disclosure.html`
  - 관련 테스트/harness docs
- 수정 금지:
  - `backend/filters.py` 및 판정 로직/임계/코드집합
  - `backend/coverage/`
  - DB/auth/payment core
  - 실 PDF/PII 커밋

## Work
- 화면: 기준일~N년전 범위 밖 항목은 숨김.
- 복사문: `가입예정상품 [상품고지문항]년 고지형 · 선택 N년 고지` 헤더를 붙이고, N년 초과 항목은 삭제한다.
- PDF: 같은 헤더를 붙이되, reports 원본은 축소하지 않는다.
- 실제 고지 판정은 상품 문항 기준으로 유지한다.

## Notes
- 현재 앱에는 상품별 청약서 문항 기간을 별도 데이터로 선택하는 UI/스키마가 없다. 현행 건강체·간편심사 결과는 최대 10년 문항을 포함하므로 헤더의 `[상품고지문항]년`은 기본 10년으로 표시한다. 상품별 3/5/10년 상품 데이터가 필요하면 Human 결정 후 별도 태스크로 확장한다.

## Result
- 조회기간 state를 `ResultView`로 올려 화면/복사문/PDF 헤더가 같은 선택값을 공유하게 했다.
- 화면: 선택 N년 밖 항목을 숨기고, 혼합 항목은 오래된 입원 회차/근거 배열과 표시용 카운트를 선택 기간 안으로 좁힌다.
- 복사문: `가입예정상품 10년 고지형 · 선택 N년 고지` 헤더를 붙이고 N년 초과 항목/회차를 삭제한다.
- PDF: 같은 헤더를 표시하되, `standard_reports`/`easy_reports` 원본은 축소하지 않아 10년 전체 병력을 보존한다.
- 상품별 문항 기간 데이터 출처는 현재 없음. 현행 최대 문항 기준 10년으로 표시하고 Human note로 남겼다.

## Verified
- `npx tsc -p tsconfig.app.json --noEmit` passed.
- `npx tsc -p tsconfig.node.json --noEmit` passed.
- `npm run lint` passed.
- `npm test` passed: `31 passed`.
- `npm run build` passed, existing Vite chunk warning only.
- `python -m py_compile pipeline\report_pdf.py` passed.
- `python -m pytest tests/test_disclosure_window_215.py -vv` passed: `1 passed`.
- `python -m pytest -q` passed: `612 passed, 8 skipped`.
