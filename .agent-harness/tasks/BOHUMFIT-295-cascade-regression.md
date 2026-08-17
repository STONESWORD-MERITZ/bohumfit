# BOHUMFIT-295 — 종합비교 케스케이드 회귀 (제안서 없음 케이스)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: **Codex**(2차 검증·커밋) / **Human**(육안 + 결정 2건)
Risk tier: 중 — 표시 계층 1곳. 값 계층·케스케이드 무접촉. git 쓰기 0.
Date: 2026-08-18 · 기준 HEAD `59fca67`(293·294 반영) · 선행 290(Q6 배선)·292 Phase E·293 §1-6

## ★PII (BOHUMFIT-295b/R2)
실명·실파일명은 익명 라벨로 표기한다 — 정본A(표준형)·정본B(overview형, Human 보고 케이스)·정본C(제안서 세트)·정본D(추가 표준형). 신규 테스트는 익명 합성 픽스처다(실 PDF 미의존).

## ★증상 (Human 실사용 보고)
제안서를 **넣지 않은** 분석에서 종합비교가 [전]과 다르게 나온다. 전 월납 = 후 월납(4,675,189)이라
제안서 없음이 확실한데, 뇌 초기·중기·말기 4,000만 → 0, 심장 동일, **암 0 → 1,410만**, Y/N 전부 Y → N.
문서는 overview형(정본B 계열 — "상품별 가입현황 페이지가 없어 전체 보장현황으로 대체").

## ★불변식
**제안서가 없으면 [후] = [전]** — 종합비교·Y/N·담보값 전부.

---

## Step 1 — 재현·원인 특정 (코드 무변경)

### 1-1. 서버 경로는 **정상** — 불변식이 이미 성립한다
`build_after_analysis(analysis, {"existing": [], "proposals": []})`로 정본 4문서(표준형 3·overview형 1)을 돌려
종합 17행·Y/N 5항목·담보 49행+비고·월납을 전수 대조했다.

| 문서 | 형태 | 결과 |
|---|---|---|
| 정본A | 표준형 | ✅ 위반 0 |
| **정본B** | **overview형** | ✅ 위반 0 |
| 정본C | 표준형 | ✅ 위반 0 |
| 정본D | 표준형 | ✅ 위반 0 |

서버 payload는 `before.stage_totals`·`before.yn_flags`와 `after.before.stage_totals`·`after.before.yn_flags`를
**모두** 내려주고, 제안서 0건이면 두 값이 **완전히 동일**하다(정본B(overview형) 실측: 뇌초기/중기/말기 40,000,000 양쪽 동일).
→ ★**케스케이드 배선(290)·산식·49행 스키마에는 결함이 없다.** 회귀는 표시 계층에 있다.

### 1-2. ★원인 — [전]과 [후]의 **계산 소스가 비대칭**이다
`src/pages/CoverageRemodel.tsx` (247 B·D 도입분)
```
beforeStages = result.before.stage_totals ?? computeStageTotals(result.before.coverages)   // 서버 값 우선
afterStages  = computeStageTotals(afterResult.after.before.coverages)                       // ★무조건 클라 재계산
beforeYn     = result.before.yn_flags ?? computeYnFlags(result.before.coverages)            // 서버 값 우선
afterYn      = computeYnFlags(afterResult.after.before.coverages)                           // ★무조건 클라 재계산
```
클라이언트 재계산(`src/lib/coverageAfterDisplayCache.ts`의 `computeStageTotals`·`computeYnFlags`)은
**구 40행 `kb_name`으로 조회**한다(`뇌혈관질환`·`암진단금`·`상해입원의료비` …). 그런데 payload의 담보 이름은
290 이후 **V2 49행 표시명**(`뇌 혈 관 질 환`·`암 진 단 비(일반암)`·`상 해/질 병 입 원`)이다.
→ 이름이 하나도 안 맞아 **재계산 결과가 0**이 된다. [전]은 서버 값을 쓰므로 멀쩡하고, [후]만 무너진다.

