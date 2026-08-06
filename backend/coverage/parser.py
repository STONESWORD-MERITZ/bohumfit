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
    split_detail_parts,
)
from .jong_surgery import (
    OUT_OF_RANGE_LABEL,
    estimated_tier_label,
    has_explicit_tier,
    lookup_jong_tiers,
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
    # BOHUMFIT-243 ①: 공제·금고·수협 등 비보험사 기관 접미도 보험사 필드로 인식한다.
    if re.search(r"(손보|화재|생명|해상|손해보험|생명보험|중앙회|공제회|공제조합|금고|수협|신협)$", value):
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


# BOHUMFIT-243 ①: 보험사 접미에 공제·금고·수협 등 비보험사 기관 형태를 추가한다.
#   실측(243): 계약리스트에서 "새마을금"(윗줄)+"고중앙회"(아랫줄)로 쪼개진 기관명이 기존
#   접미(손보·생명·화재·해상)에 걸리지 않아 보험사 필드가 비고 상품명 칸으로 밀려났다.
#   KNOWN_INSURERS 사전 매칭이 우선이고, 이 접미 규칙은 미등록 기관의 일반 폴백이다.
_INSURER_SUFFIX = r"손해보험|생명보험|손보|생명|화재|해상|중앙회|공제회|공제조합|금고|수협|신협"
_INSURER_HEAD_RE = re.compile(rf"^([가-힣A-Za-z()·]{{0,14}}?(?:{_INSURER_SUFFIX}))")
_INSURER_JOINED_RE = re.compile(rf"^[가-힣A-Z][가-힣A-Za-z()·]*(?:{_INSURER_SUFFIX})$")


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


# BOHUMFIT-239: 페이지 역할은 번호가 아니라 헤더 문구로 감지한다(179 원설계 원칙).
# "전체 보장현황"은 '상품별 가입현황' 매트릭스가 없는 KB 변형 문서(239 실사용 케이스)의
# fallback 매트릭스 소스다 — 계약별 열이 아니라 담보별 합계만 제공(parse_overview 참조).
# 파서 로컬 상수로 둔다(constants.ROLE_MARKERS는 무변경 — 태스크 범위 = parser.py).
OVERVIEW_MARKER = "전체 보장현황"


def classify_page(lines: list[str]) -> Optional[str]:
    head = " ".join(lines[:8])
    compact_head = "".join(head.split())
    for role, marker in (
        ("diagnosis", ROLE_MARKERS["diagnosis"]),
        ("contracts", ROLE_MARKERS["contracts"]),
        ("detail", ROLE_MARKERS["detail"]),
        ("matrix", ROLE_MARKERS["matrix"]),
        ("overview", OVERVIEW_MARKER),  # BOHUMFIT-239: 상품별 가입현황 부재 시 fallback
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
        # BOHUMFIT-243 ①: 보험사명이 prefix와 다음 줄에 걸쳐 쪼개진 경우(예: "새마을금"+"고중앙회")
        #   prefix_source 단독 strip이 무효(no-op)라 조각이 상품명에 남았다. 이때만 결합 문자열에서
        #   despace 기준으로 한 번 더 제거한다(연속 표기 케이스는 기존 경로라 동작 불변).
        insurer_split_across_lines = False
        if split_insurer:
            product = row_product
        elif insurer and _despace(pm.group("insurer")) == _despace(insurer):
            product = row_product
        elif insurer:
            stripped = _strip_despace_fragment(prefix_source, insurer)
            insurer_split_across_lines = stripped == prefix_source
            product = re.sub(r"^\s*\d+\s+", "", stripped)
        else:
            product = row_product
        product = _clean(" ".join([product, *after_parts]))
        if insurer and insurer_split_across_lines:
            product = _strip_despace_fragment(product, insurer)
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
    contracts = sorted(contracts, key=lambda c: c["idx"])
    # BOHUMFIT-272b: 회사명이 두 줄로 쪼개진 문서에서 조각이 앞 상품명에 흡수되는 것을 되돌린다.
    _strip_trailing_insurer_fragment(contracts)
    return contracts


def _strip_trailing_insurer_fragment(contracts: list[dict]) -> None:
    """BOHUMFIT-272b: 상품명 **끝**에 붙은 회사명 조각을 제거한다(계약리스트 후처리).

    ★현상(실측 — 6계약 실 PDF p5): 회사명이 길어 두 줄로 쪼개지는 기관에서, 조각 줄이
    `_is_product_continuation`을 통과해 앞 상품명 끝에 흡수된다.
        4 DB손보 100세청춘보험0901 …
        새마을금            ← 계약5 회사명 앞조각 → 계약4 상품명 끝에 붙음
        5 無MG BlueBird저축공제_22A …   ← 이 행에는 회사명이 아예 없다
        고중앙회            ← 계약5 회사명 뒷조각 → 잔여 "중앙회"가 상품명에 남음
    회사명이 한 줄에 들어가는 문서(정본 2건)에서는 조각 줄 자체가 생기지 않아 발생하지 않는다.

    ★파싱 루프가 아니라 **후처리**로 두는 이유: 리스트가 완성된 뒤에는 자기·다음 계약의 insurer를
    모두 알 수 있어 근거가 확실하고, 234·243이 만든 기존 경로를 건드리지 않아 회귀 위험이 없다.

    ★절삭 조건 — 아래를 **모두** 만족할 때만(251에서 코드 절삭으로 3회 반려된 이력 때문에 좁게 잡는다):
      ①상품명이 2토큰 이상이고 대상은 **끝 토큰뿐**(중간·앞은 절대 건드리지 않는다)
      ②끝 토큰이 자기·다음 계약 insurer 또는 KNOWN_INSURERS 중 하나의 **접두 또는 접미**와 일치
      ③★끝 토큰이 회사명 **전체와 일치하면 절삭하지 않는다** — 상품명이 정당하게 회사명으로 끝나는 경우 보호
      ④제거 후 상품명이 비지 않는다
    하나라도 불확실하면 그대로 둔다(오염이 남는 편이 상품명을 깎는 것보다 안전하다).
    실측: 정본 2건 30개 상품명에서 후보 **0건**, 실 케이스 6계약에서 오염 **3건만** 적중.
    """
    for index, contract in enumerate(contracts):
        product = contract.get("product")
        if not product:
            continue
        tokens = product.split()
        if len(tokens) < 2:  # ①단일 토큰 상품명은 손대지 않는다
            continue
        tail = _despace(tokens[-1])
        if not tail:
            continue

        next_insurer = contracts[index + 1].get("insurer") if index + 1 < len(contracts) else None
        candidates = [c for c in (contract.get("insurer"), next_insurer) if c]
        candidates.extend(KNOWN_INSURERS)

        for candidate in candidates:
            compact = _despace(candidate)
            if not compact or tail == compact:
                continue  # ③회사명 전체와 같으면 정당한 표기로 보고 남긴다
            if compact.startswith(tail) or compact.endswith(tail):  # ②접두·접미 조각
                remainder = " ".join(tokens[:-1]).strip()
                if remainder:  # ④빈 상품명을 만들지 않는다
                    contract["product"] = remainder
                break


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


def parse_overview(pages_lines: list[list[str]]) -> dict:
    """BOHUMFIT-239: '전체 보장현황' 페이지에서 담보별 합계(첫 셀)만 채집한다.

    이 페이지의 금액 열은 계약별이 아니라 집계 그룹(생보/손보 등, 헤더 count 행 '1 5 8 1')
    이므로 계약별 by_company를 만들 수 없다. 담보별 **합계(첫 셀)**만 신뢰하며(진단 페이지
    enrolled 값과 일치 실측), 이를 매트릭스 호환 dict로 반환하되 by_company는 비우고
    `overview` 플래그를 세운다. build_before가 이 플래그를 보고 summary/enrolled를 산출한다.
    '상품별 가입현황' 매트릭스가 아예 없는 변형 문서(239 실사용)의 fallback 전용 — 표준 문서는
    매트릭스가 있어 이 경로를 타지 않는다(회귀 0).
    """
    acc: dict[str, dict] = {}
    for page in pages_lines:
        for line in page:
            meta, _start, end = match_coverage_span(line)
            if not meta or end is None:
                continue
            kb_name, kb_group, group12, agg = meta
            if kb_name in acc:
                continue
            cells = [parse_amount(c) for c in extract_cells(line[end:])]
            if not cells or cells[0] is None:
                continue
            acc[kb_name] = {
                "kb_name": kb_name,
                "kb_group": kb_group,
                "group12": group12,
                "agg": agg,
                "summary": cells[0],
                "by_company": {},
                "overview": True,
            }
    return acc


# ── BOHUMFIT-256: overview(합계-only) 문서의 회사별 귀속 복원 ────────────────────
#   배경(255-P1 진단): overview 문서는 '전체 보장현황'에서 담보별 합계만 얻고 by_company가
#   비어 있어 엑셀 회사 열이 만들어지지 않는다. 그러나 같은 문서의 detail(상품별 가입담보상세)
#   페이지에는 계약별 담보·금액이 실재한다(진단: 원천 부재 0종).
#   ★설계 원칙
#     ① 귀속 게이트 — 담보별 detail 합이 overview summary와 **정확히 일치할 때만** 채운다.
#        불일치·부재는 미충전 유지(오귀속 0 · 251/253 원칙). summary·enrolled는 절대 불변.
#     ② 이 경로는 **overview 문서 전용**이며 담보 판정도 자체 리졸버를 쓴다 — 표준 문서가 쓰는
#        공용 매칭/별칭(constants)에 손대지 않아 표준 회귀 위험이 0이다.
#     ③ 계약 특정은 253 유일성 원칙 그대로(보험료 → 실패 시 상품명, 유일할 때만).
def _product_index(contracts: list[dict]) -> dict[str, frozenset]:
    """상품명(공백 제거) → 계약 idx 집합.

    BOHUMFIT-256: 보험료가 미제공(`monthly_premium=None`)인 계약은 253의 보험료 역인덱스로
    특정할 수 없다(라*실 실손 계약 실측). 상품명을 보조 키로 두되 중복은 집합으로 보존해
    유일하지 않으면 귀속하지 않는다.
    """
    index: dict[str, set] = {}
    for contract in contracts:
        product = _despace(contract.get("product") or "")
        if len(product) >= 8:  # 너무 짧은 상품명은 오매칭 위험 — 후보에서 제외
            index.setdefault(product, set()).add(contract["idx"])
    return {product: frozenset(ids) for product, ids in index.items()}


def _detail_idx_with_product_fallback(
    lines: list[str], premium_index: dict, product_index: dict
) -> Optional[int]:
    """보험료 경로(253) → 실패 시 상품명 폴백. 어느 경로든 ★유일할 때만 귀속한다."""
    idx = _detail_contract_idx(lines, premium_index)
    if idx is not None:
        return idx
    head = _despace("".join(lines[:16]))
    matched: set = set()
    for product, ids in product_index.items():
        if product[:12] in head:
            matched |= ids
    if len(matched) == 1:
        return next(iter(matched))
    return None  # 복수·0 매칭 = 모호 → '?' 유지


# BOHUMFIT-258: 암 진단 계열 분류(Human 결정 A안) — 일반암 → `암진단금`,
#   유사암(제자리암·상피내암·갑상샘암·소액암) → `유사암진단금`(공용 매칭이 담당),
#   재진단암·특정암(경계성종양·기타피부암·대장점막내암)·치료비 계열 → 상위 담보에 흡수 금지.
#   ★"(…제외)" 괄호는 보장 범위 한정 문구이므로 판정 전에 제거한다 —
#   예: `암진단(기타피부암,갑상선암및대장점막내암제외)`는 ★일반암 행이다(실측).
_CANCER_EXCLUSION_PAREN = re.compile(r"\([^()]*제외\)")
_CANCER_NON_GENERAL: tuple[str, ...] = (
    "유사암", "소액암", "제자리암", "상피내암", "갑상샘암", "갑상선암",
    "경계성종양", "기타피부암", "대장점막내암", "재진단암",
    "통합치료생활비",  # ★'생활비'만으로 배제하면 상품명(보험료생활비환급특약)까지 떨군다(실측)
    "항암",
)


def _cancer_core(compact: str) -> str:
    return _CANCER_EXCLUSION_PAREN.sub("", compact)


# BOHUMFIT-257(가): 상위 담보로 흡수하면 안 되는 ★한정·파생 담보 — overview 귀속 전용 배제.
#   진단(255-P1) 실측 근거: 상해사망 초과분 = 교통상해사망 5,000만 + 화재상해사망 1,000만,
#   뇌혈관질환 = 산정특례 진단비 1,000만, 상해/질병수술 = 특정·종수술 계열,
#   질병/상해입원 = 1인실·2-3인실 입원일당, 유사암 = 통합치료 생활비, 골절 = 수술·부목.
#   ★공용 매칭(constants)은 손대지 않는다 — 표준 문서 분류·EXTRA 검출에 영향 0.
_OVERVIEW_LIMITED_VARIANTS: dict[str, tuple[str, ...]] = {
    "상해사망": ("교통상해사망", "화재상해", "특정상해사망"),
    "상해후유장해": ("특정상해후유장해", "화재상해후유장해"),
    # "유사암제외"는 일반암 담보의 문구 — 유사암 담보로 흡수하면 안 된다(실측 과포함 원인).
    "유사암진단금": ("통합치료생활비", "유사암제외"),
    "뇌혈관질환": ("산정특례",),
    "상해수술": ("특정상해수술", "외모", "상해종수술", "종수술"),
    "질병수술": ("특정질병수술", "124대", "질병종수술", "종질병수술"),
    # 병실 특약(1인실·2-3인실)만 배제한다. "입원일당"은 기본 입원특약 원문에도 들어가므로
    # 배제어로 쓰면 정작 귀속해야 할 행까지 떨군다(실측).
    "질병입원": ("1인실", "2-3인실"),
    "상해입원": ("1인실", "2-3인실"),
    # BOHUMFIT-258: 공용 매칭이 암 계열을 `암진단금`으로 흡수하는 경우 차단 —
    #   일반암 행은 위 direct 규칙이 먼저 처리하므로 여기 걸리지 않는다.
    "암진단금": _CANCER_NON_GENERAL,
}


def _overview_direct_target(compact: str) -> Optional[str]:
    """BOHUMFIT-257(나): 공용 매칭이 잡지 못하는(현행 None) 담보를 원문 표기로 직접 판정.

    진단 실측: 표적항암약물허가치료특약 5,000만 · 교통사고 벌금(대인 3,000만+대물 500만) ·
    가족생활배상책임 1억 · 치과치료(보철치료) 150만 · 재해골절진단특약 50만.
    ★overview 문서 전용 경로이므로 표준 문서 매칭에는 영향이 없다.
    """
    if "표적항암" in compact:
        return "표적항암치료"
    if "벌금" in compact and "화재" not in compact and "업무상과실" not in compact:
        return "벌금(대인/스쿨존/대물)"
    if "배상책임" in compact:
        return "가족/일상/자녀배상"
    if "보철" in compact:
        return "보철치료비"
    if "골절" in compact and "진단" in compact and "수술" not in compact and "부목" not in compact:
        return "골절진단비"
    # BOHUMFIT-258 A안: 일반암 진단 행만 `암진단금`으로 귀속.
    core = _cancer_core(compact)
    if "암진단" in core and not any(bad in core for bad in _CANCER_NON_GENERAL):
        return "암진단금"
    return None


def _resolve_overview_coverage(line: str) -> Optional[str]:
    """detail 행 → 표준 담보명(overview 귀속 전용 리졸버).

    ① 실손 계열(256): 원문이 `상해(일반상해,전체상해를 의미)입원의료비`·`…외래의료비`·
       `…처방조제료` 형태여서 공용 매칭이 잡지 못한다. 통원은 외래+처방조제의 합이 양식의
       통원의료비 금액과 일치한다(실측: 25만+5만=30만).
    ② 미등록 담보(257 나): `_overview_direct_target`으로 직접 판정.
    ③ 공용 매칭 결과에 한정·파생 담보 배제(257 가)를 겹쳐 상위 담보 오귀속을 막는다.
    """
    compact = line.replace(" ", "")
    if "의료비" in compact or "처방조제" in compact:
        if "비급여" in compact:
            return "3대비급여실손"
        injury = "상해" in compact
        disease = "질병" in compact
        if "입원의료비" in compact:
            if injury and not disease:
                return "상해입원의료비"
            if disease and not injury:
                return "질병입원의료비"
            return None  # 상해·질병 동시 등장 = 모호
        if "외래의료비" in compact or "처방조제" in compact:
            if injury and not disease:
                return "상해통원의료비"
            if disease and not injury:
                return "질병통원의료비"
            return None
    direct = _overview_direct_target(compact)
    if direct:
        return direct
    meta, _start, _end = match_coverage_span(line)
    if not meta:
        return None
    target = meta[0]
    if any(bad in compact for bad in _OVERVIEW_LIMITED_VARIANTS.get(target, ())):
        return None  # 한정·파생 담보 — 상위 담보에 흡수시키지 않는다
    return target


def attribute_overview_by_company(matrix: dict, detail_pages: list[list[str]], contracts: list[dict]) -> dict:
    """overview 담보 행의 by_company를 detail에서 복원한다(귀속 게이트 통과분만).

    반환: {담보명: 귀속 합계} — 호출부·테스트가 귀속 실적을 확인할 수 있도록 노출한다.
    ★matrix 행의 summary/enrolled/overview 플래그는 건드리지 않는다.
    """
    if not matrix or not detail_pages or not contracts:
        return {}
    premium_index = _premium_index(contracts)
    product_index = _product_index(contracts)
    cells: dict[str, dict[str, int]] = {}
    for lines in detail_pages:
        idx = _detail_idx_with_product_fallback(lines, premium_index, product_index)
        if idx is None:
            continue  # 계약 모호 — 귀속하지 않는다(오귀속 금지)
        key = str(idx)
        for line in lines:
            if not re.match(r"\s*\d+\s+", line):
                continue
            target = _resolve_overview_coverage(line)
            if not target or target not in matrix:
                continue
            amount = _last_amount(line)
            if not amount:
                continue
            bucket = cells.setdefault(target, {})
            # 계약 내부는 구성 항목 합(예: 통원 = 외래 + 처방조제).
            bucket[key] = bucket.get(key, 0) + amount

    filled: dict[str, int] = {}
    for kb_name, row in matrix.items():
        got = cells.get(kb_name)
        if not got:
            continue
        values = list(got.values())
        total = sum(values) if row.get("agg") != "rep" else max(values)
        if total == row.get("summary"):   # ★귀속 게이트
            row["by_company"] = dict(got)
            filled[kb_name] = total
    return filled


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


def _premium_index(contracts: list[dict]) -> dict[int, frozenset]:
    """BOHUMFIT-253(회송): 월보험료 → 계약 idx ★집합 역인덱스.

    기존 `{monthly_premium: idx}` dict는 동일 보험료 계약이 2건 이상이면 마지막 계약만
    남겨(last-wins) 실제로는 모호한 매칭을 "유일"로 오인시켰다(Codex 실증: 50,000원
    계약 2건에서 200만원이 '?'가 아닌 계약 2로 오귀속). 중복을 집합으로 보존한다.
    """
    index: dict[int, set] = {}
    for c in contracts:
        if c.get("monthly_premium"):
            index.setdefault(c["monthly_premium"], set()).add(c["idx"])
    return {premium: frozenset(ids) for premium, ids in index.items()}


def _resolve_unique_idx(premiums: list, premium_index: dict[int, frozenset]) -> Optional[int]:
    """후보 보험료들이 가리키는 계약 후보 합집합이 ★정확히 1개일 때만 idx 반환.

    BOHUMFIT-253(회송): 기간 라인 경로·헤더 폴백이 이 단일 판정을 공유한다(경로별 복제
    금지 — 251 골든 픽스처 교훈). 동일 보험료 복수 계약·상이 보험료 복수 매칭·매칭 0은
    전부 모호 → None → '?' 유지(오귀속 0이 제1원칙 — 251 미배치+명시 원칙).
    """
    matched: set = set()
    for premium in premiums:
        matched |= premium_index.get(premium, frozenset())
    if len(matched) == 1:
        return next(iter(matched))
    return None


def _detail_contract_idx(lines: list[str], premium_index: dict[int, frozenset]) -> Optional[int]:
    # 1) 기간 라인 경로 — 기간(YYYY-MM-DD ~ YYYY-MM-DD) 라인의 보험료로 판정.
    #    253 회송: last-wins 순회를 제거하고 공용 유일성 판정 사용(모호 → 폴백 진행).
    for line in lines[:16]:
        if not re.search(r"\d{4}-\d{2}-\d{2}\s*~\s*\d{4}-\d{2}-\d{2}", line):
            continue
        premiums = [parse_won(m.group("premium") + "원") for m in DETAIL_PREMIUM_RE.finditer(line)]
        idx = _resolve_unique_idx(premiums, premium_index)
        if idx is not None:
            return idx
    # 2) BOHUMFIT-253: 기간 라인에 보험료가 없는 레이아웃 폴백 — layout=True 추출이 표 행을
    #    줄바꿈해 월보험료가 기간 라인 2줄 아래에 놓이는 페이지 실측(A p10·p17, D p15 —
    #    이 페이지들의 EXTRA 담보가 '?'로 귀속돼 회사합≠합계 발생). 헤더 16줄 전체 수집,
    #    동일한 유일성 판정(모호 → None → '?').
    all_premiums = [
        parse_won(m.group("premium") + "원")
        for line in lines[:16]
        for m in DETAIL_PREMIUM_RE.finditer(line)
    ]
    return _resolve_unique_idx(all_premiums, premium_index)


def _last_amount(line: str):
    vals = [parse_amount(t) for t in extract_cells(line)]
    for value in reversed(vals):
        if value:
            return value
    return None


def parse_detail_pages(detail_pages: list[list[str]], contracts: list[dict], jong_table: dict | None = None):
    """Parse detailed pages for contract remarks and non-standard 기타 riders."""
    # BOHUMFIT-253(회송): 동일 보험료 계약을 보존하는 집합 역인덱스(last-wins dict 제거).
    premium_index = _premium_index(contracts)
    notes: dict[int, dict] = {}
    extra: dict[str, dict] = {}
    # BOHUMFIT-245 ①②: 일반/재해사망은 KB가 동일 담보를 상해·질병사망 지급사유 행으로
    #   중복 표기한다(A 실측: `일반사망` 6,000만이 두 행) — 동일 (계약, 담보명, 금액)의
    #   재등장은 1회만 계상해 담보 자체의 이중 합산을 막는다(사망 배타 가드의 일부).
    _DEATH_DEDUP_LABELS = ("일반사망", "재해사망")
    death_seen: set[tuple] = set()

    for lines in detail_pages:
        idx = _detail_contract_idx(lines, premium_index)
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
            key = str(idx) if idx is not None else "?"
            # BOHUMFIT-238: 종수술비가 종별 마커 없이 "5종 기준 최대금액"만 표기된 경우
            # 표준 환산표로 1~5종을 세팅한다(원문에 종별이 있으면 미적용 — 원문 우선).
            if label == "종수술비":
                name, _cls = split_detail_parts(line)
                compact_name = _despace(name)
                if not has_explicit_tier(compact_name):
                    tiers = lookup_jong_tiers(amount, jong_table)
                    if tiers is None:
                        # 표 외(100만원 미만): 세팅하지 않고 "표 외" 표기 버킷으로 유지.
                        entry = extra.setdefault(OUT_OF_RANGE_LABEL, {"agg": agg, "by_company": {}})
                        entry["by_company"][key] = entry["by_company"].get(key, 0) + amount
                    else:
                        for tier, tier_amount in tiers.items():
                            entry = extra.setdefault(
                                estimated_tier_label(tier),
                                {"agg": agg, "by_company": {}, "estimated": True},
                            )
                            entry["by_company"][key] = entry["by_company"].get(key, 0) + tier_amount
                    continue
            if label in _DEATH_DEDUP_LABELS:
                name, cls = split_detail_parts(line)
                # BOHUMFIT-246: 배타 차감 근거 — 지급사유(KB분류) 행별 금액을 계약 키로 기록.
                #   계상은 dedup으로 1회지만 매트릭스 상해/질병사망 셀에는 지급사유별로 반영돼
                #   있어(A 실측: 일반사망 6,000만이 두 셀에 각각) 차감은 전 지급사유 행 기준.
                #   검출·계상 결과는 245와 동일(주석 데이터만 추가).
                compact_cls = _despace(cls)
                if compact_cls in ("상해사망", "질병사망"):
                    dead_entry = extra.setdefault(label, {"agg": agg, "by_company": {}})
                    class_map = dead_entry.setdefault("class_amounts", {}).setdefault(key, {})
                    class_map[compact_cls] = class_map.get(compact_cls, 0) + amount
                dedup_key = (label, key, _despace(name), amount)
                if dedup_key in death_seen:
                    continue
                death_seen.add(dedup_key)
            if label == "중입자방사선":
                name, _cls = split_detail_parts(line)
                if "고액항암치료비" in _despace(name):
                    # BOHUMFIT-246: KB가 이 라인을 매트릭스 표적항암치료(구 고액(표적)) 행에
                    #   합산함(D 실측: 표적 6,000만+중입자 5,000만=1.1억) — 배타 차감용 포함분
                    #   기록(검출·계상 불변). E형("기타 인보험" 분류)은 미기록 → 차감 없음.
                    ion_entry = extra.setdefault(label, {"agg": agg, "by_company": {}})
                    included = ion_entry.setdefault("target_included", {})
                    included[key] = included.get(key, 0) + amount
            entry = extra.setdefault(label, {"agg": agg, "by_company": {}})
            entry["by_company"][key] = entry["by_company"].get(key, 0) + amount
            # BOHUMFIT-237 C: N대수술비는 원문의 N(131대 등)을 채집해 표시명 병기에 쓴다.
            if label == "N대수술비":
                n = extract_n_surgery(line)
                if n is not None:
                    values = entry.setdefault("n_values", [])
                    if n not in values:
                        values.append(n)

    return notes, extra


def parse_document(pdf_bytes: bytes, jong_table: dict | None = None) -> dict:
    pages = _extract_pages(pdf_bytes)
    joined_heads = " ".join(" ".join(p[:8]) for p in pages)
    if not all(hint in joined_heads for hint in KB_FORMAT_HINTS):
        raise KBFormatError("KB 표준형 보장분석 제안서 형식이 아닙니다.")

    warnings: list[str] = []
    contracts_pages: list[list[str]] = []
    matrix_pages: list[list[str]] = []
    overview_pages: list[list[str]] = []  # BOHUMFIT-239: 전체 보장현황(매트릭스 fallback)
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
            # BOHUMFIT-239: 매트릭스는 헤더 기반 감지 + 다페이지 누적(표준 문서 p6~8 등 — 기존 정상).
            matrix_pages.append(lines)
        elif role == "overview":
            overview_pages.append(lines)
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
    # BOHUMFIT-239: '상품별 가입현황' 매트릭스가 없는 변형 문서는 '전체 보장현황'의
    # 담보별 합계로 대체한다(fallback). 표준 문서는 매트릭스가 있어 이 경로를 타지 않는다.
    matrix_from_overview = False
    if not matrix and overview_pages:
        matrix = parse_overview(overview_pages)
        matrix_from_overview = bool(matrix)
    if contracts and matrix and not matrix_from_overview:
        contracts = _ensure_contracts_for_matrix_columns(contracts, matrix)
    diagnosis = parse_diagnosis(diagnosis_lines) if diagnosis_lines else {}
    notes, extra = parse_detail_pages(detail_pages, contracts, jong_table) if detail_pages else ({}, {})
    # BOHUMFIT-256: overview fallback 문서만 — detail에서 계약별 귀속을 복원한다(귀속 게이트
    #   통과분만 채움·summary 불변). 표준 문서는 matrix_from_overview가 False라 미진입.
    if matrix_from_overview:
        attribute_overview_by_company(matrix, detail_pages, contracts)

    if not contracts:
        warnings.append("p5 계약리스트를 찾지 못했습니다.")
    if not matrix:
        warnings.append("p6~7 상품별 가입현황 매트릭스를 찾지 못했습니다.")
    elif matrix_from_overview:
        # 담보별 합계는 확보했으나 계약별 상세 금액은 이 문서에 없음(정직 표기).
        warnings.append("상품별 가입현황 페이지가 없어 전체 보장현황의 담보별 합계로 대체했습니다. 계약별 상세 금액은 표시되지 않을 수 있습니다.")
    if contracts and matrix and not matrix_from_overview:
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
