# BOHUMFIT-269b — 모바일 하단 네비게이션

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Claude Code (구현·1차 검증)
Risk tier: ★고위험(전역 레이아웃) — git 쓰기 금지(커밋 Codex).
Date: 2026-08-03 · 기준 HEAD `04bef53`(268b)
※워킹트리에 **269a 미커밋분 공존** — Codex는 **269a → 269b 순서로 분리 커밋**할 것.

## Step 1 — 현행 실측 (코드 무변경)

### Layout NAV — 데스크톱·모바일이 **같은 배열을 공유**한다
`src/components/Layout.tsx:26` `NAV` 6항목:
자료 받기(`/download-guide`) · 고지의무 분석(드롭다운 → `?mode=agent`/`?mode=customer`) ·
보장 비교분석(`/coverage-compare`) · 실손 계산(`/insurance`) · 보험사 링크(`/insurance-links`, 093) ·
요금제(`/subscription`).
- 데스크톱: `228행` `hidden ... lg:flex` 가로 메뉴
- 모바일: `268행` **햄버거 드롭다운 패널**(`lg:hidden`) — 같은 `NAV`를 그대로 돈다
→ 269b는 이 구조를 **건드리지 않고** 하단 탭을 **추가**한다(데스크톱 diff 0).

### `viewport-fit=cover`가 **없다**
`index.html:11` = `width=device-width, initial-scale=1.0`. safe-area를 쓰려면 **추가 필요**.
264 PWA manifest·theme-color 등 다른 meta는 건드리지 않는다.

### 탭 후보의 모바일 상태(실측: 고정폭 표 / 15px 미만 폰트)
| 라우트 | 고정폭·표 | 15px 미만 | 모바일 개편 |
|---|---|---|---|
| `/dashboard` | 0 | 0 | ★269a 완료 |
| `/disclosure` | 0(모바일 경로) | — | ★267·268a·268b 완료 |
| `/coverage-compare` | 0(모바일 경로) | — | ★266 완료 |
| `/insurance-links` | **0** | 29 | 미개편(넘침 위험은 낮음) |
| `/subscription` | 0 | 6 | 미개편 |
| `/insurance`(실손 계산) | 0 | 8 | 미개편 — **계산 입력 폼**이라 손이 더 필요 |
| `/history` | 0 | 17 | 미개편 |

### ★탭 4종 확정 — 홈 / 고지의무 / 보장분석 / 보험사 링크
- 앞 3개는 **모바일 개편이 끝난 화면**이다(263~269a).
- 4번째는 **보험사 링크**를 골랐다: 고정폭 표가 **0**이라 넘침 위험이 낮고, 전산·약관·팩스 링크는
  설계사가 현장에서 자주 여는 도구다.
- ★**제외한 것과 사유**:
  - **실손 계산(`/insurance`)** — 계산 **입력 폼**이라 모바일 최적화가 더 필요하다. 탭에 넣으면
    "덜 다듬어진 화면"으로 유도하게 된다(패킷 Step 1 지시).
  - **요금제** — 사용 빈도가 낮고, 무료 소진 시 업셀 카드가 이미 안내한다(159).
  - **히스토리** — 269a 홈의 "최근 분석 → 전체 보기"로 이미 한 번에 닿는다. 탭을 하나 더 쓸 이유가 없다.
  - **자료 받기** — 최초 1회 성격이라 상시 탭에 둘 필요가 없다.
- **5탭이 아니라 4탭**: 375px에서 탭 하나당 약 93px이라 한글 라벨이 뭉개지지 않는다.

### 269a가 고정한 "네비 마크업 0" 테스트
`src/components/mobile/mobileHome.test.tsx`의 `"하단 네비를 만들지 않는다(269b 범위)"` —
`MobileHome` **자체**에 네비가 없어야 한다는 계약이다. 269b는 네비를 **Layout**에 두므로
이 테스트는 **여전히 유효**하다. 다만 의도가 바뀐 만큼 **주석과 이름을 갱신**한다(삭제하지 않는다).

