# BOHUMFIT-044 디자인 시스템 — 금융권 신뢰 톤

## Owner
Cowork(Claude) — 구현 1차. 검증·커밋·푸시는 Codex(Windows), 룩 최종 확인은 Human.

## 목표
사이트 전체를 보험·금융권 수준의 신뢰감 있는 UI로. 화면별 제각각 스타일을 하나의
토큰 체계로 통일한다. **기능·산식·라우팅 변경 0 — 시각 계층만.**

## 디자인 방향 (PDF 리포트 아이덴티티 확장)
- 팔레트: 딥 네이비(주조, #0E2F4F 계열) / 골드(포인트, 절제) / 중성 그레이 / 시맨틱(성공·경고·위험).
  보라색(#4F46E5 indigo) 등 기존 산발 색상 제거(이번 범위 화면에서).
- 타이포: 4단 위계(페이지 타이틀/섹션/본문/캡션), 40~50대 가독 — 본문 15px↑, 표 13~14px,
  숫자 tabular-nums.
- 컴포넌트 공통화(`src/components/ui/` 신규): Button(주/보조/위험·로딩), Card, PageHeader,
  DataTable(헤더 네이비·줄무늬·가로스크롤), Field, Badge(판정 뱃지), Callout(안내·면책), EmptyState.
- Layout/네비: 정돈된 금융 대시보드 톤(로고 영역·메뉴 활성 상태·사용자 영역), 모바일 대응 유지.
- 면책·비저장 문구는 Callout 로 통일.

## 적용 범위 (In)
- 토큰(@theme) + `components/ui/*` + Layout/네비 + Footer + 로그인 + 메인(홈).

## 범위 밖 (Out)
- Disclosure / 실손(InsuranceCalculator) / 보장분석(CoverageAnalysis) 페이지 → **BOHUMFIT-045**.
- **Disclosure.tsx 절대 무수정.** Signup/약관/개인정보 페이지도 이번 범위 아님.
- 다크모드.

## 기술 지침
- Tailwind v4 토큰: CSS 변수 기반(@theme), 임의값 남발 금지 — 토큰 참조.
- 신규 파일 우선(components/ui/*). Layout.tsx 는 소형~중형 편집 허용.
- 접근성: 기존 ARIA 패턴 유지, 본문 대비 4.5:1 이상.

## ENV
- 마운트 git 금지, 검증 /tmp.

## 검증
- /tmp: ui 컴포넌트 tsc(strict) + Tailwind v4 컴파일 쇼케이스 → Chromium 스크린샷 육안.
- Codex(Windows): tsc(app/node)·lint·test·build + 전 라우트 브라우저 스모크(특히 045 범위
  페이지가 시각 회귀 없이 기존 스타일로 동작하는지).

## 산출 기록
- handoff 에 토큰 목록·컴포넌트 API 요약(045에서 그대로 쓸 사양) 기록.
- Next: Codex(검증·커밋·푸시) → Human(룩 확인) → 045.
