# BOHUMFIT-166 — FIT 브랜드 v1.0 리브랜딩 파운데이션 + 인증/구독/법무 토큰·접근성

## 배경
FIT COMPANY 브랜드 가이드 v1.0 확정. F·I·T 모노그램(#15663D) → ㅍ 심볼 + 에메랄드 파인(#084734) 전면 교체.
148 감사의 149(토큰 통일)·151(접근성)을 신규 브랜드 기준으로 통합.

## 브랜드 스펙(유일 진실)
- 에메랄드 파인 #084734(메인) / 라임 글로우 #CEF17B(면·배지 전용, 흰 위 텍스트·선 금지) / 그린 티 #CDEDB3(배경 면 전용, 텍스트·선 금지) / 짙은 잉크 #0A0A0A(고유명사·헤드라인) / 본문 그레이 #1E293B / 흰 #FFFFFF(에메랄드 위).
- WCAG AA: 흰/에메랄드 10.7:1, 라임/에메랄드 8.4:1, 에메랄드/그린티 8.3:1, 잉크/라임 15.5:1, 본문/흰 14.6:1. 금지: 라임·그린티/흰(1.3:1), 라임 위 흰 텍스트.
- ㅍ 심볼: 윗바+두 기둥+아랫바, 세로획15/가로획13, 라운드3.5, viewBox "0 0 82 66". 앱아이콘=에메랄드 타일+흰 ㅍ.
- 타이포: Pretendard(기존 사용중 유지). 디스플레이/헤드라인800·서브700·본문500·캡션600, 본문 행간1.7.
- 버튼: 프라이머리(에메랄드 면+흰) / 세컨더리(에메랄드 아웃라인+에메랄드) / 라임 CTA(라임 면+에메랄드, 화면당 1회·다크 위 전용).

## 토큰 방식(확인됨)
Tailwind v4 `@theme`(src/index.css). config 파일 없음. accent 스케일 값 교체 → 토큰 사용 페이지 자동 반영.

## 수정 금지
- backend/ 전체 / Disclosure·InsuranceCalculator·CoverageAnalysis 본문(167 별도, 단 공용 토큰 자연반영 허용) / 고지의무 로직.

## Part A 토큰 교체
- index.css @theme: accent 스케일 → 에메랄드(accent-600=#084734), primary/primary-strong/primary-soft 에메랄드, --color-lime #CEF17B·--color-greentea #CDEDB3 신설, ink-900 → #0A0A0A(헤드라인). text=#1E293B·text-strong=#0A0A0A 유지.
- #15663D·#0F4E2F·#0E4A2C 하드코딩 grep → 토큰(accent-*) 교체.

## Part B 로고/자산
- Logo.tsx symbol → ㅍ 브릿지 SVG. 텍스트 "BohumFit 보험핏" 병기 유지, 컬러 토큰(light=에메랄드/default=흰). variant 3종·aria 유지.
- public 자산 Pillow 재생성(favicon svg/16/32/ico, apple-180, icon-192/512): 에메랄드 타일+흰 ㅍ. og-image.svg 1200×630. site.webmanifest theme_color #084734. index.html theme-color.

## Part C 인증/구독/법무 토큰(구 149)
Login·Signup·PhoneVerify·Subscription·PrivacyPolicy·TermsOfService·NotFound·Footer·Layout — raw gray→토큰, 버튼 3종 정리, Signup 인라인 로고→Logo 컴포넌트.

## Part D 접근성(구 151, Part C 한정)
저대비→AA 토큰, 아이콘버튼 aria-label, placeholder-only→label/aria, img alt, focus-visible 에메랄드. 금지조합(흰 위 라임/그린티 텍스트, 라임 위 흰) 0건.

## 검증(샌드박스)
- repo #15663D·#0F4E2F·#0E4A2C grep 0 / 라임·그린티 텍스트색 0 / Part C raw gray 0(잔여 사유) / Logo variant 3종 / public 자산 무결성.
- tsc/build/pytest = Codex/Windows.

## 커밋(Codex)
feat(BOHUMFIT-166): FIT 브랜드 v1.0 리브랜딩 (ㅍ 심볼·에메랄드 파인) + 인증/구독/법무 토큰·접근성
