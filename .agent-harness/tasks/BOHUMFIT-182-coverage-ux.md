# BOHUMFIT-182 — 보장분석 UX 2건 (해지 즉시 미리보기 · 합계형 문서 배너)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Claude Code (구현·1차 검증)
Risk tier: 중위험(S 규모 2건) — git 쓰기 금지(커밋 Codex).
Date: 2026-08-02 · 기준 HEAD `96f2b54`(268a)

## 배경 (262 결정지 확정)
- **D-11 ①** 해지 체크 즉시 delta 미리보기 — 재계산이 클라이언트 계산이라 버튼 경유 이유가 없다.
- **D-12 ①** overview(합계형) 문서 경고를 상단 warning 나열에서 분리해 **전용 배너**로 승격.

## Step 1 — 현행 실측 (코드 무변경)

### 해지 → delta 데이터 흐름
`체크박스 onChange` → `updateContractDecision(idx, {disposition})`(`CoverageRemodel.tsx:361`)
→ `setDecisions(...)` + **`setAfterResult(null)`**(결과를 지워 "다시 계산하세요" 상태로 만든다)
→ 사용자가 **"전후 비교 계산"** 버튼 클릭 → `recalculateAfter()`(531행)
→ `setAfterResult(buildAfterResult(result, decisions, proposals))`.

### ★D-11 진행 가능 여부 판정 — **서버 왕복 없음(진행 가능)**
`src/lib/coverageAfterDisplayCache.ts` 전수 확인 결과 `fetch`·`axios`·`XMLHttpRequest`·`await`
**0건** — `buildAfterResult`는 **순수 클라이언트 계산**이다.
→ 매 체크마다 요청을 유발하지 않으므로 패킷의 중단 조건(서버 왕복)에 **해당하지 않는다**. 그대로 진행한다.

### overview 경고의 현재 위치·조건
`coverageAfterDisplayCache.ts:647~656` — 조건은 **259에서 정밀화된 두 항**:
1. `plan.existing.some(e => e.disposition === "cancel")` (해지 요청이 있고)
2. `analysis.before.coverages.some(c => c.overview && !isAttributedRow(c))` (**미귀속** overview 행이 있을 때)
   ※`isAttributedRow`(478행)는 `by_company`에 값이 하나라도 있으면 귀속으로 본다 — 256~258로 귀속된
   overview 행은 해지가 회사 단위로 반영되므로 경고 대상이 **아니다**(서버 `overview_rows_need_cancel_warning`과 동일).
→ 조건을 만족하면 `comparison.cautions`에 push되고, 화면에서는 `specialNotes`(warnings + cautions +
improvements를 합쳐 중복 제거)에 섞여 `SpecialNotes` 목록으로 나열된다.

## Step 2 — D-11 해지 즉시 미리보기
- `updateContractDecision`에서 **다음 decisions를 만들어 그 자리에서 `buildAfterResult`를 호출**한다
  (`setAfterResult(null)` → 즉시 결과 세팅). 산식·인자는 버튼 경로와 **완전히 동일**하다.
- ★**"전후 비교 계산" 버튼은 그대로 둔다**(데스크톱 동선 변경 금지). 같은 함수를 부르므로 결과도 같다.
- **제안서(proposals) 편집은 기존대로 버튼 경유** — 매 키 입력 재계산은 D-11 범위 밖이고 이득도 없다.
- 중복 계산: 토글 1회 = 순수 계산 1회이므로 디바운스가 필요 없다(입력 폭주 경로가 아니다).
  대신 **같은 입력이면 같은 결과**임을 테스트로 고정한다.

## Step 3 — D-12 합계형 문서 전용 배너
- 경고 문구를 `coverageAfterDisplayCache.ts`에 **상수(`OVERVIEW_CANCEL_CAUTION`)로 뽑아** push 지점과
  화면이 같은 값을 참조한다 — ★조건식·문구 **변경 0**, 식별을 위한 신설 조건 **0**.
- 화면은 `cautions`에서 그 상수와 일치하는 항목을 찾아 **전용 배너**로 올리고, `specialNotes` 나열에서는 제외한다.
- 표준형 문서(미귀속 overview 행 없음)에서는 애초에 push되지 않으므로 배너도 뜨지 않는다.

## Step 4 — 모바일
`useIsMobile` 분기는 **새로 만들지 않는다** — 이번은 기능 추가지 모바일 개편이 아니다.
배너·delta는 모바일 3단 뷰(266)와 데스크톱 양쪽에서 자연스럽게 흐르도록 폭 고정 없이 구성한다.

## 검증 결과 (1차 · 2026-08-02 · Windows 로컬)

