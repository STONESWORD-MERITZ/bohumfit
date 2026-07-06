# BOHUMFIT-177 — 홈 지표 섹션 은은한 구분 (그린 티 틴트 면)

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: Cowork (구현 완료) -> Codex (Windows 권위 검증·커밋·푸시)

## 배경 (Human 확정)
176 라이트 전환 후 홈 히어로와 지표(1분/99%/30초)가 같은 canvas 배경 위에 얹혀 섹션 경계감이 없음.
Human 결정 = A안: 지표 섹션에 그린 티 틴트 면 배경을 적용해 은은하게 구분.

## 브랜드 (FIT v1.1)
- 그린 티 #CDEDB3 = 섹션 배경 면 전용 (텍스트·선 금지 — 정확히 이 용도).
- "은은하게"가 핵심 — 진한 원색이 과하면 옅은 틴트로. 지표 텍스트(숫자=잉크/에메랄드, 라벨=본문 그레이)는 기존 유지.
- 그린티 위 대비: 에메랄드/그린티 8.3:1·본문/그린티 11.4:1 (전부 AA) — 옅은 틴트면 canvas와 블렌드되어 대비 더 상승.

## Step 0 — 진단 (완료)
- 176 구조: 히어로+지표가 `<div className="flex min-h-[calc(100svh-3.5rem)] flex-col">` 묶음. 히어로 `flex-1`(canvas 투명), 지표 `shrink-0`(묶음 하단).
- 지표 섹션 현재: `<section className="shrink-0 pt-[clamp(0.5rem,0.2rem+1.3vw,1.5rem)] pb-[clamp(2.5rem,1.9rem+2.6vw,4rem)]">` — 배경 없음(canvas 투명), 컨테이너 `mx-auto max-w-5xl px-6`, 그리드 `sm:grid-cols-3`.
- 틴트는 `bg-*` (배경)만 추가 → box-model 불변 → 176 1화면 높이(653px) 영향 없음.

## Step 1 — 지표 섹션 틴트 적용 (완료)
- 결정: **전폭 틴트 밴드**(섹션에 `bg-` 추가). 근거: 176이 히어로+지표를 full-bleed 라이트 서피스로 통합했고, 기존 Our Story 섹션도 `bg-accent-50` 전폭 틴트를 씀 → 카드(박스 테두리 신설)보다 전폭 밴드가 176 레이아웃/기존 패턴과 자연스럽고 fold 하단 지표 밴드로 읽힘.
- 색: `bg-greentea/50` — 그린 티 토큰(면) 50% → canvas와 블렌드되어 은은한 옅은 틴트(진한 원색 회피). 임의 hex 금지 규칙 준수(토큰 유틸리티 + 불투명도 수식어).
- 상단 hairline border: **미적용**. 근거: "배경만 추가·높이 불변" 준수(1px도 안 더함) + 옅은 색 단차 자체가 부드러운 구분. 그린티는 `bg-`로만 사용(선/텍스트 0).
- 히어로(canvas)→지표(옅은 그린티) 색 전환이 fold 안에서 은은하게 발생. 지표 텍스트 색 무변경.

## Step 2 — 대비·회귀 검증 (Cowork /tmp — tsc/build/pytest는 Codex 권위)
- 그린티 면 위 대비 AA 유지(숫자 잉크·suffix 에메랄드·라벨 본문그레이) — 옅은 틴트라 solid #CDEDB3 기준(8.3/11.4)보다 상승.
- 그린티가 텍스트/선 색으로 쓰인 곳 0건(grep) — `bg-greentea`만.
- 176 1화면 높이 불변(배경만 추가, box-model 무변). raw gray 0. TSX 파싱 0건.
- HOW IT WORKS 이하 무변경.

## 수정 금지 (준수)
- 176 히어로·1화면 묶음 로직(배경색만 추가, 높이·구조 불변). 173 clamp / 174 잔여 / 175 헤더·배지.
- 지표 수치·라벨·카피. 그린티를 텍스트·선 색으로 사용 금지(면 전용). backend 전체 / 다른 페이지.

## Stage 예정 (Codex)
- src/pages/Home.tsx
- .agent-harness/tasks/BOHUMFIT-177-metrics-section-tint.md, handoff.md, locks.md

## 커밋 메시지 (Codex)
feat(BOHUMFIT-177): 홈 지표 섹션 그린 티 틴트로 은은한 구분
