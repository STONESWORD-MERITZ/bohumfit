# BOHUMFIT-104-surgery-cast-misclassification
## 목표
부목/캐스트 처치가 수술로 오분류되는 원인 파악 및 수정
## 재현 케이스 (실제 PDF에서 확인된 오분류)
- 진료일: 2024-06-07, 병원: 본정형외과의원
- 진료내역: 처치 및 수술/캐스트(양방)
- 코드명 1: 부목-단하지[하퇴로부터 족부까지]
- 코드명 2: STARFIX LIGHT (부목 재료)
→ 위 두 항목이 수술로 분류되어 고지 대상으로 표시됨
## 예상 원인
1. surgery_exclusions.py의 NON_SURGERY_NAMES 목록에 부목/캐스트 관련 코드명 미등록
2. "처치 및 수술/캐스트" 카테고리가 수술 탐지 로직에서 걸러지지 않음
3. disease_aggregator.py 또는 result_builder.py에서 캐스트 카테고리 예외 처리 미적용
## 작업 범위
- backend/pipeline/surgery_exclusions.py
- backend/pipeline/disease_aggregator.py (읽기 + 수정 가능)
- backend/pipeline/result_builder.py (읽기 확인)
- backend/tests/test_surgery_exclusions.py (회귀 테스트 추가)
## 분석 및 수정 지침
### 1. 원인 추적 (수정 전 필수)
a. surgery_exclusions.py — NON_SURGERY_NAMES에 "부목","캐스트","STARFIX" 항목 있는지
b. disease_aggregator.py — "처치 및 수술/캐스트"를 수술로 분류하는 로직
c. result_builder.py — surgery 집계 방식
### 2. 수정 방향 (원인에 따라 A/B/C)
- Case A — NON_SURGERY_NAMES 누락: "부목-단하지","부목-장하지","STARFIX","캐스트" 추가
- Case B — 카테고리 자체가 수술로 잡힘: 캐스트 카테고리를 수술 제외 처리
- Case C — 복합: A+B
### 3. 회귀 테스트
test_surgery_exclusions.py: 부목-단하지[…] / STARFIX LIGHT / 캐스트 카테고리 → 수술 아님
## 비목표
- 모든 정형외과 처치 일괄 제외 / 수술이 맞는 항목 제외 변경
## 완료 조건
- [x] 원인 파악·handoff 기록
- [x] 부목/캐스트 오분류 수정
- [x] 회귀 테스트 추가·통과
- [x] pytest -q 통과
- [x] tsc 영향 없음 확인
