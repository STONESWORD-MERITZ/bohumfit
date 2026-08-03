# BOHUMFIT-269a — 모바일 홈 대시보드

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Claude Code (구현·1차 검증)
Risk tier: 중위험 — git 쓰기 금지(커밋 Codex).
Date: 2026-08-02 · 기준 HEAD `04bef53`(268b)

## ★범위 한정
하단 네비는 **269b 범위**다. 자리 확보·선행 작업도 하지 않는다.

## Step 1 — 현행 실측 (코드 무변경) ★판정 포함

### 163 대시보드는 **이미 존재하고, 필요한 것을 거의 다 갖고 있다**
`src/pages/Dashboard.tsx`(260줄) · 라우트 `/dashboard`(`App.tsx:107`, `ProtectedRoute`).
구성: **최근 분석**(상위 5) · **분석 사용량**(남은 횟수) · 저장된 리포트 · 바로가기 3종 · **Pro 업셀**(159) ·
admin 직원 관리(233).

| 항목 | 현재 출처 | 269a 판정 |
|---|---|---|
| 최근 분석 | `GET /history?track=recent&limit=5` | **그대로 재사용** |
| 남은 횟수 | `GET /billing/status` → `usageLeft` 계산 로직 존재 | **그대로 재사용**(백엔드 신설 0) |
| 저장 리포트 | `GET /history?track=saved&limit=1`(total) | 그대로 |
| 업셀 | `showUpsell`(159 톤) | 그대로 |

→ ★**판정: "기존 홈을 모바일 레이아웃으로 재배치"** 다. 데이터 계층은 한 줄도 새로 만들지 않고,
모바일에서 **배치·타이포·터치 규격만** 265 토큰에 맞춘다(중복 구현 금지).

### "최근 분석" 출처 — **히스토리(156a/156b)를 쓴다. 265 캐시가 아니다**
- 265 IndexedDB 캐시는 **기기 로컬 24시간 · 최근 5건**이고, 히스토리는 **서버 90일**이다.
- 홈의 "최근 분석"은 **기기를 바꿔도 보여야 하는 목록**이라 서버 히스토리가 맞다.
  기존 Dashboard가 이미 그렇게 하고 있으므로 **바꾸지 않는다**(성격이 다른 둘을 섞지 않는다).

### ★진입 카드 — 보장분석 진입이 **지금 없다**
바로가기 3종은 `분석 시작(/disclosure?mode=agent)` · `보험사 링크` · `요금제`뿐이고
**`/coverage-compare`(보장분석) 진입이 빠져 있다**. 269a가 채우는 실질은 여기다.
라우트는 기존 것을 그대로 쓴다(신설 0). 172 진입점 통합과도 충돌하지 않는다 —
`/disclosure?mode=agent`는 172가 정리한 그 경로다.

### 로그인 후 도달 지점 — 지금은 `/disclosure?mode=agent`
`App.tsx:64` `RedirectIfAuthed`가 그렇게 보낸다(163이 **의도적으로 무변경**으로 둔 A안).
→ 269a는 **모바일에서만** `/dashboard`로 보낸다. ★데스크톱 도달 지점은 건드리지 않는다.

### PII
최근 분석 항목은 `label`(사용자가 입력한 **별칭** — 실명 입력 금지 안내가 이미 있음)·`mode`·`created_at`뿐이라
**환자명·원본 파일명이 없다**. 268b에서 파일명을 "서류 N"으로 익명화한 것과 같은 기조다.
기존 표기를 **그대로 따른다**.

## Step 2~5 — 구현
- `src/components/mobile/MobileHome.tsx` 신설: **진입 카드 2종**(고지의무 분석 / 보장분석) +
  최근 분석 + 남은 횟수. ★데이터는 `Dashboard`가 이미 fetch한 것을 **props로 받는다**(중복 fetch 0).
- `Dashboard.tsx`: `useIsMobile` 분기 — 모바일이면 `MobileHome`, 데스크톱이면 **기존 그리드 그대로**.
- `App.tsx`: `RedirectIfAuthed`에서 **모바일만** `/dashboard`로.
- 265 토큰 사용(주 액션 56px·터치 44px·15px 하한).

## 검증 결과 (1차 · 2026-08-02 · Windows 로컬)

