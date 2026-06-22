# BOHUMFIT-099-icon-update
## 목표
보험핏 아이콘을 2단 스택(보험/FIT) 디자인으로 전체 교체
- 웹사이트 favicon, og-image, 헤더 로고, PWA 아이콘 전체
## 아이콘 스펙
- 배경: #15663D / 텍스트: #FFFFFF
- 상단: 보험 (Pretendard ExtraBold 800) / 하단: FIT (Pretendard Bold 700)
- 2단 스택, 양 끝선 폭 일치, 모서리 viewBox 기준 22.5% radius
## 작업 범위
1. brand/icon.svg — 마스터 512×512 (신규)
2. public/favicon.svg — 배포 favicon SVG (교체)
3. public/favicon.ico — 32×32 (가능 시 생성, 불가 시 handoff 기록)
4. public/og-image.svg — 1200×630 (교체)
5. public/apple-touch-icon(-180).png — 180×180 (가능 시 생성, 불가 시 기록)
6. public/site.webmanifest — PWA 아이콘 경로 확인
7. index.html — favicon/og/manifest 링크 확인·업데이트
8. src 헤더 로고 — 텍스트/SVG 인라인이면 현행 유지
## 비목표
- 색상 시스템 변경 / 핏히어·FC WORKS 아이콘 / 폰트 파일 설치(시스템 폰트 fallback)
## 완료 조건
- [ ] brand/icon.svg 생성 / public/favicon.svg·og-image.svg 교체
- [ ] index.html 링크 정상 / tsc·빌드 통과
## 비고(현황)
- index.html: /favicon.svg·/favicon.ico·/favicon-16/32.png·/apple-touch-icon-180.png·/og-image.svg·/site.webmanifest 링크 기존재(경로 변경 불필요). theme-color #15663D.
- site.webmanifest: /icon-192.png·/icon-512.png.
- src/components/Logo.tsx: 텍스트 워드마크 → 현행 유지.
- brand/의 fithere-logo-*는 핏히어 브랜드(비목표) — 미변경.
- 라스터(ico/png)는 한글 글리프 렌더 위해 한글 폰트(Pretendard/Noto CJK)+래스터라이저 필요 → 샌드박스 가용 여부에 따라 생성/보류, handoff 기록.
