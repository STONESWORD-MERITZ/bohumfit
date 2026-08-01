# BOHUMFIT-265 — 모바일 디자인 토큰 + 공통 컴포넌트 + 오프라인 캐시(A안)

- 위험도: 중(풀 하네스) · git 쓰기 0 — 커밋·push는 Codex
- 전제: 263 갭 분석 · 264 PWA 셸(`901cd07`) · Human 확정 캐시 A안(24h 만료·로그아웃 삭제)
- 원칙: **화면 개편(266~) 전에 토큰·공통 컴포넌트를 세운다.** 본 태스크는 ★기존 화면 레이아웃·로직 변경 0
  (신설만) — 예외는 P3-3이 명시적으로 요구한 **고지 문구 1곳 정합**뿐이다.

## STEP 0 실측
- **토큰 현황**: `src/index.css` `@theme`에 잉크/accent(에메랄드 #084734)/라임·그린티/시맨틱/타이포 4단
  (`--text-display|title|body(15px)|caption(12.5px)`)·`--radius-card 16px`·`--radius-btn 10px`가 이미 있다.
  → **모바일 스케일이 없다**(제목 20 / 본문 16 / 보조 15, 터치 56·44, 좌우 20, 반경 20·15·8).
- **컴포넌트 현황**: `Toast`(3초·액션 없음)·`ToastContext`(최대 3개)·`ui/Badge`(tone 6종)·`ui/EmptyState`·
  `InstallPrompt`(264)·`lib/pwa.ts`(264: 등록·설치 배너 상태)는 있고, **바텀시트·주 액션 바·스와이프 카드·
  고지 배지 4단·SW 업데이트 안내는 없다**.
- **캐시 현황**: 264의 `public/sw.js`가 `isCacheableRequest()` 한 곳에서 `/api/`·`/coverage/`·`/analyze`·
  `/auth/`·`/rest/v1/`·xlsx/pdf/csv·GET 외·교차 출처를 **전면 차단**한다(PII 보호 계약).
- **고지 문구 사용처 전수**(grep `저장하지 않`): 프런트 5곳 · 백엔드 8곳.

## P1 — 디자인 토큰(추가만, 기존 값 무변경)
`src/index.css @theme`에 모바일 스케일을 additive로 넣고 `src/components/mobile/tokens.ts`에 TS 정본을 둔다.
- 타이포 3단: `--text-m-title 20 / --text-m-body 16 / --text-m-sub 15`.
  ★**15px 미만 회색 본문 금지** — `MIN_BODY_FONT_PX = 15` + 가드 테스트가 모바일 컴포넌트 전체를 스캔한다.
- 터치: `--size-m-action 56` · `--size-m-tap 44` + `.m-tap::before` 히트 영역 확장(레이아웃 밀림 0).
- 간격·반경: 좌우 20 / 카드 20 · 버튼 15 · 배지 8.
- 색: **FIT 팔레트 무변경**. `--color-surface-warning/review/muted` 3종만 신설(면 전용).
  ★라임·그린티 폰트/보더 금지, ★장식 그라디언트 금지 — 둘 다 가드 테스트로 고정.

## P2 — 공통 컴포넌트(정의만 · 적용은 266~)
| 컴포넌트 | 핵심 계약 |
|---|---|
| `BottomSheet` | 배경 탭·핸들·Esc 닫힘, 맥락 유지(현재 화면 위에 얹음), 하단 안전영역 패딩. 3종 용도 재사용 |
| `PrimaryAction` | 56px·하단 고정(엄지 도달), 진행 중 라벨 교체 + 중복 탭 차단(★전체 화면 스피너 없음) |
| `DisclosureBadge` | 4단 — 고지대상·10년 / 고지대상·3개월 / 검토·1년 재검사 / 해당없음(★5년 표기 잔재 0) |
| `SwipeActionCard` | 좌=해지·우=복원, ★임계 72px 미만은 무효(스크롤 오조작 방지), 해지 상태 = 회색 면 + 취소선 |
| `UpdatePrompt` | 264가 남긴 훅 사용 — ★자동 새로고침 금지, 사용자가 누를 때만 `SKIP_WAITING`→controllerchange 1회 리로드 |
| Toast 확장 | `showUndoToast`(6초·되돌리기) **additive** — 기존 `showToast`(3초) 시그니처·동작 불변 |
★되돌리기 토스트 남용 금지: `UNDO_TOAST_ALLOWED_SCOPES = 해지 확정·복사 완료·분석 완료` 3곳만.

## P3 — 오프라인 캐시(A안)
`src/lib/analysisCache.ts` 신설. **IndexedDB** 채택 — localStorage는 용량·동기 blocking, Cache Storage는
264의 `bohumfit-shell-*` 정리 규칙과 얽히기 때문. **SW는 손대지 않았다**(`isCacheableRequest()` diff 0):
분석 결과는 **앱이 직접** 별도 스토어에 넣는다.
- 최근 **5건**(`pickRetained`) · **24h 만료**(`isEntryValid` — 정확히 24h면 만료) · 읽을 때 만료분 즉시 삭제
- **로그아웃 시 전량 삭제**: `AuthContext.signOut`이 `supabase.auth.signOut()` **이전에** `clearAnalysisCache()` 호출
- **비로그인 차단**: `userId`가 없으면 저장소를 열지 않고 빈 결과(노출 0), 조회 시 소유자 재대조
- **고지 문구 정합**(`ConsentGate`): "업로드 자료와 분석 결과는 저장하지 않으며" →
  **"서버에 저장하지 않으며, 오프라인 열람을 위해 이 기기에 24시간 임시 보관되고 로그아웃 시 삭제됩니다"**
  (보조 문구 하한 규칙에 맞춰 11px → 15px)

## ★Human 보고 — 약관·개인정보처리방침 검토 필요 지점(본 태스크 범위 밖·수정 0)
| 위치 | 현행 문구 | 캐시 정책과의 관계 |
|---|---|---|
| `src/pages/PrivacyPolicy.tsx:39` | "…서비스 데이터베이스에 저장하지 않습니다" | **서버 저장 0은 여전히 사실**. 다만 "기기 24시간 임시 보관"이 방침에 없음 → **문장 추가 검토 필요** |
| `src/pages/InsuranceCalculator.tsx:268` | "업로드한 PDF는 …저장하지 않습니다" | PDF 원본은 캐시 대상 아님 → **유지 가능**(결과만 캐시) |
| `src/pages/Disclosure.tsx:1046` · `InsuranceCalculator.tsx:346` | "입력값은 저장하지 않으며 이 화면에서만" | 입력값은 캐시 대상 아님 → **유지** |
| `backend/pipeline/report_pdf.py:105` | 산출 PDF 하단 고지 | 서버 문구 → **백엔드 무접촉 계약상 미수정**, 방침 확정 후 일괄 |

## 검증(1차 · Claude Code 로컬 실측)
- backend `pytest -q` **792 passed, 8 skipped**(기준선 불변 · backend diff 0)
- frontend `npm test` **140 passed**(기준선 109 + 신규 31) · 라우트 스모크 18건 포함 전 파일 green
- `npx tsc -p tsconfig.app.json --noEmit` / `tsconfig.node.json` clean · `npm run lint` clean
- `npm run build` 성공(343.22 kB — 248 기록대로 로컬 Application Control 껍데기, `build:verify`는 예상 FAIL)
- `npm run smoke:coverage` **PASS**(표준 604,560,000·681,312 / overview 1,542,990,000·4,675,189 —
  회사합=합계 0 · 전=후 0)
- ★**라우트 스모크 18/18 별도 재확인**(공개 16 + 보호 2) — 토큰·컴포넌트 신설이 라우팅 무영향
- `build:verify` 실측 **343,225 B**(하한 600,000 B 미달 · 앱 문자열 3종 누락) = **264와 동일 수치**로
  이번 변경과 무관함을 확인. 248 결정대로 소스 게이트 + Codex 프로덕션 번들로 판정한다.
- PII 0 · 실 PDF/xlsx 미접촉 · 시안 HTML 레포 이동 0

### 테스트 자체 결함 2건 정정(작성 후 실측에서 발견)
- `analysisCache.test.ts` 로그아웃 배선 검사 — signOut 본문 슬라이스 경계를 `"return ("`로 잡았더니
  **앞선 `useEffect`의 `return () =>`에 먼저 매칭돼 슬라이스가 빈 문자열**이 됐다(검사 무력화).
  경계를 `"\n  };"`로 바꾸고, **`clearAnalysisCache()`가 `supabase.auth.signOut()`보다 앞**인지도 함께 단언.
- 같은 파일 SW 가드 검사 — sw.js의 차단 목록은 **정규식 리터럴(`/\/api\//i`)이라 `/api/` 문자열이 없다**.
  `\/`를 `/`로 되돌린 뒤 비교하도록 정정하고 `function isCacheableRequest` 존재 단언을 추가.
→ 두 건 모두 **검사 의도는 그대로 두고 표현만 실측에 맞춘** 수정이다(제품 코드 변경 0).

## 남은 것
- 266~ 화면 적용(보장분석 3단 점진 공개 + 스와이프 해지 등)에서 이 토큰·컴포넌트를 소비
- 오프라인 목록 UI(캐시 열람 화면)는 266~ 범위 — 265는 저장·만료·삭제 계약만
- `saveAnalysis()` 호출부(분석 완료 시 적재)도 266~ — 265는 저장소 계층만 만든다

## Codex 반려 3건 보정 (2026-08-01)

### 보정 1 (★최우선) — 로그아웃 경로 전수 + 단일 삭제 지점
**전수 실측(`supabase.auth.signOut` 호출부 grep + 세션 소멸 경로)**:
| # | 경로 | 보정 전 삭제 |
|---|---|---|
| ① | 명시적 로그아웃 버튼 `AuthContext.signOut` | O |
| ② | **30분 무활동 자동 종료** `AuthContext.tsx:41` | ✗ ← Codex 반려 1 |
| ③ | `PhoneVerify.tsx:98` → context `signOut()` 경유 | O(①에 위임) |
| ③' | **비밀번호 변경 후 종료** `ResetPassword.tsx:75`(supabase 직접 호출) | ✗ ← **Codex 지적에 없던 4번째 누락**(이번 실측에서 발견) |
| ④ | 세션 만료·토큰 갱신 실패(앱 코드를 거치지 않음) | ✗ |
| ⑤ | 다른 탭에서의 로그아웃 | ✗ |

**설계 — 삭제를 호출부에 복제하지 않고 `onAuthStateChange` 구독 한 곳으로 모았다**(249·251 "단일 소스" 선례).
- 판정 기준은 **이벤트 이름이 아니라 사용자 id 전이**(`lastUserIdRef`): 로그인해 있던 id가 사라지거나(null)
  다른 id로 바뀌면 삭제. 이벤트명은 SDK 버전마다 달라지므로 의존하지 않는다.
- ①~⑤가 전부 이 구독으로 흘러오므로 **새 로그아웃 경로가 추가돼도 자동 포섭**된다. ②·③'는 호출부를
  건드리지 않고 해소됐다.
- `TOKEN_REFRESHED`처럼 같은 사용자가 유지되는 이벤트에서는 지우지 않고, 비로그인 초기 진입에서는
  저장소를 열지도 않는다.
- ★예외 1곳: 카카오 로그아웃은 즉시 외부 페이지로 이동해 구독이 시작한 비동기 삭제가 끊길 수 있어,
  `window.location.href` **직전에만** flush를 둔다(정책이 아니라 이탈 방어이며 삭제는 멱등).

### 보정 2 — ConsentGate 문구(Human 확정본)
"업로드하신 **자료 원본은 분석 후 저장하지 않습니다**. 분석 결과는 히스토리 저장을 요청하신 경우 **90일간**,
요약 기록은 **7일간** 서버에 보관되며, 오프라인 열람을 위해 최근 5건이 **이 기기에 24시간 임시 보관**됩니다
(로그아웃 시 즉시 삭제)."
- 반려 사유였던 자기모순(동의 화면은 "분석 결과 서버 저장 0" 단언 ↔ 방침 40·50행 90일 / 41·51행 7일)을 해소.
  저장하지 않는 것은 **업로드 원본**이고 분석 결과는 90일/7일 + 기기 24시간이라는 **3층 구조**를 그대로 노출한다.
- 15px 하한 유지. `PrivacyPolicy` 4항 추가 문단은 **현행 유지**(이미 정합).

### 보정 3 — "5년" 잔재
- 정정 2건: `DisclosureBadge.tsx:1`·`tokens.ts:46`의 "Human 확정: 5년 → 10년" →
  "장기 고지 배지는 **10년** 기준으로 Human 확정(초기 검토안에서 상향)". 이력 의미는 남기고 숫자 표기만 제거.
- ★**제외 근거(정정하지 않은 "5년")**: `Disclosure.tsx`(Q3 "5년 이내"·Q4 "5년 초과 10년")·`ReportSample.tsx`·
  `whyContent.ts`·`DownloadGuide.tsx`(심평원 5년/공단 10년 자료 범위)·`disclosureMemo.test.ts`·`backend/`는
  **알릴의무 질문 기간과 자료 제공 범위**라는 별개 도메인 사실이다. 배지 라벨과 무관하므로 그대로 둔다.
- 가드 강화: `mobileTokens.test.ts`가 라벨 JSON뿐 아니라 **`src/components/mobile` 전 파일의 주석까지** 스캔한다.

### 보정 검증 (2026-08-01)
- [x] ★**로그아웃 3경로 실동작 테스트**(`authCacheClear.test.tsx` 신규 7건) — 수동 / **무활동 자동(반려 결함 경로)** /
      세션 만료·갱신 실패 / 비밀번호 변경 후 종료에서 **전량 삭제 호출 확인**, 토큰 갱신(동일 사용자)은 삭제 안 함,
      **계정 전환은 삭제**, 비로그인 진입은 저장소 미접근
- [x] 구조 가드(`analysisCache.test.ts`) — 삭제가 구독 안에 있고 **무활동 타이머에 복제되지 않았음**,
      flush는 리다이렉트 직전에만
- [x] ★**고지 3층 정합**(90일·7일·24h) 동의 화면 ↔ 방침 상호 검사 + 기기 캐시 수치가 `MAX_ENTRIES`·`TTL_MS`
      구현 상수와 일치(문구만 바뀌는 것 차단)
- [x] `npm test` **161 passed / 23 files**(149 + 12) · tsc app/node · lint 클린
- [x] backend `pytest -q` **792 passed, 8 skipped** · **`backend/` diff 0**
- [x] 라우트 스모크 **18/18** · Disclosure·CoverageRemodel 렌더 회귀 0(wiring 9건 재통과) · `smoke:coverage` PASS
- [x] "5년" 잔재 — 제품 코드 **0건**(남은 것은 가드 테스트가 검사하는 문자열 자체)
- [x] `build:verify` **343,225 B** 동일 수치 예상 FAIL · diff = 265 기존 + `AuthContext.tsx`(+29/-4) +
      `ConsentGate.tsx`(+14/-3) + 주석 2건 + 테스트 · PII 0
- 정정 1건: 새로 만든 모순 가드가 **변경 사유를 적은 주석까지** 잡아 오탐 → 렌더 문구만 검사하도록 주석 제거 후 비교.

## 마무리 2건 (Human 승인 후 반영 · 2026-07-31)

### 마무리 1 — UpdatePrompt 배선 완료
`src/main.tsx`에 264 `InstallPrompt`와 **동일 패턴**으로 배선했다 — `AuthProvider` 안, `<App/>` **형제**,
`fixed` 배치. 화면 컴포넌트는 한 줄도 건드리지 않았고 diff는 **import 1줄 + 배선 1줄 + 주석 4줄(삭제 0)** 뿐이다.
대기 중인 새 버전이 없으면 `null`을 반환하므로 평상시 DOM 추가가 **0**이다.
자동 새로고침 금지 흐름(사용자 클릭 → `SKIP_WAITING` → `controllerchange` 1회 리로드)은 그대로 유지된다.

### 마무리 2 — PrivacyPolicy 1문장 추가
`4. 개인정보의 보유 및 이용기간`의 `body` 배열에 **한 문단만 추가**했다(기존 조항·번호 체계·다른 문단 diff 0,
`PrivacyPolicy.tsx` 총 **+2줄**·삭제 0). 추가 문안:
> 오프라인 열람용 기기 내 임시 보관: 최근 분석 5건이 이용자 기기(브라우저 저장소)에 24시간 동안 임시
> 보관되며, 24시간이 지나면 자동 삭제되고 로그아웃 시 즉시 삭제됩니다. 이 정보는 이용자 기기에만
> 저장되고 서비스 서버로 전송되지 않습니다.

★**패킷 제시 문안에서 첫 문장을 뺀 사유(보고)**: 패킷 문안은 "분석 결과는 서비스 데이터베이스에 저장하지
않습니다"로 시작하는데, **같은 방침 39~41행·50~51행에 "이용자가 '히스토리에 저장'을 요청하면 분석 결과가
DB에 저장된다"(90일)와 "분석 결과 요약이 최근 10건 자동 기록된다"(7일)는 조항이 이미 있다.**
그대로 넣으면 기존 조항과 정면 모순되는 방침이 된다. 서버 미저장 원칙은 39행에 이미 서술돼 있으므로,
추가 문단은 **이번에 새로 생긴 사실(기기 내 24시간 보관·로그아웃 즉시 삭제)만** 기술하고
A안의 핵심인 **"서비스 서버로 전송되지 않습니다"**를 명시하는 형태로 조정했다. 취지·범위는 패킷 그대로다.

### 마무리 검증 (2026-07-31)
- [x] 신규 `updatePromptWiring.test.tsx` **9건** — 배선 위치(AuthProvider 안·App 형제)·★배선부 자동 리로드
      코드 0·264 배너 배선 보존·null 렌더 시 DOM 0·**PrivacyPolicy/Disclosure/CoverageRemodel 3화면의
      마크업·노드 수가 배선 전후 완전 동일**·신규 고지 문장 렌더·★기존 조항 5문장 + 조항 번호 3개 보존
- [x] `npm test` **149 passed / 22 files**(140 + 9) · tsc app/node · lint 클린
- [x] backend `pytest -q` **792 passed, 8 skipped** · **`backend/` diff 0**
- [x] 라우트 스모크 **18/18** · `npm run smoke:coverage` **PASS**(정본 2건 기준값 일치)
- [x] `build:verify` **343,225 B 예상 FAIL** — 264·265 본편과 **동일 수치**로 이번 변경과 무관
- [x] diff 범위 = 265 기존 범위 + `src/main.tsx`(+6) + `src/pages/PrivacyPolicy.tsx`(+2) · PII 0
- 환경 공백 1건: jsdom에 `scrollIntoView`가 없어 Disclosure 렌더가 죽길래 테스트에서 폴리필했다
  (앱 결함 아님 · 제품 코드 변경 0).

### 후속 태스크 후보 (기록만)
- `backend/pipeline/report_pdf.py:105` 산출 PDF 하단 고지 — 백엔드 무접촉 계약상 이번 범위 밖.
  방침이 확정됐으므로 다음 백엔드 태스크에서 문구를 맞추면 된다.
- `TermsOfService.tsx`는 저장 관련 문구가 **0건**이라 무접촉(실측 확인).

## ~~★Human 결정 필요~~ — UpdatePrompt 배선 시점 → **승인·반영 완료**(위 마무리 1)
`UpdatePrompt`는 **만들었지만 아직 어디에도 배선하지 않았다**(`src/main.tsx` diff 0 — "기존 화면 변경 0"
계약 준수). 그런데 264가 install 단계의 자동 `skipWaiting()`을 제거했으므로, **안내 UI가 붙기 전까지는
새 버전이 "모든 탭을 닫기 전에는 적용되지 않는" 상태**가 유지된다. 264의 `InstallPrompt`와 동일하게
`main.tsx`에서 `<App/>` 형제로 한 줄 배선하면 화면 컴포넌트 무변경으로 해소된다.
→ **265에 포함할지 266으로 넘길지 Human 판단**(본 태스크에서는 계약대로 배선하지 않았다).

## Stage 목록 (Codex용)
`src/index.css`, `src/components/ConsentGate.tsx`, `src/components/Toast.tsx`,
`src/components/ToastContext.tsx`, `src/lib/AuthContext.tsx`, `src/lib/pwa.ts`,
`src/components/mobile/`(tokens.ts·BottomSheet.tsx·DisclosureBadge.tsx·PrimaryAction.tsx·
SwipeActionCard.tsx·UpdatePrompt.tsx·mobileTokens.test.ts·mobileComponents.test.tsx),
`src/lib/analysisCache.ts`·`src/lib/analysisCache.test.ts`,
★마무리 2건: `src/main.tsx`(+6·배선), `src/pages/PrivacyPolicy.tsx`(+2·고지 1문단),
`src/components/mobile/updatePromptWiring.test.tsx`(신규 9건),
★반려 보정 3건: `src/lib/AuthContext.tsx`(단일 삭제 지점), `src/components/ConsentGate.tsx`(확정 문구),
`src/lib/authCacheClear.test.tsx`(신규 7건),
`tasks/BOHUMFIT-265-mobile-tokens-and-shared.md`, `handoff.md`, `locks.md`
※`backend/`·`vite.config.ts`·`src/App.tsx`·**그 외 페이지 컴포넌트 diff 0**
（`main.tsx`·`PrivacyPolicy.tsx`는 Human 승인 마무리 2건으로 편입 — 둘 다 **추가만·삭제 0**）.

## 커밋 메시지 (Codex용)
feat(BOHUMFIT-265): 모바일 디자인 토큰·공통 컴포넌트·오프라인 캐시(A안)

## Next
① **Codex** — 265 **전체** 2차 검증 → 커밋·push(가드 테스트 재현 · `backend` diff 0 ·
  ★프로덕션에서 **SW 업데이트 안내 실동작** 확인: 새 버전 배포 후 안내 노출 → 클릭 시에만 갱신 ·
  자동 새로고침 0 · 방침 페이지 문단 렌더)
② **Chat** — 266 발번(공통 컴포넌트 실제 적용 + `saveAnalysis` 호출부 + 오프라인 목록 UI)
③ **Human**(후속) — 백엔드 산출 PDF 고지(`report_pdf.py:105`) 문구 정합 시점 결정
