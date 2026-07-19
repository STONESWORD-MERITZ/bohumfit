# BOHUMFIT-227 — 미사용 xlsx 의존성 제거 (npm audit no-fix high 해소)

Owner flow: Claude Chat -> Claude Code (커밋 허용) | Current owner: Claude Code
Risk tier: 저위험 — Chat 명시 "Code 커밋 허용", Codex 생략 가능
Date: 2026-07-18

## 목적

226 위생 감사에서 확인된 src 사용 0건의 `xlsx` 패키지를 제거해
npm audit의 유일한 no-fix high 취약점(GHSA-4r6h-8v6p-xvw6 Prototype Pollution,
GHSA-5pgg-2g8v-p4x9 ReDoS)을 해소한다.

## 수정 범위

package.json, package-lock.json (npm uninstall에 의한 자동 변경만)

## 수정 금지

- 다른 의존성 버전 변경 0 (npm audit fix 실행 금지 — 별도 태스크)
- src/·backend/·supabase/·.env* 무접촉
- backend requirements의 openpyxl은 별개(Python) — 무접촉

## 단계별 지시

1. STEP 0 재실측: src/ 내 xlsx import/require 0건 확인. 1건이라도 나오면 중단·보고.
2. npm uninstall xlsx
3. git diff로 package.json = xlsx 1줄 제거뿐, lockfile = xlsx 트리 제거뿐인지 확인.
   다른 패키지 버전이 움직였다면 중단·복원·보고.
4. npm audit 재실행 → no-fix high 해소 확인(수치 기록)

## 검증 체크리스트 (2026-07-18 Claude Code 실행 결과)

- [x] STEP 0 재실측: src/ xlsx import/require **0건**
- [x] tsc app/node 통과
- [x] npm run lint 통과 / npm test **68 passed** / npm run build 통과(청크 342.66 kB — 기록만, 225 이상 신호 미해결)
- [x] backend pytest **618 passed, 8 skipped** 불변
- [x] git diff 범위 = package.json(xlsx 1줄 제거) + package-lock.json(xlsx+하위 9패키지 제거·후행 콤마 1줄) 뿐 — 다른 버전 이동 0
- [x] npm audit: **8건(high 6) → 7건(1 low, 1 moderate, 5 high)** — no-fix high(xlsx) 해소, 남은 7건 전부 `npm audit fix` 경로 존재

## Stage 목록

package.json, package-lock.json, tasks/BOHUMFIT-227-*.md, handoff.md, locks.md (.env* 제외)

## 커밋 메시지

chore(BOHUMFIT-227): 미사용 xlsx 의존성 제거 — npm audit no-fix high 해소
