# BOHUMFIT-065 수술의심 임계 재검토(약 오탐) + 판정근거 안내문구 + PDF 파일명

## Owner
- Cowork (진단+구현+회귀) → Codex (Windows 전체 검증·실 PDF 재현·커밋·푸시) → Human (외래 임계 정책 승인)

## PHASE 1 진단 (읽기)
### 1-A 임계·로직 (nhis_history_constants)
- `INPATIENT_STRONG_COST=500,000`(입원 ≥50만 → +2), `OUTPATIENT_WEAK_COST=100,000`(외래 ≥10만 → +1).
- `grade_surgery_suspicion` 점수식: 입원 ≥50만(+2)·외래 ≥10만(+1)·수술 키워드(+1)·062 비수술 제외(−1). score≥2=강, ==1=약.
### 1-B 실 PDF 덤프 (공단 실 PDF, 비번 없이 열린 19-20·20-21만; 16-18은 비번 PII로 잠김)
- **K01 상악제3대구치의매복**: 외래, 공단 27,620 + 본인 11,700 = **합산 39,320원**(<10만). `상병명 매복`이 `nhis_surg_keywords`("매복") 매칭 → **키워드 +1 → 약**.
- 대조 **M512**: 입원, 총진료비 561,190(≥50만) → +2 → 강. **K605**: 입원 고액 → 강. (정상)
- K05는 잠긴 파일(16-18)에 있어 직접 덤프 불가(비번 PII 미보유). 코드상 동일 메커니즘(저액 외래 + 치과 키워드).
### 1-C 오탐 판정 — **핵심**
- 오탐 원인은 **외래 임계값(10만)이 낮아서가 아님**. 진짜 원인 = **수술 키워드 가중(+1)이 외래 cost 문턱을 우회**해, 저액(3~4만원) 외래 치과(매복/발치)가 키워드만으로 '약'이 됨.
- 따라서 임계 VALUE 상향이 아니라 **키워드 가중을 cost≥10만일 때만 적용**해야 정확. 입원 고액(강)은 영향 0.

## PHASE 2 구현
### 2-A 임계 (backend/pipeline/nhis_history_constants.py)
- `grade_surgery_suspicion`: 수술 키워드 가중을 `total_cost >= OUTPATIENT_WEAK_COST`일 때만 +1. (임계 상수값 무변경 — 10만/50만 유지.)
- 효과: K01(39,320 외래+매복) → '' (해제). 입원 고액 M51/K60/K63 → 강 유지. 외래 고액(≥10만)+키워드 → 강 유지. 기존 `test_grade_thresholds_unit` 6 단언 전부 보존(모두 cost≥10만 케이스).
### 2-B 판정근거 안내문구 (실제 확정 임계 명시 — 추측 아님)
- `src/pages/Disclosure.tsx`(L448): "…진료비(공단+본인 부담금 합산) 기준으로 추정… **강(가능성 높음)=입원 50만원 이상, 약(가능성 낮음)=외래 10만원 이상.** 실제 수술 여부는 고객님 확인이 필요합니다."
- `backend/templates/report_disclosure.html` 유의사항에 동일 범례 `<p>` 추가(PDF는 칩만이라 기준 불명 → 범례).
### 2-C PDF 파일명 (고객이름+분석기준일)
- 이름 출처 = **공단 PDF 1페이지 `성명 ○○○ 주민등록번호`** (가장 안정적·authoritative). `pdf_parser._extract_patient_name`로 **성명만** 추출(주민번호 등 다른 PII 절대 미추출), 없으면 "".
- 체인(additive·판정 무관): `pdf_parser`(parse_single_pdf result `patient_name`) → `analyzer._parse_all_pdfs`(첫 비어있지 않은 값 수집, 3-tuple 반환) → `run_analysis` result `customer_name` → `main.py` analyze 응답 `customer_name`.
- 프런트(Disclosure.tsx): `a.download = 보험핏-고지내역-{성명}-{기준일(refDate)}.pdf`, 이름 없으면 `보험핏-고지내역-{기준일}.pdf`(폴백). 공백·특수문자 제거·길이 20 제한.
- 백엔드(main.py report endpoint): Content-Disposition을 payload `customer_name`+`reference_date`로 구성(RFC 5987 `filename*` + ASCII `filename` 병기). 프런트 payload에 `customer_name` 추가.

## PHASE 3 검증
- 신규 `tests/test_surgery_threshold_065.py`(5: 저액외래+키워드→미판정·입원고액 강·외래경계+키워드게이트·상수값·성명추출[주민번호 미노출·폴백]) + `tests/test_report_filename_065.py`(3: 이름+기준일·폴백·특수문자 sanitize).
- /tmp(마운트 복구: nhis_constants/surgery_exclusions 재작성·pdf_parser·main tail 재구성·report_pdf stub·slowapi/multipart) → **065 8/8 + 광범위 92 passed·회귀 0**(059/062/056 nhis·필터·집계·060/063 포함).
- ⚠ analyzer-body 의존(test_analyze_fast_path·test_dynamic_ai_budget skip-path)·test_nhis_history·report 테스트는 마운트 truncation(analyzer /tmp 980 vs 실 ~1130, run_analysis return 절단으로 None — **065 무관 환경결함**)으로 /tmp 불가 → Codex/Windows. 실파일 Read/Grep로 customer_name 체인(pdf_parser·analyzer L249/258/280/309/323/934·main L566/L634)·grade 게이트 정합 확인.

## 자체 점검
- ☑ 임계 전수(50만/10만·점수식) ☑ K01 39,320 외래·매복 키워드 구동 약(실 PDF) 특정 ☑ 키워드 cost-floor 게이트(임계값 무변경)·강 회귀0 ☑ 문구에 실제 임계(50만/10만) 명시 ☑ 파일명 성명(공단)+기준일·폴백·sanitize ☑ 입원·통원·투약 판정 무변경(수술의심 등급만) ☑ 가용 pytest 회귀0.

## Notes — Human 확인
- **외래 임계 정책**: 임계 VALUE(10만)는 유지하고 **키워드 가중을 cost≥10만으로 게이트**하는 방식 채택(진단 결과 기반 — 단순 임계 상향은 K01 같은 키워드 구동 오탐을 못 막음). 정책 승인/대안(예: 외래 약을 cost only로) 필요 시 Human.
- **K05 확인**: K05(만성단순치주염)는 비번 잠긴 공단 파일(16-18, PII 생년월일 미보유)에 있어 직접 덤프 못 함. 동일 메커니즘으로 저액 외래면 해제됨. **Codex가 전체(비번) 데이터로 K05 1→0 재현 권위**.
- **파일명 PII**: 성명은 출력 파일명용(태스크 허용). 주민번호 등은 추출/응답/커밋 안 함. 실 PDF 로컬만.

## Next
- **Codex(Windows)**: 전체 pytest(기준선 359 + 신규 8)·tsc/lint/build·실 PDF(10파일, 비번) 재현 — K01·K05 수술의심 해제·M51/K60/K63 강 유지·파일명 성명+기준일·문구 임계 확인 → 범위 파일 stage→commit→push. 커밋: `BOHUMFIT-065: 수술의심 키워드 cost-floor 게이트(약 오탐 제거) + 판정근거 임계 문구 + PDF 파일명 고객명·기준일`.
- **Human**: 외래 임계 정책 승인.
