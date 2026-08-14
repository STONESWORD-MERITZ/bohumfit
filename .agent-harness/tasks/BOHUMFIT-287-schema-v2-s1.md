# BOHUMFIT-287 — 42행 스키마 S1: 신 스키마 정의 (구 40행과 병존)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: **Codex**(2차 검증·커밋) / **Human**(미결 3건)
Risk tier: 중 — 상수 신설만. ★제품 동작 무변경이 성립 조건. git 쓰기 금지(커밋 Codex).
Date: 2026-08-12 · 기준 HEAD `4657224`(284 `da95215` · 286 `94c18a8` 반영) · 선행 BOHUMFIT-286-D

## S1의 성립 조건
"새 상수가 생겼다"가 아니라 ★**"제품 동작이 하나도 안 바뀌었다"**가 이 태스크의 합격선이다.
따라서 아래 검증의 절반은 V2 계약이고, 절반은 **구 스키마가 그대로인지**를 지키는 증명이다.

---

## Step 1 — 42행 확정안 재검증 (코드 무변경)

### 1-1. 수기표 4개 시트 전수 대조
수기표 정본 A/B의 **기존·리모델링 4개 시트**
7~48행을 셀 단위로 대조했다.

| 결과 | 값 |
|---|---|
| 행 수 | **42행**(7~48) — 4개 시트 동일 |
| 대분류 | **11개** — 실 비·수 술·암·뇌·심 장·입 원·사 망·후유장해·골 절·배상책임·운전자 |
| 완전 일치 | **41행** |
| 차이 | **r24 1건** — 정본 A 리모델링만 `중입자 / 정위 방사선`, 나머지 3시트는 `중 입 자 치료` |
→ ★Q3 확정대로 **신형 표기 채택**, 구형은 별칭으로 보존. 고객별 가변 지점은 **없다**.

### 1-2. 최종 42행 전문 (행 성격 포함)
성격 표기 — ▣금액행(기본) · ⇄2열 병기 · Σ×합계제외 · ⓨY/N 판정 원천

| # | row_id | 대분류 | 담보명 | 성격 |
|---:|---|---|---|---|
| 1 | `actual_inpatient` | 실 비 | 상 해/질 병 입 원 | ▣ⓨ |
| 2 | `actual_outpatient` | 실 비 | 상 해/질 병 통 원 약 제 | ▣ⓨ |
| 3 | `surgery_injury` | 수 술 | 상 해 수 술 비 | ▣ |
| 4 | `surgery_disease` | 수 술 | 질 병 수 술 비 | ▣ |
| 5 | `tier_surgery_1` | 수 술 | 1종 수술비 (질병 I 상해) | ▣**⇄** |
| 6 | `tier_surgery_2` | 수 술 | 2종 수술비 (질병 I 상해) | ▣**⇄** |
| 7 | `tier_surgery_3` | 수 술 | 3종 수술비 (질병 I 상해) | ▣**⇄** |
| 8 | `tier_surgery_4` | 수 술 | 4종 수술비 (질병 I 상해) | ▣**⇄** |
| 9 | `tier_surgery_5` | 수 술 | 5종 수술비 (질병 I 상해) | ▣**⇄** |
| 10 | `surgery_cerebral` | 수 술 | 뇌혈관 수술비 | ▣ |
| 11 | `surgery_cardiac` | 수 술 | 심장질환 수술비 | ▣ |
| 12 | `cancer_general` | 암 | 암 진 단 비(일반암) | ▣ |
| 13 | `cancer_minor` | 암 | 유 사 암 진 단 비 | ▣ |
| 14 | `cancer_surgery` | 암 | 암 수 술 / 로 봇 암 수 술 | ▣ |
| 15 | `cancer_chemo_radio` | 암 | 항 암 방 사 선 약 물 치 료 | ▣ |
| 16 | `cancer_high_cost` | 암 | 고액항암치료(표적,면역) | ▣ (병합) |
| 17 | `radio_imrt_proton` | 암 | 세기조절 / 양성자 방사선 | ▣ |
| 18 | `radio_carbon_srs` | 암 | 중입자 / 정위 방사선 | ▣ (Q3) |
| 19 | `cerebral_disease` | 뇌 | 뇌 혈 관 질 환 | ▣ |
| 20 | `stroke` | 뇌 | 뇌 졸 중 | ▣ |
| 21 | `cerebral_hemorrhage` | 뇌 | 뇌 출 혈 | ▣ |
| 22 | `cardiac_disease` | 심 장 | 심 장 질 환 | ▣ |
| 23 | `ischemic_heart` | 심 장 | 허혈성 심장질환 | ▣ |
| 24 | `acute_mi` | 심 장 | 급성심근경색 | ▣ |
| 25 | `inpatient_injury` | 입 원 | 상 해 입 원 | ▣ |
| 26 | `inpatient_disease` | 입 원 | 질 병 입 원 | ▣ |
| 27 | `inpatient_private_room` | 입 원 | 1 인 실 입 원 | ▣ |
| 28 | `caregiver` | 입 원 | 간 병 인 | ▣ (병합) |
| 29 | `death_general` | 사 망 | 일 반 사 망 | ▣ |
| 30 | `death_injury` | 사 망 | 상 해 사 망 | ▣ (Q9) |
| 31 | `death_disease` | 사 망 | 질 병 사 망 | ▣ |
| 32 | `disability_80` | 후유장해 | 상해 질병 후 유 장 해 80% | **Σ×** (Q2·243) |
| 33 | `disability_injury_3` | 후유장해 | 상 해 후 유 장 해 3% | ▣ |
| 34 | `disability_disease_3` | 후유장해 | 질 병 후 유 장 해 3% | ▣ |
| 35 | `fracture_diagnosis` | 골 절 | 골 절 진 단 비 | ▣ |
| 36 | `fracture_surgery` | 골 절 | 골 절 수 술 비 | ▣ |
| 37 | `cast_treatment` | 골 절 | 깁스치료비 | ▣ |
| 38 | `liability_daily` | 배상책임 | 일 상 생 활 배 상 책 임 | ▣ⓨ |
| 39 | `driver_settlement` | 운전자 | 형 사 합 의 금 | ▣ⓨ |
| 40 | `driver_lawyer` | 운전자 | 변 호 사 선 임 | ▣ⓨ |
| 41 | `driver_fine` | 운전자 | 벌 금 | ▣ⓨ |
| 42 | `driver_injury_grade` | 운전자 | 자 부 상 | ▣ⓨ |

