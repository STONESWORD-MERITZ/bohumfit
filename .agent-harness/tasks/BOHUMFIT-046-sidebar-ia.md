# BOHUMFIT-046 사이드바 전환 + 메뉴 재편 — Mercury 무드 유지

## Owner
Cowork(Claude) — 구현 1차. 검증·커밋·푸시 Codex(Windows), 구조 확인 Human.

## 목표
상단 네비 → 좌측 사이드바 셸 전환 + 메뉴 재편. 페이지 내부 스타일은 047 — 이번엔
셸(Layout·라우팅·진입 구조)만. 기능·산식 변경 0.

## 메뉴 구성 (이 순서)
1. 왜 중요한가
2. 알릴의무 필터 ← 고객용/설계사용 단일 메뉴 통합
3. 보장분석 (컨설팅 전·후)
4. 실손 계산
(+ 기타 항목·사용자 영역은 하단/보조 영역)

## 알릴의무 통합 — 저위험 래퍼
- 현 구조(파악 결과): `/disclosure`=Disclosure(initialMode="agent"), `/check`=Disclosure(initialMode="customer").
  **Disclosure 는 `?mode=` 파라미터를 라이브 해석**(1246~1248행: param 우선, 없으면 initialMode)
  + 내부 ModeSwitch(두 카드, /check·/disclosure?mode=agent 링크) 보유.
- 신규 `DisclosureHub`: 상단 세그먼트 탭(고객용|설계사용)이 `?mode=` 만 변경 →
  기존 `<Disclosure />` 그대로 렌더(**무수정**, key 리마운트 없음).
- `/check` → `/disclosure?mode=customer` redirect(북마크·Home 링크 보존).
- 모드 전환 상태: 기존(라우트 분리)은 전환 시 리마운트로 상태 손실 — 허브(단일 라우트)는
  파라미터만 변경되어 **상태 보존(개선)**. 내부 ModeSwitch 와 허브 탭의 중복 노출은 047 정리 후보.

## 사이드바 — Mercury 대시보드 문법
- 라이트 캔버스 + 우측 헤어라인, 그림자 없음. lucide 아이콘+라벨,
  활성 = 페리윙클 텍스트+파스텔 배경, 호버 = 캔버스 톤.
- 상단 로고(잉크+포인트 도트), 하단 사용자 영역(이메일·로그아웃/로그인).
- 데스크탑 접힘(아이콘-only): **이번 미채택**(효용 대비 복잡도·접근성 비용 — handoff 기록), 047+ 후보.
- 모바일: 상단 바(햄버거) → 오버레이 드로어. 스크롤 잠금·ESC·외부클릭·라우트 변경 시 닫힘,
  aria-modal/aria-expanded, prefers-reduced-motion 가드(motion-safe 트랜지션).
- 본문: 사이드바 폭만큼 패딩, max-width 재정렬(기존 페이지 무수정 전제 최소 조정).

## 범위
- In: Layout.tsx 재작성, App.tsx 라우트 정리, DisclosureHub 신규, package.json(lucide-react).
- Out(무수정): Disclosure/InsuranceCalculator/CoverageAnalysis/Home 내부, Footer, ui/*, index.css, PDF 템플릿.
- Home: 현재 Layout 내부(index) — **사이드바 셸 안에 유지**(Home 무수정 제약상 최저위험).
  로그인 전 전용 랜딩 셸 분리는 후속 판단(handoff 기록).

## ENV
- 신규 파일 우선, 마운트 git 금지, 검증 /tmp.

## 검증
- /tmp tsc 가능 범위 + 사이드바 쇼케이스(데스크탑 1280/모바일 390 드로어) 스크린샷.
- Codex(Windows): npm install(lucide-react) → tsc/lint/test/build → 전 라우트 스모크
  (/check redirect, 허브 모드 전환 시 입력 상태 보존, 드로어 동작) → 커밋·푸시.

## 산출 기록
- handoff: 현 라우트 구조, redirect 매핑표, 접힘 미채택 사유, 상태 보존 확인.
- Next: Codex → Human(구조 확인) → 047(페이지 내부 Mercury 적용).
