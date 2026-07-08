# BOHUMFIT-196 - [전] 계약리스트 보험사 줄분리/보험료미제공 행 파싱 보정

Owner flow: Human -> Codex Windows
Current owner: Human
분류: 사후번호 정정 + 완료 기록

## Intent

이 작업은 BOHUMFIT-193 신규가입 제안서 파싱이 아니라, KB 보장분석 PDF의 **[전] 계약리스트 파서**에서 발생한 재발 버그를 수정한 것이다. 직전 커밋의 라벨이 `BOHUMFIT-193`으로 잘못 붙었으므로, 사후 번호 `BOHUMFIT-196`으로 정정한다.

## Actual Commits

- `a18f311 fix(BOHUMFIT-193): 보장분석 계약리스트 보험사 줄분리 파싱 보정`
  - 실제 내용: BOHUMFIT-196 [전] 계약리스트 파서 버그 수정.
- `9831eb3 docs(BOHUMFIT-193): 계약리스트 파싱 보정 handoff 해시 기록`
  - 실제 내용: BOHUMFIT-196 문서 기록.

위 두 커밋은 이미 push되었으므로 되돌리지 않는다. 이후 문서에서는 BOHUMFIT-196으로 해석한다.

## Problem

이상범 KB 보장분석 PDF에서 ② 컨설팅 전 계약 유지/해지 카드가 일부 계약을 제대로 표시하지 못했다.

- 메리츠화재 보험사명이 PDF 텍스트 추출상 `메리츠화`와 `재`로 분리됨.
- 현대해상 실손 행은 `월납` 없이 `보험료미제공`으로 내려와 기존 계약 행 정규식이 인식하지 못함.
- 그 결과 흥국생명 행까지 상품명/보험사 추정이 오염되고, 화면에 `계약 2`, `계약 4` placeholder가 노출됨.

## Scope

실제 구현 변경 범위:

- `backend/coverage/parser.py`
- `backend/tests/test_coverage_parser_179.py`
- `.agent-harness/handoff.md`
- `.agent-harness/locks.md`

수정 금지/무접촉:

- `backend/pipeline/`
- 신규가입 제안서 파서 구현 경로
- 실 PDF/엑셀/PII 저장 또는 커밋

## Fix Summary

- 계약 행 정규식에서 납입주기(`월납` 등)를 optional로 처리.
- 알려진 보험사명이 행/이어줄로 갈라진 경우 prefix/suffix를 결합.
- index-only 행의 앞 상품명 줄을 복원해 회사명과 상품명이 placeholder로 떨어지지 않도록 보정.
- 미등록 보험사도 `생명`, `화재`, `손보`, `해상` 등 일반 suffix가 있으면 placeholder가 되지 않도록 fallback 유지.

## Verification

수정 당시 Windows 권위 검증:

- 실제 이상범 PDF read-only smoke:
  - warning `0`
  - 월보험료 합계 `96,000`
  - 메리츠화재 `35,070`
  - 흥국생명 `10,950`
  - 현대해상 보험료미제공 실손 행 유지
- `python -m pytest backend\tests\test_coverage_parser_179.py -q`: `13 passed`
- `cd backend; python -m pytest -q`: `561 passed, 8 skipped`
- `npx tsc -p tsconfig.app.json --noEmit`: 통과
- `npx tsc -p tsconfig.node.json --noEmit`: 통과
- `npm run build`: 통과, 기존 Vite chunk-size warning만 출력

## BOHUMFIT-193 Boundary

BOHUMFIT-193은 여전히 **신규가입 제안서 PDF 파싱 -> 후 재계산 연결** 작업이다.

- `.agent-harness/tasks/BOHUMFIT-193-newproposal-parse-registry-ui-spec.md`는 조사/명세 문서로 유지.
- 193의 제품 핵심인 `③ 신규가입 제안서 PDF 첨부 -> 회사별 제안서 PDF 파싱 -> 신규제안 보험료 합계 162,154 -> [후] 데이터 변동`은 아직 구현 완료로 보지 않는다.
- 196은 [전] 계약리스트 파서 재발 수정이며 193 구현 완료 근거로 사용하지 않는다.

## Notes

- 문서 정정 커밋에서 코드 변경은 없다.
- `stash@{0}`은 건드리지 않는다.
