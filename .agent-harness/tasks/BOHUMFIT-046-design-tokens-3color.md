# BOHUMFIT-046 공통 디자인 토큰 — 3색 원칙(짙은회색·검정·보라, 골드 제외)

## Owner
Cowork(Claude) — 구현. 검증·커밋은 Codex(Windows). 기능·산식·라우팅 변경 0, 색 토큰만.

## 컬러 토큰 (index.css 단일 소스)
- --color-text #1E293B(짙은회색, 본문 기본) / --color-text-strong #0A0A0A(고유명사만) / --color-text-muted #475569(보조)
- --color-primary #7C3AED(보라, CTA·링크·브랜드, 아껴) / --color-primary-strong #6D28D9 / --color-primary-soft #EDE9FE
- accent 스케일(페리윙클) → 보라(Violet) 램프로 repoint → 기존 accent-* 유틸이 자동으로 보라.
- 골드: src에는 hex 없음(확인). Badge "gold" tone은 accent 매핑이라 보라로 자동 전환.

## 위계
- 글자 대부분 짙은회색(#1E293B). 검정(#0A0A0A)은 고유명사 강조 전용(토큰 제공·점진 적용).
- 보라는 CTA/링크/브랜드 지점에만. soft 보라는 배경/배지.

## 범위
- `src/index.css`(@theme 토큰, BOM 보존): accent→보라, 3색 토큰 추가, 본문 alias(ink/ink-soft) 3색 repoint.
- `src/components/ui/Button.tsx`: primary = 보라(CTA).
- 하드코딩 치환: `CoverageTableView.tsx` 네이비 #1F3A5F/#14253D → ink 다크 토큰. indigo 클래스(App/AnalysisProgress/CoverageAfterSection) → accent(보라).
- 페이지(Layout/Login/Home/why/보장분석)는 토큰 참조라 자동 추종 — 본문 로직·구조 무수정.
- 로고 파일 무수정(색은 handoff 제안만).

## 범위 밖
- amber/red/green 시맨틱(경고·위험·성공)은 브랜드색 아님 → 유지.
- 페이지별 텍스트 위계 전수 retrofit(점진).

## 자체검증
- /tmp tsc(편집 컴포넌트) + 잔존 페리윙클(#5B5BD6)/네이비(#1F3A5F,#14253D)/골드/indigo 하드코딩 grep(로고 제외 0) + 보라 대비 4.5:1.

## 산출
- handoff: 토큰 매핑표·골드 제거 내역·잔존 하드코딩·로고 색 제안. Next: Codex 검증·커밋 → 047.
