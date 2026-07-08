# BOHUMFIT-186 컨설팅 2단계 — 기존 계약 조정 후 재계산

## Owner
Codex (Windows 원본 구현·검증·커밋)

## 배경
BOHUMFIT-185에서 정의한 consulting plan v1을 실제 [후] 재계산 경로에 연결한다. 이번 단계는 기존 KB 보장분석 [전] 결과의 계약 유지/해지, 월보험료 조정, 담보별 감액·증액·삭제만 다룬다.

## 원칙
- [후]는 별도 산식이 아니다. consulting plan을 [전] 입력에 적용한 뒤, [전]과 동일한 집계·진단 경로를 다시 실행한다.
- 신규 제안 계약은 BOHUMFIT-188 범위로 남긴다. 186에서는 `proposals`를 무시하고 warning만 반환한다.
- `backend/pipeline/`은 건드리지 않는다.
- 실 PDF·PII·추출 데이터는 저장하거나 커밋하지 않는다.

## 구현 범위
- `backend/coverage/aggregator.py`: 기존 내부 aggregate 함수를 재계산 경로에서 재사용 가능한 public helper로 노출.
- `backend/coverage/consulting.py`: plan 적용, [후] before payload 생성, 기존 final 진단 기준 재계산, 전후 비교 요약.
- `backend/main.py`: `/coverage/consulting/after` 엔드포인트.
- `src/pages/CoverageRemodel.tsx`: 기존 계약 유지/해지, 월보험료 조정, 담보별 감액·증액·삭제 입력 UI와 서버 재계산 호출.
- `backend/tests/test_coverage_after_186.py`: cancel/reduce/increase/remove/보험료 조정/불변성/proposals defer 회귀.

## 검증
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run build`
- `cd backend && python -m pytest -q`
- `cd backend && python -m pytest -q tests/test_coverage_after_186.py -vv`
- 가능하면 문건주 실 PDF 스모크: [전] 기준선 유지, 계약 1건 해지 + 1건 감액 후 [후] 월납·진단 재계산 확인.
