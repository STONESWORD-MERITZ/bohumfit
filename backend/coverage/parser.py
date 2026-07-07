"""Rule-based parser for KB guaranteed-issue coverage proposal PDFs."""
from __future__ import annotations

import io
import re
from typing import Optional

from .amount import extract_cells, extract_diag_cells, parse_amount, parse_won, years_to_months, diag_status
from .constants import KB_FORMAT_HINTS, ROLE_MARKERS, match_coverage, match_coverage_span

CONTRACT_LINE_RE = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2})\s+"
    r"(?P<cycle>월납|연납|일시납)\s+"
    r"(?P<years>\d+\s*년)\s+"
    r"(?P<maturity>종신|\d+\s*세|\d{4})\s+"
    r"(?P<won>[\d,]+\s*원)"
)
CONTRACT_PREFIX_RE = re.compile(r"^\s*(?P<idx>\d+)\s+(?P<insurer>\S+)\s*(?P<product>.*)$")
CUSTOMER_RE = re.compile(r"(?P<name>\S+)\s*\(\s*(?P<age>\d+)\s*세\s*,\s*(?P<sex>남자|여자)\s*\)")
PAGE_COL_RE = re.compile(r"\((\d+)\)")


class KBFormatError(ValueError):
    """Raised when the PDF is not a supported KB proposal."""


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def classify_page(lines: list[str]) -> Optional[str]:
    head = " ".join(lines[:8])
    compact_head = "".join(head.split())
    for role, marker in (
        ("diagnosis", ROLE_MARKERS["diagnosis"]),
        ("contracts", ROLE_MARKERS["contracts"]),
        ("matrix", ROLE_MARKERS["matrix"]),
    ):
        if "".join(marker.split()) in compact_head:
            return role
    return None


def parse_customer(lines: list[str]) -> dict:
    for line in lines[:8]:
        if "님의" in line:
            name = _clean(line.split("님의", 1)[0])
            if name:
                age_sex = " ".join(lines[:8])
                m = re.search(r"\(\s*(?P<age>\d+)\s*세\s*,\s*(?P<sex>남자|여자)\s*\)", age_sex)
                if m:
                    return {"name": name, "age": int(m.group("age")), "sex": m.group("sex")}
    head = " ".join(lines[:8])
    m = CUSTOMER_RE.search(head)
    if not m:
        return {"name": None, "age": None, "sex": None}
    return {"name": m.group("name"), "age": int(m.group("age")), "sex": m.group("sex")}


def _is_contract_line(line: str) -> bool:
    return bool(CONTRACT_PREFIX_RE.search(line) and CONTRACT_LINE_RE.search(line))


def _is_product_continuation(line: str) -> bool:
    s = _clean(line)
    if not s:
        return False
    if CONTRACT_LINE_RE.search(s) or CONTRACT_PREFIX_RE.search(s):
        return False
    if any(stop in s for stop in ("충청GA", "기준담보", "계약리스트")):
        return False
    if re.fullmatch(r"[\d\s,]+", s):
        return False
    return True


def parse_contract_list(lines: list[str]) -> list[dict]:
    """Parse p5 contract list.

    Product names can wrap before and/or after the date row. We attach adjacent
    continuation lines around each contract row and keep the row order as the
    contract index.
    """
    contracts: list[dict] = []
    used_continuations: set[int] = set()
    for i, line in enumerate(lines):
        m = CONTRACT_LINE_RE.search(line)
        pm = CONTRACT_PREFIX_RE.search(line[: m.start()] if m else "")
        if not m or not pm:
            continue
        parts: list[str] = []
        j = i - 1
        before: list[str] = []
        while j >= 0 and j not in used_continuations and _is_product_continuation(lines[j]):
            before.append(_clean(lines[j]))
            used_continuations.add(j)
            j -= 1
        parts.extend(reversed(before))
        row_product = _clean(pm.group("product"))
        if row_product:
            parts.append(row_product)
        j = i + 1
        if j < len(lines) and j not in used_continuations and _is_product_continuation(lines[j]):
            parts.append(_clean(lines[j]))
            used_continuations.add(j)
        contracts.append(
            {
                "idx": int(pm.group("idx")),
                "insurer": pm.group("insurer"),
                "product": _clean(" ".join(parts)) or None,
                "contract_date": m.group("date"),
                "pay_cycle": m.group("cycle"),
                "pay_years": int(re.sub(r"\D", "", m.group("years"))),
                "pay_months": years_to_months(m.group("years")),
                "maturity": m.group("maturity").replace(" ", ""),
                "monthly_premium": parse_won(m.group("won")),
            }
        )
    return sorted(contracts, key=lambda c: c["idx"])