- [x] tsc app/node **PASS** · `npm run lint` **PASS**
- [x] `npm test` **260 passed / 31 files**(기준선 246 + 신규 **14**) · 회귀 0
- [x] backend `pytest -q` **818 passed, 8 skipped**(불변) · ★**`backend/` diff 0**
- [x] `npm run smoke:coverage` **PASS** · `build:verify` **343,225 B 예상 FAIL**
- [x] ★**데스크톱 회귀 0** — HEAD 사본 대비 **대시보드 렌더 `innerHTML`·노드 수 완전 일치**
      (빈 화면 오통과 방지: 노드 수 하한 + `최근 분석`·`바로가기` 마커). 사본·일회성 스크립트 **삭제**.
- [x] ★**로그인 후 도달 지점** — 데스크톱 `/disclosure?mode=agent`(163 A안 그대로) / 모바일만 `/dashboard`.
      분기식이 `App.tsx` 소스와 일치하는지도 함께 고정.
- [x] 진입 카드 2종이 **기존 라우트**(`/disclosure?mode=agent`·`/coverage-compare`)로만 이동 · 라우트 신설 0
- [x] 카드 높이 **56px 이상** · 최근 분석 행 **44px 이상** · 15px 미만 폰트 **0**
- [x] ★**최근 분석에 환자명·원본 파일명 미노출** — 표시는 별칭·분석 종류·시각뿐이고
      `.pdf`·`기본진료정보` 류 문자열이 **0건**임을 테스트로 고정(268b 익명화 기조와 동일)
- [x] 빈 상태(첫 분석 CTA)·로딩·실패 문구 전부 처리 — 빈 화면 방치 0
- [x] ★**하단 네비 자리 0** — `MobileHome`에 `BottomNav`/`TabBar`/`fixed ... bottom-0` **없음**,
      렌더 결과에 `<nav>` **0개**(269b 범위 침범 방지를 테스트로 고정)
- [x] ★**중복 fetch 0** — `MobileHome`에 `fetch`·`useEffect` **없음**. `Dashboard`가 이미 가져온 값을 props로 받는다.
- [x] `vite.config.*` diff 0 · 265 캐시(`analysisCache.ts`)·268a(`uploadWithProgress.ts`)·268b
      (`analysisProgress.ts`) **diff 0** · 요금제·결제·인증 로직 무접촉(표시만) · Supabase 무변경

### 구현 요약
- `MobileHome.tsx` 신설 — 진입 카드 2종 + 남은 횟수 + 최근 분석. 데이터는 **props 주입**.
- `Dashboard.tsx` — `useIsMobile` 분기 1곳 추가. 데스크톱 그리드는 **그대로**이고, 사용량 계산식
  (`isAdmin`/`usageUsed`/`usageLeft`/`usageWarn`)도 **기존 것을 그대로 재사용**해 값이 갈라질 수 없다.
- `App.tsx` — `RedirectIfAuthed`의 목적지만 모바일 분기.

### 판단 기록
- **"최근 분석"은 서버 히스토리를 쓴다**(265 IndexedDB 캐시 아님). 캐시는 기기 로컬 24시간이고
  홈 목록은 기기를 바꿔도 보여야 한다. 기존 Dashboard가 이미 히스토리를 쓰고 있어 **바꾸지 않았다**.
- **저장된 리포트 위젯은 모바일 홈에 넣지 않았다.** 패킷이 지정한 모바일 홈 구성은
  "진입 카드 2종 + 최근 분석 + 남은 횟수"이고, 저장 리포트는 최근 분석의 "전체 보기 → /history"로 이어진다.
  데스크톱에는 그대로 남아 있다(회귀 0).
- **업셀 카드도 모바일 홈에 넣지 않았다** — 159 로직은 데스크톱에 그대로 두었고, 남은 횟수가 적으면
  `warn` 색으로 표시된다. 업셀 노출 정책을 모바일에서 새로 정하는 것은 범위 밖이라 Human 판단 대상이다.

### 로컬에서 못 한 것 (Codex 몫)
- 375/390/430px 실렌더 넘침(jsdom 레이아웃 미계산)
- 실기기에서 로그인 → 홈 도달 흐름(모바일 판정이 실제 기기 폭에서 의도대로 걸리는지)

## Stage 목록 (Codex용)
`src/pages/Dashboard.tsx`·`src/App.tsx`·`src/components/mobile/MobileHome.tsx`(신규)·테스트,
`tasks/BOHUMFIT-269a-mobile-home.md`, `handoff.md`, `locks.md`
※제외: 실 PDF·PII·엑셀 원본·시안 HTML·렌더 산출물

## 커밋 메시지 (Codex용)
feat(BOHUMFIT-269a): 모바일 홈 대시보드(진입 카드·최근 분석·남은 횟수)