### 1-3. 증상 4가지가 **전부 이 하나로 설명된다**
| 증상 | 설명 |
|---|---|
| 뇌·심장 4,000만 → 0 | [전]=서버 `stage_totals["뇌초기"]`=40,000,000 / [후]=클라 재계산에서 구 이름 미스 → 0 |
| ★**암 0 → 1,410만** | [전]=서버 17키에 구 키 `"암"`이 **없어서** 0(290이 3단→17행으로 교체). [후]=클라 재계산이 `STAGE_COMPONENTS["암"]` 원천 중 **`항암약물방사선`만 매칭**(292 Phase E가 결합 담보를 **구 이름 그대로 비고행**에 보존 → 이름이 우연히 일치) → overview형 비고행 값 **14,100,000**이 그대로 나온다. Human이 본 1,410만과 정확히 일치 |
| Y/N 전부 Y → N | [전]=서버 `yn_flags`(Y) / [후]=클라 재계산이 구 원천명(`상해입원의료비` 등) 조회 실패 → 전부 N |
| 월납은 전=후 | 월납은 재계산 경로를 타지 않는다 — 그래서 "제안서 없음"이 확실한데 값만 틀린 모양이 됐다 |

### 1-4. 왜 290 Q6 대조표가 못 잡았나
290은 [전]·[후]를 **각각** 검증했고 **서버 값만** 봤다. 프런트가 [후]를 따로 재계산한다는 사실과
"제안서 0건 → [후]==[전]"이라는 불변식은 검증 대상이 아니었다. 293 §1-6이 "프런트가 구 축 미러를
갖고 있다(층위 3)"고 기록했는데, 그 미러가 **표시 정렬용만이 아니라 [후] 계산에도 쓰이고 있었던** 것이다.

### 1-5. ★함정 — `afterResult`는 **항상 클라이언트 계산**이다
`CoverageRemodel`의 `afterResult`는 서버 응답이 아니라 **`buildAfterResult`(순수 클라이언트 · 182 D-11
"네트워크 호출 0")** 결과다. 그리고 그 안의 `afterBefore = { ...analysis.before, coverages: afterCoverages }`가
**[전]의 파생값(`stage_totals`·`yn_flags`)을 그대로 복사**한다(254·272가 지목한 스프레드 경로).
→ 따라서 "[후]도 payload 값을 우선 쓰게" 하는 것만으로는 부족하다. **제안서·해지가 있을 때 [전] 값이
  [후]인 척 표시되는 새 결함**이 생긴다. 수정은 이 stale 판정까지 함께 해야 한다(Step 2).

### 1-6. 범위 밖에서 함께 드러난 사실 (수정하지 않고 기록)
① **프런트가 V2 스키마를 모른다** — 클라 타입 `BeforeCoverage`에 `row_id`도 `sources`도 없다. 그래서 클라 미러가
[후]를 **정확히** 재산출하는 것은 층위 3(프런트 V2 이관) 없이는 불가능하다. 295는 그 이관을 하지 않는다.

② **총납입(`paid_total`) 산식 불일치** — [전] `aggregator._paid`는 일시납을 개월 수로 곱하지 않지만(234 결정:
표기 금액이 1회 납입 총액) [후] `compare._paid_total`은 `월납 × 개월`을 그대로 쓴다. 일시납 계약이 있는
표준형 문서에서 126,083,040 vs 144,647,520로 갈린다. **제안서·해지와 무관한 상시 차이**이고 이번 회귀와 별개다.
산식을 맞추면 값 계층이 바뀌므로 **Human 결정 사안**(295는 불변식 단언에서 제외하고 사유를 테스트에 남겼다).

