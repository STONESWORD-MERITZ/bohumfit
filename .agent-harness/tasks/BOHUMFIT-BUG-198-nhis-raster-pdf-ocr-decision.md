# BOHUMFIT-BUG-198 - 건강보험 요양급여내역 래스터 PDF 파싱 긴급 진단

Owner flow: Human -> Codex Windows
Current owner: Human (deployment confirmation)
Status: Completed - OCR remains deferred; image-PDF fallback guidance only.

## Intent

- 심평원 건강보험 요양급여내역 PDF가 정상 파일인데도 이미지 PDF 안내로 실패한다는 신고를 S0에서 재현하고 원인을 분리한다.
- 기존 텍스트 기반 파서를 무리하게 변경하지 않고, OCR이 필수인 경우 Human 결정으로 넘긴다.

## Scope

- Allowed: `backend/pipeline/pdf_parser.py` image-PDF fallback copy only, `backend/tests/test_pdf_parser.py`, this task/handoff/locks documentation.
- Excluded: other pipeline analysis/parsing logic, `backend/coverage/`, Supabase, OCR dependency installation, real PDF/PII storage or staging.

## S0 Findings

- User-provided PDF: 5 pages. `pdfplumber` returned 0 characters, 0 words, and 0 non-whitespace characters on every page.
- `pdfminer` found 0 layout text characters; all pages contain image objects (two per page), while the visible table and watermark are raster graphics. `pdftotext` is unavailable in this Windows environment.
- A sanitized `parse_single_pdf` smoke (`redacted-nhis.pdf`) returned 0 records and the current image-PDF guidance. The fallback is therefore correct for this file, not a false positive.
- The existing `parse_nhis_text` understands the semantic two-row NHIS layout (date/sequence/institution/cost then sequence/visit/disease/code/cost), but it only receives extracted text. This raster layout cannot enter that parser.
- Watermark is not mixed into extracted text; it is part of the raster image and must be considered in any OCR preprocessing/accuracy work.
- No OCR stack is currently available: `pytesseract`, `pdf2image`, and `tesseract` executable are absent. Implementing OCR requires new dependencies and runtime setup.

## Human Decision Required

1. Approve an OCR approach and deployment/runtime ownership. A server-local Korean OCR stack requires image rendering, Korean language data, binary/runtime packaging, quality and performance testing.
2. If an external OCR provider is considered, approve its PII/medical-information transmission, retention, consent, and vendor-security policy before implementation.
3. Confirm the acceptance target for this form: all 49 rows, institution/date/disease code/cost extraction, and watermark-tolerant accuracy benchmark using anonymized synthetic fixtures.

## Follow-up: Fallback Guidance Only

- Keep the existing image-PDF threshold exactly as-is: `first_text.strip()` is empty (0 non-whitespace extracted characters).
- Change only the image-PDF fallback copy to explain why the file cannot be analyzed and guide users to download the original text-containing PDF from Government24 or The건강보험 app/web.
- Add anonymous synthetic regression tests for an empty/whitespace-only PDF and a text-containing NHIS PDF. No OCR, parsing rule, dependency, or real-PDF fixture is introduced.

## Verification

- S0 was performed without storing text or copying the real PDF into the repository.
- A temporary local render was deleted immediately after visual inspection.
- `python -m pytest tests/test_pdf_parser.py -vv`: `20 passed`.
- `python -m pytest tests/test_nhis_history.py -vv`: `9 passed`.
- `python -m pytest -q`: `566 passed, 8 skipped` (previous 563 baseline plus 3 new fallback tests).
- Read-only real raster PDF smoke with a redacted filename: 0 records and the new original-PDF download guidance; no PII printed, stored, staged, or committed.
- The S0 stage added no dependency, migration, or real-data fixture. The follow-up changed fallback copy and anonymous synthetic tests only.
