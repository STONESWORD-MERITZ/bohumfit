# BOHUMFIT-190 컨설팅 2단계 유지/해지 전용

## Owner
Codex (Windows 원본 직접 구현·검증·커밋·push)

## Source
- `.agent-harness/tasks/BOHUMFIT-186-after-recalculation.md`
- BOHUMFIT-189 구현 커밋 `c0ab2bf`

## Goal
컨설팅 2단계에서 기존 계약은 `유지` 또는 `해지`만 선택한다. 배서 감액/증액, 담보별 조정, 보험료 조정은 서비스 범위에서 제거한다.

## Scope
- `backend/coverage/compare.py`: [후] 재계산 입력을 유지계약 + 187 신규제안으로 제한.
- `backend/coverage/consulting.py`: legacy helper도 기존계약 유지/해지만 반영.
- `src/pages/CoverageRemodel.tsx`: 조정 보험료/담보 조정 UI·plan 스키마·클라이언트 미리보기 제거, 해지 badge/취소선 표시.
- `backend/tests/test_coverage_after_186.py`: 감액/증액/삭제/보험료 조정 테스트 제거·정리.
- `backend/tests/test_coverage_hold_cancel_190.py`: 유지/해지 전용 + 신규제안 공존 회귀 신규.

## Non-Goals
- `backend/pipeline/` 무접촉.
- BOHUMFIT-187 신규제안 경로와 BOHUMFIT-188 비교/요약 경로 회귀 금지.
- `[전]` KB 파싱·집계 기준선 및 BOHUMFIT-189 그룹 순서 회귀 금지.
- 실 PDF·엑셀·PII 파일 저장/커밋 금지.

## Acceptance
- UI에서 감액/증액/삭제/월납 조정 입력이 사라진다.
- 해지 계약은 카드 badge와 취소선으로 구분된다.
- [후]는 유지계약 + 신규제안만으로 월납, 총납입, 담보 집계를 다시 계산한다.
- 기존 조정 필드가 payload에 남아 있어도 결과를 바꾸지 않는다.
- 187 신규제안과 188 전/후 비교 출력은 유지된다.

## Verification
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run build`
- `cd backend && python -m pytest -q`
- `cd backend && python -m pytest tests/test_coverage_after_186.py tests/test_coverage_proposal_187.py tests/test_coverage_compare_188.py tests/test_coverage_hold_cancel_190.py -vv`
- 문건주 실 PDF smoke는 메모리에서만 수행하고 산출물을 저장하지 않는다.
