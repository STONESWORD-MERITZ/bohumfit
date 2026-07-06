# BOHUMFIT-173 — 뷰포트 유동 스케일 전환 (clamp 기반, 접근성 보존)

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: Cowork

## 배경 (Human 확정 — A안)
뷰포트 상대 단위 도입. 전면 vw 치환은 접근성(WCAG 1.4.4 확대/축소) 위반이라 금지.
clamp(min, 유동, max) 기반으로 상·하한을 지키는 유동 스케일만 적용.

## 적용 범위 (A안 확정)
- ✅ 히어로/디스플레이 타이포 (Home·랜딩 헤드라인) → clamp() 유동
- ✅ 주요 섹션 패딩·컨테이너 여백 → clamp() 유동 스페이싱
- ✅ 모바일 100vh 문제 → dvh 교체 (해당 위치만)
- ❌ 본문·캡션·버튼 텍스트 → 고정(rem) 유지, 절대 vw화 금지
- ❌ Tailwind 반응형 브레이크포인트 구조 → 유지 (이중 체계 금지)

## 원칙
- 순수 vw/vh 단독 금지 — 반드시 clamp 상·하한 / 확대 200% 잘림·겹침 없음(WCAG AA)
- FIT v1.1 위계 기준값 = clamp의 max (큰 화면에서 현행보다 커지지 않게)

## Step 0 — 진단
1. 타이포 정의 방식(Tailwind 유틸 vs 토큰) → 유동화 진입점
2. 히어로/디스플레이 실사용 위치 매핑 (Home·WhyDisclosure·HomeMission 등)
3. 100vh 사용처 grep
4. 유틸/변수/인라인 방식 결정 (index.css 유동 유틸 소수 정의 권장)

## Step 1 — 유동 타이포 유틸 정의 (index.css, max=현행 기준값·min=모바일 하한·360~1280 구간)
## Step 2 — 랜딩 최상위 헤드라인·디스플레이만 적용 (본문·서브·버튼·캡션 무접촉)
## Step 3 — 히어로 위주 유동 스페이싱 + 모바일 풀스크린 100vh→100dvh (svh/lvh 판단 근거 기록)

## 수정 금지
- 본문/버튼/캡션/폼 텍스트 크기 / 기능 화면 조밀 레이아웃 / Tailwind 브레이크포인트 로직 / backend

## 검증
- 순수 vw 단독 신규 0 grep / 본문·버튼 유동 미적용 / 200% 확대 코드 검토(+Codex 스모크)
- raw gray 0 / tsc·build·pytest = Codex 권위 (485/8, 백엔드 무변경)

## 커밋 (Codex)
feat(BOHUMFIT-173): 히어로 유동 스케일 전환 (clamp 기반·접근성 보존)
