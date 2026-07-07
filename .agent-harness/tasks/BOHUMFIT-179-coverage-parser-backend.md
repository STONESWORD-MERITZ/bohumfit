# BOHUMFIT-179 — KB 보장분석 제안서 파서 + 데이터 생성 API (백엔드)

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: Cowork(패스1 구현 완료) -> Codex(Windows 검증·실 PDF 패스2 보정·커밋·푸시)

## 배경
178 파싱 규칙 명세(`BOHUMFIT-178-parse-spec.md`) 구현. KB 신정원 보장분석 제안서 PDF를
규칙 기반 파싱해 [전]회사별 세부 / [최종]합산 데이터를 생성하는 백엔드. 프런트는 180.

## A방식 — 2패스
- 실계약 PDF는 PII라 로컬(`C:\Users\18_rk\BOHUMFIT\보장분석\`)에만 존재. Cowork 샌드박스엔 실파일 없음.
- **패스1(Cowork·완료)**: 178 텍스트 패턴으로 파서 골격+집계+스키마+테스트 작성, 문건주 기대값(573,227 등)을 테스트 상수로 검증.
- **패스2(Codex)**: Windows 로컬 실 PDF로 파서 실행 → pdfplumber 실제 좌표·공백과 정규식 대조·보정, 기대값 재확인.

## 178 확정 규칙(Human 승인 — 구현 반영 완료)
- 규칙 기반, KB 신정원 표준양식 전용. 소스 p5(월납·납입기간)·p6~7(회사×담보 매트릭스)·p20(진단).
- 회사 월보험료 내림차순. 12 대분류(+간병/치매).
- 집계: 정액담보(진단비·수술비·사망·후유장해·입원일당)=합산 / 실손=대표값(다건 최대) / 일상생활배상=대표값.
- 총납입 = Σ(계약별 월납×납입개월), 월납합계 = Σ(월납).

## ★설계 원칙 — 기존 파이프라인 격리(준수)
- 신규 모듈 `backend/coverage/`(파서·집계·스키마·서비스) — 고지의무 `backend/pipeline/` 무접촉.
- 기존 `pipeline/coverage_parser.py`(114 `/coverage/parse`)·pdf 유틸 변경 0(참조만).
- PII: 실계약 미저장, 요청-응답 내 처리 후 폐기.

## 산출/변경 (Cowork 패스1)
- `backend/coverage/{__init__,constants,amount,parser,aggregator,schema,service}.py`
- `backend/tests/test_coverage_parser_179.py` (익명 픽스처 11케이스)
- `backend/main.py` — `POST /coverage/analyze` 등록(import + 엔드포인트)

## 검증 체크리스트
- [x] Step 0 진단 + 정규식 취약지점(Codex 보정 대상) handoff 기록
- [x] 문건주 기대값 대조(573,227·181,984,128·상해사망5.5억·일반암1억·교통사고1.8억)
- [x] 12대분류 매핑 + 집계방식(sum/rep max) 정확
- [x] 신규 모듈 기존 파이프라인 무접촉
- [x] PII 미저장·픽스처 익명화(홍길동·합성)
- [x] 179 테스트 11 passed(/tmp·마운트) / 전체 pytest는 Codex 권위(485→496 예상)

## Stage 예정 (Codex)
- backend/coverage/ 신규 + backend/tests/test_coverage_parser_179.py
- backend/main.py (라우터 등록)
- .agent-harness/tasks/BOHUMFIT-179-coverage-parser-backend.md, handoff.md, locks.md
- ★실 PDF·엑셀·PII 미stage. `.gitignore`에 `보장분석/` 추가.

## 커밋 메시지 (Codex)
feat(BOHUMFIT-179): KB 보장분석 제안서 파서 + 데이터 생성 API
