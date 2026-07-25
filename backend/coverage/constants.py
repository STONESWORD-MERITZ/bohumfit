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
    # BOHUMFIT-243 ①: 공제·금고 등 비보험사 기관(계약리스트에 보험사 자리로 등장) — 실측 확인분.
    "새마을금고중앙회",
    "신협중앙회",
    "수협중앙회",
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
    # BOHUMFIT-245 ⑦: 표적항암 통합 — 신 체계(244) 명칭 "표적항암치료"로 개명(값 이관).
    #   KB 원문(매트릭스·진단 행)의 "고액(표적)항암치료비"는 KB_NAME_ALIASES로 계속 매칭되고,
    #   상세의 표적항암약물치료 라인은 KB가 이미 이 행에 합산함을 실측(B 7,000만=매트릭스 일치,
    #   D 표적 6,000만+중입자 5,000만=1.1억 일치) — 별도 EXTRA 패턴을 만들지 않아 이중 계상 0.
    ("표적항암치료", "암 진단", "암", AGG_SUM),
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

# BOHUMFIT-245 ⑦: KB 원문 표기 → 신 체계 정식명 별칭. 매트릭스·진단·전체보장현황(239)의
#   원문 행이 별칭으로 매칭돼도 반환 메타는 정식명이므로 하류(집계·진단 결합)는 자동 일관.
KB_NAME_ALIASES = {
    "고액(표적)항암치료비": "표적항암치료",
}
for _alias, _canonical in KB_NAME_ALIASES.items():
    _BY_DESPACE[_despace(_alias)] = _BY_DESPACE[_despace(_canonical)]

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

# BOHUMFIT-234: 상세 라인은 "번호 정액 담보명 [KB분류] [금액]" 구조 — 분류·금액 꼬리를
# 분리해 담보명 기준으로 판정한다(분류 컬럼 텍스트만 매칭되는 과추출 방지: 234 ⑨류).
_DETAIL_AMOUNT_TAIL_RE = re.compile(r"[\d,]+\s*(?:천만|만|억|원)\s*$")
_DETAIL_CLASS_TOKEN_RE = re.compile(r"(?:진단|수술|일당|사망|장해)$")
_DETAIL_CLASS_PREFIXES = ("상급종합병원", "종합병원이하", "중대")
_DETAIL_ROW_HEAD_RE = re.compile(r"^\s*\d+\s+(?:정액|실손)\s*")
_BRACKET_RE = re.compile(r"\([^()]*\)|\[[^\[\]]*\]")


def split_detail_parts(text: str) -> tuple[str, str]:
    """상세 라인 → (담보명, KB분류). 분류·금액이 없는 입력은 (원문, "")로 하위호환."""
    body = _DETAIL_AMOUNT_TAIL_RE.sub("", (text or "").strip()).rstrip()
    parts = body.split()
    cls = ""
    if len(parts) >= 2 and _DETAIL_CLASS_TOKEN_RE.search(parts[-1]):
        cls = parts[-1]
        parts = parts[:-1]
        if parts and parts[-1] in _DETAIL_CLASS_PREFIXES:
            cls = parts[-1] + cls
            parts = parts[:-1]
    name = _DETAIL_ROW_HEAD_RE.sub("", " ".join(parts))
    return name.strip(), cls


def _strip_brackets(compact: str) -> str:
    prev = None
    while prev != compact:
        prev = compact
        compact = _BRACKET_RE.sub("", compact)
    return compact


