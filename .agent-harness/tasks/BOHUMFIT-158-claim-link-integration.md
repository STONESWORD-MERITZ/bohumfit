# BOHUMFIT-158 — 분석 결과 → 보험사 청구 지원 연계 (147 시너지)

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: Cowork

## 배경
148 감사 제안 4위. 설계사의 흐름은 분석 → 고객 안내 → 청구 지원인데, 현재 분석 결과와
보험사 링크 페이지(147의 청구양식 claimFormUrl·필요서류 claimDocUrl 45개사 데이터)가 단절.
분석 결과 화면에서 청구 지원 정보로 자연스럽게 이어지게 연결한다.

## 설계 원칙 (중요 — 과잉 연계 금지)
- 질환→보험사 자동 매칭 불가(가입 보험사 정보가 분석 데이터에 없음) — 추론 로직 발명 금지
- 연계 = "동선 연결"뿐: 결과 화면 → 보험사 링크 페이지 맥락 이동

## Step 0 — 진단
1. InsuranceLinks.tsx 진입 방식: 검색·탭 필터의 URL 파라미터 지원 여부
2. ResultView에서 연계 섹션의 자연스러운 위치 (결과 하단/액션 인근)
3. customer/agent 모드 결과 화면 차이 — 연계 노출 범위 판단

## Step 1 — InsuranceLinks 딥링크
- /insurance-links?q={검색어}&tab={전체|손해보험|생명보험|공제회사} 초기값 주입(마운트 1회, 양방향 동기화 불필요)

## Step 2 — 분석 결과 화면 연계 섹션
- 결과 하단(PDF/카카오 액션 인근) 청구 지원 카드 1개: 제안 톤 제목·본문 1줄·보험사명 검색 입력
  → /insurance-links?q={입력} (빈 입력 시 /insurance-links) — 세컨더리, 라임 금지
- historyView 재열람에서도 동일 노출

## Step 3 — 역방향 동선 (선택)
- InsuranceLinks 상단 분석 유도 1줄 → /disclosure (기존재하면 무변경)

## 수정 금지
- INSURANCE_DATA 배열 값(147) / 분석 파이프라인·질환-보험사 매칭 발명 / backend 전체

## 검증
- 딥링크 ?q= 초기값 적용(기존 검색 회귀 없음) / 연계 카드 agent·customer·historyView 렌더
- raw gray 0 / 라임 CTA 0 / tsc·build·pytest = Codex 권위(기준선 485/8 — 백엔드 무변경)

## 커밋 (Codex)
feat(BOHUMFIT-158): 분석 결과 → 보험사 청구양식/필요서류 연계 동선
