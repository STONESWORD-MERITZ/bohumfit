# BOHUMFIT-066 간편심사 수술 판정 동기화 + 합산 기준 명칭 정정 + 비급여 누락 검증

## Owner
- Cowork (진단+구현+회귀) → Codex (Windows 전체 검증·실 PDF 재현·커밋·푸시) → Human (필요 시 정책 확인)

## PHASE 1 진단 (읽기)
### (A) 일반 Q4 vs 간편 Q2 수술 의심 — 두 갈래 원인
1. **result_builder.py L246**: `surgery_suspected_grade`를 `q == "Q4"`일 때만 노출 → 간편 Q2(`is_easy`+q=="Q2")는 등급 ""(누락). 그래서 간편은 "수술 의심 1건"(suspected_n)만, 등급(강/약) 없음.
2. **filters.py `_build_q2_easy`**: 간편 Q2 필터가 확정 입원(`R-E-Q2-INP-10Y`)·확정 수술(`R-E-Q2-SURG-10Y`)만 생성, **공단 '수술 의심' 경로가 아예 없음**(일반 Q4엔 `R-H-Q4-SURG-SUSP-510Y` 존재). 의심-only 질환은 간편 Q2에 항목 자체가 안 생김. 버킷도 입원∪확정수술만 순회.
### (B) "공단 진료비 기준" 문구
- `filters.py:745` reason `f"...수술 의심({_grade}) — 공단 진료비 기준"` + L691 docstring. 056에서 총진료비=공단+본인 합산으로 바뀌었으므로 명칭 부정확.
### (C) 합산식·비급여 — 검증
- `pdf_parser.py:234`: `total_cost = (cur_gongdan or 0) + bonin_cost`. **bonin_cost(2줄 본인부담금)는 항상 무조건 더해짐** → 공단=0(전액본인부담/비급여성) 행도 합산=본인부담금으로 잡힘(누락 0). 실 PDF(19-20) 스캔: 공단=0 행 없음(요양급여내역은 급여 진료만). K05 만성단순치주염=외래 공단83,050+본인35,500=118,550(≥10만)이나 수술 키워드 없음 → 현 로직(외래는 cost≥10만 AND 키워드)서 ''(해제). ※부수: 공단=0 행은 `_extract_nhis_total_cost`가 날짜·전화 숫자 잔여를 미세 가산할 수 있으나 본인부담금은 절대 누락 안 됨(과대평가는 의심판정에 무해).

## PHASE 2 구현
### (A) 간편 Q2 ↔ 일반 Q4 동기화
- `result_builder.py`: 등급 노출 조건 `q=="Q4"` → `(not is_easy and q=="Q4") or (is_easy and q=="Q2")`.
- `filters.py _build_q2_easy`: ① 순회 집합에 `surgery_suspected_dates`(10년) 보유 코드 추가, ② 신규 `R-E-Q2-SURG-SUSP-10Y`(일반 Q4 SURG-SUSP와 동일 — 간편 10년 창) 항목 생성(reason=진료비 합산 기준). 기간 기준(3-10-5: Q2=10년)·입원·확정수술 경로 불변.
### (B) 문구 명칭 정정
- `filters.py:745`(reason)·L691(docstring): "공단 진료비 기준" → "진료비 합산(공단부담금+본인부담금) 기준". 코드 전수 "공단 진료비 기준" 잔존 0.
### (C) 비급여 — 코드 무변경(검증만)
- 합산식이 본인부담금 항상 포함 → 추가 작업 없음. (검증은 회귀 ②③.)
### (2-C) 수술의심 판정근거 문구 — 코드 정확·'이상' 명확
- `Disclosure.tsx`(L448)·`templates/report_disclosure.html`(범례): 065 문구("약=외래 10만원 이상")가 Codex 보정 로직(외래는 cost≥10만 **AND** 수술 키워드)과 불일치 → **코드 정확 문구로 정정**: "진료비 합산(공단부담금+본인부담금)과 수술 관련 행위를 근거로 추정… 입원 50만원 이상, 또는 수술 관련 행위가 동반된 10만원 이상… (강=가능성 높음, 약=가능성 낮음, 금액은 모두 '이상' 기준)". (Codex 065 handoff가 이 정합성 정정을 Human 확인사항으로 남겼던 것을 해소.)

## PHASE 3 검증
- 신규 `tests/test_easy_q2_surgery_sync_066.py`(8): ①간편 Q2 등급==일반 Q4(강·약·입원동반) ④reason "진료비 합산(공단부담금+본인부담금)"·"공단 진료비 기준" 0(health·easy) ②합산=공단+본인 ③비급여성(공단0·본인60만)→합산 본인 포함·강 ⑤임계 '이상' 경계(50만/10만) ⑥065 회귀(K01·K05 해제).
- /tmp(마운트 복구: filters q5 tail 재구성·result_builder std_flagged+return 복구·nhis_constants/surgery_exclusions 재작성·pdf_parser splice) → **066 8/8 + 광범위 85 passed·6 skipped·회귀 0**(test_q4_q5_restructure·test_q_restructure·test_filters·test_nhis·059 포함).
- ⚠ 마운트 손상 심각(filters/result_builder/pdf_parser/test 파일 truncation·NameError `std_flagg`·`asse` 등 — **066 무관 환경결함**, /tmp 복구로 검증). 실파일 Read/Grep로 편집 정합 확인. 전체 pytest·실 PDF는 Codex/Windows 권위.

## 자체 점검
- ☑ 일반Q4·간편Q2 수술 동기화(필터 SURG-SUSP + result_builder 등급) ☑ 합산=공단+본인·본인 누락0(비급여 안전) ☑ "공단 진료비 기준" 전부 정정 ☑ 임계 안내 '이상' 코드정확 ☑ 065 해제(K01·K05) 유지 ☑ 입원·통원·투약 판정 무변경 ☑ 가용 pytest 회귀0.

## Notes — Human
- (2-C) 문구를 Codex 보정 로직(외래 cost≥10만+키워드)에 맞춰 정정함 — 065 단순 문구("외래 10만=약")는 부정확이었음(Codex 065 handoff가 Human 확인 요청한 항목). 정책상 외래 의심 기준 재단순화를 원하면 Human.
- (C) 공단=0 행의 미세 숫자잔여 과대평가는 본인부담금 누락이 아니며 의심판정에 무해. 정밀화는 별도(범위 외).

## Next
- **Codex(Windows)**: 전체 pytest(기준선 367 + 신규 8)·tsc/lint/build·실 PDF 10파일 재현 — 간편 Q2와 일반 Q4의 수술 의심(K60·M51 동일 등급)·문구 정정·K01/K05 해제 유지 확인 → 범위 파일 stage→commit→push. 커밋: `BOHUMFIT-066: 간편 Q2 수술의심 동기화(일반 Q4와 동일 등급) + 합산 기준 명칭 정정 + 비급여 합산 검증`.
- **Human**: 외래 수술의심 정책 문구 최종 확인.
