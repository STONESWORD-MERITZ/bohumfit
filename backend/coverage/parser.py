"""Rule-based parser for KB guaranteed-issue coverage proposal PDFs."""
from __future__ import annotations

import io
import re
from typing import Optional

from .amount import extract_cells, extract_diag_cells, parse_amount, parse_won, years_to_months, diag_status
from .constants import (
    KB_FORMAT_HINTS,
    KNOWN_INSURERS,
    ROLE_MARKERS,
    classify_extra,
    extract_n_surgery,
    match_coverage,
    match_coverage_span,
)

CONTRACT_LINE_RE = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2})\s+"
    r"(?:(?P<cycle>월납|연납|일시납)\s+)?"
    r"(?:(?P<years>\d+\s*년)\s+)?"
    r"(?P<maturity>종신|\d+\s*세|\d{4})\s+"
    r"(?P<won>[\d,]+\s*원|보험료\s*미제공|보험료미제공|미제공)"
)
CONTRACT_PREFIX_RE = re.compile(r"^\s*(?P<idx>\d+)\s+(?P<insurer>\S+)\s*(?P<product>.*)$")
CUSTOMER_RE = re.compile(r"(?P<name>\S+)\s*\(\s*(?P<age>\d+)\s*세\s*,\s*(?P<sex>남자|여자)\s*\)")
PAGE_COL_RE = re.compile(r"\((\d+)\)")
DETAIL_PREMIUM_RE = re.compile(r"(?P<premium>[\d,]+)\s*원")
KP_RE = re.compile(r"(?P<contractor>[가-힣*]{2,10})\s*/\s*(?P<insured>[가-힣*]{2,10})")


class KBFormatError(ValueError):
    """Raised when the PDF is not a supported KB proposal."""


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _despace(text: str | None) -> str:
    return "".join((text or "").split())


def _strip_despace_fragment(text: str, fragment: str) -> str:
    compact = ""
    positions: list[int] = []
    for pos, ch in enumerate(text):
        if ch.isspace():
            continue
        positions.append(pos)
        compact += ch
    target = _despace(fragment)
    start = compact.find(target)
    if start < 0:
        return text
    end = start + len(target) - 1
    return _clean(text[: positions[start]] + " " + text[positions[end] + 1 :])


def _strip_leading_despace_fragment(text: str, fragment: str) -> str:
    compact = ""
    positions: list[int] = []
    for pos, ch in enumerate(text):
        if ch.isspace():
            continue
        positions.append(pos)
        compact += ch
    target = _despace(fragment)
    if not target or not compact.startswith(target):
        return _clean(text)
    end = len(target) - 1
    return _clean(text[positions[end] + 1 :])


_KNOWN_INSURERS_BY_LEN = sorted(KNOWN_INSURERS, key=lambda value: len(_despace(value)), reverse=True)


def _known_insurer_in(text: str) -> str | None:
    compact = _despace(text)
    for insurer in _KNOWN_INSURERS_BY_LEN:
        if _despace(insurer) in compact:
            return insurer
    return None


def _fallback_insurer(value: str) -> str | None:
    value = _clean(value)
    if not value:
        return None
    if re.search(r"(손보|화재|생명|해상|손해보험|생명보험)$", value):
        return value
    return None


def _split_known_insurer(row_insurer: str, after_parts: list[str]) -> tuple[str | None, list[str]]:
    left = _despace(row_insurer)
    if not left:
        return None, after_parts
    for insurer in _KNOWN_INSURERS_BY_LEN:
        compact = _despace(insurer)
        if not compact.startswith(left) or compact == left:
            continue
        suffix = compact[len(left) :]
        for idx, part in enumerate(after_parts):
            if _despace(part).startswith(suffix):
                updated = list(after_parts)
                updated[idx] = _strip_leading_despace_fragment(part, suffix)
                return insurer, updated
    return None, after_parts


