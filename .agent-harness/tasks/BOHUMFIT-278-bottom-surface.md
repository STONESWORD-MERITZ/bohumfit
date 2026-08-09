# BOHUMFIT-278 — 모바일 bottom-surface 단일화

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Claude Code (구현·1차 검증)
Risk tier: 중~고위험 — 실사용 결함(A-F1) + 전역 표면 계약. git 쓰기 금지(커밋 Codex).
Date: 2026-08-08 · 기준 HEAD `8cce8ae`(277) · 선행 조사 BOHUMFIT-275 A 섹션
★3건 순차 세션의 **1번**(278 → 279 → 276c). 파일이 겹치지 않게 분리한다.

---

## Step 1 — 하단 표면 전수 실측 (코드 무변경)

### 하단 고정 요소 전수 (277 커밋 후 현행)
| 요소 | 위치 | z-index | bottom | safe-area | 네비 observer 감지 |
|---|---|---|---|---|---|
| 하단 네비 | `MobileBottomNav.tsx:48` | **z-40** | `bottom-0` | 자체 `paddingBottom: env(...)` | — (자신) |
| 결과 액션 바 | `PrimaryAction.tsx:113` | **z-40** | 네비 높이만큼 상향(273) | 네비 있으면 12px·없으면 `.m-action-bar` | ✖(`role` 없음) |
| ★**구형 분석 CTA** | `Disclosure.tsx:2354` | ★**z-50** | `bottom-0` | ★**없음** | ✖ |
| 설치 안내 | `InstallPrompt.tsx:69` | **z-50** | `bottom-3` | `marginBottom: env(...)` | ✖(`role=dialog`이나 `aria-modal` 없음) |
| SW 업데이트 안내 | `UpdatePrompt.tsx:22` | **z-[9997]** | `bottom-0` | `paddingBottom: calc(env(...)+12)` | ✖(`role=status`) |
| 토스트 | `ToastContext.tsx:56` | **z-[9999]** | `bottom-4 right-4` | 없음 | ✖ |
| 바텀시트 | `BottomSheet.tsx` | z-[9998] | full | `.m-sheet` safe-area | ✔ 숨김 |
| 보장 전체표 | `CoverageMobileView.tsx` | z-[9990] | full | 있음 | ✔ 숨김 |
| 저장/튜토리얼/히스토리 모달 | `Disclosure.tsx`·`History.tsx` | z-50 / z-[1000] | full | — | ✔ 숨김 |

`sticky` 하단 고정은 **0건**(헤더 top·표 첫 열 left만).

### ★A-F1 재현 확인 — 275 판정 그대로 성립
`Disclosure.tsx:2353` `{showSticky && !result && (...)}`
- `fixed inset-x-0 bottom-0 **z-50** … **md:hidden**` → 네비(z-40) **위를 덮는다**.
- ★`useIsMobile` 분기 **밖**이고 `md:hidden` CSS 숨김만 쓴다(266 제1원칙 위반).
- ★세이프에어리어 처리가 **아예 없다**(표 유일).
- 재현: 로그인 모바일 `/disclosure`, 결과 없음, `window.scrollY > 240`.

### ★Step 1-4 — 구형 CTA vs 268a 시트: 기능 차이 실측
| 항목 | 구형 CTA(`:2355~2362`) | 268a 시트(`:2311~2326`) |
|---|---|---|
| 진입 | 스크롤 240px 후 자동 노출 | `open-upload-sheet` 버튼(`:2331`) |
| 파일 선택 | ✖ 없음 | ✔ 3종 피커 |
| 동의 블록 | ✖ 없음(모바일은 `{!isMobile && consentBlock}`이라 **시트 안에만** 있다) | ✔ `consentSlot` |
| 제출 게이트 | `loading \|\| !consent \|\| (agent && !subjectConsent)` | 같은 조건 **+ `selectedFiles.names.length > 0`** |
| 호출 | `analyze` **직접** | `onSubmit: analyze()` |

→ ★**구형 CTA는 시트의 부분집합이고 게이트가 더 약하다**(파일 0개여도 눌린다).
모바일 동의는 시트 안에서만 켤 수 있으므로, 구형 CTA는 **시트를 한 번 거친 뒤 우회하는 중복 경로**다.
★`md:hidden`이라 **데스크톱은 원래 이 CTA를 못 본다** → 블록을 지워도 **데스크톱 영향 0**이고
데스크톱 분석 버튼(`:2341~2347`)은 그대로다.
**판정: 제거해도 대체 동선이 완전하다.**

### ★A-F2 — 동시 출현 조합 판정 (275 매트릭스 확장·검증)
| 조합 | 현행 판정 |
|---|---|
| 네비 + 구형 CTA | ★**겹침 확정**(z50 > z40, 둘 다 `bottom-0`) — A-F1 |
| 네비 + 액션 바 | **해소됨**(273: 네비 실측 높이만큼 상향) |
| 네비/액션 바 + **설치 안내** | ★**겹침**(z50, `bottom-3` — 네비 자리) |
| 네비/액션 바 + **업데이트 안내** | ★**겹침**(z9997, `bottom-0`) |
| 전체표(9990)·모달(1000/50) + 업데이트 안내(9997) | ★**모달 위를 덮는다** |
| 시트/모달 + 네비 | 없음(observer가 네비를 숨김) |
| 무엇이든 + 토스트(9999) | 최상단 — **의도된 동작**(아래 판단 기록) |

