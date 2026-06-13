# BOHUMFIT-050 사이트 전역 로고 적용 — 브랜드 워드마크

## Owner
Cowork(Claude) — 구현 1차. 검증·커밋·푸시 + 구 파일 삭제는 Codex(Windows).

## 에셋 (기존, src/assets/brand/)
- `bohumfit_logo.svg` — 컬러(잉크 #000000 + 포인트 #5955DE), 밝은 배경용. viewBox 1099×263(≈4.18:1).
- `bohumfit_logo_white.svg` — 흰색(#FFFFFF) + 포인트 #5955DE, 어두운 배경용.
- `bohumfit_logo.png` — 폴백.
- color vs white 별도 파일 확인(cmp differ). `@` 별칭 미설정 → **상대경로 import**, `vite/client`가 *.svg를 string으로 타이핑.

## 적용 (로고 노출 지점만)
- 상단 네비(Layout): 좌측 텍스트 워드마크 → `bohumfit_logo.svg` `<img>`(높이 ~28px), 클릭 홈(/). 데스크탑·모바일 BrandLogo 공용.
- 로그인(Login): 상단 브랜드 영역 텍스트 → 컬러 로고 중앙 배치(적정 높이).
- 푸터(Footer): 배경 라이트(bg-canvas) → **컬러 버전**.
- 메인(Home): 미션 섹션(HomeMission) 상단에 컬러 로고 1회(레터헤드 느낌, 과용 금지·선택).
- 기존 텍스트/타일 로고 마크업 제거. alt="BOHUMFIT".

## 범위 밖 / 금지
- 파비콘: 가로 워드마크라 정사각 부적합 → **이번 미수정**(handoff에 정사각 미니마크 후속 기록).
- 045 토큰 포인트색 변경(#5B5BD6) — 범위 밖, handoff에 #5955DE 통일 제안만.
- 루트 untracked 구 파일('보험학 로고.png'/'보험학-로고.svg') — **Cowork 미접촉**, import 금지. 삭제는 Codex.
- 다른 페이지 본문·스타일·라우트 무수정.

## ENV
- 신규 에셋 참조, 마운트 git 금지, 검증 /tmp. 스크린샷 불가 시 SSR/마커 검증 + handoff ⚠.

## 검증
- /tmp tsc + 로고 적용부 SSR 마커(img + alt). Codex(Windows): tsc/lint/build + 네비/로그인/푸터/홈 육안.

## 산출 기록
- handoff: 적용 4지점, 파비콘 후속, 포인트색 통일 제안, 구 파일 삭제 Codex 위임. Next: Codex.