# 담보명 기준 패턴(순서 = 우선순위). bracket=True는 괄호/대괄호 안 수식어 제거 후 매칭
# ("간편심사[355(6대질병)] 질병1~5종수술"의 '6대'가 N대수술로 오포섭되는 234 ② 방지).
EXTRA_PATTERNS: tuple[tuple[re.Pattern[str], str, str, bool], ...] = (
    (re.compile(r"(?:상급종합|종합)병원.*(?:입원|통원)일당"), "상급/종합병원 일당", AGG_SUM, False),
    (re.compile(r"(?:상급종합|종합)병원.*수술"), "상급/종합병원 수술비", AGG_SUM, False),
    (re.compile(r"장기이식"), "장기이식수술비", AGG_SUM, False),
    (re.compile(r"폴립|양성종양"), "양성종양·폴립", AGG_SUM, False),
    # BOHUMFIT-236 E: 2대주요치료비(뇌·심) — 혈전용해·뇌심수술·중환자실 치료비 계열.
    # 타 보험사 문서에서 텍스트로 등장 시 자동 분류(수동 입력과 병행). N대수술보다 선순위.
    (re.compile(r"2대주요치료"), "2대주요치료비(뇌·심)", AGG_SUM, False),
    # BOHUMFIT-236 F: 실사용 A 케이스 c4 실측 — 간편보험의 비표준 담보 2종 가시화.
    (re.compile(r"중환자실\S*일당"), "중환자실 입원일당", AGG_SUM, False),
    (re.compile(r"80[%％]이상\S*후유장해"), "80%이상 후유장해", AGG_SUM, False),
    (re.compile(r"\d+종수술"), "종수술비", AGG_SUM, True),
    # BOHUMFIT-237 C: "5대골절수술비"류가 N대수술비 N 병기에 혼입되지 않도록 분리
    # (234에서 기록만 했던 잔존 포섭 해소 — 골절 그룹).
    (re.compile(r"골절수술"), "골절수술비", AGG_SUM, False),
    (re.compile(r"혈관수술"), "심·뇌혈관수술비", AGG_SUM, False),
    (re.compile(r"\d+대\S*수술"), "N대수술비", AGG_SUM, True),
    (re.compile(r"통원일당"), "통원일당", AGG_SUM, False),
    # BOHUMFIT-237 B: 운전자 6주미만 계열 — 실측 원문 "교통사고 처리지원금(6주미만 진단)"
    # (실손 유형·C/D/H 케이스 실재). 기존 교통사고처리지원금(기준담보)과 별도 담보로 표시.
    (re.compile(r"6주미만"), "교통사고처리지원금(6주미만)", AGG_SUM, False),
    # BOHUMFIT-245: 신 체계(244 S2) 미커버 담보 — 기존 패턴 뒤에 추가해 기존 캡처 우선순위 불변
    #   (S0 시뮬레이션: 5케이스 전 상세 라인에서 기존 라벨과 교집합 0 실측).
    # ⑤③ 중입자 > 항암약물방사선 선순위(244 명시) — 포괄 패턴이 중입자 라인을 선점하는 것을
    #   방지(D·E 실측: 항암중입자방사선치료가 ③ 패턴에도 걸림). ③의 (?<!표적)는 표적항암약물
    #   라인 배제 — KB가 매트릭스 표적항암치료(구 고액(표적)) 행에 이미 합산함(이중 계상 방지).
    (re.compile(r"중입자"), "중입자방사선", AGG_SUM, False),
    (re.compile(r"(?<!표적)항암\S*(?:방사선|약물)\S*치료"), "항암약물방사선", AGG_SUM, False),
    # ①② 사망 — 원문에 독립 담보로 명시된 경우만(A `일반사망`·D `재해사망특약` 실측).
    #   상호배타 가드: 그룹 미등록(기타 귀속)으로 매트릭스 상해/질병사망 집계와 분리하고,
    #   KB의 지급사유별 중복 행은 parser 측 dedup으로 1회만 계상(A: 동일 6,000만이 2행).
    (re.compile(r"^일반사망"), "일반사망", AGG_SUM, False),
    (re.compile(r"재해사망"), "재해사망", AGG_SUM, False),
    # ⑥⑦⑧ 순환계·응급실·깁스. 깁스는 `깁스치료(비|특약)` 종결형만 — 복합특약의 분류 전용
    #   행("상해 통합치료비 … 깁스치료" C 실측)은 234 ⑨ 원칙대로 미계상.
    (re.compile(r"순환계\S*치료"), "순환계 치료비", AGG_SUM, False),
    (re.compile(r"응급실\S*(?:내원|치료)"), "응급실", AGG_SUM, False),
    (re.compile(r"깁스치료(?:비|특약)"), "깁스치료비", AGG_SUM, False),
)

