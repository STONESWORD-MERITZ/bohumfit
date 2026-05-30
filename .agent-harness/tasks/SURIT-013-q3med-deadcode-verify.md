# SURIT-013: BUG-012 검증 마무리 + Q3 투약 누적 교정 + 데드코드 정리

project: SURIT
owner: Codex
status: completed

## Goal

BUG-012의 `row_is_junk` 부작용을 실제 오성심 PDF와 회귀 테스트로 마무리 검증하고, 건강체 Q3 투약 30일 판정을 날짜별 최대 처방일수 누적으로 교정하며, 구버전 `_build_health` 데드코드를 제거한다.

## Scope

Editable files:

- `backend/filters.py`
- `backend/pipeline/helpers.py` (검증 대상, 추가 변경 금지 원칙)
- `backend/tests/`
- `.agent-harness/handoff.md`
- `.agent-harness/locks.md`

Do not edit:

- Q1 3개월 투약 로직
- `detect_drug_changes`
- `_max_presc`
- `row_is_junk` 로직
- frontend files

## Requirements

- 건강체 Q3 `R-H-Q3-MED-30D`는 동일질병 기준 날짜별 최대 처방일수를 모두 합산해 30일 이상이면 고지한다.
- 같은 날짜에 여러 약/여러 병원이 있으면 그날 최대 1건만 반영한다.
- 다른 날짜의 처방일수는 합산한다.
- `med_dict[date] = {drug_key: days}`와 `med_dict[date] = int` 형태를 모두 처리한다.
- 잘못된 날짜는 무시하고, 기준일 경계는 포함한다.
- `_max_presc`는 변경하지 않는다.
- `_build_health` 직접 호출 여부를 검색하고 호출이 없으면 제거한다.
- 오성심 PDF end-to-end 분석으로 질염 14회, 기침 7회, 약국행 오검 없음, 간편 Q2 순수 입원·수술 표시를 확인한다.

## Verify

- `python -c "import ast; ast.parse(open('backend/filters.py', encoding='utf-8').read()); ast.parse(open('backend/pipeline/helpers.py', encoding='utf-8').read()); print('OK')"`
- `cd backend && python -m pytest -q`
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run build`

## Publish

- 검증 전부 통과 시 Codex가 커밋·푸시한다.
- Commit message: `SURIT-013: 건강체 Q3 투약 누적 교정 + BUG-012 실제 PDF 검증 + 데드코드 제거`

## Notes

- 실제 PDF 경로는 사용자 제공 로컬 파일을 사용한다. PDF 비밀번호는 문서에 기록하지 않는다.
