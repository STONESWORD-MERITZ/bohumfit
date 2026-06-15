# BOHUMFIT-051 텍스트 로고 락업 + 파비콘 그린 (050 위에서)

## Owner
Cowork(Claude) — 구현. 검증·커밋은 Codex(Windows). 색·로고 표시 외 변경 금지(기능·구조·카피·산식·라우팅 불변).

## A. 텍스트 로고 전환
- 현재 네비(Layout)·로그인(Login)·푸터(Footer)·미션(HomeMission) 4곳에 `bohumfit_logo.svg`(워드마크 이미지) 사용.
- 텍스트 락업 "BOHUMFIT 보험핏"으로 교체(핏히어 "FitHere 핏히어" 결): 영문 메인(굵게·잉크) + 한글 보조(작게·muted). 포인트는 마침표(.)만 그린(accent-600 = #15663D, 과하지 않게).
- 신규 `src/components/BrandWordmark.tsx`(재사용, size sm/md/lg) → 4곳 적용, 사이트 폰트(Pretendard) 그대로(웹폰트 추가 금지).
- 접근성: 네비 Link `aria-label="보험핏 홈"`·홈(/) 이동 유지, Login `<h1>` 의미 유지(락업 텍스트가 접근명 제공).
- `bohumfit_logo.svg` import 제거. **에셋 파일은 삭제하지 말고 미사용 보존**(정식 로고 재제작 예정).

## B. 파비콘·메타 그린
- 파비콘: `index.html <link rel="icon" type="image/svg+xml" href="/favicon.svg">` → `public/favicon.svg`(SVG·색 변경 가능).
  · 보라 번개 hex `#7e14ff`/`#863bff`/`#ede6ff` → 그린(#15663D/#2E8056/#E3F0E8). 블루 액센트 `#47bfff`는 보라 아님 → 유지(handoff 기록).
- `index.html` theme-color `#4F46E5`(구 인디고) → `#15663D`.
- og:image: `index.html`은 `/og-image.png` 참조이나 실제 파일은 `public/og-image.svg`(불일치, 기존 이슈). og-image.svg `#4F46E5` → `#15663D`(트리비얼). png/svg 불일치는 handoff 기록(범위 밖).

## 제약/ENV
- 색·로고 표시 외 변경 금지. 그린은 049 토큰 재사용. Windows 원본 무결성 기준, 마운트 git 금지, 검증 /tmp.

## 자체검증
- /tmp tsc(BrandWordmark + 의존) + 4곳 텍스트 락업 마커 + 파비콘/메타 보라 잔재 grep 0(로고 워드마크 에셋·#47bfff 제외) + 그린 대비.

## 산출
- handoff: 락업 형식·적용 4곳·파비콘 형식과 처리·미사용 에셋 보존·메타 잔재. Next: Codex 검증·커밋·푸시 → Human 육안(탭 파비콘).
