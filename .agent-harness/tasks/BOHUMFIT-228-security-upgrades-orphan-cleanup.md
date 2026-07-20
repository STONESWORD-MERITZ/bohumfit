# BOHUMFIT-228 — vite 제외 보안 업그레이드 + 고아 파일 정리 + 백엔드 취약점 리포트

Owner flow: Claude Chat -> Claude Code -> Codex
Current owner: Codex (A~C 완료 — 2차 검증·커밋 대기)
Risk tier: 중위험 — 풀 하네스. git 쓰기(add/commit/push) 전면 금지, 커밋은 Codex 담당.
Date: 2026-07-20

## 목적

(A) npm audit 잔여 7건 중 vite 계열을 제외한 semver-호환 업그레이드로 취약점 축소
(B) 226 위생 감사의 고아 파일 후보 2건(BeforeAfter.tsx, HomeMission.tsx) 실측 후 제거
(C) pip-audit로 backend 의존성 취약점 리포트 산출 (조사·문서 전용, 코드 0)

## 수정 범위

- A: package.json, package-lock.json (대상 패키지 한정)
- B: src/ 내 고아 확정 파일 삭제만
- C: .agent-harness/tasks/BOHUMFIT-228-pip-audit-report.md 신규만
- 공통: harness 문서(tasks/228, handoff, locks)

## 수정 금지

- ★vite 및 vite 관련 플러그인 버전 이동 금지 — 이동 발견 시 되돌리고 사유 기록(225 빌드 이상 신호 미해결)
- npm audit fix --force 금지 (semver-호환 경로만)
- src/·backend/ 코드 수정 금지 (B의 파일 삭제 제외)
- backend/pipeline/, backend/coverage/, supabase/, .env*, 인증 코어 무접촉
- backend 의존성 설치·업그레이드 금지 (pip-audit 도구 자체 설치만 허용)
- 기존 테스트 수정 금지

## 파트 A — STEP 0 실측 (npm audit --json, 2026-07-20) 및 업그레이드 결과

시작 7건(1 low, 1 moderate, 5 high) — 전부 semver-호환 fix 존재:

| 패키지 | 심각도 | direct | 조치 | 결과 버전 |
| --- | --- | --- | --- | --- |
| react-router / react-router-dom | high | dom=direct | `npm update`(spec ^7.14.2 유지, 메이저 점프 없음) | 7.14.2 → **7.18.1** |
| undici | high | 전이 | `npm update` | 7.x → **7.28.0** |
| ws | high | 전이 | `npm update` | 8.x → **8.21.1** |
| brace-expansion | moderate | 전이 | `npm update` | → **5.0.7** |
| @babel/core | low | 전이 | `npm update` (@babel/* 헬퍼·browserslist 데이터 패키지 동반 이동 — 동일 트리) | → **7.29.7** |
| vite | high | direct | **보류(지시)** — 225 빌드 이상 신호 미해결 | 8.0.10 고정 |

- 방식: 일괄 audit fix 대신 대상 지정 개별 실행. 전이 의존성은 `npm install`(package.json 승격 부작용) 대신
  `npm update <pkg>`(lockfile 범위 내 이동)로 통제 — **package.json diff 0**(lockfile-only).
- 각 단계 후 lockfile 이동 목록 실측: 대상 트리 밖 이동 0, ★vite·@vitejs/plugin-react·@tailwindcss/vite·vitest 이동 **0**.
- 완료 후 npm audit: **7건 → 1건**(vite high 1건만 잔존 — 명시적 보류, dev 서버 한정 취약점).

## 파트 B — 고아 파일 실측 및 삭제

- `BeforeAfter.tsx`: src/·index.html·vercel.json 전수 grep(문자열 경로·동적 import 포함) **참조 0** → 삭제 확정.
- `HomeMission.tsx`: 코드 참조 0(유일 언급 = index.css `--text-fluid-title` 토큰 주석) → 삭제 확정.
  ※기록만: 삭제로 `text-fluid-title` 토큰(index.css)이 미사용화 — 토큰·주석 정리는 범위 밖, 후속 저위험 태스크 후보.
- 삭제 직후 tsc app/node·build 통과(파손 0). 삭제는 파일시스템 rm — git 쓰기 금지 준수, stage는 Codex.

## 검증 체크리스트 (1차 — Code 직접 실행, 2026-07-20 결과)

- [x] tsc app/node, npm run lint 통과
- [x] npm test — **68 passed** 전부 유지, 2연속 확인 (라우트 스모크 18건 = react-router 7.18.1 회귀망 통과)
- [x] npm run build 통과 — 청크 **343.22 kB**(기록만 — react-router 업그레이드분 +0.56 kB, 기준선 등록 금지)
- [x] backend pytest — **618 passed, 8 skipped** 불변
- [x] git diff에서 vite 계열 버전 이동 **0** 확인
- [x] diff 범위 = lockfile + 삭제 2파일 + harness 문서만 (★package.json diff 0 — npm update가 spec 유지)

## Stage 목록 (Codex용 — Code는 실행 금지)

package.json, package-lock.json, 삭제 파일(git rm 반영), tasks/BOHUMFIT-228-*.md 2개, handoff.md, locks.md (.env* 제외)

## 커밋 메시지 (Codex용)

chore(BOHUMFIT-228): vite 제외 보안 업그레이드 + 고아 컴포넌트 제거 + 백엔드 취약점 리포트
