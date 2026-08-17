# BOHUMFIT-293 — 층위 2 정리: 구 40행 제거·서식 회귀 테스트·잔재 스캔

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: **Codex**(2차 검증·커밋) / **Human**(결정 1건 — 층위 3 발주 여부)
Risk tier: 중 — 제거는 넓으나 **값·양식 무변경**(산출물 해시 12종 동일로 증명). git 쓰기 0.
Date: 2026-08-18 · 기준 HEAD `6efce30`(292 반영) · 선행 286~292

## ★이 태스크의 성격
286~292로 49행 V2가 완전히 배선·산출됐다. S1에서 롤백 여지로 남겨둔 구 40행 상수와 전환기 잔재를 걷어내고,
291에서 실제로 발생한 **서식 회귀**(261 차액 색상이 양식 이식 중 조용히 누락 → Codex 2차 검증에서 발견) 유형을
테스트로 막는다. **값·양식은 한 셀도 바뀌지 않는다.**

---

## Step 1 — 잔재 스캔 (코드 무변경)

### 1-1. ★핵심 발견 — 구 40행 상수는 **두 역할을 겸하고 있었다**
`KB_COVERAGES`를 "구 양식 40행"으로만 보면 통째로 지울 것 같지만, 실측하면 살아 있는 소비처가 있다.

| 역할 | 소비처(실측) | 생사 |
|---|---|---|
| ① **산출물 양식 40행** | 291에서 export가 49행으로 전환되며 참조 0 | **죽음** |
| ② **KB 원문 담보명 사전** | `_BY_DESPACE` → `match_coverage`(parser.py 4곳)·`coverage_meta`(proposal_parser 2곳). PDF 원문 담보명 → 정식명 정규화 | **살아 있음** |
| ③ **V2 행 agg 결정** | `v2_mapping._LEGACY_AGG` → `ROW_AGG` — 실손 rep 여부를 이 표의 `agg` 필드가 정한다 | **살아 있음** |
| ④ **신설 행 판별** | `_LEGACY_NAMES_V2` → `NEW_ROWS_V2`(19) | **살아 있음** |
| ⑤ **구 페이로드 호환 축** | `compare._LEGACY_GROUP13` — row_id 없는 과거 저장분·구 프런트 미러 정렬 | **살아 있음** |

→ ②~⑤를 없애려면 **파서를 고쳐야 하는데 파서는 이 태스크의 무접촉 범위**다. 그래서 293은 **①만 제거**한다.

### 1-2. 제품 참조 0 — 제거 대상 확정
| 상수 | coverage/ | tests/ | 대체 |
|---|---:|---:|---|
| `NEW_ITEM_ORDER`(구 시트2 10~49행 순서) | 정의만 | 2파일 | `KB_COVERAGES_V2` 정의 순서(`ROW_INDEX`) |
| `YN_ITEMS`(구 45~49행 Y/N 파생) | 정의만 | 1파일 | `YN_ITEMS_V2` + `CoverageRowV2.yn_source` |
| `STAGE_COMPONENTS`·`STAGE_COMMON_ADD`(구 시트3 3단 수식) | 정의만 | 1파일 | `PAYOUT_CASCADE_V2` 17체인 |
| `STANDARD_COUNT` | 정의만 | 2파일 | `STANDARD_COUNT_V2` |
※`FORM_ITEMS`·`YN_ROWS`·`STAGE_ROWS`·`GROUP_ORDER`는 **291에서 이미 제거**됐고, 272·287이 "부재"를 단언 중이다.

### 1-3. 전환기 임시물
| 대상 | 판단 |
|---|---|
| `tests/v2names.py`의 `legacy_form_view`(27개 테스트가 사용) | **정착** — 이름이 역할과 정확히 일치하는 **영구 테스트 헬퍼**다(구 담보명으로 V2 행 조회). 구 이름 단언이 남아 있는 한 필요하고, 27곳 rename은 검증만 흐린다 |
| 287 `test_legacy_constants_are_untouched`(구 상수 sha256) | **재목적화** — 이제 "S1 무배선 증명"이 아니라 **파서 사전 불변 가드**다. 통과 상태 유지 |
| 287 `test_v2_wiring_...` | **강화** — 삭제한 5종이 제품 모듈에 되살아나지 않는지 `hasattr`로 검사 추가 |
| `scripts/prototype_286_ohj.py` | **유지** — 286 프로토타입 산출 재현 스크립트. 제품 경로가 아니고 `npm run`/CI에 물려 있지 않다. 삭제하면 286 대조를 재현할 수 없다 |

### 1-4. `_V2` 접미 rename 범위 — **산정만**
고유 이름 31종 · 총 참조 **302곳**(backend + scripts). 패킷 지시대로 **rename하지 않는다** — diff가 커져 이번 검증(산출물
무변경 증명)이 흐려진다. 대신 `GROUP12_V2` 정의부와 문서에 "이제 유일한 스키마"임을 명시했다.

