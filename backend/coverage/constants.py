"""KB guaranteed-issue coverage proposal constants for BOHUMFIT-179/179b."""
from __future__ import annotations

import re

AGG_SUM = "sum"
AGG_REP = "rep"

GROUP12 = (
    "사망",
    "후유장해",
    "암",
    "뇌",
    "심장",
    "수술",
    "입원(간병 포함)",
    "운전자",
    "골절",
    "실손",
    "화재",
    "배상책임",
)

GROUP_ETC = "기타"
GROUP_EXCLUDED = "제외"
GROUP13 = GROUP12 + (GROUP_ETC,)

KNOWN_INSURERS = (
    "ABL생명",
    "AIA생명",
    "DB손해보험",
    "DB손보",
    "KB라이프생명",
    "KB손해보험",
    "KB손보",
    "KDB생명",
    "MG손해보험",
    "NH농협생명",
    "NH농협손해보험",
    "교보생명",
    "농협생명",
    "농협손해보험",
    "동양생명",
    "라이나생명",
    "롯데손해보험",
    "메리츠화재",
    "미래에셋생명",
    "삼성생명",
    "삼성화재",
    "신한라이프",
    "악사손해보험",
    "에이스손해보험",
    "우체국보험",
    "처브라이프",
    "푸본현대생명",
    "하나생명",
    "한화생명",
    "한화손해보험",
    "한화손보",
    "현대해상",
    "흥국생명",
    "흥국화재",
)

# (kb_name, kb_group, group12, agg) in the KB proposal display order.
KB_COVERAGES: tuple[tuple[str, str, str, str], ...] = (
    ("상해사망", "사망", "사망", AGG_SUM),
    ("질병사망", "사망", "사망", AGG_SUM),
    ("상해80%미만후유장해", "장해", "후유장해", AGG_SUM),
    ("질병80%미만후유장해", "장해", "후유장해", AGG_SUM),
    ("장기요양간병비", "치매/간병", GROUP_EXCLUDED, AGG_SUM),
    ("경증치매진단", "치매/간병", GROUP_EXCLUDED, AGG_SUM),
    ("간병인/간호간병상해일당", "치매/간병", "입원(간병 포함)", AGG_SUM),
    ("간병인/간호간병질병일당", "치매/간병", "입원(간병 포함)", AGG_SUM),
    ("일반암", "암 진단", "암", AGG_SUM),
    ("유사암", "암 진단", "암", AGG_SUM),
    ("고액암", "암 진단", "암", AGG_SUM),
    ("고액(표적)항암치료비", "암 진단", "암", AGG_SUM),
    ("뇌혈관질환", "뇌 진단", "뇌", AGG_SUM),
    ("뇌졸중", "뇌 진단", "뇌", AGG_SUM),
    ("뇌출혈", "뇌 진단", "뇌", AGG_SUM),
    ("허혈성심장질환", "심장 진단", "심장", AGG_SUM),
    ("급성심근경색증", "심장 진단", "심장", AGG_SUM),
    ("상해입원의료비", "실손", "실손", AGG_REP),
    ("상해통원의료비", "실손", "실손", AGG_REP),
    ("질병입원의료비", "실손", "실손", AGG_REP),
    ("질병통원의료비", "실손", "실손", AGG_REP),
    ("3대비급여실손", "실손", "실손", AGG_REP),
    ("상해수술비", "수술/입원", "수술", AGG_SUM),
    ("질병수술비", "수술/입원", "수술", AGG_SUM),
    ("암수술비", "수술/입원", "수술", AGG_SUM),
    ("뇌혈관질환수술비", "수술/입원", "수술", AGG_SUM),
    ("허혈성심장질환수술비", "수술/입원", "수술", AGG_SUM),
    ("상해입원일당", "수술/입원", "입원(간병 포함)", AGG_SUM),
    ("질병입원일당", "수술/입원", "입원(간병 포함)", AGG_SUM),
    ("벌금(대인/스쿨존/대물)", "운전자/기타", "운전자", AGG_SUM),
    ("교통사고처리지원금", "운전자/기타", "운전자", AGG_SUM),
    ("변호사선임비용", "운전자/기타", "운전자", AGG_SUM),
    ("자동차사고부상", "운전자/기타", "운전자", AGG_SUM),
    ("골절진단비", "운전자/기타", "골절", AGG_SUM),
    ("보철치료비", "운전자/기타", "골절", AGG_SUM),
    ("가족/일상/자녀배상", "운전자/기타", "배상책임", AGG_REP),
    ("화재벌금", "운전자/기타", "화재", AGG_SUM),
)

STANDARD_COUNT = len(KB_COVERAGES)


def _despace(text: str) -> str:
    return "".join((text or "").split())


_BY_DESPACE = {_despace(n): (n, g, g12, a) for (n, g, g12, a) in KB_COVERAGES}
_NAMES_BY_LEN = sorted(_BY_DESPACE.keys(), key=len, reverse=True)


def match_coverage(text: str):
    d = _despace(text)
    for name in _NAMES_BY_LEN:
        if name in d:
            return _BY_DESPACE[name]
    return None


def match_coverage_span(text: str):
    """Return (meta, start, end) using whitespace-insensitive matching."""
    compact = ""
    positions: list[int] = []
    for idx, ch in enumerate(text or ""):
        if not ch.isspace():
            positions.append(idx)
            compact += ch
    for name in _NAMES_BY_LEN:
        start = compact.find(name)
        if start >= 0:
            end = start + len(name) - 1
            return _BY_DESPACE[name], positions[start], positions[end] + 1
    return None, None, None


def coverage_meta(kb_name: str):
    return _BY_DESPACE.get(_despace(kb_name))


ROLE_MARKERS = {
    "contracts": "전체 계약리스트",
    "matrix": "상품별 가입현황",
    "detail": "상품별 가입담보상세",
    "diagnosis": "전체 담보 진단 현황",
}

KB_FORMAT_HINTS = ("계약리스트", "상품별", "진단")

EXTRA_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"(?:상급종합|종합)병원.*(?:입원|통원)일당"), "상급/종합병원 일당", AGG_SUM),
    (re.compile(r"(?:상급종합|종합)병원.*수술"), "상급/종합병원 수술비", AGG_SUM),
    (re.compile(r"\d+대\S*수술"), "N대수술비", AGG_SUM),
    (re.compile(r"화상"), "화상", AGG_SUM),
    (re.compile(r"폴립|양성종양"), "양성종양·폴립", AGG_SUM),
    (re.compile(r"통원일당"), "통원일당", AGG_SUM),
)

EXTRA_LABEL_GROUP = {
    "골절보철치료비": "골절",
    "화상": "골절",
}


def classify_extra(text: str):
    """Classify non-standard detailed riders into the BOHUMFIT-179b 기타 bucket."""
    compact = _despace(text)
    for pattern, label, agg in EXTRA_PATTERNS:
        if pattern.search(compact):
            return label, agg
    if match_coverage(text):
        return None
    return None
