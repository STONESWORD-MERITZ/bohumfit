# BOHUMFIT-163 — 로그인 대시보드 홈 (최근 분석·사용량·바로가기)

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: Cowork

## 배경 (Human 확정)
148 감사 163 항목. 히스토리(156·171)·사용량(billing_status)·청구 링크(147)가 이미 갖춰져
신규 API 없이 조합으로 구성 가능. 진입 방식 = A안: 별도 /dashboard 라우트 신설,
기존 로그인 후 흐름(현행 /disclosure 진입)은 무변경. 헤더/NAV에서 대시보드 진입.

## 설계 원칙
- ★신규 백엔드 API 발명 금지 — 기존 엔드포인트 조합만(부족 발견 시 구현 말고 handoff 보고)
- 위젯은 기존 데이터 소스 재사용, 신규 데이터 수집 로직 0
- FIT v1.1 토큰·기존 ui 컴포넌트, 라임 CTA 화면당 1회 원칙

## Step 0 — 진단
1. 로그인 후 진입 라우트 현황 (무변경 전제 확인)
2. 재사용 API 시그니처: /history?track=recent|saved, /billing/status — 필드 충족 확인
3. 재사용 컴포넌트 매핑 (히스토리 아이템·UsageBadge·ui/Card 등)
4. 최소 호출 수 확인 (기존 목록 API로 카운트 커버 여부)

## Step 1 — /dashboard 라우트 + 골격 (ProtectedRoute·NAV 진입점·인사 타이틀)
## Step 2 — 위젯 5종: 최근 분석 3~5건(빈 상태 CTA)·이번 달 사용량(159 톤)·저장 리포트 수·
  바로가기(분석/보험사 링크/요금제)·Pro 업셀(무료 한정·internal 미노출) + 위젯별 graceful
## Step 3 — 반응형(다단→1단)·접근성(heading 위계·aria)

## 수정 금지
- 로그인 후 기본 진입 라우트 / 분석 파이프라인·히스토리·빌링 백엔드 / 신규 API / 신규 라우트는 /dashboard 1개만

## 검증
- 신규 API 0 / 위젯별 graceful / raw gray 0·라임 ≤1 / 반응형 1단 / tsc·build·pytest = Codex 권위(485/8)

## 커밋 (Codex)
feat(BOHUMFIT-163): 로그인 대시보드 홈 (최근 분석·사용량·바로가기)
