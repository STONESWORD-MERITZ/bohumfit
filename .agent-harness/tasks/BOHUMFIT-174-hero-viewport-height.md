# BOHUMFIT-174 — 히어로 뷰포트 높이·세로 중앙 정렬 (173 A안 후속)

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: Cowork

## 목적 (Intent)
173의 A안(타이포·패딩 clamp, dvh 부분 교체)은 유지한 채, 히어로 섹션에 뷰포트 상대 높이 +
세로 중앙 정렬을 추가해 노트북/27인치 모니터에서도 "히어로 + 지표 1페이지 균형"이 나오게 한다.

## 적용 (Scope)
1. 히어로 섹션 높이 = min-h-[calc(100svh - 헤더높이)]
2. 히어로 내부 콘텐츠 세로 중앙 정렬
3. 173 타이포 clamp와 새 높이 정합 재검토 (필요 시 최소 조정·근거 기록)

## 비범위 (수정 금지)
- 173 A안의 다른 항목(본문 rem·브레이크포인트·섹션 패딩 clamp) / 히어로 외 섹션 높이
- dvh→svh 일괄 치환 금지 — 히어로만 svh / backend 전체

## Step 0 — 진단
1. ★헤더 높이 가변 여부·sticky 여부 → --header-h 변수화 필요성 판단
2. 173 dvh 적용 위치 재확인 (svh는 히어로만 — 경계 명확화)
3. 대상 히어로 판단: Home(주 대상), WhyDisclosure·HomeMission 포함 여부 (과잉 적용 방지)

## Step 1 — 헤더 높이 변수화(필요 시) / 고정이면 상수 근거 기록
## Step 2 — 히어로 min-h + flex 세로 중앙 (짧은 화면 중앙·긴 화면 확장, 잘림 0)
## Step 3 — clamp 정합 재검토 (173 토큰 최소 수정)

## 검증
- svh 히어로 한정·기존 dvh/vh 무변경 grep / 본문 rem 고정 유지 / 잘림 0
- tsc·build·pytest = Codex 권위 (485/8 — 백엔드 무변경)

## 커밋 (Codex)
feat(BOHUMFIT-174): 히어로 뷰포트 높이·세로 중앙 정렬 (노트북·27인치 1페이지 균형)
