# BOHUMFIT-176 — 홈 히어로 라이트 전환 + 히어로·지표 1화면 통합

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: Cowork (구현 완료) -> Codex (Windows 권위 검증·커밋·푸시)

## 배경 (Human 확정)
현재 홈 히어로는 다크 배경 full-height(174 svh)라 첫 화면이 검정 밴드로 크게 차지하고,
핵심 지표(1분/99%/30초)는 스크롤해야 보임.
Human 결정: ① 히어로 배경 다크→라이트 통일(검정 배경 제거) ② 히어로 + 지표 섹션을 한 화면(1페이지)에 함께 담기 (A안).
"HOW IT WORKS 3단계"는 스크롤 유지.

## 174/175/173 관계
- 174 히어로 min-h-[calc(100svh-3.5rem)] full-height → 176에서 히어로+지표 묶음 컨테이너로 이전(부분 롤백).
  svh 값·계산식(100svh-3.5rem, 3.5rem=헤더 h-14)은 그대로 두고, 적용 대상만 히어로 단독→묶음으로 옮김.
- 173 clamp 타이포 토큰(text-fluid-hero 등)·히어로 패딩 clamp 값은 무변경. 라이트 배경 대비만 재검토(통과).
- 175 히어로 2xl:max-w-4xl 중앙 배치·133b 마운트 트랜지션 유지.

## Step 0 — 진단 (완료)
현행 Home.tsx 구조:
1. HERO `<section min-h-[calc(100svh-3.5rem)] flex items-center bg-ink-900>` (다크·흰 텍스트·accent-400 포인트, dot=흰 0.06)
   - 별도 섹션으로 bg-canvas 래퍼 **바깥**에 존재.
2. `<div relative z-10 bg-canvas>` 래퍼 안에 지표(py-24)·HOW IT WORKS(py-24)·Features·Our Story·가격 CTA 순.
3. 지표 = StatCard(값 text-ink-900 / suffix text-accent-600 / 라벨 text-ink-soft) — 이미 라이트.
- 다크 전용 클래스 위치: 섹션 `bg-ink-900`, 히어로 h1 `text-white`, "1분" `text-accent-400`, eyebrow `text-accent-400`,
  서브 `text-ink-200`, 세컨더리 CTA 2개 `border-ink-700 bg-transparent text-ink-100 hover:bg-ink-800`, 캡션 `text-ink-400`, dot `rgba(255,255,255,0.06)`.
- 합산 높이: 헤더 h-14(3.5rem/56px), 묶음 min-h=100svh-56px. 노트북 768→712px / 900→844px.
  히어로 콘텐츠 실측 약 380~420px + 지표 밴드 약 160~200px = fold 안. (검증 스크립트로 재확인)
- 색 토큰(index.css @theme): ink-900 #0A0A0A / ink #1E293B(본문) / ink-soft #475569(보조) / accent-600 #084734 / canvas #FAFAF8 / line-strong #D9D9D4.

## Step 1 — 히어로 라이트 전환 (완료)
- 히어로 `bg-ink-900` 제거 → bg-canvas 래퍼 안으로 흡수(라이트 통일).
- dot 패턴 `rgba(255,255,255,0.06)`(흰) → `rgba(10,10,10,0.04)`(잉크 극연점 — 라이트서 가시·과하지 않게).
- h1 `text-white` → `text-ink-900`(#0A0A0A, 19.8:1). "1분" `text-accent-400` → `text-accent-600`(#084734, 10.7:1).
- eyebrow(For Insurance Planners) `text-accent-400`(3.3:1 미달) → `text-accent-600`(10.7:1).
- 서브카피 `text-ink-200` → `text-ink`(#1E293B, 14.6:1).
- 세컨더리 CTA 2개 `border-ink-700 bg-transparent text-ink-100 hover:bg-ink-800` → `border-line-strong bg-white text-ink-900 hover:bg-ink-50`.
- 캡션 `text-ink-400`(#A8A8A4, 2.4:1 미달) → `text-ink-soft`(#475569, ~7:1).
- 프라이머리 CTA(bg-accent-600 text-white·bf-shimmer) 무변경. 라임 CTA 미사용(라이트 서피스 → 원칙 자동 충족).

## Step 2 — 히어로 + 지표 1화면 통합 (완료)
- bg-canvas 래퍼를 히어로 앞으로 이동(히어로도 라이트 서피스 위).
- 히어로+지표를 `<div flex min-h-[calc(100svh-3.5rem)] flex-col>` 묶음으로 감쌈(=1화면).
  · 히어로 `<section flex flex-1 items-center>` — 잔여 공간 흡수·콘텐츠 세로 중앙(174 min-h는 묶음으로 이전).
  · 지표 `<section shrink-0 pt-[clamp(0.5rem,0.2rem+1.3vw,1.5rem)] pb-[clamp(2.5rem,1.9rem+2.6vw,4rem)]>` — py-24(192px) → 압축(≈48~88px)로 fold 안 진입.
- 지표 라이트 톤·StatCard 무변경. HOW IT WORKS 이하 무변경(묶음 바깥 스크롤).
- 모바일: min-h는 최소값 → 콘텐츠 초과 시 자연 확장(스크롤 허용·잘림 0).

## Step 3 — 대비·회귀 검증 (Cowork /tmp 범위)
- 라이트 대비 AA: 잉크/흰 19.8:1, 에메랄드/흰 10.7:1, 본문/흰 14.6:1, ink-soft 캡션 ~7:1 — 전부 AA↑(계산 스크립트 확인).
- 흰 바탕 위 라임/그린티 텍스트 0건(grep). raw gray 0. 173 text-fluid 3곳 유지. svh 실코드 1곳(묶음). dvh 8곳 무변경.
- tsc/build/pytest·실뷰포트 스모크는 Codex/Windows 권위(백엔드 무변경 → 기준선 485/8).

## 수정 금지 (준수)
- HOW IT WORKS·Features·Our Story·가격 CTA 내용/구조. 173 clamp 토큰 값. 175 헤더/배지. 다른 페이지. backend 전체. 카피·지표 수치.

## Stage 예정 (Codex)
- src/pages/Home.tsx
- .agent-harness/tasks/BOHUMFIT-176-hero-light-onepage.md, handoff.md, locks.md
- (index.css는 미변경 — 스테이지 제외)

## 커밋 메시지 (Codex)
feat(BOHUMFIT-176): 홈 히어로 라이트 전환 + 히어로·지표 1화면 통합
