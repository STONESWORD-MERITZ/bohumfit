# BOHUMFIT-264 — PWA 셸 구축 (manifest·SW·설치·오프라인 폴백)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Codex (2차 검증·커밋)
Risk tier: 중위험 — 풀 하네스. git 쓰기 금지(커밋 Codex).
Date: 2026-07-31 · 기준 HEAD `6e87cc5`(263)

## 배경
263 실측: 서비스워커·오프라인·설치 프롬프트 미구현. 앱아이콘·파비콘은 브랜드 규격 일치(자산 준비됨).
모바일 디자인 개편(265~)과 독립적인 인프라 계층이라 선행 구축.

## ★선행 확인 — 263 커밋 미푸시
- `6e87cc5`(263)는 **로컬에만 있고 `origin/main`은 `8325131`(262)** — `main...origin/main [ahead 1]`.
- 이번 264 작업분은 그 위에 쌓였으므로 **Codex가 263 → 264 순서로 push**해야 한다(인계 사항).

## 구현

### 1. manifest (`public/site.webmanifest` — 파일명·`index.html:10` 링크 유지)
- 기존 필드(name/short_name/start_url/display/theme·background #084734/icons 192·512) 유지 +
  설치 요건 보강: `id`·`scope`·`lang`·`dir`·`orientation`·`categories`.
- 아이콘을 **`any`와 `maskable`로 분리 선언**(기존은 `"any maskable"` 한 항목). 안드로이드
  마스킹 크롭 시에도 `any` 원본이 남아 홈 화면·스플래시 품질이 유지된다.
- 자산은 **기존 브랜드 파일 재사용**(263 실측: `icon-192` 흰 타일+에메랄드 ㅍ,
  `favicon-32` 에메랄드 타일+흰 ㅍ) — 새로 만들지 않았다.

### 2. 서비스워커 (`public/sw.js` — ★수동 작성)
- **`vite-plugin-pwa` 미사용**: 플러그인이 vite 계열 버전 이동을 요구할 수 있고 241에서
  rolldown 바인딩 문제로 로컬 빌드가 깨진 전례가 있어 **버전 고정이 계약**이다. 표준 SW API만
  사용하고 `public/`에 두어 **빌드 파이프라인 무접촉**(빌드 시 그대로 복사됨 — 아래 검증).
- 전략: 내비게이션 = **네트워크 우선 → 캐시 → `/offline.html`**, 정적 자산 =
  **stale-while-revalidate**. 그 외 요청은 SW가 아예 손대지 않는다(원래 동작 유지).
- **버전 관리**: `CACHE_VERSION = "bohumfit-shell-v1"` — `activate`에서 다른 버전 캐시를 전부
  삭제해 stale SW를 방지한다. `SKIP_WAITING` 메시지 훅도 준비(앱이 동의를 받은 뒤 사용).
- ★**PII 캐시 금지**(264 범위 계약): `isCacheableRequest()` 단일 판정에서
  `GET`이 아니거나 · 교차 출처거나 · `/api/`·`/coverage/`·`/analyze`·`/auth/`·`/rest/v1/`
  경로거나 · `.xlsx|.xls|.pdf|.csv`면 **전부 제외**. 응답도 `status 200 && type basic`만 저장.
- **265 훅**: 분석 결과 캐시(A안 24h 만료·로그아웃 삭제)는 **이 함수 하나만 넓히면** 되도록
  정책을 한 곳에 모았다. 264에서는 실제로 캐시하지 않는다(테스트로 고정).

### 3. 설치 프롬프트 (`src/lib/pwa.ts` · `src/components/InstallPrompt.tsx`)
- `beforeinstallprompt` 캡처 → 브라우저 기본 배너를 막고 **우리 시점에 안내 배너** 노출.
- **중복 노출 방지**: 설치됨(`display-mode: standalone` 또는 iOS `navigator.standalone`)이거나
  최근 닫음이면 렌더 자체를 하지 않는다. 닫으면 `localStorage`에 **30일** 기억.
- **iOS 대체**: `beforeinstallprompt` 미지원이라 "공유 → 홈 화면에 추가" 안내 문구로 대체
  (설치 버튼 없이 문구만).
- 등록은 `registerServiceWorker()`가 **`import.meta.env.PROD`에서만** 수행(개발 HMR 간섭 방지),
  실패해도 조용히 무시해 앱 동작을 막지 않는다.
- ★기존 화면 무간섭: 배너는 `main.tsx`에서 `<App/>` 형제로 `fixed` 배치 — **기존 레이아웃·
  라우팅·화면 컴포넌트는 한 줄도 바꾸지 않았다**.

### 4. 오프라인 폴백 (`public/offline.html`)
- 외부 자산 의존 0(네트워크 없을 때 뜨는 화면). 브랜드 마크(에메랄드 타일 + ㅍ)·안내 문구·
  **재시도 버튼**, `online` 이벤트에 자동 새로고침. 안전영역(`env(safe-area-inset-*)`)과
  다크 모드 대응 포함.

### 5. Vite 구성
- **변경 0** — 플러그인·버전 이동 없음(위 2번 사유). `vite.config.ts` diff 0.

## 검증 (1차 — 완료 · 2026-07-31)
- [x] backend pytest **792 passed, 8 skipped**(불변) · **backend diff 0**
- [x] npm test **109 passed**(99 + 신규 10) · tsc app/node · lint 클린
- [x] ★**라우트 스모크 18건 통과**(SW·배너 도입이 라우팅을 깨지 않음 — 18 test files 전부 green)
- [x] manifest 유효성·아이콘 규격·`theme_color` 브랜드(#084734) 일치 — 테스트로 고정
- [x] ★**SW 캐시 대상에 분석 결과/파일 응답 미포함**(가드 테스트): `/api/coverage/analyze`·
      `/coverage/export/excel`·`/auth/v1/token`·`/rest/v1/*`·`.xlsx`·`.pdf`·POST·교차 출처
      **전부 `false`**. 셸·정적 자산만 `true`
- [x] **오프라인 폴백 실렌더**(375px): 가로 넘침 **false**(문서폭 375 = 뷰포트 375) ·
      재시도 버튼 **48px 높이**(44px 권장 충족) · 본문 16px·제목 20px(263이 지적한 소형 폰트
      문제 없음) · `theme-color` #084734
- [x] **빌드 자산 복사 확인**: `dist/sw.js`·`dist/offline.html`·`dist/site.webmanifest` 생성됨
      (※`dist` 번들 크기 343 kB는 248 로컬 껍데기 이슈로 별개 — 이번 변경과 무관)
- [x] `npm run smoke:coverage` **PASS**(정본 2건) · PII 0
- [x] diff 범위 = `public/`(sw.js·offline.html·site.webmanifest) · `src/`(pwa.ts·InstallPrompt.tsx·
      main.tsx 배선) · 테스트 1 + harness. **`vite.config.ts`·backend·기존 화면 컴포넌트 diff 0**

## Codex 2차 보정 (2026-07-31)

- 프로덕션 263 선행 push 후 전체 게이트를 재현했다: backend **792/8**, frontend **109**,
  tsc app/node·lint, 라우트 **18/18**, PWA **10/10**, coverage smoke PASS.
- 375px 실렌더에서 안내 본문이 1차 기록과 달리 15px임을 발견해 CSS 한 줄을 **16px**로
  정정했다. 재계측: 가로 넘침 0·버튼 48px·본문 16px·theme `#084734`·콘솔 error 0.
- activate가 동일 출처의 모든 Cache Storage를 삭제하던 한 줄을 **`bohumfit-shell-*` 구버전만**
  삭제하도록 좁혔다. 현재 stale 제거는 유지하고 265 분석 캐시·타 캐시 삭제 위험은 제거했다.
- install 단계의 자동 `skipWaiting()`을 제거해, 최초 설치는 정상 활성화하되 업데이트 시에는
  기존 SW를 유지하고 265 안내 UI가 `SKIP_WAITING` 메시지를 보낼 수 있게 계약을 바로잡았다.
- 빌드 후 `dist/sw.js`·`offline.html`·`site.webmanifest`는 public 원본과 해시가 같다.
  `build:verify`는 기존 248 껍데기 343,225 B로 예상 FAIL이며 PWA 자산 판정과 무관하다.

## 잔여·후속 (기록)
- **실기기 설치 확인**은 로컬에서 불가(HTTPS 필요) → Codex/프로덕션에서 확인 필요.
  로컬 빌드가 248 껍데기 상태라 로컬 `vite preview`로도 실사용 검증이 어렵다.
- SW **업데이트 안내 UI**(새 버전 감지 → "새로고침" 토스트)는 265 범위로 남겼다.
  현재는 `SKIP_WAITING` 훅만 준비돼 있다.
- 분석 결과 오프라인 열람(시안의 "최근 분석 5건 오프라인 열람")은 **265 A안**에서 구현.

## Stage 목록 (Codex용)
`public/sw.js`·`public/offline.html`·`public/site.webmanifest`,
`src/lib/pwa.ts`·`src/lib/pwa.test.ts`·`src/components/InstallPrompt.tsx`·`src/main.tsx`,
`tasks/BOHUMFIT-264-*.md`, `handoff.md`, `locks.md`
※`vite.config.ts` 변경 0 — 패킷 Stage 목록에서 제외.

## 커밋 메시지 (Codex용)
feat(BOHUMFIT-264): PWA 셸 — manifest·서비스워커·설치 프롬프트·오프라인 폴백

## Next
① **Codex** — ★**263(`6e87cc5`) 먼저 push** 후 264 검증·커밋(라우트 스모크·PII 캐시 가드·
  프로덕션 실기기 설치 확인) ② **Chat** — 265(디자인 토큰·공통 컴포넌트 + SW 업데이트 안내·
  분석 결과 A안 캐시) 발번 ③ **Human** — 262 결정지 3건.
