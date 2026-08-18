# BOHUMFIT-298 — 층위 3: 프런트 종합비교 V2 17키 이관 (7키 → 17키)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: **Codex**(2차 검증·커밋 · ★295b→298 순서 분리 커밋) / **Human**(육안)
Risk tier: 중 — 표시 계층만. 값 계층·백엔드 무접촉. git 쓰기 0.
Date: 2026-08-18 · ★야간 순차 1/4 · 기준 HEAD `59fca67`(295/295b 미커밋분 위) · 선행 290·291·292·295

## ★배경 (295 §1-6 ③이 특정)
295는 "제안서 0건 → [후]==[전]" 불변식만 복원했다. 그러나 화면 표가 아직 **구 7키**라 `암`·`심장말기`가
[전]에서도 0으로 보이고 암 계열 12행이 아예 안 나온다. 291이 export를 `resolve()`로 투영했으나 화면 미러는
이관되지 않았다. **표시 계층만** V2 17키로 옮긴다(값 무변경).

## ★Human 확정 (재검토 금지)
프런트 종합비교를 케스케이드 17키로 이관 · 암 계열 12행 표시 · 구 7키 폐기 · 값 계층 무변경.

---

## Step 1 — 실측

### 1-1. 프런트 종합비교 표시 경로 (전수)
| # | 지점 | 역할 |
|---|---|---|
| ① | `CoverageRemodel.tsx` `beforeStages`/`afterStages` (295 헬퍼 `displayStageTotals` 호출) | 표시값 선택 |
| ② | `CoverageInsightBlocks.tsx` `STAGE_ROWS`(구 **7키**) → `StageComparisonTable` | 데스크톱 표 축 |
| ③ | `mobile/CoverageInsightMobile.tsx` `StageComparisonMobile rows={STAGE_ROWS}` | 모바일(같은 축 — 단일 소스) |
| ④ | `coverageAfterDisplayCache.ts` `computeStageTotals`(구 40행 이름 미러) | **구 payload 폴백** |
★`STAGE_ROWS`가 데스크톱·모바일 **단일 소스**다(295b 교훈: 우회 경로 없음). 295 헬퍼는 그대로 재사용.

### 1-2. 구 40행 이름 조회 잔재 (295가 고친 곳 외)
- `STAGE_ROWS` 구 7키(`암`·`뇌초기`~`심장말기`) — 서버 17키와 겹치는 건 뇌 3·심장 2뿐 → **`암`·`심장말기`가 [전]에서도 0**.
- `computeStageTotals`가 구 40행 `kb_name`으로 조회 + `STAGE_COMMON_ADD`(종수술5종+질병수술) 공통 가산 — **290에서 폐기된 산식**.
- `YN`은 5항목 그대로(서버 yn_flags 5항목과 일치) — 이관 불필요.

### 1-3. 서버 17키 구조 (290·291 산출 · `PAYOUT_CASCADE_V2` 1:1)
뇌초기·뇌중기·뇌말기 · 심장초기·심장중기 · 암 수 술 (레보아이 포함)·유사암 수술·다빈치(일반암/전립선/갑상선)·
항암 약물 치료·표적 약물 치료·면역 약물 치료·방사선 치료·세기조절 방사선 치료·양성자 방사선 치료·중 입 자 치료 = **17**.

### 1-4. ★구 7키 → 17키 대응표
| 구 7키 | 처분 | 17키 대응 |
|---|---|---|
| `암` | **소멸·분화** | 암 계열 **12행**으로(진단금 합산 폐기 · 케스케이드 체인 12개) |
| `뇌초기`·`뇌중기`·`뇌말기` | **유지**(키 동일) | 단 정의 변경(290: cerebral_disease 단독→누적 · 공통 가산 폐기) |
| `심장초기`·`심장중기` | **유지** | 290 정의(ischemic_heart→+acute_mi) |
| `심장말기` | **소멸** | 290이 심장 2단만 정의 |

### 1-5. 구 payload(90일 히스토리) 렌더 판단
히스토리 저장분은 `stage_totals` 없음 + 구 40행 이름 + `row_id` 없음. 291이 export에서 쓴 `resolve()` 투영을
**화면 미러에도 적용**한다 — `computeStageTotals`를 `row_id` 기준으로 바꾸고, `row_id`가 없으면 구 담보명→row_id
(`LEGACY_TO_V2` 이식)로 투영한다. ★투영 실패(체인 밖 담보)는 조용히 0을 만들지 않고 **기여하지 않는다**(honest 0만 남는다).

---

## Step 2 — 17키 이관 (`CoverageInsightBlocks.tsx`)
- `STAGE_ROWS` 7키 → **17키**(key = 서버 `stage_totals` 키와 정확히 일치 · label만 가독화). 구 `암`·`심장말기` 제거.
- 데스크톱·모바일 자동 반영(단일 소스). 295 헬퍼(`displayStageTotals`·`displayYnFlags`) 그대로 — **우회 경로 미신설**.

