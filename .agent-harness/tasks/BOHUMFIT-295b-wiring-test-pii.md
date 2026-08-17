# BOHUMFIT-295b — 295 반려 보정: 화면 배선 회귀 테스트 + PII 익명화

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: **Codex**(2차 재검증·커밋) / **Human**(육안 + 295 결정 2건 승계)
Risk tier: 중 — 테스트·문서·PII. 제품 로직 무변경(295 위에 보정). git 쓰기 0.
Date: 2026-08-18 · 기준 HEAD `59fca67` · ★295 미커밋분 위에 보정(되돌리지 않음) · 295+295b 합쳐 커밋

## ★상황
295 구현이 워킹트리 미커밋인 채 Codex 2차 검증에서 **2건으로 반려**됐다. 295를 되돌리지 않고 그 위에 보정한다.

## 반려 사유 2건 (Codex 기록)
- **R1 — 화면 배선 회귀 뮤테이션 미검출** ★최우선: `CoverageRemodel`의 네 useMemo를 **종전 비대칭 구현으로
  되돌려도** 전체 `npm test`가 `410 passed`로 통과. 295가 만든 헬퍼(`displayStageTotals`·`displayYnFlags`)는
  테스트되지만 **컴포넌트가 그 헬퍼를 실제로 쓰는지(배선)**는 검증되지 않았다. 295가 고친 결함이 정확히
  "배선 비대칭"인데 그 재발을 막는 테스트가 없었다.
- **R2 — PII 0 위반**: 신규 `test_no_proposal_invariant_295.py`와 태스크 문서에 실명·실파일명이 남아 있다.

---

## Step 1 — R1 재현 (코드 무변경)

### 1-1. ★반려 재현 확인 — 직접 실행
Codex 절차대로 `CoverageRemodel`의 네 useMemo를 종전 비대칭([후]=구 미러 강제 재산출)으로 되돌리고
전체 테스트를 돌렸다 → **`Test Files 41 passed / Tests 410 passed`**. 반려가 정확하다.

### 1-2. 현행 테스트가 검증하는 것 / 놓치는 것
| 대상 | 상태 |
|---|---|
| 헬퍼 **로직**(`displayStageTotals`가 payload 값 우선·폴백) | ✅ 검증됨(`coverageNewTaxonomyDisplay.test.ts`) |
| `buildAfterResult`의 stale 판정 | ✅ 검증됨(같은 파일) |
| **컴포넌트 → 헬퍼 배선**(useMemo가 그 헬퍼를 실제로 호출) | ❌ **미검증** ← R1 |
헬퍼는 순수 함수라 단위 테스트가 쉽지만, 컴포넌트가 그것을 **안 쓰고** 직접 재산출해도 헬퍼 테스트는 통과한다.

### 1-3. 배선 검증 방법 선택 (사유)
| 후보 | 판단 |
|---|---|
| 헬퍼 스파이(`vi.spyOn`) | 호출 여부만 봄 — "결과가 화면에 맞게 나오는지"를 못 잡는다. 약함 |
| **컴포넌트 렌더 후 실제 표시 셀 단언** | ★채택 — 배선이 깨지면 [후] 셀이 실제로 0/N이 되어 실패. 사용자가 보는 것과 동일 |
| 렌더 스냅샷 대조 | 취약(무관 변경에 깨짐)·회귀 원인이 안 드러남. 미채택 |
→ ★**컴포넌트를 실제 렌더**해 종합비교·Y/N **표시 셀 텍스트**를 단언한다(헬퍼 단위 테스트로 대체 불가).

### 1-4. ★회귀가 렌더 테스트로 드러나는 조건 (픽스처 설계)
기존 렌더 테스트(182)가 R1을 못 잡은 이유: 골든 픽스처(211)가 **구 40행 이름 + 파생값 없음**이라
[전]·[후] **둘 다** 폴백 미러를 타서 비대칭이 드러나지 않는다.
→ 재현 픽스처는 **V2 표시명 담보 + 서버 `stage_totals`·`yn_flags` 존재**여야 한다. 그러면
  대칭 배선: [후]=서버 값(=[전]) / 비대칭 배선: [후]=구 미러가 V2 이름 미스 → **0/N**. 차이가 렌더에 나타난다.

---

## Step 2 — R1 배선 회귀 테스트 (신설 `src/pages/CoverageRemodelWiring295.test.tsx`)
`CoverageRemodel`을 **실제 렌더**(기존 182 하네스 재사용 — `stubAnalyze`·업로드 동선)하고 `data-testid`
(`stage-comparison`·`yn-flags`) 표의 셀을 읽어 단언한다.
- **제안서·해지 0**: "뇌 초기"·"심장 초기" 행 [후] 셀 == [전] 셀(4,000만원, 0원 아님) · "암" 행 [전]=[후]=0원
  (회귀 때 [후]에 결합 담보 값이 들어왔었다) · 실손 Y/N 2항목 [전]=[후]=Y.
- **해지 有**: 계약 1 해지 → [후] "뇌 초기"가 [전]의 **복사가 아니다**(stale 판정으로 파생값 버려짐 → 0원).
- ★`→` 셀이 `aria-hidden`이라 접근성 트리에서 빠지는 점을 실측해 셀 인덱스를 맞췄다(cells=[라벨,전,후,개선]).

