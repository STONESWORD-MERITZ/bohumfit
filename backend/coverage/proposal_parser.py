"""BOHUMFIT-193 회사별 신규 가입제안서 PDF 파서.

``backend/pipeline``의 [전] 파서와 분리된 모듈이다. 회사별 가입제안서
PDF를 기존 컨설팅 플랜의 ``proposals`` 형태로 변환해 [후] 재계산에 넘긴다.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
import io
import re
from typing import Any

import pdfplumber

from .constants import AGG_REP, AGG_SUM, coverage_meta
from .proposal_registry import (
    DEFAULT_PAY_MONTHS,
    PRODUCT_PROFILES,
    PROPOSAL_RULES,
    REGISTRY_VERSION,
    ProductProfile,
    ProposalRule,
    RegistryCoverage,
)

KRW_MAN = 10_000
KRW_EOK = 100_000_000

_MONEY_RE = re.compile(
    r"(?:(?:\d[\d,]*)\s*억\s*)?"
    r"(?:(?:\d[\d,]*)\s*천\s*)?"
    r"(?:(?:\d[\d,]*)\s*백\s*)?"
    r"(?:(?:\d[\d,]*)\s*십\s*)?"
    r"(?:\d[\d,]*\s*)?만\s*원?"
    r"|(?:\d[\d,]*)\s*억\s*원?"
)
_PREMIUM_PATTERNS = (
    re.compile(r"1회차보험료\(할인후\)\D{0,20}([\d,]{4,})\s*원?"),
    re.compile(r"할인후초회보험료\D{0,20}([\d,]{4,})\s*원?"),
    re.compile(r"실납입보험료\D{0,20}([\d,]{4,})\s*원"),
    re.compile(r"합계\s+([\d,]{4,})\s*(?:원|\s)"),
    re.compile(r"보험료\s*[:：]\s*([\d,]{4,})\s*원?"),
    re.compile(r"(?:월납\s*)?보험료\D{0,18}([\d,]{4,})\s*원"),
)
_PAY_TERM_RE = re.compile(r"(\d{1,2})\s*년\s*납")
_FIRST_PAY_TERM_RE = re.compile(r"최초계약\s*(\d{1,2})\s*년")
_MATURITY_RE = re.compile(r"(\d{1,3}\s*세|\d{1,3}\s*년)\s*만기")
_MAX_MATURITY_RE = re.compile(r"최대\s*(\d{1,3}\s*세)\s*만기")


class ProposalParseError(ValueError):
    """신규 가입제안서 파싱 실패."""


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _compact(text: str | None) -> str:
    return "".join((text or "").split())


def _parse_under_eok_man(value: str) -> int:
    text = value.replace(",", "").replace("만원", "").replace("만", "").replace("원", "")
    if not text:
        return 0
    if text.isdigit():
        return int(text)
    total = 0
    for unit, multiplier in (("천", 1000), ("백", 100), ("십", 10)):
        match = re.search(rf"(\d+)\s*{unit}", text)
        if match:
            total += int(match.group(1)) * multiplier
            text = text.replace(match.group(0), "")
    tail = re.sub(r"\D", "", text)
    if tail:
        total += int(tail)
    return total


def parse_korean_amount_to_krw(value: str | None) -> int | None:
    """가입금액 문자열을 원 단위 정수로 변환한다."""
    if not value:
        return None
    text = _clean(value).replace(",", "")
    if "억" not in text and "만" not in text:
        return None
    total = 0
    eok_match = re.search(r"(\d+)\s*억", text)
    if eok_match:
        total += int(eok_match.group(1)) * KRW_EOK
        text = text[eok_match.end() :]
    man_match = re.search(
        r"(?:(?:\d+)\s*천\s*)?(?:(?:\d+)\s*백\s*)?(?:(?:\d+)\s*십\s*)?(?:\d+\s*)?만",
        text,
    )
    if man_match:
        total += _parse_under_eok_man(man_match.group(0)) * KRW_MAN
    return total or None


def _amount_candidates(text: str) -> list[tuple[int, int]]:
    candidates: list[tuple[int, int]] = []
    for match in _MONEY_RE.finditer(text or ""):
        parsed = parse_korean_amount_to_krw(match.group(0))
        if parsed is not None:
            candidates.append((match.start(), parsed))
    return candidates


def _first_amount(text: str) -> int | None:
    candidates = _amount_candidates(text)
    return candidates[0][1] if candidates else None


def _plain_man_amount(text: str, keyword: str) -> int | None:
    compact_keyword = _compact(keyword)
    compact_text = _compact(text)
    start = compact_text.find(compact_keyword)
    search_area = text if start < 0 else text[max(0, start) :]
    for match in re.finditer(r"(?<![\d.])(\d[\d,]{2,})(?!\s*원)(?![\d.])", search_area):
        amount_man = int(match.group(1).replace(",", ""))
        if amount_man >= 10:
            return amount_man * KRW_MAN
    return None


def _mirae_table_amount(text: str) -> int | None:
    unit_amount = _first_amount(text)
    if unit_amount is not None:
        return unit_amount
    patterns = (
        re.compile(r"\s(\d[\d,]*)\s+\d{1,3}\s+(?:갱신계약|20년|전기납|월납)"),
        re.compile(r"\b(\d[\d,]*)\s+\d{1,3}\s+월납"),
    )
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            amount_man = int(match.group(1).replace(",", ""))
            if amount_man >= 10:
                return amount_man * KRW_MAN
    return None


def _line_windows(lines: Sequence[str]) -> Iterable[str]:
    for line in lines:
        yield _clean(line)


def _line_plus_next_windows(lines: Sequence[str]) -> Iterable[str]:
    for index, line in enumerate(lines):
        parts = [line]
        if index + 1 < len(lines):
            parts.append(lines[index + 1])
        yield _clean(" ".join(parts))


def _detect_profile(text: str) -> ProductProfile | None:
    compact = _compact(text)
    for profile in PRODUCT_PROFILES:
        if any(_compact(keyword) in compact for keyword in profile.keywords):
            return profile
    return None


def _detect_insurer(text: str, profile: ProductProfile | None) -> str:
    if profile:
        return profile.insurer
    compact = _compact(text)
    for insurer in ("KB손해보험", "메리츠화재", "미래에셋생명", "현대해상", "DB손해보험"):
        if _compact(insurer) in compact:
            return insurer
    return "알 수 없음"


def _extract_premium(text: str, profile: ProductProfile | None) -> int | None:
    for pattern in _PREMIUM_PATTERNS:
        match = pattern.search(text)
        if match:
            return int(match.group(1).replace(",", ""))
    return profile.fallback_premium if profile else None


def _extract_pay_months(text: str) -> int | None:
    match = _PAY_TERM_RE.search(text)
    if match:
        return int(match.group(1)) * 12
    match = _FIRST_PAY_TERM_RE.search(text)
    if match:
        return int(match.group(1)) * 12
    return DEFAULT_PAY_MONTHS


def _extract_maturity(text: str) -> str | None:
    match = _MATURITY_RE.search(text) or _MAX_MATURITY_RE.search(text)
    return match.group(1).replace(" ", "") if match else None


def _known_meta(kb_name: str, group12: str, agg: str) -> tuple[str, str, str]:
    meta = coverage_meta(kb_name)
    if meta:
        return meta[1], meta[2], meta[3]
    return group12, group12, agg


def _entry(
    kb_name: str,
    amount: int,
    group12: str,
    agg: str,
    source: str,
    raw: str,
    merge_rule: str = AGG_REP,
) -> dict[str, Any]:
    kb_group, resolved_group, resolved_agg = _known_meta(kb_name, group12, agg)
    return {
        "kb_name": kb_name,
        "amount": amount,
        "kb_group": kb_group,
        "group12": resolved_group,
        "agg": resolved_agg,
        "merge_rule": merge_rule,
        "source": source,
        "raw": raw,
    }


def _matches(rule: ProposalRule, window: str) -> bool:
    compact = _compact(window)
    return all(_compact(keyword) in compact for keyword in rule.keywords) and not any(
        _compact(excluded) in compact for excluded in rule.excludes
    )


def _skip_rule(rule: ProposalRule, window: str, profile: ProductProfile | None) -> bool:
    compact = _compact(window)
    if rule.kb_name == "일반암" and profile and profile.key == "meritz-cancer":
        return "암종별" not in compact
    if profile and profile.key == "mirae-mcare" and rule.kb_name in {"상해사망", "일반암", "유사암"}:
        return True
    if rule.kb_name == "자동차사고부상":
        return True
    return False


def _extract_rule_entries(lines: Sequence[str], profile: ProductProfile | None) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()
    for window in _line_windows(lines):
        for rule in PROPOSAL_RULES:
            if _skip_rule(rule, window, profile) or not _matches(rule, window):
                continue
            amount = _first_amount(window)
            if amount is None:
                continue
            key = (rule.kb_name, amount, window[:80])
            if key in seen:
                continue
            seen.add(key)
            entries.append(_entry(rule.kb_name, amount, rule.group12, rule.agg, "text", window, rule.merge_rule))
    return entries


def _extract_car_injury_14(lines: Sequence[str]) -> list[dict[str, Any]]:
    for window in _line_windows(lines):
        compact = _compact(window)
        if "자동차사고부상" not in compact or not re.search(r"(?<![-\d])14급", compact):
            continue
        marker = window.find("14급")
        after_marker = window[marker:] if marker >= 0 else window
        amount = _first_amount(after_marker) or _first_amount(window)
        if amount is not None:
            return [_entry("자동차사고부상", amount, "운전자", AGG_SUM, "14급 기준", window)]
    return []


def _extract_mirae_table_entries(lines: Sequence[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    start = 0
    for index, line in enumerate(lines):
        compact_line = _compact(line)
        if "주계약[갱신형]" in compact_line or "보험가입금액" in compact_line:
            start = index
            break
    end = len(lines)
    for index in range(start, len(lines)):
        if _compact(lines[index]).startswith("합계"):
            end = index + 1
            break
    table_lines = lines[start:end] if start < end else lines

    for window in _line_plus_next_windows(table_lines):
        compact = _compact(window)
        amount: int | None = None
        if "암(유사암제외)진단특약" in compact:
            amount = _mirae_table_amount(window) or _plain_man_amount(window, "암(유사암제외)진단특약")
            if amount is not None:
                entries.append(_entry("일반암", amount, "암", AGG_SUM, "미래 표", window))
        elif "유사암진단특약" in compact:
            amount = _mirae_table_amount(window) or _plain_man_amount(window, "유사암진단특약")
            if amount is not None:
                entries.append(_entry("유사암", amount, "암", AGG_SUM, "미래 표", window))
        elif "주계약[갱신형]" in compact:
            amount = _mirae_table_amount(window) or _plain_man_amount(window, "주계약")
            if amount is not None:
                entries.append(_entry("상해사망", amount, "사망", AGG_SUM, "미래 표", window))
        tier_match = re.search(r"1-5종수술특약\(([1-5])종\)", compact)
        if tier_match:
            amount = _mirae_table_amount(window) or _plain_man_amount(window, "1-5종수술특약")
            if amount is not None:
                tier = tier_match.group(1)
                entries.append(_entry(f"N종수술비(상해 {tier}종)", amount, "수술", AGG_SUM, "미래 표", window))
                entries.append(_entry(f"N종수술비(질병 {tier}종)", amount, "수술", AGG_SUM, "미래 표", window))
    return entries


def _extract_tier_surgery_entries(lines: Sequence[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for window in _line_windows(lines):
        compact = _compact(window)
        if "종" not in compact or "수술" not in compact:
            continue
        amount = _first_amount(window) or _plain_man_amount(window, "수술")
        if amount is None:
            continue

        typed_match = re.search(r"(상해|질병)\s*([1-5])\s*종\s*수술", compact)
        if typed_match:
            kind, tier = typed_match.groups()
            name = f"N종수술비({kind} {tier}종)"
            key = (name, amount)
            if key not in seen:
                seen.add(key)
                entries.append(_entry(name, amount, "수술", AGG_SUM, "제안서 종수술", window))
            continue

        tier_match = re.search(r"([1-5])\s*종\s*수술", compact)
        if tier_match:
            tier = tier_match.group(1)
            for kind in ("상해", "질병"):
                name = f"N종수술비({kind} {tier}종)"
                key = (name, amount)
                if key in seen:
                    continue
                seen.add(key)
                entries.append(_entry(name, amount, "수술", AGG_SUM, "제안서 종수술", window))
    return entries


def _registry_entries(profile: ProductProfile | None, existing_names: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not profile:
        return [], []
    entries: list[dict[str, Any]] = []
    bundle_meta: list[dict[str, Any]] = []
    for coverage in profile.fallback_coverages:
        item = {
            "kb_name": coverage.kb_name,
            "amount": coverage.amount,
            "group12": coverage.group12,
            "agg": coverage.agg,
            "source": "registry",
            "note": coverage.note,
            "include_in_coverages": coverage.include_in_coverages,
        }
        if not coverage.include_in_coverages or coverage.kb_name in existing_names:
            continue
        entries.append(
            _entry(
                coverage.kb_name,
                coverage.amount,
                coverage.group12,
                coverage.agg,
                "registry",
                coverage.note,
                coverage.merge_rule,
            )
        )
    for coverage in profile.bundle_coverages:
        item = {
            "kb_name": coverage.kb_name,
            "amount": coverage.amount,
            "group12": coverage.group12,
            "agg": coverage.agg,
            "source": "registry",
            "note": coverage.note,
            "include_in_coverages": coverage.include_in_coverages,
        }
        bundle_meta.append(item)
        if not coverage.include_in_coverages:
            continue
        entries.append(
            _entry(
                coverage.kb_name,
                coverage.amount,
                coverage.group12,
                coverage.agg,
                "registry",
                coverage.note,
                coverage.merge_rule,
            )
        )
    return entries, bundle_meta


def _merge_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for entry in entries:
        name = str(entry.get("kb_name") or "")
        amount = int(entry.get("amount") or 0)
        if not name or amount <= 0:
            continue
        current = merged.get(name)
        if not current:
            merged[name] = dict(entry)
            continue
        if entry.get("merge_rule") == AGG_SUM and current.get("merge_rule") == AGG_SUM:
            current["amount"] = int(current.get("amount") or 0) + amount
            current["source"] = f"{current.get('source')}, {entry.get('source')}"
        elif amount > int(current.get("amount") or 0):
            merged[name] = dict(entry)
    return sorted(merged.values(), key=lambda item: (str(item.get("group12") or ""), str(item.get("kb_name") or "")))


def _proposal_id(index: int) -> str:
    return f"P{index}"


def parse_proposal_text(text: str, filename: str = "proposal.pdf") -> dict[str, Any]:
    """가입제안서 텍스트를 컨설팅 신규제안 dict로 변환한다."""
    normalized = text or ""
    lines = [_clean(line) for line in normalized.splitlines() if _clean(line)]
    profile = _detect_profile(normalized)
    insurer = _detect_insurer(normalized, profile)
    product = profile.product if profile else "가입제안서"
    warnings: list[str] = []

    premium = _extract_premium(normalized, profile)
    if premium is None:
        warnings.append(f"{filename}: 월납보험료를 찾지 못해 수기 확인이 필요합니다.")

    entries = _extract_rule_entries(lines, profile) + _extract_car_injury_14(lines) + _extract_tier_surgery_entries(lines)
    if profile and profile.key == "mirae-mcare":
        entries.extend(_extract_mirae_table_entries(lines))
    existing_names = {str(entry.get("kb_name")) for entry in entries}
    registry_entries, bundle_meta = _registry_entries(profile, existing_names)
    entries.extend(registry_entries)

    coverages = [
        {
            "kb_name": entry["kb_name"],
            "amount": entry["amount"],
            "kb_group": entry.get("kb_group"),
            "group12": entry.get("group12"),
            "agg": entry.get("agg"),
            "source": entry.get("source"),
        }
        for entry in _merge_entries(entries)
    ]
    if not coverages:
        warnings.append(f"{filename}: 담보를 자동 추출하지 못했습니다. 수기 입력으로 보완해 주세요.")

    return {
        "proposal_id": "",
        "insurer": insurer,
        "product": product,
        "monthly_premium": premium,
        "pay_cycle": "월납",
        "pay_months": _extract_pay_months(normalized),
        "maturity": _extract_maturity(normalized),
        "coverages": coverages,
        "filename": filename,
        "parse_warnings": warnings,
        "metadata": {
            "profile": profile.key if profile else None,
            "registry_version": REGISTRY_VERSION,
            "bundle_subbenefits": bundle_meta,
        },
    }


def _extract_text(pdf_bytes: bytes) -> str:
    chunks: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                chunks.append(page.extract_text() or "")
                try:
                    page.flush_cache()
                except Exception:
                    pass
    except Exception as exc:  # pragma: no cover - pdfplumber 오류 형태가 환경별로 다름
        raise ProposalParseError("가입제안서 PDF를 열 수 없습니다.") from exc
    text = "\n".join(chunks).strip()
    if not text:
        raise ProposalParseError("텍스트 레이어가 없는 PDF는 자동 파싱할 수 없습니다.")
    return text


def parse_proposal_pdf(pdf_bytes: bytes, filename: str = "proposal.pdf") -> dict[str, Any]:
    if b"%PDF-" not in pdf_bytes[:1024]:
        raise ProposalParseError("올바른 PDF 파일이 아닙니다.")
    return parse_proposal_text(_extract_text(pdf_bytes), filename)


def _sort_key(item: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(item.get("insurer") or ""),
        str(item.get("product") or ""),
        str(item.get("filename") or ""),
    )


def _finalize_proposals(proposals: list[dict[str, Any]], warnings: list[str]) -> dict[str, Any]:
    proposals.sort(key=_sort_key)
    for index, proposal in enumerate(proposals, start=1):
        proposal["proposal_id"] = _proposal_id(index)

    monthly_total = sum(int(item.get("monthly_premium") or 0) for item in proposals)
    return {
        "proposals": proposals,
        "warnings": warnings,
        "premium": {"monthly_total": monthly_total, "currency": "KRW"},
        "premium_total": monthly_total,
        "count": len(proposals),
        "metadata": {
            "registry_version": REGISTRY_VERSION,
            "company_order": [item.get("insurer") for item in proposals],
        },
    }


def parse_proposal_texts(files: Sequence[tuple[str, str]]) -> dict[str, Any]:
    proposals: list[dict[str, Any]] = []
    warnings: list[str] = []
    for filename, text in files:
        proposal = parse_proposal_text(text, filename)
        warnings.extend(proposal.get("parse_warnings") or [])
        proposals.append(proposal)
    return _finalize_proposals(proposals, warnings)


def parse_proposal_files(files: Sequence[tuple[str, bytes]]) -> dict[str, Any]:
    proposals: list[dict[str, Any]] = []
    warnings: list[str] = []
    for filename, data in files:
        proposal = parse_proposal_pdf(data, filename)
        warnings.extend(proposal.get("parse_warnings") or [])
        proposals.append(proposal)
    return _finalize_proposals(proposals, warnings)