③ 화면 표시 축 `CoverageInsightBlocks.STAGE_ROWS`는 **구 7키**(암·뇌초기·뇌중기·뇌말기·심장초기·심장중기·심장말기)인데
서버는 **17키**(뇌 3 + 심장 2 + 암 계열 12)를 준다. 겹치는 키는 뇌 3·심장 2뿐이라
**`암`·`심장말기`는 [전]에서도 이미 0으로 표시**되고 있다(이번 회귀와 별개인 **층위 3 미이관 잔재**).
→ 295는 불변식([후]==[전])만 복원한다. 구 7키 → 17키 표시 이관은 **별도 태스크**(Human 결정 항목).

---

## Step 2 — 수정

### 수정 2가지 — 둘 다 "비대칭·stale 제거"이고, 방어를 흩지 않는다

**(a) 표시 선택을 헬퍼 하나로 합쳐 [전]·[후]를 대칭화** (`coverageAfterDisplayCache.ts` 신설 `displayStageTotals`·
`displayYnFlags`, `CoverageRemodel.tsx`가 양쪽에 같은 함수 호출)
```
displayStageTotals(payload) = payload.stage_totals ?? computeStageTotals(payload.coverages)
```
종전에는 [전]만 이 규칙이었고 [후]는 무조건 재산출이었다. ★규칙을 **한 곳에 두어** 비대칭이 재발할 수 없게 했다
(useMemo에 규칙을 두 번 쓰면 또 갈라진다 — 뮤테이션 테스트로 확인).

**(b) stale 파생값 판정** (`buildAfterResult`의 `afterBefore` 조립 1곳)
파생값은 `coverages`에서 나오므로 **입력이 그대로면 유효하고 바뀌면 stale**이다. 이 판정을 한 번만 한다.
- 해지 0·제안 0 → [전] 파생값 유지 → **[후] == [전]**(불변식 복원)
- 해지/제안 있음 → **stale 값을 지운다.** 조용히 [전] 값을 [후]인 척 보여주지 않는다(폴백 미러로 떨어진다 —
  정확한 [후] 재산출은 §1-6 ①의 층위 3 이관에서 해결하며, **이번 변경으로 나빠지지 않는다**)

공통:
- 집계 산식·케스케이드 정의·49행 스키마·**서버 코드는 한 줄도 바꾸지 않는다**(서버는 이미 정확하다 — §1-1).
- 클라 미러는 **구 payload 폴백으로 남긴다**(247 패리티 계약 · `stage_totals` 없는 과거 저장분).
- 암 +1,410만은 별도 차단 로직 없이 사라진다 — 비고행이 체인에 유입되던 통로가 **클라 미러 재산출 자체**였다.

---

## Step 3 — 불변식 테스트

### 서버 (`backend/tests/test_no_proposal_invariant_295.py` · 신설 6건 · ★295b/R2로 익명 합성 전환)
제안서 0건·해지 0이면 **종합 17행 · Y/N 5항목 · 담보 49행+비고 · 월납 · payload 파생값이 전부 동일**함을
정본 2(표준형·overview형) + 정본C + 정본D 실문서로 고정(4문서 × 2 + 2). 비고행이 `stage_totals` 체인에
유입 0, overview형 결합 담보 1,410만이 어떤 체인에도 없음, 제안서가 있으면 정상적으로 달라짐도 함께 단언.
★총납입은 §1-6 ②의 별개 산식 불일치라 이 불변식에서 제외하고 사유를 테스트 주석에 남겼다.

### 프런트 (`src/lib/coverageNewTaxonomyDisplay.test.ts` · 신규 4건)
- 제안서·해지 0이면 [후] 파생값 == [전] · ★같은 픽스처에서 **구 이름 미러는 뇌 0 · 암 1,410만**임을 함께 단언해
  회귀를 재현하고, 화면이 그 오염을 쓰지 않음을 확인
- 해지가 있으면 stale 파생값이 **지워진다**
- ★표시 선택 헬퍼로 [전]·[후]가 동일(비대칭 재발 시 실패)
- `stage_totals`가 없는 **구 payload**는 종전대로 클라 미러 폴백(하위호환)

