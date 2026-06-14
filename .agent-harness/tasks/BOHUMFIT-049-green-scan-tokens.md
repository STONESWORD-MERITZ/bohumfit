# BOHUMFIT-049 보라→그린(포레스트) 전수 스캔 + 토큰 정의만 교체

## Owner
Cowork(Claude) — 1단계 스캔 + 2단계 토큰 교체. 검증·커밋은 Codex(Windows). 하드코딩/클래스/SVG/backend 잔재 치환은 050.

## 목표
3색(짙은회색/검정/보라) 중 **보라만** 차분한 포레스트 그린으로 교체. 회색·검정 유지. 색 외 변경 절대 금지(기능·카피·구조 불변). 토큰 변수로 분리 유지. ★네온·라임 금지 — 포레스트 톤만.

## 그린 토큰 값
- --color-primary #7C3AED → **#15663D**
- --color-primary-strong #6D28D9 → **#0F4E2F**
- --color-primary-soft #EDE9FE → **#E3F0E8**
- --color-text/-strong/-muted: 유지
- accent 램프(현재 보라 violet) → 포레스트 그린 램프(어두운 #0F4E2F ~ 기본 #15663D ~ 옅은 #E3F0E8 보간). BOM 보존.

## 1단계 스캔(읽기 전용) — 결과는 handoff '보라 인벤토리(A~F)'
- (A) 토큰 정의 (B) 토큰 참조(자동 전환) (C) 하드코딩 hex (D) violet-/purple- 클래스 (E) SVG/인라인(로고 별도) (F) backend PDF.

## 2단계 — index.css 토큰 정의만 교체
- accent 램프 50~900 + --color-primary/-strong/-soft 를 그린으로. BOM 보존.
- 토큰 참조(B)는 자동 그린. 하드코딩(C)·클래스(D 없음)·SVG(E)·backend(F)는 **050 범위**.

## 자체검증
- /tmp tsc(영향 없음 확인) + index.css 토큰 그린 확인 + 그린 대비(본문/버튼) 4.5:1 + 포레스트 톤(#15663D 계열, 라임/네온 아님).

## 산출
- handoff: 보라 인벤토리(A~F) + 050 범위(C/D/E/F 잔재). Next: Codex(049 검증·커밋) → 050(잔재 치환).