## Step 3 — 담보 표시 V2 (판단 결과)
화면 담보 목록·해지 UI는 **이미 서버 payload의 V2 표시명·`by_company`를 그대로 렌더**한다(`groupComparisonRows` 등은
`kb_name`·`group12`·`summary`를 그대로 표시 — 구 40행 이름 조회가 아니다). 해지 delta(182 D-11)는 `buildAfterResult`가
`by_company`에서 재집계하므로 V2 기준으로 정상. → 담보 표시부는 **추가 이관 불필요**(종합비교·미러만 구 7키였다).

## Step 4 — 구 payload 호환 (`computeStageTotals` V2 이관)
- `computeStageTotals`를 `row_id` 기준 17키 합산으로 재작성(서버 `compute_stage_totals`와 동일 규칙 · 공통 가산 폐기).
- `row_id` 없는 구 payload는 `LEGACY_TO_V2_ROW_ID`(케스케이드 체인에 쓰이는 row_id만 이식)로 투영.
- ★새 payload는 애초에 `stage_totals`(17키)를 헬퍼가 직접 쓰므로 이 미러를 안 탄다 — 미러는 순수 폴백.

## Step 5 — ★배선 회귀 테스트 (295b 교훈 적용)
- 신설/갱신 없이 **295b 배선 테스트(`CoverageRemodelWiring295.test.tsx`)를 17키 픽스처로 갱신** — 컴포넌트 실제 렌더로
  17키 표시 셀 단언(암 수술 3,000만 [전]=[후] · 비고행 1,410만이 암 체인 어느 행에도 없음).
- `CoverageInsightBlocks.test.tsx`(17행·암 12행·심장말기 없음) · `coverageNewTaxonomyDisplay.test.ts`(17키 미러·구 payload 투영) 갱신.
- ★**뮤테이션 3종 전부 검출**(원복 확인):
  | 되돌린 결함 | 검출 |
  |---|---|
  | ① STAGE_ROWS를 구 7키로 | ✅ 배선 테스트 + 표 테스트 실패 |
  | ② 헬퍼 우회(무조건 재산출) | ✅ 배선 테스트 실패(불변식·해지) |
  | ③ resolve 투영 제거(`LEGACY_TO_V2_ROW_ID` 비움) | ✅ 구 payload 투영 테스트 실패 |
- ★295b 배선 테스트가 계속 통과(17키 픽스처로 갱신 후).

---

## 검증 (1차 · 2026-08-18 · Windows 로컬)
- [x] ★종합비교 17행 표시 · 암 계열 12행 보임 · 구 7키(`암`·`심장말기`) 조회 0
- [x] ★제안서 0건: [후]==[전](295 불변식 — 배선 테스트가 렌더로 고정) · 서버 stage_totals 17키 그대로
- [x] `암`·`심장말기`가 [전]에서 0으로 표시되던 문제 해소(17키 기준 정상)
- [x] 구 payload(row_id 없음) → `LEGACY_TO_V2_ROW_ID` 투영으로 17키 채움 · 투영 실패는 미기여(silent 0 아님)
- [x] 해지 체크 즉시 delta V2 기준 정상(`buildAfterResult` by_company 재집계 — 무변경)
- [x] ★뮤테이션 3종 전부 검출 · 295b 배선 테스트 통과
- [x] `backend/` **무접촉**(diff = 295b 테스트 1파일뿐) · 산출물 해시 **12종 293 기준 동일** · smoke **PASS 기준값 무변경**
- [x] `npm test` **413 passed / 42 files**(412 + 298 표 테스트 갱신분 · 순증 1) · tsc app/node · lint 무경고
- [x] backend pytest **1058/8 불변**(298 프런트 전용 — 백엔드 byte-identical) · build:verify 예상 FAIL(248)
- [x] 케스케이드 상수(289)·`compute_stage_totals`(290)·49행 스키마·`pipeline/`·`filters.py`·`vite.config` diff 0
- [x] 295/295b 헬퍼(`displayStageTotals`·`displayYnFlags`)·stale 판정 **보존**(되돌림 0)

## 확인 불가 / 기록
- 실 히스토리(90일 저장분) payload로 구 payload 폴백을 재현하지는 못함(로컬에 히스토리 없음) — 합성 픽스처로 투영 로직만 고정.
- 제안서 3건([후] 종합비교 292 산출값 일치)은 **서버 stage_totals가 정본**이라 프런트는 그 값을 그대로 표시 —
  프런트가 재계산하지 않으므로 292 산출과 자동 일치(별도 프런트 검증 불요 · 서버 테스트가 292값 고정).

## Stage 목록 (Codex용 · ★295b→298 순서)
`src/components/CoverageInsightBlocks.tsx`(STAGE_ROWS 17키) · `src/lib/coverageAfterDisplayCache.ts`(computeStageTotals V2·상수) ·
`src/components/CoverageInsightBlocks.test.tsx`·`src/lib/coverageNewTaxonomyDisplay.test.ts`·`src/pages/CoverageRemodelWiring295.test.tsx`(17키 갱신) ·
`tasks/BOHUMFIT-298-frontend-v2.md` · `handoff.md` · `locks.md`
※제외: 실 PDF·PII·산출물 · ★295/295b 헬퍼·stale은 298이 건드리지 않음(분리 커밋 시 298 = 표시 축·미러만)

## 커밋 메시지 (Codex용)
fix(BOHUMFIT-298): 프런트 종합비교 V2 17키 이관(암 12행 표시·구 7키 폐기)
