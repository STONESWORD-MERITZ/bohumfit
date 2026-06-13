# BOHUMFIT-045 디자인 시스템 v2 — Mercury 스타일 전면 전환

## Owner
Cowork(Claude) — 구현 1차. 검증·커밋·푸시 Codex(Windows), 룩 확인 Human.

## 목표
044 네이비+골드 방향 폐기 → Mercury(mercury.com)식 라이트 프리미엄 핀테크 미니멀리즘으로
토큰 전면 재정의. **기능·로직·라우팅 변경 0. ui 8종 API(props) 불변 — 내부 스타일만 교체.**

## 디자인 언어 (Mercury 문법)
- 캔버스: 따뜻한 오프화이트(#FAFAF8). 섹션 구분은 배경 블록이 아닌 여백.
- 텍스트: 잉크 뉴트럴(#1A1A1E~#3A3A40). 보조 그레이도 대비 4.5:1 사수.
- 포인트 1색: 페리윙클 인디고-바이올렛(#5B5BD6) — CTA·활성·링크만. **골드 전면 제거.**
- 보더: 헤어라인 1px(#E8E8E4)가 구조의 주인공. 그림자는 호버/오버레이만 옅게.
  카드 = 화이트 + 1px 보더 + 큰 라운드(16px).
- 타이포: Pretendard(jsdelivr CDN + 시스템 폴백), tabular-nums, 헤드라인 에디토리얼(자간 -2~-3%),
  본문 15px↑ 유지. 위계는 굵기·크기로만.
- 표: 네이비 헤더 제거 → 캔버스 헤더 + 그레이 캡션, 헤어라인 행 구분, 줄무늬 제거, 호버만 하이라이트.
- 버튼: primary=잉크 솔리드(라운드 10px), secondary=고스트 1px, danger=시맨틱 레드, 로딩 유지.
- Badge/Callout: 파스텔 배경 + 진한 동계열 텍스트. 면책 Callout = 옅은 그레이 박스.
- '비어 보일 만큼 깔끔'이 정답 — 장식 금지.

## 히어로 scroll-scrub (Home 1곳만)
- 스크롤 진행도 비례 scale(1→0.94)+opacity(1→0), 다음 섹션이 덮음(sticky 패턴).
- transform/opacity만. CSS scroll-driven(animation-timeline: scroll()) 우선,
  미지원 브라우저는 효과 생략(정적 — 기능 영향 0). prefers-reduced-motion: 전체 비활성.
- 모바일(≤768px): scale 0.97 약화. 섹션 반복 금지.

## 범위
- In: index.css(@theme v2·BOM 보존), ui 8종 내부, Layout/네비, Footer, Home(+스크럽), Login,
  vercel.json CSP(style/font-src에 jsdelivr — Pretendard 로드 필수, 사전 점검에서 차단 확인).
- Out(무수정): Disclosure/InsuranceCalculator/CoverageAnalysis(다음 태스크),
  backend/templates 리포트 PDF(네이비+골드 = 승인 산출물 유지).
- 레거시 인디고 커스텀 토큰: src 참조 0 확인 → 제거(분석 3페이지는 표준 팔레트/임의 hex 사용, 무영향).

## ENV
- 신규/소형 편집 우선, 마운트 git 금지, 검증 /tmp, index.css BOM 보존.

## 검증
- /tmp: tsc(strict+jsx) + Tailwind v4 실컴파일 쇼케이스(Login/Home 히어로/Layout/8종) Chromium 스크린샷.
- navy/gold/레거시 토큰 잔존 grep 0(범위 밖 파일 기준 — 사전 점검에서 0 확인됨).
- Codex(Windows): tsc/lint/test/build + 전 라우트 스모크(분석 3페이지 시각 회귀 없음) + 배포 후 Pretendard 로드(CSP) 확인.

## 산출 기록
- handoff: 토큰 v2 목록, 044 대비 변경 요약, **컴포넌트 API 불변 확인** 명시.
- Next: Codex(검증·커밋·푸시) → Human 룩 확인 → 페이지 적용 태스크.