### ★뮤테이션으로 검출력 확인 (테스트가 장식이 아님)
| 되돌린 결함 | 결과 |
|---|---|
| stale 판정 제거(스프레드 그대로) | ✅ 실패 검출 |
| 표시 헬퍼를 무조건 재산출로(=회귀 재현) | ✅ 실패 검출 |
주입분은 전부 되돌렸고 최종 diff에 남지 않았다. ※1차 시도 때는 `CoverageRemodel`의 useMemo를 되돌려도
**아무 테스트도 잡지 못했다** — 그래서 선택 로직을 헬퍼로 뽑아 테스트 가능하게 만들었다(위 (a)).

### 제안서 있을 때 무회귀
정본C 3제안서로 292 결과(뇌·심장 수술비 1,300만 등)가 그대로인지 확인.

---

## 검증 (1차 · 2026-08-18 · Windows 로컬)
- [x] ★★제안서 0건: 종합 17행·Y/N·담보 49행·월납 전부 [후]==[전] — 정본 4문서(표준형 3·overview형 1) **위반 0**
- [x] ★암 +1,410만 소거 · 비고행이 stage 체인에 유입 0(서버 `row_id` 기반 · 테스트 고정)
- [x] 제안서 3건(정본C) 292 결과 무회귀
- [x] overview형(정본B)·표준형(정본A) 양쪽 통과
- [x] `cd backend && python -m pytest -q` — **1058 passed, 8 skipped**(1052 + 합성 6 · 회귀 0)
- [x] `npm test` **412 passed / 42 files**(406 + 295 파생 4 + 295b 배선 2) · tsc app/node · lint 무경고
- [x] `npm run smoke:coverage` **PASS — 기준값 무변경**(정본 불변 · 갱신 0)
- [x] `build:verify` 예상 FAIL(248)
- [x] 엑셀·PDF 산출물 **해시 12종(4문서 × 엑셀·HTML·payload) 완전 동일** — 293 기준 해시와 재대조(산출물 무영향)
- [x] 케스케이드 상수(289)·`compute_stage_totals`(290)·49행 스키마·`backend/coverage/`·`backend/pipeline/`·
      `filters.py`·`backend/main.py`·`vite.config` **diff 0** — ★**백엔드 전체 diff 0**(수정은 프런트 2파일)

## ★Human 결정 필요
1. **구 7키 → 17키 표시 이관 + 프런트 V2 이관(층위 3)** — §1-6 ①③. 화면 종합비교 표가 아직 구 7키라 `암`·`심장말기`가
[전]에서도 0으로 보인다(이번 회귀와 별개인 미이관 잔재). 서버는 17키를 이미 준다.
이관하면 암 계열 12행이 화면에 제대로 보이고, **제안서가 있을 때의 [후] 종합비교도 정확해진다**(295는
제안서 0건 케이스만 복원했다). 293이 기록한 층위 3 태스크와 같은 뿌리다.
2. **총납입 산식 불일치** — §1-6 ②. [전]은 일시납 미곱(234), [후]는 곱함. 맞추면 값이 바뀌므로 승인이 필요하다.

## Stage 목록 (Codex용)
`src/lib/coverageAfterDisplayCache.ts`(stale 판정 + 표시 헬퍼) · `src/pages/CoverageRemodel.tsx`(헬퍼 호출) ·
`backend/tests/test_no_proposal_invariant_295.py`(신설) ·
`src/lib/coverageNewTaxonomyDisplay.test.ts`(신규 4건) · `tasks/BOHUMFIT-295-cascade-regression.md` ·
`handoff.md` · `locks.md`
※제외: 실 PDF·PII·산출물

## 커밋 메시지 (Codex용)
fix(BOHUMFIT-295): 제안서 없음 케이스 종합비교 회귀 — [후]==[전] 불변식 복원
