"""오케스트레이터: KB 제안서 PDF → {before, final, warnings}."""
from __future__ import annotations

from .parser import parse_document, KBFormatError  # noqa: F401
from .aggregator import build_before, build_final
from .proposal_parser import ProposalParseError, parse_proposal_files  # noqa: F401


def analyze_kb_coverage(pdf_bytes: bytes) -> dict:
    """KB 신정원 보장분석 제안서 PDF 바이트 → 리모델링 [전]/[최종] 데이터.

    비-KB/손상 PDF는 KBFormatError(ValueError) 발생 → 라우터에서 400.
    ※ PII: pdf_bytes/파싱 중간물은 서버에 저장하지 않는다(호출부에서 즉시 폐기).
    """
    raw = parse_document(pdf_bytes)
    before = build_before(raw)
    final = build_final(before, raw.get("diagnosis", {}))
    return {"before": before, "final": final, "warnings": raw.get("warnings", [])}


def parse_newproposal_files(files: list[tuple[str, bytes]]) -> dict:
    """회사별 신규 가입제안서 PDF 바이트 목록 → 컨설팅 신규제안 목록.

    PDF 원본과 추출 텍스트는 저장하지 않고 요청 처리 중 메모리에서만 사용한다.
    """
    return parse_proposal_files(files)