### ★뮤테이션 3종 — 각각 이 배선 테스트를 실패시킴 (실증 완료)
| 되돌린 결함 | 배선 테스트 결과 |
|---|---|
| ① `CoverageRemodel` 네 useMemo를 종전 비대칭으로 (=R1 그 자체) | ✅ 실패 검출(불변식 테스트) |
| ② 헬퍼(`displayStageTotals`)를 무조건 재산출로 | ✅ 실패 검출(불변식·해지 둘 다) |
| ③ `buildAfterResult` stale 판정 제거(스프레드 그대로) | ✅ 실패 검출(해지 테스트) |
주입분은 전부 원복했고 워킹트리에 잔재 없음(제품 소스 diff = 295 정본 그대로 재확인). ★295 반려의 "410 통과"
구멍이 이 테스트로 닫혔다(뮤테이션 ①이 이제 실패한다).

---

## Step 3 — R2 PII 익명화
- **신규 배선 테스트**: 익명 합성(담보 V2 표시명·회사 idx만 · 인물·실파일명 0). 골든 픽스처(211)에서 shape만
  빌리고 값은 합성으로 교체.
- **서버 불변식 테스트 전면 익명 합성 전환**: 실 PDF 4문서 로드(실명 파일명) → 290 `_raw` 선례의 익명 합성
  (`build_before`→`build_after_analysis`)으로 교체. 실 PDF·실명 미의존 → **재현성·robustness도 향상**
  (gitignore 폴더 존재에 안 기댄다). 10건 실문서 파라미터 → 6건 합성(표준형·overview형 2형태 + 결합 비고행 + 제안서).
- **소스 주석**: `CoverageRemodel.tsx`의 실명 1건 → 익명 표현(`overview형 문서의 비고행`).
- **태스크 문서 295·295b**: 실명 → 익명 라벨(정본A 표준형·정본B overview형·정본C 제안서 세트·정본D 추가 표준형).
- ★**전수 확인**: `git diff` 추가 줄 + 신규 파일 전체에서 실 고객명·실파일명(입력 PDF·제안서 파일명)·주민번호·
  연락처 패턴을 grep으로 스캔 → **0건**(스캔 대상 실명 목록은 이 문서에 나열하지 않는다 — 그 자체가 PII다).

### 범위 밖 — 기록만 (기존 커밋분)
`backend/tests/`의 **기존** 5파일(276b·286·290·291·292)에 실명·실파일명이 있으나 **295 이전 커밋분**이라
295b 범위(=295 반려 보정) 밖이다. 백엔드 값 계층 diff 0 계약도 있어 이번에 건드리지 않는다.
→ **별도 PII 정리 태스크**로 기록(Human/Chat 판단). ※CLAUDE.md 관례상 태스크 문서·handoff의 고객명은
  허용이나, **테스트 소스**의 PII 0은 별개 계약이라 향후 일괄 정리 대상이다.

---

## Step 4 — verify.md 표준 보강
"회귀 수정 태스크는 결함이 있던 **그 지점**에 뮤테이션을 심는다. 추출한 헬퍼의 로직 테스트는 배선 회귀를
검출하지 못한다(295 선례 — 컴포넌트를 종전 구현으로 되돌려도 410 passed 통과). 컴포넌트 렌더 결과를
단언하는 테스트가 필요하다." — verify.md에 반영.

---

## 검증 (2026-08-18 · Windows 로컬)
- [x] ★★**뮤테이션 3종 전부 검출**(종전 useMemo 되돌림 포함) · 원복 후 제품 소스 diff = 295 정본
- [x] ★`git diff` 추가 줄 + 신규 파일 실명·실파일명·주민번호·연락처 **0건**
- [x] 295 불변식 유지: 제안서 0건 → [후]==[전] (배선 테스트가 렌더로 고정)
- [x] 제안서/해지 있을 때 [후]가 [전] 복사 아님(배선 테스트 2번째 케이스)
- [x] `backend/` 값 계층 diff 0(변경 = 신규 테스트 1파일뿐) · 산출물 해시 **12종 293 기준 동일**
- [x] `npm run smoke:coverage` PASS(기준값 무변경)
- [x] `cd backend && python -m pytest -q` — **1058 passed, 8 skipped**(1052 + 합성 6 · 회귀 0)
- [x] `npm test` **412 passed / 42 files**(406 + 295 파생 4 + 295b 배선 2) · tsc app/node · lint 무경고
- [x] `build:verify` 예상 FAIL(248)
- [x] 케스케이드·`compute_stage_totals`·49행 스키마·`pipeline/`·`filters.py`·`vite.config` diff 0

## Human 결정 (295 승계 — 변동 없음)
1. 층위 3(프런트 V2 이관 + 구 7키 → 17키) — 제안서가 있을 때의 [후] 종합비교 정확도는 그 태스크에서 해결.
2. 총납입 산식 불일치([전] 일시납 미곱 234 / [후] 곱함) — 값 계층 변경이라 승인 필요.

## Stage 목록 (Codex용 · 295 + 295b 합쳐 커밋)
`src/lib/coverageAfterDisplayCache.ts`·`src/pages/CoverageRemodel.tsx`(295 헬퍼·stale + 295b 소스 주석 익명화) ·
`src/pages/CoverageRemodelWiring295.test.tsx`(신설) · `src/lib/coverageNewTaxonomyDisplay.test.ts`(295 신규 4) ·
`backend/tests/test_no_proposal_invariant_295.py`(익명 합성) · `tasks/BOHUMFIT-295-cascade-regression.md`·
`tasks/BOHUMFIT-295b-wiring-test-pii.md` · `.agent-harness/verify.md` · `handoff.md` · `locks.md`
※제외: 실 PDF·PII·수기 엑셀·산출물

## 커밋 메시지 (Codex용)
fix(BOHUMFIT-295): 제안서 없음 케이스 종합비교 회귀 — 표시 대칭화·stale 판정·배선 회귀 테스트
