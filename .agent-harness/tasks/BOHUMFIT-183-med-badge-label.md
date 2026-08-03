# BOHUMFIT-183 — 205 투약 배지 표기 보강 (A안 확정)

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Claude Code (구현·1차 검증)
Risk tier: 중위험 — ★**표시 계층 전용**. git 쓰기 금지(커밋 Codex).
Date: 2026-08-02 · 기준 HEAD `96f2b54`(268a)

## ★이건 버그 수정이 아니다
현행 산식 `filters._sum_daily_max_presc` = **날짜별 최대 처방일수의 누적 합**은 030 진단 → 031/032에서
"배지 = 헤더 판정 일치"를 위해 **의도적으로 채택**된 설계다. B안(최대 단일청구)은 030을 재발시키므로 금지.
따라서 이번 태스크는 **산식이 무엇인지 밝히는 표기만** 추가한다.

## ★워킹트리 인계 사항
착수 시점 워킹트리에 **182 미커밋분이 공존**한다(`CoverageRemodel.tsx`·`coverageAfterDisplayCache.ts`·
`CoverageRemodelUx182.test.tsx`). 183은 그 위에 쌓였으므로 **Codex는 182 → 183 순서로 분리 커밋**해야 한다.

## Step 1 — 현행 실측 (코드 무변경)

### 배지·투약 표기가 나오는 3곳
| 위치 | 현재 표기 | 형태 |
|---|---|---|
| 화면 `Disclosure.tsx:496~502` | `투약 {med_days}일` (Chip) · `title={windowTip}` · 색 `≥30 amber / >0 emerald / 0 gray` | 라벨+값+색 |
| 리포트 PDF `report_pdf.py:375` | 독립 배지가 아니라 **판정라인(`detail`) 파생** — "투약"·"처방"이 포함된 조각을 그대로 보존 | 문장 조각 |
| 카카오 `main.py:407` | 동일하게 **판정라인 파생** | 문장 조각 |

- ★PDF·카카오에는 "투약 N일" 배지가 **독립적으로 존재하지 않는다**. 그래서 각주/축약문은 배지 옆이 아니라
  **섹션 각주 1회 / 메시지 말미 1줄**로 넣는 것이 맞다.
- 기존 고정 문구는 `report_pdf.py`의 `NO_DISCLOSURE_CRITERIA_NOTE`·`NON_COVERED_NOTE`·`NHIS_CAP_NOTE`처럼
  **모듈 상단 상수 → 템플릿 컨텍스트 주입** 방식이다. 183도 같은 방식을 따른다.
- `main.py`는 이미 `from pipeline.report_pdf import (...)`(51행)로 상수를 가져다 쓴다 →
  **백엔드 두 곳은 상수 1벌을 공유**할 수 있다.

### 213 접이식 패턴 재사용 가능 여부
`DiseaseCard`에 `evidenceOpen` 상태와 "근거 상세 보기 (N건)" 접이식이 이미 있다(508~). 신규 컴포넌트 없이
**같은 패턴의 작은 토글**을 배지 옆에 붙일 수 있다.

### ★툴팁을 쓰지 않기로 한 근거
현재 Chip은 브라우저 native `title` 속성을 쓰는데 **모바일에는 hover가 없어 동작하지 않는다**.
패킷도 "툴팁이 모바일에서 부적합하면 접이식으로 통일"을 허용하므로 **접이식으로 통일**한다.
→ 데스크톱·모바일이 **같은 동작**이므로 `useIsMobile` 분기가 **필요 없다**(패킷 Step 3의 제1원칙은
분기를 쓸 경우의 규칙이며, 분기 자체를 강제하지 않는다). 분기를 만들지 않는 편이 회귀 위험도 낮다.

### 산식 무변경 기준값
`_sum_daily_max_presc` 본문 앞 900바이트 SHA-256(앞 16자리) = **`f92601d87b934c77`** (착수 시점).
검증에서 이 값이 같은지 다시 확인한다.

## Step 2 — 문구 (패킷 확정본 그대로)
- 기본형: `동일 날짜에 여러 처방이 있으면 가장 긴 처방일수 1건만 반영한 합계입니다.`
- 카카오 축약형: `※ 같은 날 복수 처방은 최장 1건만 반영`

★**언어가 달라 물리적 단일 상수는 불가능**하다(프런트 TS / 백엔드 Python). 251 선례(서버·클라이언트가 같은
골든 값을 대조)를 따라 **각 언어에 상수 1개씩 두고, 문자열이 완전히 같은지 테스트로 고정**한다.
백엔드 내부(PDF·카카오)는 `report_pdf.py` 상수 1벌을 `main.py`가 import해 **실제로 공유**한다.

## Step 3~5 — 적용
- **화면**: 투약 배지 옆 작은 토글("산식") → 펼치면 기본형 문구 1줄. 배지 라벨·값·색은 무변경.
- **PDF**: 투약이 실제로 등장할 때만 섹션 각주 1회. 폰트·레이아웃(261) 무변경.
- **카카오**: 투약 항목이 있을 때만 말미에 축약형 1줄. 기존 구조·순서 무변경.

## 검증 결과 (1차 · 2026-08-02 · Windows 로컬)

