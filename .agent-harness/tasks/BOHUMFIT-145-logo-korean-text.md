# BOHUMFIT-145 Logo.tsx 한글 텍스트만으로 단순화
## 배경
현재 Logo = SVG 심볼 + 영문 BOHUMFIT(투박). "보험핏" 한글 텍스트만 깔끔하게.
## 확정 스펙
- 메인 로고: "보험핏" 한글만, font-bold, 브랜드 그린(#15663D). 심볼·영문 제거.
- variant: default(흰 텍스트·다크배경) / light(그린·라이트배경, 기본) / symbol(SVG 심볼만 — PWA/파비콘용 유지).
- showText: true(보험핏 표시)/false(숨김). size: 텍스트 크기 비례(18→text-lg, 20→text-xl, 24+→text-2xl).
## 작업
- src/components/Logo.tsx 스펙대로 교체(심볼 제거, 보험핏 텍스트). 사용처(Layout/Footer/HomeMission/Login)는 144b에서 variant="light" 지정됨 → 그대로 유지(추가 변경 불필요).
## 수정 금지: PWA 아이콘(public/*.png)·분석 로직·backend.
## 완료: 헤더 "보험핏" 텍스트만, tsc/build. (커밋/푸시는 Codex — Cowork는 마운트 git 미실행)
