# BOHUMFIT-179b — 보장분석 파서 보강 (기타 대분류 + 계약 특이사항 비고)

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: Cowork(구현 완료) -> Codex(Windows 검증·실 PDF 패스2 보정·커밋·푸시)

## 배경 (Human 확정)
179 파서는 37 표준담보(p6~7)→12대분류로 매핑하나, KB 제안서 상세페이지(p8~15)에는
N대수술비·화상·폴립/양성종양·상급/종합병원 수술비·상급/종합 입원일당·통원일당 등 표준 외 항목이 있음.
Human 결정: ① 이 항목들 → "기타" 대분류 신설(12→13) ② 계약 특이사항(계피관계 등) → 값이 아닌 비고 메모.

## 179 관계
- 179 파서(backend/coverage/) 확장 — 기존 37/12 로직 무접촉(append만). 179 기대값 회귀 무결.

## Step 0 — 진단 (완료, 실 PDF 문건주 자료)
- 상세페이지(p8~15) 구조: `[순번][정액/실손][상품담보명 col3][KB표준매핑명 col4][금액(만/억)]`. 계피 = 헤더 "계약자/피보험자"(예: 문건주/문건주=동일).
- ★상세 col4 네임스페이스는 37 기본형과 별개(암진단/특정질병수술 등 100+) → 잔여버킷 부적합. **태스크가 열거한 비표준 패턴만 기타로 포섭**(37/12 중복 0).
- 문건주 실제 기타 항목: N대수술비(112대질병수술비Ⅰ~Ⅵ·5대장기이식·[갱신형]5대골절수술비)·양성종양/폴립·중대화상·상급/종합병원 입원일당. (N대수술비 라벨엔 5대장기이식 등 포함 / 통원일당은 문건주 자료엔 없음)
- 계피: 전 계약 문건주/문건주(동일). 삼성 상세(p12~15) 계피 라인 포맷 상이 → 일부 미검출(Codex 보정점).

## Step 1~2 — 구현 (완료)
- `constants.py`: `GROUP_ETC="기타"`, `GROUP13`(12+기타), `EXTRA_PATTERNS`(상급/종합병원 일당·수술비 → N대수술비 → 화상 → 양성종양/폴립 → 통원일당, 구체 우선) + `classify_extra(text)→(label,agg)`. 기본형/표준담보는 None(회귀 안전).
- `parser.py`: `classify_page`에 detail 역할(‘상품별 가입담보상세’, matrix보다 우선) 추가. `parse_detail_pages(detail_pages, contracts)` → (notes, extra). 계약 식별=상세헤더 월보험료(원, 계약별 고유)→p5 idx. 계피 A/B 추출. 기타 행=classify_extra 매치 + 마지막 금액. `parse_document` 반환에 notes·extra 추가.
- `schema.py`: Contract.remark(비고) 필드. `aggregator.py`: 계피 비고 주입(`_remark` — 계피상이 시 계약자≠피보험자), 기타 대분류 coverage append(group="기타", 정액 합산), rollup GROUP13.
- `service.py`/`main.py`: 179 엔드포인트가 확장 데이터(before.기타·companies.remark·rollup 기타) 자동 반환(코드 변경 불필요).

## Step 3 — 테스트 (완료)
- `backend/tests/test_coverage_parser_179b.py` 7케이스 + 179 회귀 11케이스 = **18 passed**(/tmp·마운트).
- 검증: 기타 집계 N대수술비 4,090만·화상 6,000만·양성종양/폴립 30만·상급/종합 일당 120만 / 계피 동일·상이 감지 / **179 값(573,227·181,984,128·상해사망 5.5억·일반암 1억·입원일당 6만) 불변** / 37 기본형 수 유지·상세 표준담보(상해사망 등) 기타 미포섭.

## 수정 금지 (준수)
- 고지의무 파이프라인 / 179의 12대분류·집계 로직(값 무변경, append만) / 프런트(180) / 총납입·월납 산식.

## 검증 체크리스트
- [x] Step 0 미매핑/비표준 담보 전수 + 계피 소스 handoff 기록
- [x] 기타 대분류 매핑 + 집계방식(정액 합산)
- [x] 계약 비고(계피) 추출
- [x] 179 기대값 회귀 무결(12대분류·월납·총납입)
- [x] 179b 테스트 18 passed(/tmp·마운트) / 전체 pytest는 Codex 권위(기준선 496→+7=503 예상)
- [ ] 실 PDF 검증(삼성 상세 계피 포맷·상품명 wrap·추가 기타 패턴)은 Codex 로컬

## Stage 예정 (Codex)
- backend/coverage/{constants,parser,aggregator,schema}.py (변경분)
- backend/tests/test_coverage_parser_179b.py
- .agent-harness/tasks/BOHUMFIT-179b-coverage-parser-etc.md, handoff.md, locks.md
- ★실 PDF·PII stage 금지 (.gitignore 보장분석/ 유지)

## 커밋 메시지 (Codex)
feat(BOHUMFIT-179b): 보장분석 파서 기타 대분류 + 계약 특이사항 비고
