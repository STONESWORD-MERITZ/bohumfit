# BOHUMFIT-266 — 보장분석 모바일: 3단 점진 공개 + 스와이프 해지

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Codex (2차 검증·커밋)
Risk tier: ★고위험(핵심 화면 개편) — 풀 하네스. git 쓰기 금지(커밋 Codex).
Date: 2026-08-01 · 기준 HEAD `c24bfa7`(265)

## 배경
263 실측: `CoverageRemodel`의 ⑤ 매트릭스가 40행×15열 ≈1,680px로 모바일 폭의 4.5배.
265에서 토큰·공통 컴포넌트를 준비했고, 이번에 시안의 정보 계층 분해를 적용한다.

## ★제1원칙 — 데스크톱 회귀 0
회사별 열 전개(252)·2단 헤더·Y/N 회사별(254)·해지 토글·수동 담보(236 E)·계피/납만기·
납입완료 병기·미확인 열 가드(252)·엑셀/PDF 동선·overview 분기(259)는 **데스크톱에서 무변경**.

## STEP 0 실측 (2026-08-01)

### 현행 구조 (`CoverageRemodel.tsx` 1,499줄)
| 섹션 | 위치 | 역할 |
|---|---|---|
| ① 업로드 | 610~648 | 파일 업로드·동의 |
| ② 계약 유지/해지 | 776~866 | `companies.map` → 카드 + **해지 체크박스** → `updateContractDecision(idx,{disposition})` |
| ③ 신규 제안 | 868~1089 | 제안서 슬롯 |
| ④ 특약별 비교 | 1093~1367 | 요약 지표 3종 + 종합비교/Y/N + 대분류 요약 + **담보별 표**(`comparisonGroups`) |
| ⑤ 회사별 세부 | 1369~1491 | **40행×N열 매트릭스**(`by_company`) — 담보 열 이미 sticky |

- 상태 단일 흐름: `decisions` → `recalculateAfter()` → `buildAfterResult(result, decisions, proposals)` → `afterResult`.
  `decisions` 변경 시 `setAfterResult(null)`(재계산 유도). ★이 흐름을 그대로 쓴다 — UI만 교체한다.
- 1단 재료: `afterResult.comparison.premium`(before_monthly·after_monthly·delta_monthly·delta_paid_total).
- 2단 재료: `comparisonGroups`(kb_name·before_value·after_value·delta_value) + `after.before.coverages[].by_company`.
- 3단 재료: ⑤와 동일(`after.before.coverages` × `after.before.companies`).

### 시안 실측 (Desktop `보험핏 모바일 PWA (오프라인).html` · ★레포 이동 0)
- 2단 문구: "담보 8개 요약 행 — 현재/리모델링 2열만. 탭하면 그 담보의 계약별 내역이 아래로 펼쳐짐(가로 스크롤 없음)."
- 시안 `coverDefs` 8개: 암진단비(일반암) / 뇌혈관질환진단비 / 허혈성심장질환진단비 / 질병수술비(1~5종) /
  실손의료비 / 질병입원일당 / 질병후유장해(3~100%) / 일반사망.

### ★전제 반전 — "8개 kb_name 상수화"는 실데이터에서 깨진다
실 PDF 2건에서 정본 `kb_name`을 뽑아 시안 8개와 대조한 결과:

| 시안 담보 | 표준 B(46행) | overview E(54행) |
|---|---|---|
| 암진단비 | `암진단금` ✓ | `암진단금` ✓ |
| 뇌혈관질환진단비 | **없음**(대신 `뇌졸중`·`뇌출혈`) | `뇌혈관질환` ✓ |
| 허혈성심장질환진단비 | **없음**(대신 `급성심근경색`) | `허혈성심장질환` ✓ |
| 질병수술비 | `질병수술` ✓ | `질병수술` ✓ |
| **실손의료비** | **없음** | **없음** |
| 질병입원일당 | `질병입원` ✓ | `질병입원` ✓ |
| 질병후유장해 | **없음**(`80%이상 후유장해`뿐) | `질병후유장해` ✓ |
| 일반사망 | `질병사망`·`상해사망`(분리) | `질병사망`·`상해사망`(분리) |