def _page_contract_indices(lines: list[str]) -> list[int]:
    for line in lines[:20]:
        nums = [int(n) for n in PAGE_COL_RE.findall(line)]
        if nums:
            return nums
    return []


def parse_matrix(pages_lines: list[list[str]]) -> dict:
    """Parse p6~p7 가입현황 matrix into by_company coverage rows."""
    acc: dict[str, dict] = {}
    next_fallback_idx = 1
    for page in pages_lines:
        col_indices = _page_contract_indices(page)
        for line in page:
            meta, _start, end = match_coverage_span(line)
            if not meta or end is None:
                continue
            kb_name, kb_group, group12, agg = meta
            cells = [parse_amount(c) for c in extract_cells(line[end:])]
            if not cells:
                continue
            if not col_indices:
                col_count = max(len(cells) - 1, 0)
                col_indices = list(range(next_fallback_idx, next_fallback_idx + col_count))
            entry = acc.setdefault(
                kb_name,
                {
                    "kb_name": kb_name,
                    "kb_group": kb_group,
                    "group12": group12,
                    "agg": agg,
                    "summary": cells[0],
                    "by_company": {},
                },
            )
            if entry["summary"] is None:
                entry["summary"] = cells[0]
            for idx, val in zip(col_indices, cells[1:]):
                entry["by_company"][str(idx)] = val
        if col_indices:
            next_fallback_idx = max(next_fallback_idx, max(col_indices) + 1)
    return acc


def parse_diagnosis(lines: list[str]) -> dict:
    out: dict[str, dict] = {}
    for line in lines:
        meta, _start, end = match_coverage_span(line)
        if not meta or end is None:
            continue
        kb_name = meta[0]
        vals = [parse_amount(t) for t in extract_diag_cells(line[end:])]
        out[kb_name] = {
            "recommended": vals[0] if len(vals) > 0 else None,
            "enrolled": vals[1] if len(vals) > 1 else None,
            "gap": vals[2] if len(vals) > 2 else None,
            "status": diag_status(line),
        }
    return out


def _extract_pages(pdf_bytes: bytes) -> list[list[str]]:
    import pdfplumber

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            return [(page.extract_text(layout=True) or "").split("\n") for page in pdf.pages]
    except Exception as exc:
        raise KBFormatError(f"PDF를 읽을 수 없습니다: {exc}") from exc


def parse_document(pdf_bytes: bytes) -> dict:
    pages = _extract_pages(pdf_bytes)
    joined_heads = " ".join(" ".join(p[:8]) for p in pages)
    if not all(hint in joined_heads for hint in KB_FORMAT_HINTS):
        raise KBFormatError("KB 표준형 보장분석 제안서 형식이 아닙니다.")

    warnings: list[str] = []
    contracts_lines: list[str] = []
    matrix_pages: list[list[str]] = []
    diagnosis_lines: list[str] = []
    customer = {"name": None, "age": None, "sex": None}

    for lines in pages:
        if customer["age"] is None:
            parsed_customer = parse_customer(lines)
            if parsed_customer["age"] is not None:
                customer = parsed_customer
        role = classify_page(lines)
        if role == "contracts":
            contracts_lines = lines
        elif role == "matrix":
            matrix_pages.append(lines)
        elif role == "diagnosis":
            diagnosis_lines = lines

    contracts = parse_contract_list(contracts_lines) if contracts_lines else []
    matrix = parse_matrix(matrix_pages) if matrix_pages else {}
    diagnosis = parse_diagnosis(diagnosis_lines) if diagnosis_lines else {}

    if not contracts:
        warnings.append("p5 계약리스트를 찾지 못했습니다.")
    if not matrix:
        warnings.append("p6~7 상품별 가입현황 매트릭스를 찾지 못했습니다.")
    if contracts and matrix:
        ncol = max((len(v["by_company"]) for v in matrix.values()), default=0)
        if ncol != len(contracts):
            warnings.append(f"매트릭스 열({ncol})과 계약 수({len(contracts)})가 다릅니다.")

    return {
        "customer": customer,
        "contracts": contracts,
        "matrix": matrix,
        "diagnosis": diagnosis,
        "warnings": warnings,
    }
