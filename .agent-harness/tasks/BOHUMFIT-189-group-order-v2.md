# BOHUMFIT-189 대분류 순서 v2 + 뇌/심장 분리 + 골절 라벨 환원

## Owner
Codex (Windows 원본 직접 구현·검증·커밋·push)

## Source
- `.agent-harness/tasks/BOHUMFIT-183-group-reorg.md`
- 2026-07-08 사용자 확정 변경: 183 개정, 189 우선 적용

## Goal
고객용 보장분석/컨설팅 화면과 산출물에서 대분류를 새 순서로 보여준다. 담보 단위 집계 금액은 변경하지 않고, 분류·정렬·표시 라벨만 조정한다.

## 확정 순서
`사망 > 후유장해 > 암 > 뇌 > 심장 > 수술 > 입원(간병 포함) > 운전자 > 골절 > 실손 > 화재 > 배상책임 > 기타`

## 구현 범위
- `backend/coverage/constants.py`: 그룹 순서, 뇌/심장 분리, 골절/화상 라벨, 실손·입원 라벨 반영.
- `backend/coverage/aggregator.py`, `export_excel.py`, `export_pdf.py`: `GROUP13` 소비 경로 회귀 확인. 하드코딩 변경이 없으면 코드 수정하지 않는다.
- `src/pages/CoverageRemodel.tsx`: 화면 정렬 순서 반영.
- `backend/tests/test_coverage_group_189.py`: 신규 189 회귀.
- 기존 그룹 회귀 테스트 중 낡은 183 기대값은 189 기준으로 갱신.

## Non-Goals
- `backend/pipeline/` 무접촉.
- `[전]` KB 파싱·집계 기준선 변경 금지.
- BOHUMFIT-182 회사/카운트, 184 계약리스트, 186/187/188 코어 경로 회귀 금지.
- 실 PDF·엑셀·PII 파일 저장/커밋 금지.

## Acceptance
- 뇌 진단 담보는 `뇌`, 심장 진단 담보는 `심장`으로 분리된다.
- `뇌혈관질환수술비`, `허혈성심장질환수술비`는 기존처럼 `수술`에 남는다.
- `골절진단비`, `보철치료비`, extra `화상`은 `골절`로 표시된다.
- 간병·입원일당 담보는 `입원(간병 포함)`으로 표시된다.
- 문건주 기준선 월납 `573,227`, 총납입 `181,984,128`, 상해사망 `550,000,000`, 일반암 `100,000,000`은 유지된다.

## Verification
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run build`
- `cd backend && python -m pytest -q`
- `cd backend && python -m pytest tests/test_coverage_group_189.py -vv`
- 문건주 실 PDF smoke는 메모리에서만 수행하고 산출물을 저장하지 않는다.
