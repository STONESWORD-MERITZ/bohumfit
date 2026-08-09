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
    INJECT_REGISTRY_FALLBACKS,
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
# BOHUMFIT-276b(T5): 산출값 105,800 vs 원문 105,802의 2원 차는 반올림이 아니라
#   **다른 항목을 읽고 있던 것**이었다 — 원문에 `보장보험료 합계 105,802 원`과
#   `1회차보험료(할인후) 105,800 원`이 **둘 다 실재**하는데 후자를 먼저 잡았다(할인보험료는 0원).
#   고객·파일명이 인식하는 월납 금액은 **보장보험료 합계**이므로 그 패턴을 앞에 둔다.
#   ★기존 패턴은 지우지 않고 순서만 바꾼다(합계 표기가 없는 양식의 폴백으로 남긴다).
_PREMIUM_PATTERNS = (
    re.compile(r"보장보험료\s*합계\D{0,10}([\d,]{4,})\s*원"),
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


# BOHUMFIT-276a: 미확인 담보 표기 **단일 상수**. 엑셀·PDF·화면이 같은 문구를 쓴다.
#   ★"0원"으로 읽히면 미가입으로 오해되므로 금액이 아니라 **문장**으로 알린다(271 행동 지침형).
UNRESOLVED_COVERAGE_NOTE = "일부 담보를 제안서에서 확인하지 못했습니다. 해당 담보는 빈칸으로 두었으니 원본 가입담보리스트와 대조해 수기로 입력해 주세요."


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


#: BOHUMFIT-276c — 가입제안서 월납은 **원 단위 절삭**(버림, Human 확정 2026-08-08).
#:   원문 `보장보험료 합계 105,802` → 산출 `105,800`.
PREMIUM_TRUNCATE_UNIT = 10


def truncate_premium(value: int | None) -> int | None:
    """월납보험료를 원 단위로 **버림**한다(반올림 아님).

    ★절삭은 **여기 한 곳에서만** 한다 — 여러 지점에서 깎으면 이중 적용이 된다.
      `_extract_premium`이 유일한 호출자이고, 합계(`_finalize_proposals`)는 이미 절삭된 값을 더한다.
    """
    if value is None:
        return None
    return (value // PREMIUM_TRUNCATE_UNIT) * PREMIUM_TRUNCATE_UNIT


def _extract_premium(text: str, profile: ProductProfile | None) -> int | None:
    for pattern in _PREMIUM_PATTERNS:
        match = pattern.search(text)
        if match:
            # BOHUMFIT-276c: 항목은 276b가 `보장보험료 합계`로 교정했고, 여기서 원 단위만 버린다.
            return truncate_premium(int(match.group(1).replace(",", "")))
    # BOHUMFIT-276a: 프로필 고정 보험료(193 표본값) 폴백 제거 — 못 읽으면 값 없음으로 두고
    #   호출부가 수기 확인 경고를 띄운다(틀린 금액을 고객 안내문서에 싣지 않는다).
    _ = profile
    return None


def _extract_pay_months(text: str) -> int | None:
    match = _PAY_TERM_RE.search(text)
    if match:
        return int(match.group(1)) * 12
    match = _FIRST_PAY_TERM_RE.search(text)
    if match:
        return int(match.group(1)) * 12
    # BOHUMFIT-276b(T4): 20년(240개월) 가정 폴백 제거 — 못 읽으면 값 없음으로 두고 총납입을
    #   계산하지 않는다(276a 원칙 승계 · 272 `총납입보험료(계약별 납입기간 반영)` 라벨과 정합).
    return None


# BOHUMFIT-276b(T3): 프로필 고정 상품명이 실제 상품을 덮어써 **틀린 버전이 고객 안내문서에 나갔다**.
#   실측: 원문은 `(무) 메리츠 The좋은 알파Plus보장보험2607(2.0) …`인데 산출물은
#   `(무)메리츠 The좋은알파Plus종합보장보험2604` — **버전(2607→2604)과 상품 종류(보장보험→종합보장보험)**가
#   둘 다 달랐다. 원문 머리글이 p2~p26 전 페이지에 반복돼 추출 근거가 강하다.
#   ★272b 선례(과잉 절삭 금지): 괄호 수식어를 임의로 깎지 않고 **줄에 있는 그대로** 쓴다.
def _extract_product(text: str, profile: ProductProfile | None) -> str | None:
    """원문에서 상품명 줄을 찾아 **그대로** 돌려준다(없으면 None)."""
    for raw in (text or "").splitlines():
        line = _clean(raw)
        if not line or len(line) > 120:
            continue
        if not line.startswith("(무)") and not line.startswith("(유)"):
            continue
        if "보험" not in line and "공제" not in line:
            continue
        # 프로필이 있으면 그 키워드가 같은 줄에 있는지로 한 번 더 확인한다(오탐 방지).
        if profile and not any(_compact(keyword) in _compact(line) for keyword in profile.keywords):
            continue
        return line
    return None


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
    # BOHUMFIT-246: 텍스트 룰의 구명칭(일반암 등)을 정식명으로 정규화 — 파서·레지스트리와
    #   동일한 별칭 테이블(coverage_meta) 경유. compare kb_name 결합 정합(값 유실 방지).
    meta = coverage_meta(kb_name)
    if meta:
        kb_name = meta[0]
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


# BOHUMFIT-276b(T1): 실제 가입담보가 아니라 **예시·대표계약 설명**에 실린 금액을 담보로 채택하던 문제.
#   274 실측: 오현지 제안서 p3의 실제 `일반상해사망 1백만원`보다 p6 `대표계약 기준 : … 5,000만원`이
#   커서 채택됐다(`_merge_entries`가 큰 값을 고른다).
#   ★배제를 **페이지 단위가 아니라 줄(window) 단위**로 좁힌 이유: 가입제안서 샘플이 **1건뿐**이라
#     페이지 역할 규칙을 일반화할 근거가 부족하다. 반면 아래 문구는 그 줄 안에서 자기 자신이
#     "이건 예시다"라고 밝히므로, 다른 양식에서도 오탐 위험이 낮고 부작용 범위가 그 줄로 한정된다.
#   ★값을 낮게 채택하는 식의 우회는 쓰지 않는다 — **예시 줄은 아예 읽지 않는다**.
EXAMPLE_SECTION_MARKERS = ("대표계약기준", "대표계약 기준", "보험료비교(예시)", "보험료 비교(예시)")


def _is_example_window(window: str) -> bool:
    """예시·비교 설명 줄이면 True — 담보 후보에서 제외한다."""
    compact = _compact(window)
    return any(_compact(marker) in compact for marker in EXAMPLE_SECTION_MARKERS)


def _extract_rule_entries(lines: Sequence[str], profile: ProductProfile | None) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()
    for window in _line_windows(lines):
        if _is_example_window(window):
            continue
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


def _registry_hint(coverage, kind: str) -> dict[str, Any]:
    """BOHUMFIT-276a: 표본 고정값을 **담보 행이 아니라 힌트 메타**로만 남긴다."""
    return {
        "kb_name": coverage.kb_name,
        "amount": coverage.amount,
        "group12": coverage.group12,
        "agg": coverage.agg,
        "source": "registry-hint",
        "note": coverage.note,
        "kind": kind,
    }


def _registry_entries(
    profile: ProductProfile | None, existing_names: set[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """레지스트리 고정값을 **주입하지 않고** 힌트·미확인 목록만 돌려준다.

    BOHUMFIT-276a: 예전에는 텍스트 룰이 못 잡은 `kb_name`에 193 표본 금액을 담보 행으로 채워 넣었고
    (`fallback_coverages`), `bundle_coverages`는 **존재 확인조차 없이 무조건** 넣었다.
    274 조사에서 그 경로로 상해후유장해 1억원(실제 100만원)·깁스치료비 50만원(원문에 문자열 0건)이
    산출물에 실렸다. 설계사가 이 표로 고객에게 안내하므로 **틀린 숫자보다 빈칸이 안전하다**.

    ★"미가입이라 없는 것"과 "못 읽어서 없는 것"을 현행 구조가 구분하지 못하므로, 어느 쪽이든
      값을 지어내지 않고 **미확인 목록**으로 올려 사용자가 수기로 확인하게 한다.
    """
    if not profile:
        return [], [], []
    hints = [_registry_hint(c, "fallback") for c in profile.fallback_coverages]
    hints += [_registry_hint(c, "bundle") for c in profile.bundle_coverages]
    if INJECT_REGISTRY_FALLBACKS:  # pragma: no cover - 276a 이후 항상 False
        raise RuntimeError("BOHUMFIT-276a: 레지스트리 고정값의 담보 행 주입은 제거됐다.")
    # 텍스트에서 못 잡은 항목만 미확인으로 본다(잡힌 담보는 실제 값이 이미 있다).
    unresolved = [
        hint["kb_name"]
        for hint in hints
        if hint["kind"] == "fallback" and hint["kb_name"] not in existing_names
    ]
    # bundle은 부모 담보 확인 없이 주입되던 항목이라 전부 미확인으로 올린다.
    unresolved += [hint["kb_name"] for hint in hints if hint["kind"] == "bundle"]
    seen: set[str] = set()
    ordered = [name for name in unresolved if not (name in seen or seen.add(name))]
    return [], hints, ordered


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
    # BOHUMFIT-276b(T3): 원문 상품명을 최우선으로 쓴다. 못 읽으면 프로필 상품명으로 폴백하되
    #   ★그때는 **버전이 다를 수 있음을 경고**한다(무의미한 "가입제안서" 기본값보다 정보가 많다).
    product = _extract_product(normalized, profile)
    product_from_text = product is not None
    if product is None:
        product = profile.product if profile else "가입제안서"
    warnings: list[str] = []

    if not product_from_text and profile:
        warnings.append(f"{filename}: 상품명을 원문에서 확인하지 못해 대표 상품명으로 표기했습니다. 실제 상품·버전을 확인해 주세요.")

    premium = _extract_premium(normalized, profile)
    if premium is None:
        warnings.append(f"{filename}: 월납보험료를 찾지 못해 수기 확인이 필요합니다.")

    pay_months = _extract_pay_months(normalized)
    if pay_months is None:
        warnings.append(f"{filename}: 납입기간을 찾지 못해 총납입보험료를 계산하지 않았습니다. 수기로 확인해 주세요.")

    entries = _extract_rule_entries(lines, profile) + _extract_car_injury_14(lines) + _extract_tier_surgery_entries(lines)
    if profile and profile.key == "mirae-mcare":
        entries.extend(_extract_mirae_table_entries(lines))
    existing_names = {str(entry.get("kb_name")) for entry in entries}
    # BOHUMFIT-276a: 레지스트리 고정값은 **담보 행으로 넣지 않는다** — 힌트·미확인 목록만 받는다.
    registry_entries, registry_hints, unresolved = _registry_entries(profile, existing_names)
    entries.extend(registry_entries)  # 항상 빈 리스트(구조 유지 — 276b가 실제 추출로 채운다)
    if unresolved:
        warnings.append(f"{filename}: {UNRESOLVED_COVERAGE_NOTE} ({', '.join(unresolved)})")

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
        "pay_months": pay_months,
        "maturity": _extract_maturity(normalized),
        "coverages": coverages,
        "filename": filename,
        "parse_warnings": warnings,
        "metadata": {
            "profile": profile.key if profile else None,
            "registry_version": REGISTRY_VERSION,
            "bundle_subbenefits": [h for h in registry_hints if h.get("kind") == "bundle"],
            # BOHUMFIT-276a: 193 표본 고정값은 담보 행이 아니라 힌트로만 남긴다(276b 수기 확인용).
            "registry_hints": registry_hints,
            "unresolved_coverages": unresolved,
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