def _contract_prefix_source(lines: list[str], row_idx: int, row_prefix: str, used: set[int] | None = None) -> str:
    row_match = CONTRACT_PREFIX_RE.search(row_prefix)
    if row_match and _clean(row_match.group("product")):
        return _clean(row_prefix)
    prefix: list[str] = []
    for j in range(row_idx - 1, max(row_idx - 5, -1), -1):
        if used and j in used:
            continue
        prev = _clean(lines[j])
        if not prev:
            continue
        if CONTRACT_LINE_RE.search(prev):
            break
        if any(stop in prev for stop in ("충청GA", "기준담보", "계약리스트")):
            break
        prefix.insert(0, prev)
        if CONTRACT_PREFIX_RE.search(prev):
            break
    if row_match:
        return _clean(" ".join([_clean(row_prefix), *prefix]))
    prefix.append(_clean(row_prefix))
    idx_only = re.fullmatch(r"\s*(\d+)\s*", row_prefix or "")
    if idx_only and prefix:
        return _clean(" ".join([idx_only.group(1), *prefix[:-1]]))
    return _clean(" ".join(prefix))


_INSURER_HEAD_RE = re.compile(r"^([가-힣A-Za-z()·]{0,14}?(?:손해보험|생명보험|손보|생명|화재|해상))")
_INSURER_JOINED_RE = re.compile(r"^[가-힣A-Z][가-힣A-Za-z()·]*(?:손해보험|생명보험|손보|생명|화재|해상)$")


def _join_split_insurer_fragments(
    lines: list[str], row_idx: int, row_insurer: str, after_parts: list[str]
) -> tuple[str | None, list[str], bool]:
    """BOHUMFIT-234 ⑥①: 셀 안에서 세로로 쪼개진 보험사명 복원.

    예: "메리츠화"(윗줄)+"재"(아랫줄), "라이나(에"(행 안)+"이스)손보"(아랫줄).
    결합 후보를 KNOWN_INSURERS 우선으로, 실패 시 보험사 접미 종결형으로 판정한다.
    반환: (insurer, 갱신된 after_parts, 행 안 조각 사용 여부).
    """
    row_frag = _despace(row_insurer)
    if row_frag and (any(ch.isdigit() for ch in row_frag) or len(row_frag) > 10):
        row_frag = ""
    after_head = _despace(after_parts[0]) if after_parts else ""
    head_match = _INSURER_HEAD_RE.match(after_head) if after_head else None
    head = head_match.group(1) if head_match else ""

    prev_frag = ""
    if row_idx > 0:
        prev = _clean(lines[row_idx - 1])
        if prev and not CONTRACT_LINE_RE.search(prev):
            compact_prev = _despace(prev)
            if 0 < len(compact_prev) <= 8 and not any(ch.isdigit() for ch in compact_prev):
                prev_frag = compact_prev

    # (결합명, row조각 사용, after에서 소비할 접두)
    candidates: list[tuple[str, bool, str]] = []
    for frag, row_used in ((row_frag, True), (prev_frag, False)):
        if not frag:
            continue
        # 접미 경계가 조각 사이에 걸린 경우("메리츠화"+"재") — after 접두 1~6자를 붙여 KNOWN 대조.
        for k in range(1, min(6, len(after_head)) + 1):
            candidates.append((frag + after_head[:k], row_used, after_head[:k]))
        if head:
            candidates.append((frag + head, row_used, head))
    if prev_frag and row_frag:
        candidates.append((prev_frag + row_frag, True, ""))

    for candidate, row_used, consumed_head in candidates:
        known = _known_insurer_in(candidate)
        if known and _despace(known) != candidate:
            known = None  # 결합명이 KNOWN 전체와 정확히 일치할 때만 채택(부분 포함 오인 방지)
        joined = known or (
            candidate if _INSURER_JOINED_RE.match(candidate) and len(candidate) >= 4 else None
        )
        if not joined:
            continue
        updated = list(after_parts)
        if consumed_head and updated:
            remainder = _strip_leading_despace_fragment(updated[0], consumed_head)
            if remainder:
                updated[0] = remainder
            else:
                updated = updated[1:]
        return joined, updated, row_used
    return None, after_parts, False


