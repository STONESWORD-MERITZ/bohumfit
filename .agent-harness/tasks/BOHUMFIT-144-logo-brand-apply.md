# BOHUMFIT-144 로고 브랜드 전체 적용
## 브랜드: BOHUMFIT/보험핏, 컬러 #15663D(딥그린)·다크 #0E4A2C, 심볼 F·I·T 모노그램(M13 13 H35 M24 13 V35 M24 24 H33, viewBox 0 0 48 48, sw5, round).
## 144a: 파비콘/앱아이콘/OG 교체
- public/favicon.svg(32, 배경 #15663D rx4, 흰 심볼), public/og-image.svg(1200×630, #0E4A2C, 심볼+워드마크), public/icons.svg(symbol fit-favicon/fit-icon).
- PNG 생성: favicon-16/32, apple-touch-icon-180, icon-192/512 (rsvg-convert 또는 cairosvg).
- site.webmanifest 갱신(name/short_name/description/theme/background/icons).
## 144b: Logo.tsx
- 심볼(SVG)+텍스트 조합. props: size?(24)·variant?("default"흰/"light"그린/"symbol"심볼만)·showText?(true)·className. Layout 호출 variant 조정(다크→default, 라이트→light).
## 수정 금지: 분석 로직·backend·index.html 파비콘 경로(파일명 유지 교체).
## 완료: 144a 자산+webmanifest, 144b Logo variant/showText, tsc/build, handoff.
