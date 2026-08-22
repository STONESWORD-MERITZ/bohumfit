# BOHUMFIT-303 — 수술 판정 3단 표시: `수술 여부 확인` 티어 신설 (285 C-1)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: **Codex**(2차 검증·커밋) · Risk tier: 표시 계층(값·판정 계층 불변 — Q1~Q5·수술 N건 Δ=0)
Date: 2026-08-22 · 기준 HEAD `20cec2c`(285) · 야간 무인 · git 쓰기 0 · 실 PDF 읽기 전용·복사/stage 0
★실 고지 PDF는 세션에 입력된 비밀번호로 열람만 — 비밀번호는 이 문서·handoff·픽스처·임시 스크립트 어디에도 없다
(실측 스크립트는 환경변수로만 받았고 파일에 쓰지 않았다). 환자명·병원 실명 미기재(상병코드·시술명·건수만).

## ★이 태스크의 정의(불변식)
Q1~Q5 판정·"수술 N건"·헤더 reason이 **한 건도 변하지 않는다**. 변하는 것은 **라벨뿐**(`수술 확정` → `수술 여부 확인`).

---

## Step 1 — 실측 (코드 무변경)

### 1-1. 수술 판정 흐름 우선순위 (코드 기준 · `_is_detail_surgery_match` / `_is_surgery_match`)
| 순서 | 단계 | 함수 | 결과 |
|---|---|---|---|
| 1 | 보조재 가드(SNARE·카테터·치석제거…) | `_is_detail_support_only` | 미판정 |
| 2 | 062 완전일치 제외(4건) | `is_non_surgery_excluded` | 미판정 |
| 3 | 059/104/106/130 행위 제외(강수술 신호 통과) | `is_non_surgery_action` | 미판정 |
| 4 | 양성 키워드(`surg_keywords` 23) − negative(강수술 있으면 통과) | `_is_surgery_match` | **확정** |
| 5 | detail 확정 키워드·nhis 키워드 | `_DETAIL_CONFIRMED_SURGERY_KEYWORDS`·`nhis_surg_keywords` | **확정** |
| (병렬) | 처치및수술 **컬럼 비공란**(행위 제외만 거침) | `is_surg_by_column` | **확정** |
→ 303 티어 판정은 **4·5·컬럼 경로로 확정된 뒤**에만 적용된다(제외 단계는 무접촉).
  우선순위(구현): 제외 → **강수술 신호 유지(확정)** → **강등 패턴(확인)** → 일반 양성·컬럼(확정). 실측 순서와 동일.

### 1-2. 확정 수술 소비처 전수 · 현행 라벨
| 경로 | 지점 | 현행 라벨 |
|---|---|---|
| Q3/Q1/Q4 헤더 | `filters.py` reason | `5년이내 수술: {명} — 세부진료 확인` 등(**무변경**) |
| 화면 배지 | `Disclosure.tsx` DiseaseCard 칩 | `수술 N건`(red) |
| 카카오 서버 | `main._kakao_item` 건별 줄/이름 나열 | `{날짜} / {맥락} / {명} / {병원}` |
| 카카오 프런트 | `disclosureMemo.memoItem` | 동일 형식(251 골든) |
| 리포트 PDF | `report_disclosure.html` 칩 | `수술 N건`(chip red) |

### 1-3. 강등 후보 현행 상태 분류 (실측)
| 후보 | 현행 | 분류 |
|---|---|---|
| `이물제거술(단순` | `제거`로 **확정**(실 고지 1건) | (a) 강등 대상 |
| `(단순` 일반화 | 3문서+픽스처 스윕 **1건**(위 건)뿐 — 진짜 수술 반례 검증 불가 | **303b 결정지**(좁게 유지) |
| `발사`·`세척`·`흡인`·`천자` | 059 목록에 없어 컬럼/키워드 경로로 확정 도달 가능 | (a) 강등 대상(`천자`는 양성 키워드) |
| `드레싱`·`도뇨` | 059/130 `_NON_SURGERY_ACTION_KEYWORDS`에 이미 있음 | (b) 이미 제외 → **무접촉** |
| 294 B 유형 `치료재료비용`·`절삭기류` | 키워드 미매칭 — **컬럼 경로**로만 확정 가능 | (c) **303c 결정지**(보조재/재료 가드 계열) |
| `수술팩(…)` | `수술` 강신호 → 확정 | (c) 303c |
| `정맥내주입(IVPCA)` | `주입` 양성으로 확정(`정맥내주사`만 059에 있음) | (c) 303c |

### 1-4. 실 고지 3문서 BEFORE (basic 124·detail 550·pharma 440 · 파싱오류 0)
확정 수술 **1건** — T17 그룹 `인두이물제거술(단순[…])` · Q3 `5년이내 수술: …` · Q2(easy) `10년이내 수술: …` · 수술 1건 · 라벨=확정.