→ 시안 이름을 그대로 상수화하면 **문서에 따라 8칸 중 3~4칸이 빈 행**이 된다.
**보강 설계(취지 우선)**: 8개를 고정 이름이 아니라 **슬롯(의미 단위) + 후보 kb_name 배열**로 정의하고,
문서에 실재하는 첫 후보를 채택한다. 채워지지 않은 슬롯은 **가입 담보 중 [후] 금액이 큰 순**으로 보충해
항상 8행을 채운다. 표시 이름은 **실제 `kb_name`**을 쓴다(설계사가 원문서와 대조하는 화면이므로).
※ 슬롯·후보 목록은 `coverageMobileSlots.ts` 한 곳에 두어 추후 변경이 쉽다(명세의 "상수화" 취지 유지).

### ★반응형 분기 방식 — CSS가 아니라 JS 분기
`md:hidden` / `hidden md:block`으로 하면 **양쪽 마크업이 모두 DOM에 남아** 데스크톱 노드 수가 늘어난다
(제1원칙 위반). `useIsMobile()`(matchMedia `max-width: 767px`)로 **한쪽만 렌더**한다.
matchMedia가 없는 환경(jsdom 등)은 **데스크톱으로 폴백**해 기존 경로가 기본값이 되게 한다.

## 구현
1. `src/components/mobile/coverageMobileSlots.ts` — 슬롯 8종 + `pickKeyCoverages()`(순수 함수).
2. `src/components/mobile/useIsMobile.ts` — matchMedia 훅(SSR·테스트 안전).
3. `src/components/mobile/CoverageMobileView.tsx` — **1단** 월납 전/후·차액·총납입 차액·20년 차액·증감 수,
   **2단** 담보 8행([전]/[후])+계약별 세로 아코디언, **3단** 전체화면 시트(첫 열 고정+가로 스크롤)를 함께 정의.
4. `src/components/mobile/CoverageContractCards.tsx` — 265 `SwipeActionCard` 적용(좌 해지·우 복원·
   임계 72px·회색 면+취소선) + `showUndoToast` 6초 되돌리기.
5. `CoverageRemodel.tsx` — ②와 ④⑤ 자리에 **모바일일 때만** 위 컴포넌트를 렌더(데스크톱 경로 무변경).

## 수정 금지
backend 무접촉 · 집계/파서/carry 로직 변경 0 · 데스크톱 렌더 경로 변경 0 · export 동선 변경 0(268) ·
시안 파일 레포 이동 금지.

## 검증 결과 (1차 · 2026-08-01 · Windows 로컬)

- [x] ★**데스크톱 회귀 0 — HEAD 대비 실렌더 증명**. `git show HEAD:src/pages/CoverageRemodel.tsx`로 265 시점
      사본을 꺼내 **같은 동선(동의→업로드→전후 비교 계산)을 태우고 두 버전의 `innerHTML`과 노드 수를 직접 대조**했다.
      ①초기 결과 화면 ②계약 해지 토글 후 — **둘 다 완전 일치**(노드 수 동일·마크업 문자열 동일).
      빈 화면 비교로 통과하는 것을 막기 위해 노드 수 >200과 ⑤ 섹션 문구 존재도 함께 단언했다.
      ※이 대조는 **일회성**으로 수행하고 사본·스크립트는 삭제했다(레포 잔재 0).
- [x] ★**모바일 = 데스크톱 값 동등성** — 골든 픽스처 `coverage_after_parity_211.json`로 **해지 0/1/3건** 각각:
      1단 요약(`comparison.premium` 4개 수치 + 20년 차액) · 2단 담보 행(`before_value`/`after_value`) ·
      3단 전체 표(**모든 담보 × 모든 계약의 `by_company` 셀**)를 payload와 1:1 대조. 같은 포맷터를 props로
      주입해 표기까지 동일함을 구조적으로 보장한다.
