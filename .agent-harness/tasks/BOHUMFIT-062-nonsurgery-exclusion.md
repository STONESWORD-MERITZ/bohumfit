# BOHUMFIT-062 비수술 코드 수술 오분류 제외

## Owner
Cowork(구현) → Codex(Windows 검증·커밋·푸시). 마운트 git 금지·원본 PDF 커밋 금지.

## 문제
수술 필터(`_is_surgery_match` / `_is_detail_surgery_match`)가 비수술 코드명을 "10년 이내 수술"로 오분류 → 화면 고지대상 오노출.

## 제외 대상(전역, 4건·확장 예정)
1. 수액제주입로를통한주사  2. 치관수복물또는보철물의 제거[1치당]-간단한것
3. 치관수복물또는보철물의 제거[1치당]-복잡한것  4. 후두내주입

## 구현
- 신규 `backend/pipeline/surgery_exclusions.py`: `NON_SURGERY_NAMES`(공백 제거 정규화 후 exact) + `is_non_surgery_excluded(name)`. **항목 추가는 이 한 곳**.
- `helpers._is_surgery_match` 최상단 가드(`is_non_surgery_excluded → False`).
- `disease_aggregator._is_detail_surgery_match` 최상단 가드 + nhis OR-branch(`... and not is_non_surgery_excluded`).
- 수술 감지 알고리즘/패턴 규칙 불변(제외 리스트만).
- 프런트: 수술 감지 중복 없음(`surgery_count`/`surgeries` 백엔드 플래그 표시만) → 백엔드만.

## 검증
- /tmp(061 적용 base) pytest: 관련 + 신규 = 90 passed/6 skipped. 신규 `test_surgery_exclusions.py` 4/4(4건 미집계·공백 변형·실수술 정상·detail 미집계).
- Codex(Windows): `cd backend && python -m pytest -q`; frontend tsc app/node·build(backend 무관·영향 없음). 캐노니컬 PDF(최유미 세부진료)로 1·2·3 화면 제외 확인(4는 유닛 커버).

## 가정
- 제외 "전역"(질병·창 무관). 질병별 제외 필요 시 회신.

## 산출
- handoff: 변경·검증·전후. Next: Codex.