## Step 2~5 — 구현
- `src/components/mobile/MobileBottomNav.tsx` 신설: 4탭 · 아이콘+한글 라벨 · 활성 탭 `accent-600`(#084734) ·
  터치 44px 이상 · `env(safe-area-inset-bottom)`.
- `Layout.tsx`: `useIsMobile`일 때만 렌더 + **페이지 셸 최하단 여백**(네비 높이 + safe-area)으로
  본문뿐 아니라 Footer 마지막 요소까지 가림 방지.
- `index.html`: `viewport-fit=cover` 추가(264 meta 구성은 그대로).
- **숨김 조건**: ①비로그인 ②`role="dialog"`(268a 시트) 열림 ③분석 진행 중.
  ★Disclosure를 건드리지 않기 위해 **네비가 스스로 관찰**한다(`MutationObserver`) —
  268a·268b 동작에 손대지 않고 겹침만 피한다.
- z-index: 시트(9998) > 네비(40) > 콘텐츠.

## 검증 결과 (1차 · 2026-08-03 · Windows 로컬)

- [x] tsc app/node **PASS** · `npm run lint` **PASS**
- [x] `npm test` **278 passed / 32 files**(269a까지 260 + 신규 **18**) · 회귀 0
      ★269a "네비 마크업 0" 가드는 **삭제하지 않고 갱신**했다 — 의미를 "홈이 자기 네비를 만들지 않는다
      (소유는 Layout)"로 바꿔 **네비가 두 벌 생기는 것**을 계속 막는다.
- [x] backend `pytest -q` **818 passed, 8 skipped**(불변) · ★**`backend/` diff 0**
- [x] `npm run smoke:coverage` **PASS** · `build:verify` **343,225 B 예상 FAIL**
- [x] ★**데스크톱 회귀 0 — 전 주요 화면**(전역 변경이라 범위를 넓게): HEAD 사본 대비
      `/dashboard`·`/disclosure`·`/coverage-compare`·`/insurance-links`·`/history` **5경로에서 Layout
      `innerHTML`·노드 수 완전 일치**. `AnalysisProgress`도 **요소 수 동일**(추가된 것은 마커 속성 1개뿐).
      빈 화면 오통과 방지 마커 포함. 사본·일회성 스크립트 **삭제**.
- [x] ★**데스크톱에 하단 네비 미표시** · **비로그인 모바일에도 미표시**
- [x] ★**세이프에어리어** — `paddingBottom: env(safe-area-inset-bottom, 0px)` 적용(인디케이터 없으면 0) ·
      `index.html`에 **`viewport-fit=cover` 추가**(264 manifest·theme-color meta는 그대로 유지 확인)
- [x] ★**본문 가림 방지** — `Layout`의 `<main>`에 `BOTTOM_NAV_HEIGHT + env(safe-area-inset-bottom) + 2rem`
      하단 여백. 데스크톱에서는 `undefined`라 기존 스타일 그대로다.
- [x] ★**겹침 회피** — 268a 시트(`role="dialog"[aria-modal]`)나 분석 진행(`data-analysis-busy`)이 있으면
      네비를 **렌더하지 않는다**(z-index 다툼 자체를 만들지 않음). 시트가 닫히면 다시 나타난다.
      z-index: 시트 **9998** > 네비 **40** > 콘텐츠.
- [x] 활성 탭 표시 — 현재 경로만 `accent-600`, 쿼리스트링 탭(`/disclosure?mode=agent`)도 **경로로 판정**
- [x] 탭 4개 균등 분할(`flex-1`) · 고정폭·가로 스크롤 **0** · 터치 **44px 이상** · 라벨 **15px**(265 하한 준수)
- [x] 라우트 신설 0 — 4탭 경로가 전부 `App.tsx`에 실재함을 테스트로 확인
- [x] `vite.config.*` diff 0 · 265 캐시·268a 시트·268b 티커 **파일 diff 0**(겹침 회피는 네비 쪽에서만 처리)

### 구현 판단 3건
1. **탭 4종 = 홈/고지의무/보장분석/보험사 링크.** 앞 3개는 모바일 개편이 끝난 화면이고, 4번째는 고정폭 표가
   0이라 넘침 위험이 낮으면서 설계사가 자주 여는 도구다. **실손 계산은 입력 폼이 미개편이라 제외**했고,
   요금제·히스토리·자료 받기는 빈도·대체 경로를 근거로 뺐다(위 Step 1 표).
2. **겹침 회피를 Disclosure 수정 없이 처리했다.** 네비가 `MutationObserver`로 시트·분석 마커를 관찰한다.
   전역 컨텍스트를 새로 만들거나 268a·268b 경로를 고치는 것보다 침습이 작다.
   `AnalysisProgress`에는 **속성 1개**(`data-analysis-busy`)만 붙였고 렌더 요소 수는 그대로다.
3. **라벨을 15px로 올렸다.** 처음엔 11px로 썼다가 265 하한 가드에 걸렸고, 375px ÷ 4탭 ≈ 93px이라
   한글 4글자가 들어가는 것을 확인해 **가드를 우회하지 않고 규격을 지켰다**.

### 자체 정정 2건
1. 상수를 컴포넌트 파일에서 내보내 `react-refresh/only-export-components`에 걸렸다 →
   `bottomNavTabs.ts`로 분리.
2. jsdom이 `env()`를 파싱하지 못해 인라인 style 단언이 실패했다 → **소스 검사로 바꾸고 그 사유를 주석에 남겼다**
   (실제 적용은 브라우저 실측 몫).

### 로컬에서 못 한 것 (Codex 몫)
- **375/390/430px 실렌더 넘침·탭 라벨 뭉개짐** (jsdom은 레이아웃을 계산하지 않는다)
- ★**세이프에어리어 실제 동작** — 홈 인디케이터가 있는 기기(iOS)에서 겹침 0인지
- ★**키보드 올라올 때 네비 거동**(Android 리사이즈 / iOS 오버레이) — 명세 Step 4의 실측 항목이다.
  코드상 `position: fixed`라 iOS에서 키보드 위에 뜰 수 있어 **실기기 확인이 필요**하다.
  현재는 시트가 열리면 네비가 사라지므로 **업로드 폼 입력 중에는 문제가 없다**(가장 흔한 입력 경로).

## Codex 2차 보정 (2026-08-03)

- 실브라우저 375px에서 `<main>`에만 둔 여백은 그 뒤의 Footer 마지막 줄을 네비 뒤로 약 16px 가렸다.
  여백을 `Layout` 페이지 셸의 Footer 뒤로 옮기고 회귀 단언을 보강했다.
- 보정 후 375·390·430px × 4탭 전 조합에서 가로 넘침 0·Footer 가림 0을 재현했다.

## Stage 목록 (Codex용)
`src/components/mobile/MobileBottomNav.tsx`(신규)·`src/components/Layout.tsx`·`index.html`·
`src/components/AnalysisProgress.tsx`(진행 마커 1속성)·`src/components/mobile/mobileHome.test.tsx`(가드 갱신)·테스트,
`tasks/BOHUMFIT-269b-bottom-nav.md`, `handoff.md`, `locks.md`
※제외: 실 PDF·PII·엑셀 원본·시안 HTML·렌더 산출물

## 커밋 메시지 (Codex용)
feat(BOHUMFIT-269b): 모바일 하단 네비게이션(세이프에어리어·시트 겹침 회피)