- [x] 해지 결과 동등성 — 스와이프가 만드는 `decisions`와 데스크톱 체크박스의 `decisions`가 같은 형태이고
      `buildAfterResult` 산출이 동일함을 단언(유지 상태와는 실제로 다름도 함께 확인해 무의미 통과 차단).
- [x] 3단 동작 — 아코디언 개폐·전체 표 개폐·**첫 열 sticky**·★1·2단에 `table`·`overflow-x`·`min-w-[` **0건**.
- [x] 스와이프 — 임계 72px 미만 무효 / 초과 시 `cancel` / 해지 상태 회색 면+취소선+배지 / 우 스와이프 복원 /
      6초 되돌리기(`showUndoToast` scope `cancel-confirm`) / ★스와이프를 모르는 사용자를 위한 동일 동작 버튼 병기.
- [x] `npm test` **190 passed / 25 files**(161 + 신규 **29**) · tsc app/node · lint 클린
- [x] backend `pytest -q` **792 passed, 8 skipped** · ★**`backend/` diff 0**
- [x] 라우트 스모크 **18/18** · `npm run smoke:coverage` **PASS**(정본 2건 기준값 일치) · PII 0
- [x] `build:verify` **343,225 B** — 264·265와 동일 수치 예상 FAIL(248 로컬 껍데기 · 이번 변경과 무관)
- [x] diff 범위 = `src/pages/CoverageRemodel.tsx`(**+71/-1 · 분기 래핑만**) + `src/components/mobile/` 신규 4 +
      테스트 2 + harness. 신규 모바일 구현 파일은 4개이며 backend·집계·파서·carry·export 동선 diff 0.

### 실측으로 드러난 사실 2건(기록)
1. **"대분류별 보장 변화 요약"은 골든 픽스처에서 데스크톱에도 렌더되지 않는다**(`comparisonValueGroups`가 빔).
   처음에 이걸 데스크톱 존재 단언으로 넣었다가 실패해서 확인했고, **모바일 부재 단언도 무의미**해지므로
   양쪽 다 실재하는 `min-w-[680px]` 표 대조로 바꿨다.
2. **모바일에 종합비교(560px)·Y/N(420px) 표는 남는다.** 266 명세 범위 밖(3단 대상은 ④ 담보 표와 ⑤ 매트릭스)이라
   임의로 손대지 않았다. 둘 다 `overflow-x-auto` 안이라 **문서 자체는 넘치지 않고**(263과 같은 판정 기준),
   1,680px처럼 화면을 밀어내는 표는 남아 있지 않음을 테스트로 고정했다.
   → 이 두 블록의 모바일 최적화(12px 폰트 포함)는 **267~ 후속 후보**로 남긴다.

### 로컬에서 못 한 것 (Codex 몫)
- **375/390/430px 실렌더 넘침 측정**: jsdom은 레이아웃을 계산하지 않아 폭을 잴 수 없다. 구조적 근거
  (고정폭 표 0 · 남은 표는 전부 `overflow-x-auto` 래핑)까지만 로컬에서 고정했고, **실측은 프로덕션 브라우저**에서
  263과 같은 방식으로 확인해야 한다.
- 실기기 스와이프 감각(임계 72px가 실제 엄지 조작에 적절한지)은 Human 실사용 확인 대상이다.

## Stage 목록 (Codex용)
`src/pages/CoverageRemodel.tsx`, `src/components/mobile/*`(신규 4), 테스트,
`tasks/BOHUMFIT-266-coverage-mobile.md`, `handoff.md`, `locks.md`

## 커밋 메시지 (Codex용)
feat(BOHUMFIT-266): 보장분석 모바일 3단 점진 공개 + 스와이프 해지

## Next
① **Codex** — 2차 검증(데스크톱 회귀 0·모바일 동등성·375~430px 실렌더·배포 스모크) → 커밋·push
② **Human** — 폰에서 보장분석 실사용(3단 탐색·스와이프 해지·되돌리기)
③ **Chat** — 267(고지 결과 모바일) 발번
