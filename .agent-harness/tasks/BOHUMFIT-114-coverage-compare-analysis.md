# BOHUMFIT-114: 보장 비교분석 기능 구현
## 목표
기존 "보장 비교분석" 페이지(/coverage-compare)를 실제 작동하는 기능으로 구현(현재 "준비 중").
## 지원 PDF 형식
### 보장분석서 (현재 보험 현황·doc_type=current)
- 한화손보 보장분석서(형식 지정 파싱), KB손보 보장분석서(형식 지정 파싱)
### 가입제안서 (신규 담보·doc_type=proposal)
- 모든 손보/생보 범용 텍스트 파싱. 회사/상품 무관 담보명·보장금액·보험료 추출.
- 파싱 실패 시 throw 금지, 추출된 것만 반환. 회사별 보정 레이어는 추후.
## 백엔드
- backend/pipeline/coverage_parser.py(신규): parse_hanwha_current / parse_kb_current /
  parse_proposal_generic / _detect_insurer / _extract_premium / _extract_coverages /
  parse_coverage_pdf(pdf_bytes, doc_type) 진입점. 반환: insurer·doc_type·contracts[]·summary·parse_warnings.
- backend/main.py: POST /coverage/parse (multipart file+doc_type, verify_jwt, 크기/확장자 검증,
  PDF 열기 실패 400·그외 파싱오류는 warnings 기록 후 200).
- backend/tests/test_coverage_parser.py(신규): 한화/KB current mock·proposal 범용 mock·빈/이미지 PDF·parse_warnings.
## 프런트
- src/pages/CoverageCompare.tsx 전면 재작성: Step1 현재보험 업로드(해지/담보삭제 체크) → Step2 제안서 업로드(다중) → Step3 비교 리포트(세부 비교표·요약표·인쇄). 비로그인은 Step1까지·분석 시작 시 로그인 유도.
## ★ 개인정보
- 업로드 실 PDF(한대원 등)는 로컬 형식 파악용. PII·실 PDF 미커밋. 테스트는 mock 텍스트만.
## 검증
- cd backend && pytest -q / tsc app·node / lint / npm test / build