### 1-5. ★서식 규칙 전수 — "값은 같은데 빠질 수 있는 것"
| # | 규칙 | 출처 |
|---|---|---|
| ① | `최종` 기대효과 열 방향 색 — 보장 증가=에메랄드/감소=앰버 · **월납·20년 총납입은 반대**(절감=에메랄드) | 261 ★291에서 실제 누락 |
| ② | 담보행 합계 2열 bold | 291 |
| ③ | Q2 80% 행 라벨 메모 `합계 미포함` | 243·291 |
| ④ | Q5 yn_source 7행 라벨 메모 `가입특약 Y/N` | 254·291 |
| ⑤ | L 접두 10행 — **`최종` 시트에만** | 291 |
| ⑥ | 2열 헤더 `질병 \| 상해` · 간병인 순서 통일 | 292 |
| ⑦ | 브랜드 — 에메랄드 헤더+흰 글자·그린 티 대분류 선두·라임 특수행·**빨강 0** | 250 |
| ⑧ | 인쇄 — 전/후·최종 landscape·fitToWidth=1·fitToHeight=0·눈금선 off·틀고정 / 표지 portrait | 248·291 |
| ⑨ | PDF 고령 가독성 13.5pt·line-height 1.65 · 회사 5개씩(`COMPANY_CHUNK`) · 섹션 page-break | 261 |
| ⑩ | 비고 블록 — 49행 밖 담보 이름 보존 | 276a·291 |

### 1-6. ★범위 밖 발견 (기록만 — `src/` 무접촉)
프런트가 구 40행 축의 **자체 미러**를 갖고 있다: `src/lib/coverageAfterDisplayCache.ts`(`GROUP_ORDER` 11그룹·
`YN_ITEMS`·`STAGE_COMPONENTS`·`STAGE_COMMON_ADD`)·`CoverageInsightBlocks.tsx`(`STAGE_ROWS` 7행)·`CoverageRemodel.tsx`.
백엔드 payload는 V2 49행/11그룹(`실 비`·`수 술`·…)인데 미러의 `GROUP_ORDER`는 구 그룹명(`사망`·`후유장해`·…)이다.
→ **층위 3(프런트 V2 이관) 태스크가 필요하다**(Human 결정 항목). 293은 `src/` 무접촉이라 손대지 않았다.

---

## Step 2 — 제거·정리

- `constants.py`에서 **5종 삭제**: `NEW_ITEM_ORDER`·`YN_ITEMS`·`STAGE_COMPONENTS`·`STAGE_COMMON_ADD`·`STANDARD_COUNT`.
- ★`YN_ITEMS_V2`가 `tuple(YN_ITEMS)`로 **구 상수에서 파생**되고 있었다(스캔에서 `_V2` 필터에 가려 놓쳤다) —
  **같은 값을 리터럴로 정착**시켰다. 값은 한 글자도 바뀌지 않았고 287 테스트가 항목 5종·원천 담보명을 문자열로 고정한다.
- `KB_COVERAGES`·`KB_NAME_ALIASES`·`GROUP12/13`은 **유지**하되, 정의부 주석을 §1-1의 역할표로 교체해
  "양식이 아니라 사전"임을 명시했다. 삭제한 5종의 대체재도 주석에 남겼다.
- ★삭제 주석 안에만 있던 **비분양식 시트3 원본 수식(I5~I11)·H10 정정·K7 미이식 근거**는 `decisions.md`로 옮겨 보존했다
  (주석이 "decisions.md에 보존"이라고 쓰면서 실제로는 없는 상태를 만들지 않기 위해 실제로 이관했다).
- `_V2` rename **미실시**(§1-4). `scripts/prototype_286_ohj.py` **유지**(§1-3).

### 제거 과정에서 잡은 사고 1건 (기록)
1차 절삭이 `NEW_ITEM_ORDER`~V2 섹션 구간을 통째로 잘라 그 사이에 있던 **`classify_extra`·`davinci_label`·
`anticancer_label`·`DAVINCI_*`·`DEATH_EXCLUSION_LABELS`까지 함께 삭제**됐다(292 산출물의 핵심 함수들).
전체 테스트 57개 수집 오류로 즉시 드러났고, HEAD에서 해당 블록만 복원한 뒤 **HEAD 대비 최상위 이름 diff**로
"의도한 5개만 사라졌고 그 외 차이 0"을 재확인했다. 이후 산출물 해시 12종이 전부 동일함도 확인했다.

---

## Step 3 — 서식 회귀 테스트

신설 `backend/tests/test_format_regression_293.py` — §1-5의 10개 규칙을 **실문서 3건**(표준 정본·overview 정본·0805 사례)으로 고정. **13건 전부 통과.**
- 차액 색상은 방향이 **반대인 두 축**(보장 증가=개선 / 보험료 절감=개선)을 실제 값으로 확인하기 위해
  **해지 1건을 넣은 시나리오**를 별도로 돌린다(무해지 문서만으로는 감소 케이스가 안 나온다).
- 빨강 미사용은 4시트 **전 셀**(글자·면)을 훑어 확인한다.