## Step 2 — 구현
- **판정 한 곳**: `surgery_exclusions.py` — `SURGERY_REVIEW_PATTERNS`(5) + `surgery_tier(name)`(강수술→확정 · 패턴→확인 · 그 외 확정 · 빈 이름→확정).
- **데이터(카운트 불변의 구조적 보장)**: `surgeries`/`surgery_dates` **그대로** + 부가 필드 `surgery_review_names`(그룹) →
  `surgery_records[].tier`·item `surgery_review`(result_builder, 창 내). 소비처는 티어 부재 시 **확정 폴백**(구 payload 호환).
- **4경로 라벨** `수술 여부 확인`: 서버 `main.SURGERY_REVIEW_LABEL` 1상수 · 프런트 `disclosureWindow.SURGERY_REVIEW_LABEL` 1상수 —
  카카오 서버/프런트 `수술 여부 확인: {명칭}` · 화면 칩 `수술 여부 확인 N건`(**amber** — 회색 강등 아님) · PDF 칩 동일.
  배지 합 불변식: 확정 N + 확인 M = `surgery_count`(`_surgery_tier_counts` / `surgeryTierCounts` 동일 규칙 — 같은 날 확정·확인 공존은 확정).
- 모바일(267)은 DiseaseCard 통과 구조 — 별도 생성부 없음(확인).
- 무접촉: `surgeries` 확정 조건·`filters.py`·062/059/강수술/보조재 목록·공단 의심·`keywords.json`·251 원문·294 압축·보장분석·골든·smoke.

## ★Step 3 — AFTER 대조표 (BEFORE=`git show HEAD:` 6파일 복원 · 별도 프로세스 · 3문서 전부 실행 · 추정 0)
복원 검증(변경 심볼 출현): `surgery_tier` **0 / 6**(aggregator) · `SURGERY_REVIEW_LABEL` **0 / 3**(main).
| 지표 | BEFORE | AFTER | Δ |
|---|---|---|---|
| Q1~Q5 판정 항목(q·rule·code·reason·is_surgery·surgery_name) | 15 | 15 · **전부 동일** | **0** |
| 리포트 14항목 `surgery_count`·`surgeries` | — | 동일 | **0** |
| 라벨 변화 | — | T17만: `surgery_review`=[인두이물제거술(단순…)] · record tier=`review` | 표시만 |
| 카카오(건강체·간편) | `… / 인두이물제거술(단순[…]) / …` | `… / 수술 여부 확인: 인두이물제거술(단순[…]) / …` | **1줄 접두만**(양쪽 각 1줄) |
★251 골든: 강등 패턴 0건 → 골든 문자열 **무변동**(갱신 없음 · 251·294 테스트 통과). smoke:coverage **무변동 PASS**.

## Step 4 — 회귀 테스트 · 뮤테이션
- 백엔드 신설 `tests/test_surgery_review_tier_303.py` **9건** + 골든 `fixtures/surgery_review_parity_303.json`(확인·확정·구 payload 3종).
- 프런트 신설 `src/pages/SurgeryReviewTier303.test.tsx` **6건** — ★DiseaseCard **실제 렌더**(확인 칩 amber·확정 칩 red·혼합) ·
  memoItem == 서버 골든 3종 · 라벨 상수 서버 원문과 일치 · 구 payload 폴백.
- ★뮤테이션 3종 전부 검출 후 원복(blob 동일):
  | 주입 | 검출 |
  |---|---|
  | ① 강등 목록 비움 | 백엔드 4건 실패(확인 티어 소멸) |
  | ② 강등을 카운트 제외로(확정 집합에서 제거) | `test_q_items_and_counts_are_unchanged_by_tier` 등 2건 실패(헤더 변화) |
  | ③ 프런트 티어 분기 제거(칩 합침) | 렌더 테스트 2건 실패 |

## 검증 (2026-08-22 · Windows 로컬 · 실측)
- [x] ★3문서 Q1~Q5·수술 N건·헤더 reason **Δ=0**(전부 실행·추정 0) · 251 골든·smoke 무변동
- [x] 인두이물(단순) 확인 티어 · 카운트 포함 · 배지 합 = 헤더
- [x] 4경로 라벨 동일 · 서버==프런트 문자열(골든)
- [x] 컴포넌트 렌더 단언 · 뮤테이션 3종 검출 후 원복
- [x] npm test **419 passed / 43 files**(413+6) · tsc app·node 0 · lint 0 · build:verify 예상 FAIL(343,702 B 껍데기)
- [x] backend pytest **1102 passed / 8 skipped**(1093 + 신설 9 · 회귀 0)
- [x] 비밀번호·PII 0건 · 실 PDF·임시 산출물 미저장·미stage
★실측 중 한 번 잡힌 것: 프런트 전체 스위트에서만 칩 **숫자**(AnimatedNumber) 렌더 타이밍이 달라 3건이 실패 → 숫자 애니메이션에
기대지 않고 **칩 요소 자체**(자기 텍스트 `수술 여부 확인 건`/`수술 건`·톤 class)로 단언하도록 재작성(뮤테이션 ③ 재검출 확인).

### Codex 2차 검증(2026-08-22)
- 전체 게이트: backend **1102 passed, 8 skipped** · frontend **419 passed / 43 files** · tsc app/node · lint · 라우트 **18/18** ·
  `smoke:coverage` PASS. `npm run build`는 **343,702 B**, `build:verify`가 앱 문자열 3종 부재와 600 kB 하한 미달을 예상대로 거부했다.
