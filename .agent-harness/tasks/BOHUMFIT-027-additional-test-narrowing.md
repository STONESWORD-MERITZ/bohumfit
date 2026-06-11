# BOHUMFIT-027 — 추가검사·재검사 판정 정교화 (과검 축소 + 과소 방지)

- Owner: Cowork (구현) → 검증·푸시 Codex
- 기준: BOHUMFIT-026 진단(handoff 2026-06-07). 알릴의무 핵심 로직(정확도).
- 생성: 2026-06-07

## 확정 방향
- 실제 검사 근거가 있을 때만 의심 소견 부착. 검사 정황 없는 1년 진단은 "1년 내 진단"으로만 표시.
- 확정 4기준: ①선행검사 존재 ②결과로 후속검사 필요 ③단순 추적관찰 아닌가 ④같은날 일련검사 아닌가.
- ★과소 방지 최우선(고지 누락 > 과검). 진짜 후속검사·이상소견 동반 건은 떨구지 말 것.

## 범위 (잠금)
- `backend/pipeline/ai_judgment.py` (가 프롬프트)
- `backend/analyzer.py` (나 후보 게이트 collapse + B 게이팅 헬퍼·배선)
- `backend/tests/` (양방향 회귀)
- `backend/filters.py`, `backend/pipeline/result_builder.py` — 잠금만(수정 없음: Q2 항목 자체는 유지, 게이팅은 analyzer 에서).

## 변경
- **(B) q2_suspicion 검사근거 게이팅** [1순위] — `analyzer.run_analysis`:
  신규 헬퍼 `_codes_with_recent_test_evidence(disease_stats, d1y)` (1년 내 detail_test_events 보유 코드 집합).
  `_suspicion_prompt_items`/`_suspicion_apply_items` 를 이 집합에 속한 코드로 필터 → 검사 근거 없는 항목엔 의심 소견·꼬리표 미부착(항목은 Q2 유지). 화상·피부염 등 과검 제거.
- **(가) 프롬프트** — `MEDICAL_JUDGMENT_SYSTEM_PROMPT [판단 1]`:
  추가검사/재검사 정의 + 확정 4기준 명시. 구 line 103("동일검사 14일+ 2회→true") 의 103↔105 모순 제거 → "동일검사 반복만으로 true 금지, 이상소견 없으면 추적관찰 false". 과소 방지 단서("명백한 이상소견 동반 후속검사를 false 로 떨구지 말 것 — 고지 누락 방지").
- **(나) 후보 게이트 same-day collapse** — `analyzer._build_medical_judgment_inputs`:
  '횟수' 기준을 `len(events)` → `distinct 진료일` 로 collapse(같은날 동일검사 묶음 1과정). **types(2종) 기준은 유지** → 같은날 다종·교차일·이상소견 동반은 후보 보존(과소 방지). 임계값(2회/2종) 자체는 유지.

## 과소 방지 설계 결정 (중요)
- 결정론(나)은 **같은날 '동일검사' 묶음만** 횟수 collapse 한다. 같은날 '다종' 일련검사·교차일 추적관찰은
  결정론에서 후보로 **남긴다** — 이유: 이상소견 신호가 detail_test_events 에 없어, 결정론으로 이들을
  제외하면 진짜 후속검사(예: 같은날 초음파→조직검사+이상)를 떨굴 위험(과소). 따라서 추적관찰 vs
  재검사 최종 판정은 (가) Gemini 4기준에 위임. [제외돼야]의 '같은날 3종'·'교차일 추적관찰'은
  결정론 후보로 남고 프롬프트로 false 처리됨(회귀는 결정론 후보 보존 + 프롬프트 문구로 고정).

## 회귀 (양방향)
- [제외/결정론] 같은날 동일검사 묶음·단일검사 → 후보 아님. 검사근거 없는 진단(화상·피부염) → 의심 미부착.
- [유지/과소방지] 같은날 다종(초음파+조직검사)·교차일 후속 → 후보 유지. 검사근거 있는 코드 → 게이팅 통과.
- [Gemini 위임] 교차일 추적관찰 → 결정론 후보 보존(프롬프트가 false 판단).
- 프롬프트 4기준·동일검사 반복 금지·고지누락 방지 문구 존재.

## 범위 밖
- Q1/Q3/Q4 로직 변경 금지. 실손 모듈 변경 금지. 후보 게이트 임계값(2회/2종) 유지.

## 검증
- `cd backend && python -m pytest -q` (기준선 160 passed/7 skipped 유지 + 신규 `test_additional_test_narrowing.py`)
- `npx tsc` / `npm run build` (백엔드만 변경 — 영향 없음 확인)
- 가능 시 오성심 PDF: 화상·피부염 의심 꼬리표 사라지는지 + 실제 검사근거 항목 유지 확인.