### ★검출력 확인 — 뮤테이션 4종 (테스트가 장식이 아님을 증명)
| 주입한 결함 | 결과 |
|---|---|
| A. 담보행 차액 색상 제거(**291에서 실제로 일어난 회귀**) | ✅ 실패 검출 |
| B. Q2 80% 메모 제거 | ✅ 실패 검출(3건) |
| C. PDF 본문 13.5pt → 10pt | ✅ 실패 검출(3건) |
| D. 간병인 2열 순서 역전(292 되돌림) | ✅ 실패 검출(3건) |
주입분은 모두 되돌렸고 `export_excel.py`·`export_pdf.py`의 최종 diff는 **0**이다.

---

## Step 4 — 문서 정합
- **`decisions.md`**: `2026-08-18 — 층위 2 결정 전수` 신설 — Q1~Q9 표 · 케스케이드/분배/다빈치 3분류/재해사망 합산/
  2열 헤더/L 접두 · 292 Human ①③④⑥ 확정과 ②⑤ 이월 · **293 결정(구 40행 부분 제거 사유)** · **시트3 원본 수식 보존**.
- **`verify.md`**: `★스키마 정본` 절 신설(49행이 유일 · 구 40행 폐기 · 남은 3종의 역할 · 서식 회귀 스위트) +
  **smoke 기준값 이력 표**(290 Q6 +1,030만/−4,130만 · 291 무변경 · 292 overview 정본 enrolled 42 · 293 무변경) + 기준선 1044/8.
- **`CLAUDE.md`·`AGENTS.md`**: 기준선 1044/8.

---

## 검증 (1차 · 2026-08-18 · Windows 로컬)
- [x] ★**4문서 산출물 무변경** — 엑셀(셀 값 + 서식 + 병합 + 인쇄설정 + 메모 전수)·PDF HTML·payload **해시 12종 완전 동일**
      (제거 전 HEAD에서 채취 → 제거 후 재채취 대조). 타임스탬프는 고정 인자로 배제
- [x] 구 40행 **양식 파생 상수 5종 참조 0**(제품·테스트) · 287이 `hasattr`로 부활 방지 · 291 제거분(FORM_ITEMS 등) 부재 유지
- [x] ★서식 회귀 13건 전부 현행 산출물에서 **통과** · 뮤테이션 4종 **전부 검출**
- [x] `cd backend && python -m pytest -q` — **1044 passed, 8 skipped**(1031 + 신규 13 · 회귀 0)
- [x] ★`npm run smoke:coverage` **PASS — 기준값 무변경**(2/2)
- [x] `npm test` 402/41 · tsc app/node · lint 무경고 · build:verify 예상 FAIL(248)
- [x] 보호 영역 diff **0** — `aggregator.py`·`v2_mapping.py`·`compare.py`·`integrated_treatment.py`·`parser.py`·
      `proposal_parser.py`·`export_excel.py`·`export_pdf.py`·`pipeline/`·`filters.py`·`src/`·`scripts/`·`vite.config`
- [x] 문서 4종 정합(decisions·verify·CLAUDE·AGENTS)

### 기존 테스트 갱신 — 3파일 (전부 제거의 직접 귀결 · 완화 0)
| 파일 | 내용 |
|---|---|
| `test_coverage_parser_179.py` | `STANDARD_COUNT == 40` → `len(KB_COVERAGES) == 40`. ★의미를 **"양식 행 수"에서 "파서 사전 표제어 수"로 재정의**해 단언은 유지(사전이 줄면 파싱이 조용히 실패한다) |
| `test_taxonomy_246.py` | 미사용 `NEW_ITEM_ORDER` import 제거(본문 사용 0) |
| `test_schema_v2_287.py` | Y/N 원천을 `YN_ITEMS_V2`로 이관하되 **항목 5종·원천 담보명 9개를 문자열로 별도 고정**(자기참조 방지) · 삭제 5종 부활 방지 가드 추가 · docstring 293 현재형 |

## ★Human 결정 필요 1건
- **층위 3(프런트 V2 이관) 발주 여부** — §1-6. 프런트가 구 40행 축 미러를 갖고 있어 `GROUP12/13`과
  `compare._LEGACY_GROUP13`을 아직 지울 수 없다. 이관하면 구 축을 완전히 걷어낼 수 있다.
  (293 범위에서는 `src/` 무접촉이라 손대지 않았고, 현재 동작에 회귀를 만들지도 않았다.)

## 확인 불가
- `build:verify` FAIL은 248 환경 제약(Application Control이 네이티브 바이너리 차단) — 291·292와 동일 조건.

## Stage 목록 (Codex용)
`backend/coverage/constants.py` · `backend/tests/test_format_regression_293.py`(신설) ·
`backend/tests/test_coverage_parser_179.py`·`test_taxonomy_246.py`·`test_schema_v2_287.py` ·
`.agent-harness/tasks/BOHUMFIT-293-schema-v2-cleanup.md`·`decisions.md`·`verify.md`·`handoff.md`·`locks.md` · `CLAUDE.md`·`AGENTS.md`
※제외: 실 PDF·PII·수기 엑셀·생성 산출물(scratchpad)

## 커밋 메시지 (Codex용)
chore(BOHUMFIT-293): 층위 2 정리 — 구 40행 제거·서식 회귀 테스트·문서 정합(산출물 무변경)