- 뮤테이션 3종을 재주입해 **4건/2건/2건 실패**를 각각 확인하고 원복했다. 원복 후 세 파일 SHA-256은 주입 전과 바이트 단위로 동일하다.
- 중점 E 보강: 칩 요소·amber 톤뿐 아니라 `AnimatedNumber`의 최종 `1건`을 `waitFor`로 직접 단언한다. 단독 6건·전체 419건 모두 통과했다.
- `git show 20cec2c:` 복원 검증은 `surgery_tier` **0/6**, `SURGERY_REVIEW_LABEL` **0/3**으로 일치했다. 격리 복원본과 현재 코드를
  익명 T17 동일 입력으로 별도 프로세스 실행한 결과 Q 항목·리포트 `surgery_count`/`surgeries`가 동일하고, 건강체·간편 카카오 각 1줄의
  `수술 여부 확인:` 접두만 달라졌다.
- 실 고지 3문서 Codex 재파싱은 **확인 불가**: 로컬 3파일이 모두 암호화돼 있고, Code 1차 검증 때 환경변수로만 주입한 비밀번호가
  현재 Codex 셸에는 남아 있지 않다. 비밀번호·`.env*`를 조회하거나 추측하지 않았다. 위 Step 3의 실문서 15항목/14항목 결과는 Code 1차 실측 기록이다.
- 익명 T17 리포트 PDF를 실제 Chromium으로 생성해 3페이지 텍스트·좌표를 전수 확인했다. 확인 칩은 표준/간편 각 1곳, 047 면책 문구는
  그대로이고 페이지 밖 침범은 없다. 자동 PDF 래스터 도구와 Orca CLI 부재로 PDF 페이지 이미지 육안은 **확인 불가**(이유 기록).
- 실제 Vite dev + Chromium 375px: 가로 넘침 **0**(`scrollWidth=375`) · 칩 `수술 여부 확인 1건` · 15px · amber 면/폰트 · 콘솔 error 0.
  일회성 HTML/TSX·PDF·스크린샷·격리 복원본은 검증 후 전부 삭제했고 레포 잔재 0이다.

---

## ★303b 결정지 (코드 무변경 · 스크래치 사본 시뮬레이션)
### 누락 스윕 — 3문서 detail에서 `술`로 끝나는데 현행 양성 미매칭 **전수 5건**
| 명칭 | 판정 |
|---|---|
| **누점폐쇄술** (H16 그룹) | ★잠재 누락 — `폐쇄술` 양성 키워드 부재 |
| 구술(간접구)-기기구술 · 복강내 침술 · 투자법 침술 · 침전기자극술 | 한방 자극요법 — 미판정 **정당** |
### `폐쇄술` 양성 추가 시뮬레이션 (스크래치 사본 keywords.json만 패치 · 레포 무접촉)
- Q 판정 항목 **15 → 17**: `+ H16 5년이내 수술: 누점폐쇄술 — 세부진료 확인` · `+ H16 10년이내 수술: 누점폐쇄술`
- 리포트: Q3 H16 수술 **0 → 1** · easy Q2 항목 수 1 → 2(H16 신규) · 다른 그룹 변화 0
- ★누점폐쇄술은 **확정** 티어로 떨어진다(강등 패턴 미해당). 확인 티어로 두려면 패턴 추가가 함께 필요.
→ 채택 시 값 계층 변경(카운트 증가 방향)이라 **Q6 절차**. Human 결정.
### 303c(별도 결정지) — 294 B 유형 경로 실측
`치료재료비용`·`절삭기류`=컬럼 경로 전용(키워드 미매칭) · `수술팩`=강수술 신호 확정 · `정맥내주입(IVPCA)`=`주입` 양성 확정.
→ 강등 목록이 아니라 **보조재/재료 가드(`_is_detail_support_only`) 확장** 또는 059 목록 검토 대상. 이번 표본엔 0건.
### `(단순` 일반화 — 표본 1건(위 인두이물)뿐이라 반례 검증 불가 → 좁게(`이물제거술(단순`) 유지. 추가 표본 시 재판정.

## Stage (Codex)
`backend/pipeline/surgery_exclusions.py`·`disease_aggregator.py`·`result_builder.py`·`report_pdf.py` · `backend/main.py` ·
`backend/templates/report_disclosure.html` · `backend/tests/test_surgery_review_tier_303.py`·`fixtures/surgery_review_parity_303.json` ·
`src/lib/disclosureWindow.ts`·`disclosureMemo.ts` · `src/pages/Disclosure.tsx`·`SurgeryReviewTier303.test.tsx` · 태스크 문서 · handoff · locks.
※제외: 실 PDF·PII·임시 산출물. ★pytest 기준선 1093 → **1102**(verify/CLAUDE/AGENTS 갱신은 Codex).

## 커밋 메시지
feat(BOHUMFIT-303): 수술 판정 3단 표시 — 심평원 확정 중 처치 패턴을 `수술 여부 확인` 티어로 강등(카운트·Q1~Q5 불변)