def classify_page(lines: list[str]) -> Optional[str]:
    head = " ".join(lines[:8])
    compact_head = "".join(head.split())
    for role, marker in (
        ("diagnosis", ROLE_MARKERS["diagnosis"]),
        ("contracts", ROLE_MARKERS["contracts"]),
        ("detail", ROLE_MARKERS["detail"]),
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
        if not m:
            continue
        prefix_source = _contract_prefix_source(lines, i, line[: m.start()], used_continuations)
        pm = CONTRACT_PREFIX_RE.search(prefix_source)
        if not pm:
            continue
        row_product = _clean(pm.group("product"))
        after_parts: list[str] = []
        j = i + 1
        if j < len(lines) and j not in used_continuations and _is_product_continuation(lines[j]):
            after_parts.append(_clean(lines[j]))
            used_continuations.add(j)
        split_insurer, after_parts = _split_known_insurer(pm.group("insurer"), after_parts)
        insurer = split_insurer or _known_insurer_in(" ".join([prefix_source, *after_parts])) or _fallback_insurer(pm.group("insurer"))
        if insurer is None:
            # BOHUMFIT-234 ⑥①: 보험사명이 셀 안에서 세로로 쪼개진 양식 복원
            # (예: "메리츠화"/"재", "라이나(에"/"이스)손보"). 인접 조각을 결합해
            # KNOWN 매칭 또는 보험사 접미(손보·생명·화재 등) 종결 매칭으로 채운다.
            insurer, after_parts, row_frag_used = _join_split_insurer_fragments(
                lines, i, pm.group("insurer"), after_parts
            )
            if insurer is not None and row_frag_used:
                # 행 안의 보험사 조각은 상품명에서 제거한다(무배당 등 비조각 토큰은 보존).
                prefix_source = _strip_despace_fragment(prefix_source, pm.group("insurer"))
        if split_insurer:
            product = row_product
        elif insurer and _despace(pm.group("insurer")) == _despace(insurer):
            product = row_product
        elif insurer:
            product = _strip_despace_fragment(prefix_source, insurer)
            product = re.sub(r"^\s*\d+\s+", "", product)
        else:
            product = row_product
        product = _clean(" ".join([product, *after_parts]))
        years = m.group("years")
        contracts.append(
            {
                "idx": int(pm.group("idx")),
                "insurer": insurer,
                "product": product or None,
                "contract_date": m.group("date"),
                "pay_cycle": m.group("cycle"),
                "pay_years": int(re.sub(r"\D", "", years)) if years else None,
                "pay_months": years_to_months(years) if years else None,
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


def _matrix_contract_indices(matrix: dict) -> set[int]:
    out: set[int] = set()
    for row in matrix.values():
        for key in row.get("by_company", {}):
            try:
                out.add(int(key))
            except (TypeError, ValueError):
                continue
    return out


def _ensure_contracts_for_matrix_columns(contracts: list[dict], matrix: dict) -> list[dict]:
    existing = {int(c["idx"]) for c in contracts if c.get("idx") is not None}
    missing = sorted(_matrix_contract_indices(matrix) - existing)
    if not missing:
        return contracts
    completed = list(contracts)
    for idx in missing:
        completed.append(
            {
                "idx": idx,
                "insurer": None,
                "product": None,
                "contract_date": None,
                "pay_cycle": None,
                "pay_years": None,
                "pay_months": None,
                "maturity": None,
                "monthly_premium": None,
                "remark": "보험료 미제공",
            }
        )
    return sorted(completed, key=lambda c: c["idx"])


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


def _detail_contract_idx(lines: list[str], premium_to_idx: dict[int, int]) -> Optional[int]:
    for line in lines[:16]:
        if not re.search(r"\d{4}-\d{2}-\d{2}\s*~\s*\d{4}-\d{2}-\d{2}", line):
            continue
        premiums = [parse_won(m.group("premium") + "원") for m in DETAIL_PREMIUM_RE.finditer(line)]
        for premium in reversed(premiums):
            if premium in premium_to_idx:
                return premium_to_idx[premium]
    return None


def _last_amount(line: str):
    vals = [parse_amount(t) for t in extract_cells(line)]
    for value in reversed(vals):
        if value:
            return value
    return None


def parse_detail_pages(detail_pages: list[list[str]], contracts: list[dict]):
    """Parse detailed pages for contract remarks and non-standard 기타 riders."""
    premium_to_idx = {c["monthly_premium"]: c["idx"] for c in contracts if c.get("monthly_premium")}
    notes: dict[int, dict] = {}
    extra: dict[str, dict] = {}

    for lines in detail_pages:
        idx = _detail_contract_idx(lines, premium_to_idx)
        for line in lines[:16]:
            if "월납" not in line and "연납" not in line and "일시납" not in line:
                continue
            match = KP_RE.search(line)
            if match and idx is not None and idx not in notes:
                contractor = match.group("contractor")
                insured = match.group("insured")
                notes[idx] = {
                    "contractor": contractor,
                    "insured": insured,
                    "kp_differs": contractor != insured,
                }
                break

        for line in lines:
            classified = classify_extra(line)
            if not classified:
                continue
            amount = _last_amount(line)
            if amount is None:
                continue
            label, agg = classified
            entry = extra.setdefault(label, {"agg": agg, "by_company": {}})
            key = str(idx) if idx is not None else "?"
            entry["by_company"][key] = entry["by_company"].get(key, 0) + amount
            # BOHUMFIT-237 C: N대수술비는 원문의 N(131대 등)을 채집해 표시명 병기에 쓴다.
            if label == "N대수술비":
                n = extract_n_surgery(line)
                if n is not None:
                    values = entry.setdefault("n_values", [])
                    if n not in values:
                        values.append(n)

    return notes, extra


def parse_document(pdf_bytes: bytes) -> dict:
    pages = _extract_pages(pdf_bytes)
    joined_heads = " ".join(" ".join(p[:8]) for p in pages)
    if not all(hint in joined_heads for hint in KB_FORMAT_HINTS):
        raise KBFormatError("KB 표준형 보장분석 제안서 형식이 아닙니다.")

    warnings: list[str] = []
    contracts_pages: list[list[str]] = []
    matrix_pages: list[list[str]] = []
    detail_pages: list[list[str]] = []
    diagnosis_lines: list[str] = []
    customer = {"name": None, "age": None, "sex": None}

    for lines in pages:
        if customer["age"] is None:
            parsed_customer = parse_customer(lines)
            if parsed_customer["age"] is not None:
                customer = parsed_customer
        role = classify_page(lines)
        if role == "contracts":
            # BOHUMFIT-234 ⑥: 계약이 많으면 계약리스트가 여러 페이지로 이어진다 —
            # 마지막 페이지만 남기던 덮어쓰기를 누적으로 교체(234 실사용: 15계약 중 1건만 파싱되던 결함).
            contracts_pages.append(lines)
        elif role == "matrix":
            matrix_pages.append(lines)
        elif role == "detail":
            detail_pages.append(lines)
        elif role == "diagnosis":
            diagnosis_lines = lines

    contracts = []
    seen_contract_idx: set[int] = set()
    for contract_lines in contracts_pages:
        for contract in parse_contract_list(contract_lines):
            if contract["idx"] in seen_contract_idx:
                continue
            seen_contract_idx.add(contract["idx"])
            contracts.append(contract)
    contracts.sort(key=lambda c: c["idx"])
    matrix = parse_matrix(matrix_pages) if matrix_pages else {}
    if contracts and matrix:
        contracts = _ensure_contracts_for_matrix_columns(contracts, matrix)
    diagnosis = parse_diagnosis(diagnosis_lines) if diagnosis_lines else {}
    notes, extra = parse_detail_pages(detail_pages, contracts) if detail_pages else ({}, {})

    if not contracts:
        warnings.append("p5 계약리스트를 찾지 못했습니다.")
    if not matrix:
        warnings.append("p6~7 상품별 가입현황 매트릭스를 찾지 못했습니다.")
    if contracts and matrix:
        contract_indices = {int(c["idx"]) for c in contracts if c.get("idx") is not None}
        matrix_indices = _matrix_contract_indices(matrix)
        if matrix_indices != contract_indices:
            warnings.append(
                f"매트릭스 열({len(matrix_indices)})과 계약 수({len(contract_indices)})가 다릅니다."
            )

    return {
        "customer": customer,
        "contracts": contracts,
        "matrix": matrix,
        "diagnosis": diagnosis,
        "notes": notes,
        "extra": extra,
        "warnings": warnings,
    }