# BOHUMFIT-237 C: N대수술비의 N 병기용 — 괄호 수식어 제거본에서 매칭된 N을 추출.
_N_SURGERY_RE = re.compile(r"(\d+)대\S*수술")


def extract_n_surgery(text: str):
    """상세 라인에서 N대수술비의 N(예: 131) 추출 — 미매칭 시 None."""
    name, _cls = split_detail_parts(text)
    match = _N_SURGERY_RE.search(_strip_brackets(_despace(name)))
    return int(match.group(1)) if match else None

EXTRA_LABEL_GROUP = {
    "골절보철치료비": "골절",
    "화상": "골절",
    "화상진단비": "골절",
    "화상수술비": "골절",
    "중환자실 입원일당": "입원(간병 포함)",
    # BOHUMFIT-243 ②(2026-07-24 Human 결정 · 244 양식 기준 정합): "80%이상" 후유장해는
    #   후유장해 대분류 집계에서 제외(미포섭)한다 — 상해/질병 후유장해 집계는 3-100% 담보만.
    #   담보 자체는 기타(GROUP_ETC 기본값)로 표시해 정보는 보존한다(매핑 미등록 = 기타).
    "교통사고처리지원금(6주미만)": "운전자",
    "골절수술비": "골절",
    # BOHUMFIT-245: 깁스치료비만 골절 귀속(244 S2 ⑧ 명시·매트릭스 미포함이라 이중 계상 없음).
    #   나머지 신규 6종(일반/재해사망·중입자·항암약물방사선·순환계·응급실)은 의도적으로 미등록
    #   = 기타 — 사망은 매트릭스 상해/질병사망과의 이중 계상 방지(배타 가드), 중입자는 매트릭스
    #   표적항암치료 행에 포함된 케이스(D) 실측, 그룹 이관은 2단계(집계·스키마 전환) 소관.
    "깁스치료비": "골절",
}


def classify_extra(text: str):
    """Classify non-standard detailed riders into the BOHUMFIT-179b 기타 bucket.

    BOHUMFIT-234: 담보명/KB분류를 분리해 담보명 기준으로 판정한다.
    - 화상: 담보명에 '화상'이 있어야 계상(상품명·타담보 라인이 분류 컬럼 '화상진단'만으로
      집계되던 과추출 제거). KB분류로 화상진단비/화상수술비를 분리 집계(234 ⑤).
    - 종수술·장기이식·혈관수술은 N대수술비에서 분리(234 ②⑦⑩ 과포섭 해소).
    """
    name, cls = split_detail_parts(text)
    compact_name = _despace(name)
    compact_cls = _despace(cls)
    if not compact_name:
        return None

    if "화상" in compact_name:
        if "화상진단" in compact_cls or (not compact_cls and "화상진단" in compact_name):
            return "화상진단비", AGG_SUM
        if "화상수술" in compact_cls or (not compact_cls and "화상수술" in compact_name):
            return "화상수술비", AGG_SUM
        if re.match(r"^(?:골절)?화상", compact_name):
            # 담보명이 화상(또는 골절화상)으로 시작하는 순수 화상 담보 — 통합 라벨 유지.
            return "화상", AGG_SUM
        # 복합 특약("교통사고 및 골절.화상 관련보장")의 비화상 분류 행은 계상하지 않는다.
        return None

    stripped_name = _strip_brackets(compact_name)
    for pattern, label, agg, use_stripped in EXTRA_PATTERNS:
        target = stripped_name if use_stripped else compact_name
        if pattern.search(target):
            return label, agg
    return None
