"""Amount and duration tokenizers for KB coverage proposal PDFs."""
from __future__ import annotations

import re
from typing import Optional

UNIT_EOK = 100_000_000
UNIT_MAN = 10_000

AMOUNT_TOKEN_RE = re.compile(
    r"[+\-]?\s*(?:\d+\s*억(?:\s*\d[\d,]*\s*[만幻])?|\d[\d,]*\s*[만幻]|0|-)"
)
CELL_TOKEN_RE = AMOUNT_TOKEN_RE
DIAG_TOKEN_RE = AMOUNT_TOKEN_RE
_STATUS = ("충분", "부족", "미가입")


def parse_amount(token: Optional[str]) -> Optional[int]:
    """Convert Korean coverage amount tokens to KRW.

    Examples: ``5억 5,000만`` -> 550000000, ``27만`` -> 270000,
    ``+3만`` -> 30000, ``-1억`` -> -100000000, ``-`` -> None.
    Some embedded-font PDFs extract ``만`` as ``幻``; treat it as the same unit.
    """
    if token is None:
        return None
    t = str(token).strip().replace(" ", "").replace("幻", "만")
    if t in ("", "-"):
        return None
    sign = 1
    if t.startswith("+"):
        t = t[1:]
    elif t.startswith("-"):
        sign = -1
        t = t[1:]
    if t == "0":
        return 0
    total = 0
    matched = False
    m = re.search(r"(\d+)억", t)
    if m:
        total += int(m.group(1)) * UNIT_EOK
        matched = True
    m = re.search(r"([\d,]+)만", t)
    if m:
        total += int(m.group(1).replace(",", "")) * UNIT_MAN
        matched = True
    if matched:
        return sign * total
    digits = re.sub(r"[^\d]", "", t)
    return sign * int(digits) if digits else None


def extract_cells(text: str) -> list[str]:
    return [m.group().strip() for m in CELL_TOKEN_RE.finditer(text or "")]


def parse_won(token: Optional[str]) -> Optional[int]:
    if not token:
        return None
    digits = re.sub(r"[^\d]", "", str(token))
    return int(digits) if digits else None


def years_to_months(token: Optional[str]) -> Optional[int]:
    if not token:
        return None
    m = re.search(r"(\d+)\s*년", str(token))
    return int(m.group(1)) * 12 if m else None


def diag_status(text: str) -> Optional[str]:
    for status in _STATUS:
        if status in (text or ""):
            return status
    return None


def extract_diag_cells(text: str) -> list[str]:
    return extract_cells(text)
