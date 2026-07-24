# BOHUMFIT-241 — vite 보안 업그레이드 (npm audit 잔여 1건 해소)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Codex (★Chat 결정 반영 — 지연(수용), 1안 채택. 문서 커밋 대기)
Risk tier: 중위험 — 풀 하네스. git 쓰기 금지(커밋 Codex).
Date: 2026-07-22

## 결론 요약 (★지연(수용) — 1안 채택, 롤백 유지)

vite 업그레이드(8.1.5·8.0.16 모두 audit 0) 자체는 성공하나, **바뀐 rolldown 네이티브 바인딩이
이 Windows(win32-x64) 환경에서 로드 실패**(`ERR_DLOPEN_FAILED`, npm optionalDependencies 버그
npm/cli#4828)로 **build·test 전부 깨짐**. 최소 패치(8.0.16·rolldown 1.0.3)와 클린 `npm ci`로도 재현
→ **버전 무관·rolldown 변경 자체가 트리거**. 에러가 요구하는 해법(package-lock.json + node_modules
전체 삭제 후 재생성)은 이번 **"vite 계열 한정" 스코프를 위반**하고 "무리한 진행 금지" 가드에 걸린다
→ **lockfile 롤백, 그린 복구 확인. 즉시 해소를 차단 상태로 두지 않고 1안(지연·저위험 수용)을 채택한다.**

## Chat 결정 (2026-07-24 — 1안 채택)

- 잔여 vite 취약점은 **Windows 개발 서버에만 해당**하고 프로덕션 번들에는 포함되지 않아 사용자 노출은 **0**이다.
- 프로덕션 빌드·배포는 **Vercel Linux**에서 수행되므로 이번 `rolldown-binding.win32-x64-msvc` 배선 문제는 발생하지 않는다.
- 원인은 vite 특정 버전 결함이 아니라 npm의 optionalDependencies 배선 문제(`npm/cli#4828`)다. **8.0.16과 8.1.5가 모두 같은 `ERR_DLOPEN_FAILED`**로 실패해 버전 핀만으로는 해결되지 않음을 재확인했다.
- 2안(전체 클린 재생성)은 **조건부 승인**한다. 지금 단독 수행하지 않고 차기 대규모 의존성 작업—React/Tailwind 메이저 업그레이드, Node 교체, 신규 개발 환경 세팅—중 하나와 묶어 lockfile 전면 검증 비용을 함께 부담한다.
- 따라서 현재 상태는 **BLOCKED가 아니라 지연(수용)**이다. vite 8.0.10과 잔여 audit 1건을 명시적으로 수용하고 프로덕션 운영을 계속한다.

## S0 — 실측

- 취약점: `vite [high] 8.0.0–8.0.15`, direct, fix available(non-major).
- vite 계열 현재: vite@8.0.10 / @vitejs/plugin-react@6.0.1 / @tailwindcss/vite@4.2.4 / vitest@4.1.6.
- npm audit 총계: high 1(vite뿐). 취약점 상세: launch-editor NTLMv2 해시 노출(GHSA-v6wh-96g9-6wx3),
  `server.fs.deny` 우회(GHSA-fx2h-pf6j-xcff) — **둘 다 dev 서버 + Windows 로컬 한정. 프로덕션
  빌드 산출물(Vercel/Linux)에는 무영향**(실사용 리스크 낮음 — 지연 판단의 근거).

## 시도·결과

### 시도 1 — `npm update vite` → 8.1.5 (rolldown ~1.1.5)
1. vite 8.0.10 → **8.1.5**(8.x 내·non-major). package.json 무변경(^8.0.10 유지). 이동 = vite + 전이
   번들러 체인(rolldown·@emnapi·postcss·nanoid·picomatch·tinyglobby). **앱 런타임 의존성
   (react·supabase·sentry·react-router·lucide) 이동 0**, 명명 vite계열 플러그인 버전 이동 0.
2. `npm audit`: **0 vulnerabilities** 달성.
3. ★검증 실패: `npm test`·`npm run build` 모두 `ERR_DLOPEN_FAILED` — rolldown이
   `rolldown-binding.win32-x64-msvc.node`를 못 찾음(파일은 디스크에 존재하나 loader 경로 미해결).
4. `npm install`·클린 `npm ci`(lockfile 미변경) 후에도 동일 실패 → 증분 버그 아님, **lockfile 자체가 불가**.

### 시도 2 — `npm install vite@8.0.16` (최소 패치, rolldown 1.0.3) ★재발송 시 추가 조사
- 배경: 취약 범위 8.0.0–8.0.15 → **8.0.16 패치 존재**. 8.1.x(rolldown 1.1.x) 대신 현재 작동하는
  8.0.10의 rolldown 1.0.0-rc.17과 같은 **1.0.x 라인(8.0.16=rolldown 1.0.3)**으로 최소 이동해 바인딩
  버그 회피를 시도(package.json ^8.0.16, semver 호환).
- 결과: `npm audit` **0** 달성했으나 **build·test 동일하게 `ERR_DLOPEN_FAILED`(win32-x64 바인딩 미해결)**.
- ★결론 강화: 버그는 8.1.x/rolldown 1.1.x 특정이 아니라 **rolldown 버전이 어떤 값으로든 바뀌면
  증분 설치가 win32-x64 네이티브 바인딩을 못 잡는 npm optionalDependencies 버그(npm/cli#4828)**다.
  현재 작동하는 8.0.10(rolldown 1.0.0-rc.17)은 과거 클린 설치로 바인딩이 올바로 배선된 상태이고,
  **어떤 rolldown 변경도 이 환경에선 클린 재생성 없이 배선 불가**.

### 롤백
- package.json·package-lock.json을 241 이전(vite 8.0.10)으로 복원 → `npm ci` → **build 343.22 kB·
  npm test 79 passed 그린 복구**. package diff 0. (시도 1·2 모두 롤백)

## 검증 체크리스트 (1차 — Code, 2026-07-22)

- [x] S0 audit·버전 실측 기록
- [x] 업그레이드 시 audit 0 확인 / ★build·test는 rolldown 바인딩 오류로 실패(클린 ci 포함)
- [x] 롤백 후 그린 복구: `npm run build` 343.22 kB(240 기준 동일), `npm test` **79 passed**
- [x] backend 무접촉(pytest 미실행 사유: package 변경 롤백으로 diff 0·백엔드 무관)
- [x] 최종 워킹트리 = harness 문서만(handoff·locks·tasks/241). **package.json·lock diff 0**(롤백)
- [x] vite.config·tsconfig 무접촉

## 결정안 이력 (Chat — 1안 채택)

1. **[채택·저위험 수용] 지연**: 잔여 vite 취약점은 dev 서버+Windows 로컬 한정·프로덕션 무영향이라
   사용자 노출 0. 현재 버전을 유지하고 차기 대규모 의존성 작업 시 함께 해소한다.
2. **[조건부 승인·즉시 미실행]** 전체 클린 재생성: `rm -rf node_modules package-lock.json && npm i`
   후 vite 상향 — lockfile 전면 재생성으로 다수 전이 의존성 이동 가능(별도 검증·회귀 부담).
   React/Tailwind 메이저·Node 교체·신규 개발 환경 세팅 중 하나가 발번될 때 같은 태스크에 편승한다.
3. **[대안]** rolldown 바인딩 버그가 해결된 특정 vite 8.x 패치 버전으로 핀 고정(버전 확인 후).
   ※단, 8.0.16(rolldown 1.0.3)도 실패했으므로 특정 버전 핀만으로는 부족할 수 있음 — 문제는
   rolldown 변경 시 win32-x64 바인딩 배선(npm 버그)이라 클린 재생성이 사실상 필수(2안과 결합).

## Stage 목록 (Codex용)

**코드/패키지 변경 없음**(롤백). `tasks/BOHUMFIT-241-*.md`, `handoff.md`, `locks.md`만 — 지연 수용 결정 기록.

## 커밋 메시지 (Codex용)

docs(BOHUMFIT-241): vite 업그레이드 지연 결정 — npm optionalDependencies 배선 이슈
