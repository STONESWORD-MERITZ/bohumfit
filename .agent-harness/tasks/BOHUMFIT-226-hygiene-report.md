# BOHUMFIT-226-C — 레포 위생 감사 리포트 (조사 전용 · 코드 변경 0)

Date: 2026-07-17 | 작성: Claude Code | 수정·설치·업그레이드 실행: 0

## ① SURIT 잔재

- 프로덕션 코드·설정(src/·backend/·vercel.json·.env.example): **0건** ✓
- 잔존 2파일(모두 이력 서술 — 정리 불필요 판정):
  - `AGENTS.md` — 커밋 전 검증 계약의 "SURIT 0건" grep 규칙 문구 자체(계약 정의)
  - `PROGRESS.md` — 031 리네임 이력 서술(165에서 아카이브 유지 결정 기존재)
  - `.agent-harness/handoff.md` — 과거 165 기록(무수정 원칙)

## ② TODO/FIXME/HACK 전수

| 파일:라인 | 표기 | 요지 |
| --- | --- | --- |
| `backend/main.py:980` | TODO | 통신사 본인인증(PASS/OTP) 라이브 연동 후 실제 검증(토큰/CI 대조) 추가 — 현재 스텁. 087/206 설계와 연결됨 |

- src/: **0건** ✓. backend/ 위 1건뿐.

## ③ 의존성 취약점 (리포트만 — 설치·업그레이드 실행 0)

### npm audit — 8 vulnerabilities (1 low, 1 moderate, 6 high)

| 패키지 | 심각도 | 내용 | 수정 경로 |
| --- | --- | --- | --- |
| `xlsx` (*) | **high** | Prototype Pollution + ReDoS (GHSA-4r6h-8v6p-xvw6, GHSA-5pgg-2g8v-p4x9) | **fix 없음** — 단, 아래 ④: src 사용 0건이라 **제거 가능** |
| `react-router` 7.0.0–7.15.0 (+react-router-dom) | high | __manifest DoS(GHSA-8x6r-g9mw-2r78), PUT/PATCH/DELETE CSRF(GHSA-84g9-w2xq-vcv6) | `npm audit fix` 가능 |
| `undici` 7.0.0–7.27.2 | high | TLS 검증 우회·헤더 주입 등 7건 | `npm audit fix` 가능 |
| `vite` 8.0.0–8.0.15 | high | launch-editor NTLMv2 해시 노출(Windows)·fs.deny 우회(Windows) — dev 서버 한정 | `npm audit fix` 가능 |
| `brace-expansion` 5.0.2–5.0.5 | moderate | DoS 보호 우회 | `npm audit fix` 가능 |
| `@babel/core` ≤7.29.0 | low | sourceMappingURL 임의 파일 읽기(빌드 도구 한정) | `npm audit fix` 가능 |

### pip (backend)

- `pip-audit` 미설치 — "설치 실행 금지" 지시로 이번 세션에서 실행 불가. **미확인 상태**로 기록.
- 후속 태스크에서 `pip-audit`(또는 GitHub Dependabot/`pip install pip-audit` 1회 승인)로 확인 필요.

## ④ 미사용 의존성 후보

| 패키지 | 근거 | 비고 |
| --- | --- | --- |
| `xlsx` (dependencies) | src/ 전수 grep import **0건** | ★③의 유일한 no-fix high 취약점 — 제거 시 취약점도 함께 해소. 과거 CoverageCompare(엑셀 도구, 180에서 라우트 재편) 잔재로 추정 |

- `lucide-react` 사용 확인(Layout·CoverageRemodel·Dashboard·Disclosure·Home 등) — 유지.
- devDependencies는 도구 체인이라 판단 보류(vitest/eslint/tailwind 등 모두 사용 확인).

## ⑤ src/ 미참조 파일 후보

| 파일 | 근거 | 비고 |
| --- | --- | --- |
| `src/pages/BeforeAfter.tsx` | 라우트 165에서 제거, src/ 내 import 0건(index.css 주석 언급뿐) | 148 감사에서 고아 판정 기존재. emerald-* 잔재도 이 파일(226-A 기록만 항목) |
| `src/pages/HomeMission.tsx` | src/ 내 TSX import 0건(index.css 언급뿐) | 173~176 히어로 재편 과정에서 미사용화 추정 — 삭제 전 Human 확인 필요 |

- `src/pages/why/whyContent.ts`는 WhyDisclosure.tsx가 사용 — 참조 정상.
- `src/components/Toast.tsx`는 ToastContext.tsx가 상대경로로 사용 — 참조 정상.

## ⑥ 후속 태스크 제안 (위험도 표기)

1. **[저위험] xlsx 의존성 제거** — package.json에서 제거 + lock 재생성. no-fix high 취약점 해소. 검증: build·test 전체. (①순위 권장)
2. **[저위험] npm audit fix 일괄 적용** — react-router/undici/vite/brace-expansion/@babel. semver 범위 내 패치. 검증: tsc·lint·test 50+·build. ※vite는 225 빌드 이상 신호 해결 후 진행 권장(기준선 혼동 방지).
3. **[저위험] pip-audit 1회 설치·실행** — backend 취약점 미확인 해소. Human 설치 승인 1건.
4. **[저위험·Human 결정] 고아 파일 삭제** — BeforeAfter.tsx·HomeMission.tsx `git rm`. 삭제 전 Human 확인(과거 148 원칙).
5. **[중위험] backend main.py:980 PASS/OTP 스텁 해소** — 087/206 설계 후속. 외부 연동·비용이라 Chat 발번 + Human 결정 필요.