---

## Step 2~4 — 구현

### Step 2 (A-F1) — 구형 CTA 제거
`Disclosure.tsx`의 `{showSticky && !result && (…)}` 블록과 스크롤 감지 상태·리스너를 **삭제**했다.
모바일 진입은 `open-upload-sheet` → 268a 시트 하나로 단일화된다.
★`md:hidden`이라 데스크톱은 원래 못 보던 요소여서 **데스크톱 동선 diff 0**이고,
데스크톱 분석 버튼(`onClick={analyze}`)은 그대로다.

### Step 3 (A-F2) — 하단 표면 단일 계약
`src/components/mobile/bottomSurface.ts` **신설**.
- `BOTTOM_SURFACE_Z` 층위 토큰: 네비 40 < 액션 바 45 < 배너 60 < 오버레이 9990 < 토스트 9999.
- ★**273이 만든 네비 높이 추종 로직을 공용 훅 `useBottomSurfaceOffset()`으로 승격**했다
  (로직·근거 그대로 — 상수 대신 `offsetHeight`를 재는 이유 3가지를 주석으로 승계). 273 테스트 13건 전부 통과.
- `PrimaryAction`은 이 훅을 쓰고 z는 토큰(`action`)으로.
- `InstallPrompt`(z-50·bottom-3) → 토큰 `banner` + `BANNER_BELOW` 오프셋.
- `UpdatePrompt`(z-[9997]) → 토큰 `banner` + 오프셋. ★기존 9997은 **전체표(9990)·모달(1000/50) 위를
  덮고 있었다** — 층위 정리로 해소.
- ★**토스트만 시트보다 위(9999)로 유지**했다. 되돌리기 토스트(265·6초)가 시트를 닫은 직후에도 보여야
  하고 가려지면 되돌릴 기회를 잃는다. 패킷 권장 순서에서 **이 한 칸만 의도적으로 다르며** 사유를 코드 주석에 남겼다.

### Step 4 — 세이프에어리어·본문 여백
- 각 요소의 `offsetHeight`에 자신의 `env(safe-area-inset-bottom)`가 **이미 포함**돼 이중 적용이 구조적으로 없다.
- ★**실브라우저에서 새 결함 1건 발견·수정**: 3단(네비+액션 바+배너) 동시 출현 시 하단 점유가
  **231px(safe 0)/265px(safe 34)** 까지 커져 **본문 마지막 줄이 가려졌다**.
  `Layout`의 하단 여백이 `BOTTOM_NAV_HEIGHT` **상수**만 빼두고 있었기 때문이다.
  → `PAGE_BOTTOM_SURFACES` 실측 총합으로 바꿨다(요소가 늘어도 배열에만 추가하면 따라온다).

---

## 검증 결과 (1차 · 2026-08-08 · Windows 로컬)

### ★실브라우저 조합 매트릭스 (프로덕션 CSS · 390px · safe 0/34)
| 조합 | 겹침 | 하단 점유(safe 0 / 34) |
|---|---|---|
| 네비만 | 단일 | 57 / 91 |
| 네비 + 액션 바 | **nav×bar = 0** | 138 / 172 |
| 네비 + 배너 | **nav×banner = 0** | 151 / 184 |
| **네비 + 액션 바 + 배너** | **전 쌍 0**(nav×bar·nav×banner·bar×banner) | 231 / 265 |
| 액션 바만(네비 숨김) | 단일 | 81 / 81 |
★**모든 조합에서 겹침 0**. 수정 전 구형 CTA는 z50으로 네비(z40) 위를 덮었다(275 재현).

### 게이트
- [x] `npm test` **385 passed / 39 files** — 373 + **신규 12**, 회귀 0(★273 테스트 13건 포함 통과)
- [x] backend `pytest -q` **890 passed, 8 skipped 불변**(★`backend/` diff **0**)
- [x] `smoke:coverage` PASS · tsc app/node · lint · `build:verify` 343,702 B 예상 FAIL
- [x] ★269b 네비 구조·감지 조건·세이프에어리어 **무변경**(테스트로 고정)
- [x] ★범위 diff 0: `backend/` · **279 범위**(`PrivacyPolicy`·`TermsOfService`·`ConsentGate`·
      `analysisCache`) · `vite.config.ts`

### ★확인 불가
- **좌표 히트 테스트**: 브라우저 pane의 `clientWidth`가 0으로 보고돼 `elementFromPoint`가 `null`을
  돌려준다(이전 세션에서도 동일). **기하학적 겹침 0**으로 판정했고, 히트 판정은 실기기 몫으로 남긴다.
- **실제 설치 이벤트·waiting worker·iOS 34px**: 합성 조건으로 재현했고 실기기 확인은 못 했다.

## Stage 목록 (Codex용)
★**278 단독 커밋**(279·276c와 분리). 변경된 프런트 소스 + 278 테스트,
`.agent-harness/tasks/BOHUMFIT-278-bottom-surface.md`, `handoff.md`, `locks.md`
※제외: 실 PDF·PII·산출물

## 커밋 메시지 (Codex용)
fix(BOHUMFIT-278): 모바일 하단 표면 단일화 — 구형 CTA 제거·z층위 계약
