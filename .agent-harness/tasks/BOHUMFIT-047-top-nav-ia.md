# BOHUMFIT-047 상단 가로 네비 + 메뉴 재편 — Mercury, 설계사 대면 운용 기준

## Owner
Cowork(Claude) — 구현 1차. 검증·커밋·푸시 Codex(Windows), 구조 확인 Human.

## 046 처리
- 046(좌측 사이드바)은 Cowork 구현분이 작업 트리에 존재(`Layout.tsx` 사이드바, `DisclosureHub.tsx`, `App.tsx` redirect, lucide-react). Codex 검증/커밋 기록은 locks/handoff에 없음.
- **047 결정**: 사이드바 Layout 을 **상단 가로 네비로 재작성(폐기)**. DisclosureHub·`/check` redirect·lucide-react 는 047 도 요구하는 통합 구조이므로 **유지·재사용**.

## 사용 맥락
- 모든 화면은 설계사가 노트북/태블릿으로 고객에게 보여주며 대면 진행 → 빠른 전환·시연 편의 우선. 고객 직접 조작 시나리오 고려 불필요.

## 메뉴 구성 (이 순서)
1. 왜 중요한가
2. 알릴의무 필터 ← 고객용/설계사용 통합(드롭다운으로 두 모드 바로가기)
3. 보장분석 (컨설팅 전·후)
4. 실손 계산
(우측 끝: 사용자 이메일·로그아웃)

## 상단 네비 — Mercury 문법
- sticky 상단 고정 바, 라이트 캔버스 + 하단 1px 헤어라인, 그림자 없음.
- 좌측 로고(잉크). 메뉴=텍스트 링크, 활성=페리윙클 텍스트+하단 2px 인디케이터, 호버=옅은 캔버스.
- '알릴의무 필터'=드롭다운(고객용/설계사용 바로 선택 — 대면 중 빠른 전환).
- 우측: 사용자 이메일 + 로그아웃(고스트). 데스크탑·태블릿 한 줄 유지.
- 좁은 모바일: 햄버거 → 드롭다운 메뉴(aria-expanded/role, ESC·외부클릭 닫기, prefers-reduced-motion 가드).
- 본문: 상단바 높이만큼 패딩, 콘텐츠 max-width 중앙 정렬.

## 알릴의무 통합 — 저위험 래퍼
- 현 구조: `/disclosure`=DisclosureHub(세그먼트 탭, 내부에서 `<Disclosure/>` 렌더), `/check`→`/disclosure?mode=customer` redirect. Disclosure 가 `?mode=` 라이브 해석.
- 상단 드롭다운에서 모드로 진입(`/disclosure?mode=agent|customer`)해도 페이지 안 세그먼트 탭으로 즉시 상호 전환(단일 라우트, 리마운트 없음 → 상태 보존).
- Disclosure.tsx 등 기존 페이지 **무수정**.

## 범위
- In: Layout.tsx 네비 재작성(상단), App.tsx 라우트 정리, DisclosureHub 재사용/소형 보완.
- Out(무수정): Disclosure/InsuranceCalculator/CoverageAnalysis/Home 내부, Footer, ui/*, index.css, PDF 템플릿.
- 046 사이드바 컴포넌트(aside·드로어)는 제거(상단 네비로 대체).

## ENV
- 신규 파일 우선, Layout 재작성 허용. 마운트 git 금지, 검증 /tmp.

## 검증
- /tmp tsc(실 의존성 체인) + 쇼케이스: 데스크탑/태블릿(한 줄 유지)/모바일 햄버거 + 드롭다운 열린 상태.
- Codex(Windows): npm install → tsc/lint/test/build → 라우트 스모크(드롭다운 모드 진입·세그먼트 탭 전환·/check redirect·모바일 메뉴 ARIA) → 커밋·푸시.

## 산출 기록
- handoff: 현 라우트 구조, 046 처리, redirect 매핑, 알릴의무 통합 방식. Next: Codex → Human → 페이지 내부 Mercury.
