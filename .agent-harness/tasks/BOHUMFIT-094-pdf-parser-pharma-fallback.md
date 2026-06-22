# BOHUMFIT-094 처방 PDF 오분류 보정
## 증상
헤더 OCR 누락 시 처방 PDF가 다른 문서 유형으로 오분류됨.
페이지 텍스트 신호를 신뢰하도록 보정 필요.
## Scope
- backend/pipeline/pdf_parser.py
- backend/tests/test_pdf_parser.py (회귀 테스트 보강)
## Out of Scope
- 다른 파이프라인 파일 무변경
- 프런트 무변경

## ⚠️ Cowork 진단(2026-06-22)
- 핵심 보정은 **이미 BOHUMFIT-002에 구현·테스트됨**:
  - `_detect_ftype_by_page_text`(기본진료정보/세부진료정보/처방조제 섹션 표제어, 공백 무시) +
    `_resolve_ftype`(강헤더 신뢰, 단 본문=pharma면 detail/basic 강헤더도 pharma로 보정 / 약·unknown 헤더 → 본문 신호 우선).
  - test_pdf_parser.py에 13개 회귀(약헤더→pharma, unknown→본문, 강헤더 pharma 우선, 합본 뒤쪽 처방페이지 등) 존재.
- 잔여 갭(좁음): **표 헤더 + 섹션 표제어가 둘 다 OCR 누락**된 처방 페이지. 이 경우 컬럼 휴리스틱으로 떨어져 오분류 가능.
- 보강(이번 변경): `_detect_ftype_by_page_text`에 처방조제 표 전용 컬럼어 **'투약일수'** 본문 신호를 최후순위로 추가(기본/세부 섹션엔 없는 어휘, 공단 NHIS는 별도 분기라 무영향). 표제어가 있으면 표제어가 우선.
- 더 넓은 키워드(처방전/조제/의약품 단독)는 false positive 위험(세부/기본 본문·상병명에 출현 가능)으로 **추가하지 않음** — 실 PDF 재현 확보 후 별도 검토 권장.