- [x] ★**`git diff backend/filters.py` 완전 비어 있음** · `_sum_daily_max_presc` 본문 SHA-256(앞 16)
      **`f92601d87b934c77`** — 착수 시점과 **동일**(산식 무변경 증명). 테스트로도 "filters.py에 183 흔적 0"을 고정.
- [x] ★**실데이터 회귀 통과** — 비식별 정본 실 PDF(기본/세부/처방조제) 분석 결과:
      **I10 1,002일 · G45 344일 · E78 210일** — 패킷 기대값과 **정확히 일치**. 값 변동 0.
- [x] `npx tsc -p tsconfig.app.json --noEmit` · `tsconfig.node.json` **PASS** · `npm run lint` **PASS**
- [x] `npm test` **235 passed / 29 files**(182 포함 227 + 신규 8) · 회귀 0
- [x] backend `pytest -q` **803 passed, 8 skipped** — 기준선 792 + **신규 11**, **기존 회귀 0**
- [x] `npm run smoke:coverage` **PASS** · `build:verify` **343,225 B 예상 FAIL**(264~ 동일 수치)
- [x] ★**30일 임계 색 규칙 무변경** — 조건식 `>= 30 ? "amber" : > 0 ? "emerald" : "gray"` 그대로(테스트 고정)
- [x] ★**배지 라벨 무교체** — `투약 {N}일` 바인딩 유지, "처방일수 합계" 등으로 바뀌지 않음
- [x] ★**세 곳 문구 동일 출처** — 프런트 `MED_SUM_FORMULA_NOTE`(disclosureWindow.ts)와
      백엔드 `MED_SUM_FORMULA_NOTE`(report_pdf.py) **문자열 완전 일치**를 양쪽 테스트에서 교차 검증.
      백엔드 내부(PDF·카카오)는 `main.py`가 `report_pdf`에서 import해 **실제로 1벌을 공유**한다.
- [x] PDF 각주는 `total_med_sum`이 있을 때만 렌더(조건·컨텍스트 테스트) · 카카오 축약형은
      **투약 항목이 있을 때만 말미 1줄**(없으면 미삽입·머리 구조 불변)
- [x] ★**HEAD 대비 화면 영향 = 토글 1개뿐**: 결과 화면 요소 수 차이 **정확히 +1**, 설명은 **기본 접힘**,
      **투약 배지 마크업(라벨·색) 완전 동일**. 사본·일회성 스크립트는 **삭제**.
- [x] 설명 줄에 폭 고정·`whitespace-nowrap` 없음(모바일 잘림 방지) · `break-keep` 적용
- [x] `backend/pipeline/` diff = **`report_pdf.py` 문구 상수·컨텍스트 추가뿐**(패킷이 허용한 범위) ·
      `backend/coverage/` diff 0 · `vite.config.*` diff 0

### 판단 기록 2건
1. **툴팁 대신 접이식** — 현행 Chip의 native `title`은 모바일에 hover가 없어 뜨지 않는다. 패킷이 허용한
   "접이식 통일"을 택했고, 그 결과 **데스크톱·모바일 동작이 같아 `useIsMobile` 분기가 불필요**해졌다
   (분기를 만들지 않는 편이 회귀 위험도 낮다).
2. **문구 "단일 상수"의 물리적 한계** — 프런트(TS)·백엔드(Python)는 언어가 달라 한 곳에 둘 수 없다.
   251 선례대로 **각 언어에 1개씩 + 문자열 동일성 테스트**로 계약을 고정했다. 백엔드 두 곳은 실제 1벌 공유.

### 자체 정정 3건 (테스트 쪽 · 제품 코드 영향 0)
1. `_sum_daily_max_presc` 픽스처를 리스트로 만들었는데 실제 구조는 **날짜 → (기관별 dict | 스칼라)** 였다 → 실측 반영.
2. 같은 함수의 기준 인자를 `date`로 넘겼으나 내부가 `datetime` 비교라 타입 오류 → `datetime`으로 정정.
3. 배지 값 검사에 `AnimatedNumber` 카운트업 때문에 렌더 직후 최종값이 없었고, `metric.med`가
   **med_days가 아니라 질문별 표시 규칙**으로 정해진다는 것도 확인 → 값·조건 검사를 소스 계약 검사로 바꿨다.

### 로컬에서 못 한 것 (Codex 몫)
- 375/390/430px 실렌더 넘침(jsdom 레이아웃 미계산) · **PDF 실물에서 각주가 페이지 경계에 걸리지 않는지**
  (로컬은 248 이슈로 실 PDF 렌더 확인이 제한적 — 프로덕션/Codex 렌더 필요).

## Stage 목록 (Codex용)
`src/pages/Disclosure.tsx`, `src/lib/disclosureWindow.ts`(문구 상수), `backend/pipeline/report_pdf.py`(문구 상수·각주),
`backend/main.py`(카카오 1줄), 테스트, `tasks/BOHUMFIT-183-med-badge-label.md`, `handoff.md`, `locks.md`
※제외: 실 PDF·PII·엑셀 원본·시안 HTML·렌더 산출물
※★182 미커밋분과 분리해 **182 → 183 순서로 커밋**할 것.

## 커밋 메시지 (Codex용)
fix(BOHUMFIT-183): 투약 배지 산식 표기 보강(화면·PDF·카카오 통일, 산식 무변경)