★`row_id`는 **표시명과 분리된 안정 키**다. r24처럼 표기가 흔들려도 코드 전반은 흔들리지 않는다.
★Q2 해석: 80% 행은 **보이되 더해지지 않는다**(`sum_excluded` + `SUM_EXCLUDED_NOTE_V2="합계 미포함"`).
  243의 "집계 제외"와 수기표의 "행 존재"를 **동시에** 지키는 유일한 형태다.
★Q5 해석: ⓨ는 "이 행이 Y/N **판정의 원천**"이라는 뜻이고, 행 자체는 금액행이다.
  `yn_flags` 산출은 내부에 그대로 남고 표시만 이 7행으로 분산된다.

### 1-3. ★286-D 설계 문서의 오류 2건 (Step 1 재검증에서 발견)
| # | 286-D 기재 | 실제 | 조치 |
|---|---|---|---|
| 1 | 40행 전 항목의 처리를 매핑표에 정리했다고 함 | ★**`암 주요치료비`가 누락**됐다. 유지·병합·이동·폐기 어디에도 없다 | 임의 배치하지 않고 **보류 목록**에 넣고 Human 질문으로 올렸다(미결 ③) |
| 2 | 신설 **11행** | ★**13행**이다. 종수술 5행의 별칭(`N종수술비(질병 1종)` 등)은 파서·238 환산 라벨이지 **구 40행 이름이 아니고**, `항암약물방사선`·`중입자방사선`도 구 40행에 없다 | `NEW_ROWS_V2`를 "별칭이 비었는가"가 아니라 **"구 40행 이름을 하나라도 갖는가"**로 판정하도록 정의했다 |

### 1-4. 별칭 소요 목록 (S4 입력물 — 여기서는 목록만)
`CoverageRowV2.aliases`에 담았다. 성격별로:
- **1:1 개명** 17건 — `상해수술`→상해수술비 · `벌금(대인/스쿨존/대물)`→벌 금 · `자동차사고부상`→자 부 상 등
- **병합 4행 8건** — 실손 입원 2·통원 2 · `표적/면역항암치료` 2 · 간병 일당 2
- **표기 흔들림 1건** — `중 입 자 치료` → `중입자 / 정위 방사선`
- **파서·환산 라벨 15건** — `N종수술비({종별} N종)` 10 · `일반종수술 N종(표준환산)` 5
★S4가 채워야 할 **신설 13행**: 종수술 5 · `cancer_chemo_radio` · `radio_imrt_proton` ·
  `radio_carbon_srs` · `inpatient_private_room` · `death_general` · `disability_80` ·
  `fracture_surgery` · `cast_treatment`

---

## Step 2 — 신 상수 정의 (`backend/coverage/constants.py` **말미 추가**)

| 이름 | 내용 |
|---|---|
| `CoverageRowV2` | `NamedTuple` — `row_id`·`group`·`display`·`dual_column`·`sum_excluded`·`yn_source`·`aliases` |
| `KB_COVERAGES_V2` | 42행 |
| `GROUP12_V2` | 대분류 11 |
| `STANDARD_COUNT_V2` | 42 |
| `SUM_EXCLUDED_NOTE_V2` | `"합계 미포함"` — ★S3가 그대로 쓰도록 **한 곳에서만** 정의 |
| `APPENDIX_ITEMS_V2` | Q4 4항목(고액암·3대비급여실손·보철치료비·화재벌금) |
| `PENDING_DISPOSITION_V2` | ★보류 3항목(장기요양간병비·경증치매진단·**암 주요치료비**) |
| `LEGACY_TO_V2` | 구 40행 → `row_id` 또는 `APPENDIX`/`PENDING` |
| `NEW_ROWS_V2` | 신설 13행 |

