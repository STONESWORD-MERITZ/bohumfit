# BOHUMFIT-146 로고 영한 병기 (BohumFit 보험핏)
## 확정 스펙
"FitHere 핏히어" 스타일 — 영어(카멜케이스) bold + 한국어 muted 작게 병기: `BohumFit 보험핏`.
- variant light(라이트): 영 font-bold #15663D + 한 font-medium #64748B text-sm ml-1.5.
- variant default(다크): 영 bold white + 한 font-medium rgba(255,255,255,0.55) text-sm ml-1.5.
- variant symbol: 기존 SVG 심볼(변경 없음).
- size: >=24 → 영 text-2xl/한 text-lg / >=20 → 영 text-xl/한 text-base / 기본 → 영 text-lg/한 text-sm.
## 작업: src/components/Logo.tsx만. 사용처(Layout/Footer/HomeMission/Login)는 variant="light" 그대로.
## 완료: 헤더 "BohumFit 보험핏" 병기, tsc/build. (커밋/푸시는 Codex — Cowork 마운트 git 미실행)