- [x] `npx tsc -p tsconfig.app.json --noEmit` **PASS** · `tsconfig.node.json` **PASS**
- [x] `npm run lint` **PASS**
- [x] `npm test` **227 passed / 28 files**(기준선 217 + 신규 **10**) · 회귀 0
- [x] backend `python -m pytest -q` **792 passed, 8 skipped**(불변) · ★**`backend/` diff 0**
- [x] `npm run smoke:coverage` **PASS** — 표준(604,560,000·681,312)·overview(1,542,990,000·4,675,189)
      **기준값·불변식(회사합=합계 0·전=후 0) 그대로**. ★이번 태스크의 핵심 가드가 통과했다.
- [x] `npm run build:verify` **343,225 B 예상 FAIL**(248 로컬 껍데기 — 264~268a와 동일 수치)
- [x] ★**데스크톱 회귀 0**(HEAD 사본 대비 실렌더): ①**해지 미체크 초기 상태** `innerHTML`·노드 수 **완전 일치**
      ②★**버튼 경유 결과 화면도 완전 일치** — 산식·표시가 바뀌지 않았음을 함께 증명했다.
      빈 화면 오통과 방지 마커(`전후 비교 계산`·`② 컨설팅 전 계약`·`⑤` 섹션) 포함. 사본·스크립트는 **삭제**.
- [x] ★**즉시 반영 == 버튼 경유** — 같은 조작 후 두 경로의 **`innerHTML` 전체가 동일**함을 대조(테스트 고정).
      payload 레벨에서도 `buildAfterResult` 동일 인자 → 동일 결과를 단언했고, 유지 상태와는 실제로 다름도 확인해
      무의미 통과를 막았다.
- [x] 표준형 문서에서 배너 미표시 · ★**귀속된 overview 행은 배너 대상 아님**(259 조건 그대로) ·
      해지가 없으면 배너 없음(조건 ①) · 배너에 폭 고정·표 없음(가로 넘침 방지)
- [x] `vite.config.*` diff **0** · 고지의무 화면·268a 업로드 경로·265 캐시 로직 diff **0**
- [x] diff 범위 = `src/pages/CoverageRemodel.tsx`(+45/-13 상당) · `src/lib/coverageAfterDisplayCache.ts`
      (**문구 상수화 +주석뿐** — 조건식·문구 문자열 자체는 무변경) · 테스트 1 + harness

### 구현 요약
- **D-11**: `updateContractDecision`이 다음 `decisions`를 만들어 **그 자리에서 `buildAfterResult`를 호출**한다.
  기존에는 `setAfterResult(null)`로 결과를 지워 사용자가 버튼을 눌러야 했다. 버튼은 **그대로 남겨** 데스크톱
  동선을 바꾸지 않았고, 같은 함수·같은 인자를 부르므로 결과가 갈라질 수 없다.
- **D-12**: 경고 문구를 `OVERVIEW_CANCEL_CAUTION` 상수로 뽑아 push 지점과 화면이 같은 값을 참조한다.
  화면은 `cautions`에서 그 항목을 찾아 **전용 배너**로 올리고 `specialNotes` 나열에서는 제외한다.

### 판단 기록
- **디바운스를 넣지 않았다.** 체크박스 토글은 사용자 클릭당 1회이고 `buildAfterResult`는 순수 계산이라
  입력 폭주 경로가 아니다. 대신 **연속 토글(해지→복원→해지) 후 첫 해지 상태와 마크업이 같음**을 테스트로 고정해
  상태 누적 오류가 없음을 보장했다.
- **제안서(proposals) 편집은 기존대로 버튼 경유**로 뒀다. 매 키 입력 재계산은 D-11 범위가 아니고 이득도 없다.
- 모바일 전용 레이아웃은 신설하지 않았다(패킷 Step 4 지시) — 배너·delta는 266 모바일 3단 뷰와 데스크톱
  양쪽에서 폭 고정 없이 흐른다.

### 로컬에서 못 한 것 (Codex 몫)
- **375/390/430px 실렌더 넘침 측정** — jsdom은 레이아웃을 계산하지 않는다. 배너에 폭 고정·표가 없음까지만
  구조적으로 고정했고 실측은 프로덕션 브라우저 몫이다.
- 실사용에서 해지 토글 반응 체감(즉시 반영이 실제로 끊김 없이 보이는지).

## Stage 목록 (Codex용)
`src/pages/CoverageRemodel.tsx`, `src/lib/coverageAfterDisplayCache.ts`(문구 상수화), 테스트,
`tasks/BOHUMFIT-182-coverage-ux.md`, `handoff.md`, `locks.md`
※제외: 실 PDF·PII·엑셀 원본·시안 HTML·렌더 산출물

## 커밋 메시지 (Codex용)
feat(BOHUMFIT-182): 보장분석 해지 즉시 미리보기 + 합계형 문서 전용 배너