---

## Step 3 — 검증 (1차 · 2026-08-12 · Windows 로컬)

### ★★제품 동작 무변경 — 3중 증명
1. **구조 증명(추가만)**: HEAD의 `constants.py` 본문이 현재 파일의 **정확한 접두**다
   (`import` 한 줄 추가 제외). **+162줄**이 뒤에 붙었을 뿐 기존 줄은 한 글자도 안 바뀌었다.
2. **이름 증명**: AST로 대조해 새 블록이 **기존 이름을 하나도 재정의하지 않음**을 확인했다.
3. ★**산출물 바이트 증명**: HEAD의 `constants.py`를 넣은 backend 사본과 현재 backend로
   **같은 입력**을 돌려 결과 JSON의 sha256을 비교했다 — **완전 일치**.
   `74d7fce03b97d050c0a6bd860f79040383fc471f65efce2fc869b1125429aeae`
   대상: 제안서 3건 · 6계약 문서 · **정본 2건** · 20260805 분석서.

### 게이트
- [x] backend `pytest -q` **955 passed, 8 skipped** — 기준선 937 + **신규 18**, 회귀 0
- [x] ★★`npm run smoke:coverage` — **정본 2건 기준값 완전 불변**(604,560,000/681,312 · 1,542,990,000/4,675,189)
- [x] `npm test` **402 passed / 41 files** — 회귀 0(`src/` 무변경)
- [x] `npx tsc -p tsconfig.app.json --noEmit` / `tsconfig.node.json` — PASS · `npm run lint` 무경고
- [x] `npm run build:verify` — 343,702 B **예상 FAIL**(248 Application Control)
- [x] ★보호 영역 **diff 0**: `aggregator.py`·`export_excel.py`·`export_pdf.py`·`pipeline/`·
      `filters.py`·`src/`·`vite.config.ts`
- [x] ★구 상수 스냅샷(sha256) 3종 불변 — `KB_COVERAGES`·`GROUP12`·`KB_NAME_ALIASES`
- [x] ★**무배선 증명 테스트** — 집계·export 3파일에 `_V2` 참조 0건(코드로 고정)
- [x] ★수기표 원본 대조 — V2 행명 42개가 두 수기표와 **문자열 단위 일치**

### 테스트 18건 (`backend/tests/test_schema_v2_287.py`)
골격 4 · 행 성격 3 · 구 40행 대응 6 · **병존 증명 3**(구 상수 스냅샷·무배선·수기표 대조 2건 포함)
※수기표 대조 2건은 `보장분석/`이 gitignore라 파일 부재 시 `skip`한다. **로컬에서는 실행돼 통과**했고,
  계약 자체는 `EXPECTED_DISPLAY` 상수로 파일 없이도 고정된다(자기 검증 회피).

---

## ★Human 미결 3건 (S2 착수 전 결정 필요)
| # | 항목 | 왜 못 정했나 | 선택지 |
|---|---|---|---|
| ① | `장기요양간병비` | 구 `제외` 그룹. Q1~Q9가 다루지 않았다 | 부록 / 폐기 |
| ② | `경증치매진단` | 위와 동일 | 부록 / 폐기 |
| ③ | **`암 주요치료비`** | ★286-D 매핑표 누락분. 244가 "원문 데이터 없는 신담보, [후] 전용 자리로 행만 존치"로 만든 행이라 **`고액항암치료`로 병합할지 부록으로 내릴지**가 갈린다 | `cancer_high_cost` 병합 / 부록 / 폐기 |
★셋 다 `PENDING_DISPOSITION_V2`에 넣어 **보류로 표시**했다. 임의로 부록에 끼워 넣지 않았다 —
Q4는 4항목만 명시했고, 여기에 5번째를 더하는 건 Human 결정의 확장이다.

## 확인 불가
- **엑셀·PDF 산출물의 실제 바이트 비교** — S1은 export를 건드리지 않아 생성 경로가 동일하다.
  대신 **파싱 결과 JSON 해시**로 비교했다(입력이 같고 상수가 같으면 산출물도 같다).
- **[전] 트랙 전수 대조**(286 이월) — 이번 범위 밖. S2 착수 전 별도 태스크 권고.

## Stage 목록 (Codex용)
`backend/coverage/constants.py`(V2 추가분) · `backend/tests/test_schema_v2_287.py` ·
`tasks/BOHUMFIT-287-schema-v2-s1.md` · `handoff.md` · `locks.md` ·
기준선 3문서(`verify.md`·`CLAUDE.md`·`AGENTS.md` — backend 937→**955**)
※제외: 실 PDF·PII·수기 엑셀·`보장분석/` 하위 전부

## 커밋 메시지 (Codex용)
feat(BOHUMFIT-287): 42행 스키마 V2 정의(구 40행과 병존·무배선)
