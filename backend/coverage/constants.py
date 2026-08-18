"""KB guaranteed-issue coverage proposal constants for BOHUMFIT-179/179b."""
from __future__ import annotations

import re
from typing import NamedTuple

AGG_SUM = "sum"
AGG_REP = "rep"

# BOHUMFIT-246: 대분류를 비분양식(244 S3 실측) 섹션으로 전면 교체(정본화).
#   변수명 GROUP12/GROUP13은 역사적 명칭으로 유지(소비처 import 안정) — 항목 수와 무관.
#   ★BOHUMFIT-293: 산출물 대분류는 `GROUP12_V2`(11) / `GROUP13_V2`가 **유일**하다. 아래 구 축은
#   `KB_COVERAGES` 필드값과 구 페이로드 정렬(`compare._LEGACY_GROUP13`)에만 남는다 — 층위 3에서 제거.
#   "가입특약(Y/N)"은 양식 45~49행(Y/N 표기 항목)의 판정 원천 담보(운전자·배상·실손)를
#   금액 보존 상태로 묶는 그룹이다(제1원칙: 누락 0 — Y/N 파생은 yn_flags 별도 산출).
GROUP12 = (
    "사망",
    "후유장해",
    "암",
    "뇌",
    "심장",
    "종수술",
    "수술",
    "의료이용",
    "골절",
    "가입특약(Y/N)",
)

GROUP_ETC = "기타"
GROUP_EXCLUDED = "제외"
GROUP13 = GROUP12 + (GROUP_ETC,)
GROUP_YN = "가입특약(Y/N)"

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

# ★BOHUMFIT-293(층위 2 정리) — 이 표의 **역할이 바뀌었다**. 더 이상 "산출물 양식 40행"이 아니다.
#   52행 V2(`KB_COVERAGES_V2`)가 **유일한 산출물 스키마**이고(286~296), 이 표는 아래 둘로만 남는다.
#     ① **KB 원문 담보명 사전** — `_BY_DESPACE` → `match_coverage`/`match_coverage_span`/`coverage_meta`.
#        parser.py·proposal_parser.py가 PDF 원문 담보명을 정식명으로 정규화할 때 쓴다(정식명 = `meta[0]`).
#        `agg` 필드는 `v2_mapping._LEGACY_AGG` → `ROW_AGG`로 흘러 **V2 행의 sum/rep을 정한다**(실손 rep).
#        이름 집합은 `_LEGACY_NAMES_V2` → `NEW_ROWS_V2`(신설 행 판별)의 기준이다.
#     ② **구 페이로드 호환 축** — `GROUP13`은 row_id 없는 과거 저장분·구 프런트 미러 payload를
#        정렬할 때만 쓴다(`compare._LEGACY_GROUP13`). 프런트가 V2로 옮겨오면 그때 제거한다(층위 3).
#   ★그래서 293은 이 표를 지우지 않는다 — 지우려면 파서를 고쳐야 하고, 파서는 무접촉 범위다.
#     `group12`(3번째 필드)는 산출물에는 더 이상 쓰이지 않으나 튜플 모양을 바꾸면 파서가 바뀌므로 남긴다.
#
# (kb_name, kb_group, group12, agg) — BOHUMFIT-246: 정식명·그룹을 비분양식 항목으로 교체.
#   kb_name = 신 체계 정식명(양식 시트2 담보명 원문), kb_group = KB 원문 분류(참고 정보 유지).
#   KB 원문 표기(일반암·암수술비 등)는 KB_NAME_ALIASES로 계속 매칭된다(매트릭스·진단·overview).
#   면역항암치료·암 주요치료비·심혈관질환은 원문 데이터 없는 신담보 — [후] 전용 자리로 행만
#   존치([전]은 매칭 원문이 없어 미가입/None — 244 결정).
KB_COVERAGES: tuple[tuple[str, str, str, str], ...] = (
    # ── 사망(양식 10~13행 중 표준 매트릭스 원천 — 일반·재해사망은 상세 검출 EXTRA)
    ("질병사망", "사망", "사망", AGG_SUM),
    ("상해사망", "사망", "사망", AGG_SUM),
    # ── 후유장해(14~15행) — 243: 80%이상 제외(기타 보존) 유지, 3-100%만
    ("상해후유장해", "장해", "후유장해", AGG_SUM),
    ("질병후유장해", "장해", "후유장해", AGG_SUM),
    # ── 암(16~23행)
    ("암진단금", "암 진단", "암", AGG_SUM),
    ("유사암진단금", "암 진단", "암", AGG_SUM),
    ("암수술", "수술/입원", "암", AGG_SUM),
    # BOHUMFIT-245 ⑦: 표적항암 통합 — "표적항암치료"로 개명(값 이관). 상세의 표적항암약물
    #   라인은 KB가 이미 이 행에 합산함을 실측(B 7,000만=매트릭스 일치, D 표적 6,000만+
    #   중입자 5,000만=1.1억 일치) — 별도 EXTRA 패턴을 만들지 않아 이중 계상 0.
    ("표적항암치료", "암 진단", "암", AGG_SUM),
    ("면역항암치료", "암 진단", "암", AGG_SUM),
    ("암 주요치료비", "암 진단", "암", AGG_SUM),
    # ── 뇌(24~27행)
    ("뇌혈관질환", "뇌 진단", "뇌", AGG_SUM),
    ("뇌졸중", "뇌 진단", "뇌", AGG_SUM),
    ("뇌출혈", "뇌 진단", "뇌", AGG_SUM),
    ("뇌혈관수술", "수술/입원", "뇌", AGG_SUM),
    # ── 심장(28~31행 — 순환계 치료비(32행)는 EXTRA)
    ("심혈관질환", "심장 진단", "심장", AGG_SUM),
    ("허혈성심장질환", "심장 진단", "심장", AGG_SUM),
    ("급성심근경색", "심장 진단", "심장", AGG_SUM),
    ("심혈관수술", "수술/입원", "심장", AGG_SUM),
    # ── 수술(38~39행)
    ("상해수술", "수술/입원", "수술", AGG_SUM),
    ("질병수술", "수술/입원", "수술", AGG_SUM),
    # ── 의료이용(40~42행 — 응급실은 EXTRA)
    ("질병입원", "수술/입원", "의료이용", AGG_SUM),
    ("상해입원", "수술/입원", "의료이용", AGG_SUM),
    # ── 골절(43~44행 — 깁스치료비는 EXTRA)
    ("골절진단비", "운전자/기타", "골절", AGG_SUM),
    # ── 가입특약(Y/N) 판정 원천(45~49행) — 금액 보존(제1원칙), Y/N 파생은 YN_ITEMS
    ("벌금(대인/스쿨존/대물)", "운전자/기타", GROUP_YN, AGG_SUM),
    ("교통사고처리지원금", "운전자/기타", GROUP_YN, AGG_SUM),
    ("변호사선임비용", "운전자/기타", GROUP_YN, AGG_SUM),
    ("자동차사고부상", "운전자/기타", GROUP_YN, AGG_SUM),
    ("가족/일상/자녀배상", "운전자/기타", GROUP_YN, AGG_REP),
    ("상해입원의료비", "실손", GROUP_YN, AGG_REP),
    ("상해통원의료비", "실손", GROUP_YN, AGG_REP),
    ("질병입원의료비", "실손", GROUP_YN, AGG_REP),
    ("질병통원의료비", "실손", GROUP_YN, AGG_REP),
    # ── 기타 보존(신 양식 비항목 — 정보 무손실·246 귀속만 이동)
    ("고액암", "암 진단", GROUP_ETC, AGG_SUM),
    ("3대비급여실손", "실손", GROUP_ETC, AGG_REP),
    ("간병인/간호간병상해일당", "치매/간병", GROUP_ETC, AGG_SUM),
    ("간병인/간호간병질병일당", "치매/간병", GROUP_ETC, AGG_SUM),
    ("보철치료비", "운전자/기타", GROUP_ETC, AGG_SUM),
    ("화재벌금", "운전자/기타", GROUP_ETC, AGG_SUM),
    # ── 제외 유지(기존 동작 — 집계·표시 모두 미포함)
    ("장기요양간병비", "치매/간병", GROUP_EXCLUDED, AGG_SUM),
    ("경증치매진단", "치매/간병", GROUP_EXCLUDED, AGG_SUM),
)

def _despace(text: str) -> str:
    return "".join((text or "").split())


_BY_DESPACE = {_despace(n): (n, g, g12, a) for (n, g, g12, a) in KB_COVERAGES}

# BOHUMFIT-245 ⑦/246: KB 원문 표기 → 신 체계 정식명 별칭. 매트릭스·진단·전체보장현황(239)의
#   원문 행이 별칭으로 매칭돼도 반환 메타는 정식명이므로 하류(집계·진단 결합)는 자동 일관.
#   원문 전체 명칭이 별칭 키로 남아 있어 길이 우선 매칭(_NAMES_BY_LEN)의 기존 우선순위도 보존
#   (예: "허혈성심장질환수술비"(별칭)가 "허혈성심장질환"(정식명)보다 먼저 걸림 — 종전과 동일).
KB_NAME_ALIASES = {
    "고액(표적)항암치료비": "표적항암치료",
    # BOHUMFIT-246: 비분양식 항목명으로 정식명 교체 — KB 원문 행 표기는 별칭으로 유지.
    "상해80%미만후유장해": "상해후유장해",
    "질병80%미만후유장해": "질병후유장해",
    "일반암": "암진단금",
    "유사암": "유사암진단금",
    "암수술비": "암수술",
    "뇌혈관질환수술비": "뇌혈관수술",
    "허혈성심장질환수술비": "심혈관수술",
    "급성심근경색증": "급성심근경색",
    "상해수술비": "상해수술",
    "질병수술비": "질병수술",
    "상해입원일당": "상해입원",
    "질병입원일당": "질병입원",
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
    # BOHUMFIT-292(S4·Phase E): 합성 라벨 `심·뇌혈관수술비` 분리 — 담보명에 뇌/심 구분이 있으면
    #   각자 행(뇌혈관 수술비·심장질환 수술비). 둘 다·둘 다 아님은 아래 합성 라벨로 비고 보존(추측 금지).
    (re.compile(r"\A(?!.*심).*뇌\S*혈관수술"), "뇌혈관수술비", AGG_SUM, False),
    (re.compile(r"\A(?!.*뇌).*심\S*혈관수술"), "심혈관수술비", AGG_SUM, False),
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
    # BOHUMFIT-292 Human ③: 카티(CAR-T)는 면역약물치료 행. KB 고액항암 매트릭스 포함분은 배타 차감한다.
    (re.compile(r"카티\(CAR-T\)"), "면역항암치료", AGG_SUM, False),
    # BOHUMFIT-292(S4·Phase C): 다빈치 로봇 수술 — KB가 KB분류 `암수술`로 매트릭스 암수술 행에 합산하는
    #   라인(오현지 [전] #24 특정암 100만·#25 특정암제외 500만 실측). classify_extra가 종별(일반/전립선/
    #   갑상선/특정암/미상) 라벨로 세분하고 parser가 matrix_included(암수술)를 기록해 aggregator가 차감한다.
    (re.compile(r"다빈치|로봇\S*암수술"), "다빈치", AGG_SUM, False),
    # BOHUMFIT-292(S4·Phase B): 세기조절·양성자는 **각자 행**(49행 r23·r24). 종전 포괄 패턴이 이 둘을
    #   `항암약물방사선`으로 과포섭해 매트릭스 표적항암치료(KB분류 고액항암치료비)와 **이중 계상**했다
    #   (오현지 [전] #37·#39, 우상균 #42·#43 실측). 중입자와 같은 target_included 차감 대상.
    (re.compile(r"세기조절"), "세기조절방사선", AGG_SUM, False),
    (re.compile(r"양성자"), "양성자방사선", AGG_SUM, False),
    # ★292 협소화: `항암(방사선|약물|방사선약물|방사선및약물)치료` — 치료가 **바로** 이어지는 순수
    #   항암약물·항암방사선 담보만. `…약물허가치료`(표적·카티(CAR-T) 고액항암 계열 — 매트릭스 표적항암치료에
    #   KB가 이미 합산)·`항암세기조절…`·`항암양성자…`·`항암중입자…`는 제외(각자 규칙·이중 계상 방지).
    #   라벨은 classify_extra가 약물/방사선/결합으로 세분한다(Phase E).
    (re.compile(r"(?<!표적)항암(?:방사선및약물|방사선약물|약물방사선|방사선|약물)치료"), "항암약물방사선", AGG_SUM, False),
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

#: BOHUMFIT-292(S4): 매트릭스 표적항암치료(KB분류 고액항암치료비) 셀에서 배타 차감할 상세 라벨.
#:   246 중입자 기전을 세기조절·양성자로 확장(라벨 → 착지 행은 V2 별칭이 정한다).
TARGET_INCLUDED_LABELS: frozenset[str] = frozenset({"중입자방사선", "세기조절방사선", "양성자방사선", "면역항암치료"})

# BOHUMFIT-237 C: N대수술비의 N 병기용 — 괄호 수식어 제거본에서 매칭된 N을 추출.
_N_SURGERY_RE = re.compile(r"(\d+)대\S*수술")


def extract_n_surgery(text: str):
    """상세 라인에서 N대수술비의 N(예: 131) 추출 — 미매칭 시 None."""
    name, _cls = split_detail_parts(text)
    match = _N_SURGERY_RE.search(_strip_brackets(_despace(name)))
    return int(match.group(1)) if match else None

# BOHUMFIT-246: EXTRA 귀속을 비분양식 그룹으로 전환. 미등록 라벨 = 기타(정보 보존).
#   243 결정 유지: "80%이상 후유장해"는 미등록(기타) — 후유장해 집계는 3-100%만.
#   기존 골절 인접 귀속이던 골절수술비·화상류·보철, 운전자 귀속이던 6주미만, 입원 귀속이던
#   중환자실은 신 양식 비항목 → 기타 보존(귀속만 이동, 값 무변경).
EXTRA_LABEL_GROUP = {
    # 사망(양식 10~11행) — 승격. 상호배타는 aggregator의 매트릭스 차감으로 보장하며,
    #   차감 근거(지급사유 행)가 없는 계약 미확인 분은 "(계약 미확인)" 라벨로 기타 보존.
    "일반사망": "사망",
    "재해사망": "사망",
    # 암(19·22행)
    "항암약물방사선": "암",
    "중입자방사선": "암",
    "세기조절방사선": "암",  # BOHUMFIT-292(S4)
    "양성자방사선": "암",    # BOHUMFIT-292(S4)
    "면역항암치료": "암",    # BOHUMFIT-292 Human ③: 카티(CAR-T)
    "다빈치(일반암)": "암", "다빈치(전립선)": "암", "다빈치(갑상선)": "암", "다빈치(특정암)": "암",
    "다빈치(종별 미상)": "암",  # BOHUMFIT-292(S4)
    "항암약물치료비": "암", "항암방사선치료비": "암", "뇌혈관수술비": "뇌", "심혈관수술비": "심장",  # BOHUMFIT-292(S4·Phase E)
    # 심장(32행)
    "순환계 치료비": "심장",
    # 종수술(33~37행) — 238 환산 라벨(jong_surgery.estimated_tier_label)과 원문 버킷.
    #   원문 종별 분리형("종수술비")은 파서 무변경 제약상 1~5종 분해 불가 — 그룹 보존만.
    "일반종수술 1종(표준환산)": "종수술",
    "일반종수술 2종(표준환산)": "종수술",
    "일반종수술 3종(표준환산)": "종수술",
    "일반종수술 4종(표준환산)": "종수술",
    "일반종수술 5종(표준환산)": "종수술",
    "종수술비": "종수술",
    "종수술비(표 외)": "종수술",
    # 의료이용(40행)·골절(44행)
    "응급실": "의료이용",
    "깁스치료비": "골절",
}





# BOHUMFIT-246: 사망 상호배타 — 일반/재해사망 상세 라인의 지급사유(KB분류) 행 금액을
#   해당 표준 매트릭스 행에서 차감한다(동일 담보 이중 계상 0). 차감 실적은 death_dedup으로
#   반환해 총액 대사(구총합 = 신총합 + 차감액)에 쓴다. A 실측: 일반사망 6,000만이
#   상해사망·질병사망 매트릭스 셀에 각 6,000만으로 반영돼 있었다.
DEATH_EXCLUSION_LABELS: tuple[str, ...] = ("일반사망", "재해사망")


# ★BOHUMFIT-293(층위 2 정리): 구 40행 **양식 파생 상수**를 제거했다 — 제품 참조 0을 확인하고 지웠다.
#   · `NEW_ITEM_ORDER`(구 시트2 10~49행 표시 순서) → V2 `KB_COVERAGES_V2` 정의 순서(`ROW_INDEX`)가 대체
#   · `YN_ITEMS`(구 45~49행 Y/N 파생)      → `YN_ITEMS_V2` + `CoverageRowV2.yn_source`가 대체
#   · `STAGE_COMMON_ADD`/`STAGE_COMPONENTS`(구 시트3 3단 수식) → `PAYOUT_CASCADE_V2` 17체인이 대체
#   · `STANDARD_COUNT`                     → `STANDARD_COUNT_V2`가 대체
#   ※구 시트3 원본 수식 원문·H10 정정·K7 미이식 근거는 `.agent-harness/decisions.md`(246)에 보존한다.
#   ※`KB_COVERAGES`·`KB_NAME_ALIASES`·`GROUP12/13`은 **지우지 않았다** — 아래 ②의 사유(역할이 다르다).


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
            if label == "다빈치":
                return davinci_label(compact_name), agg
            if label == "항암약물방사선":
                return anticancer_label(compact_name), agg
            return label, agg
    return None


# ── BOHUMFIT-292(S4·Phase E): 합성 라벨 `항암약물방사선` 분리 ────────────────────────────
_KB_CANCER_CLASS_TAIL_RE = re.compile(r"(?:항암방사선약물치료비|고액항암치료비|기타인보험\(정액\)담보)$")
ANTICANCER_DRUG_LABEL = "항암약물치료비"          # → V2 `항암 약물 치료`
ANTICANCER_RADIATION_LABEL = "항암방사선치료비"   # → V2 `방사선 치료`
ANTICANCER_COMBINED_LABEL = "항암약물방사선"       # 결합 담보(방사선·약물을 한 담보로 지급) — 비고 보존


def anticancer_label(compact_name: str) -> str:
    """담보명이 약물만/방사선만/결합인지로 라벨을 가른다 — ★결합 담보는 갈라 추측하지 않는다(비고 보존).

    실측: `항암약물치료비`·`항암약물치료특약` → 약물 / `항암방사선치료비` → 방사선 /
          `항암방사선약물치료비`·`26종 항암방사선및약물치료비`·`계속받는 항암방사선약물치료비` → 결합.
    """
    # KB분류 열(`항암방사선약물치료비`·`고액항암치료비`)은 split_detail_parts의 분류 토큰(진단/수술/…)이 아니라
    # 담보명 뒤에 붙어 온다 — 판정은 **담보명 본체**로만(분류 꼬리 제거 · 꼬리만 남으면 원문 유지).
    core = _KB_CANCER_CLASS_TAIL_RE.sub("", compact_name) or compact_name
    has_drug = "약물" in core
    has_radiation = "방사선" in core
    if has_drug and not has_radiation:
        return ANTICANCER_DRUG_LABEL
    if has_radiation and not has_drug:
        return ANTICANCER_RADIATION_LABEL
    return ANTICANCER_COMBINED_LABEL


# ── BOHUMFIT-292(S4·Phase C): 다빈치 종별 식별 ────────────────────────────────────────
#: 종별 라벨 → 착지는 V2 별칭이 정한다(일반암·종별 미상 → 다빈치 로봇 수술 / 전립선·갑상선·특정암 → 다빈치 특정암).
DAVINCI_GENERAL_LABEL = "다빈치(일반암)"
DAVINCI_PROSTATE_LABEL = "다빈치(전립선)"
DAVINCI_THYROID_LABEL = "다빈치(갑상선)"
DAVINCI_SPECIFIC_LABEL = "다빈치(특정암)"
DAVINCI_UNKNOWN_LABEL = "다빈치(종별 미상)"
DAVINCI_LABELS: frozenset[str] = frozenset({
    DAVINCI_GENERAL_LABEL, DAVINCI_PROSTATE_LABEL, DAVINCI_THYROID_LABEL, DAVINCI_SPECIFIC_LABEL, DAVINCI_UNKNOWN_LABEL,
})


def davinci_label(compact_name: str) -> str:
    """담보명 문자열만으로 다빈치 종별을 판정한다 — ★추측 금지(276a).

    · `특정암제외`·`일반암` → 일반암        · `전립선` → 전립선        · `갑상선` → 갑상선
    · `특정암`(제외 없음) → 특정암(행은 다빈치 특정암 — 전립선/갑상선 중 어느 체인인지는 원문에 없다)
    · 그 밖(종별 미기재) → 종별 미상: 다빈치 로봇 수술 행에만 두고 `needs_review`(일반암으로 추측하지 않는다)
    실측 패턴(오현지 [전]): `다빈치로봇암수술비(연간1회한,특정암)` / `(연간1회한,특정암제외)`.
    """
    if "특정암제외" in compact_name or "일반암" in compact_name:
        return DAVINCI_GENERAL_LABEL
    if "전립선" in compact_name:
        return DAVINCI_PROSTATE_LABEL
    if "갑상선" in compact_name:
        return DAVINCI_THYROID_LABEL
    if "특정암" in compact_name:
        return DAVINCI_SPECIFIC_LABEL
    return DAVINCI_UNKNOWN_LABEL


# ═══════════════════════════════════════════════════════════════════════════
# BOHUMFIT-287 — 42행 스키마 V2 (S1: **정의만**. 구 40행과 병존하며 아무 데도 배선되지 않는다)
# ═══════════════════════════════════════════════════════════════════════════
#
#   ★근거: 수기표 정본 A/B 2건의
#     '기존'·'리모델링' 4개 시트 7~48행을 전수 대조한 결과 **41행이 완전 일치**하고
#     r24 표기만 흔들렸다(286 Phase A 실측). 고객별 가변 지점은 없다.
#
#   ★S1 원칙(287): 위쪽 `KB_COVERAGES`·`GROUP12`·`KB_NAME_ALIASES`는 **한 글자도 바꾸지 않는다.**
#     배선은 S2(집계)·S3(산출물)·S4(매칭)에서 했다. ★BOHUMFIT-293에서 배선이 끝난 지금도 이 원칙은
#     그대로 유효하다 — 세 상수는 이제 **파서 사전·구 페이로드 축**이라 바뀌면 파싱 결과가 달라진다.
#     아래 V2 52행이 **유일한 산출물 스키마**다(구 40행 양식 상수는 293에서 제거됨).
#
#   ★Human 확정(286-D Q1~Q9, 재검토 금지)
#     Q1 40행 → 42행 전면 교체        Q2 80% 행은 신설하되 **합계 제외 + 미포함 표기**(243 유지)
#     Q3 r24 = `중입자 / 정위 방사선`  Q4 자리 없는 4항목은 **비고행(부록)**
#     Q5 `yn_flags`는 내부 유지, 표시만 운전자/배상/실비 행으로 분산
#     Q7 종수술 2열은 엑셀 2열·PDF 한 칸(S3)  Q8 r16·r17 출처는 통합치료비류의 "수술" 항목(S4)
#     Q9 기본계약 상해사망은 [후]에 표시(제외 규칙을 만들지 않는다)

#: ★BOHUMFIT-293: 산출물(엑셀·PDF·API)의 **유일한 대분류 축**. 구 `GROUP12`는 파서 사전 필드로만 남았다.
#:   `_V2` 접미는 역사적 명칭으로 유지한다 — rename은 302개 참조를 건드려 검증을 흐리므로 별도 결정 사항.
GROUP12_V2: tuple[str, ...] = (
    "실 비", "수 술", "암", "뇌", "심 장", "입 원", "사 망", "후유장해", "골 절", "배상책임", "운전자",
)

#: Q2 — 합계에서 뺀 행 옆에 붙일 표기. ★문구를 여기 한 곳에서만 정의한다(S3가 그대로 쓴다).
SUM_EXCLUDED_NOTE_V2 = "합계 미포함"


class CoverageRowV2(NamedTuple):
    """42행 스키마의 한 행.

    ★`row_id`는 **표시명과 분리된 안정 키**다. 수기표 표기가 흔들려도(예: r24) 코드 전반은
      `row_id`만 참조하므로 파급되지 않는다 — 이게 V2를 새로 만드는 이유 중 하나다.
    """

    row_id: str
    group: str
    display: str
    #: 질병 | 상해 2열 병기(종수술 5행만) — Q7.
    dual_column: bool = False
    #: 합계에서 제외하고 `SUM_EXCLUDED_NOTE_V2`를 붙인다(80% 행만) — Q2 · 243.
    sum_excluded: bool = False
    #: `yn_flags` 판정의 원천 행 — Q5. ★행 자체는 금액행이고, Y/N은 파생일 뿐이다.
    yn_source: bool = False
    #: 구 40행 이름·수기표 표기 흔들림 등 이 행으로 모아야 할 후보(S4 입력물).
    aliases: tuple[str, ...] = ()


KB_COVERAGES_V2: tuple[CoverageRowV2, ...] = (
    # ── 실 비 (Q5: 실손 Y/N 판정 원천) ───────────────────────────────────────
    # BOHUMFIT-296: 비고 → 정규 행 이관(Human 확정) — 실손 대분류 상단(입원 위). 구 appendix(rep) 유지.
    CoverageRowV2("actual_3major_nonpay", "실 비", "3 대 비 급 여 실 손", aliases=("3대비급여실손",)),
    CoverageRowV2("actual_inpatient", "실 비", "상 해/질 병 입 원", yn_source=True,
                  aliases=("상해입원의료비", "질병입원의료비")),
    CoverageRowV2("actual_outpatient", "실 비", "상 해/질 병 통 원 약 제", yn_source=True,
                  aliases=("상해통원의료비", "질병통원의료비")),
    # ── 수 술 ───────────────────────────────────────────────────────────────
    CoverageRowV2("surgery_injury", "수 술", "상 해 수 술 비", aliases=("상해수술",)),
    CoverageRowV2("surgery_disease", "수 술", "질 병 수 술 비", aliases=("질병수술",)),
    CoverageRowV2("tier_surgery_1", "수 술", "1종 수술비 (질병 I 상해)", dual_column=True,
                  aliases=("N종수술비(질병 1종)", "N종수술비(상해 1종)", "일반종수술 1종(표준환산)")),
    CoverageRowV2("tier_surgery_2", "수 술", "2종 수술비 (질병 I 상해)", dual_column=True,
                  aliases=("N종수술비(질병 2종)", "N종수술비(상해 2종)", "일반종수술 2종(표준환산)")),
    CoverageRowV2("tier_surgery_3", "수 술", "3종 수술비 (질병 I 상해)", dual_column=True,
                  aliases=("N종수술비(질병 3종)", "N종수술비(상해 3종)", "일반종수술 3종(표준환산)")),
    CoverageRowV2("tier_surgery_4", "수 술", "4종 수술비 (질병 I 상해)", dual_column=True,
                  aliases=("N종수술비(질병 4종)", "N종수술비(상해 4종)", "일반종수술 4종(표준환산)")),
    CoverageRowV2("tier_surgery_5", "수 술", "5종 수술비 (질병 I 상해)", dual_column=True,
                  aliases=("N종수술비(질병 5종)", "N종수술비(상해 5종)", "일반종수술 5종(표준환산)")),
    # BOHUMFIT-296: 신규 행(Human 확정) — 종수술 5종 하단·뇌혈관 수술비 상단. N값(124·132대) 무관하게 **최대 보상금액**
    #   한 행으로 담는다(케스케이드 없음·독립·2열 아님). base 라벨 `N대수술비`로 라우팅(build_v2_rows) → 여러 건 max(REP).
    CoverageRowV2("major_n_surgery", "수 술", "N대수술비 최대 보상금액", aliases=("N대수술비",)),
    CoverageRowV2("surgery_cerebral", "수 술", "뇌혈관 수술비", aliases=("뇌혈관수술", "뇌혈관수술비")),   # 292(S4·E): 상세 분리 라벨
    CoverageRowV2("surgery_cardiac", "수 술", "심장질환 수술비", aliases=("심혈관수술", "심혈관수술비")),  # 292(S4·E)
    # ── 암 (BOHUMFIT-289: 7행 → **11행** 재설계. 제품 오너 확정) ────────────
    #   ★구 42행의 묶음 3개가 전부 풀렸다:
    #     `암 수 술 / 로 봇 암 수 술` → 암수술 + 다빈치 로봇 수술
    #     `항 암 방 사 선 약 물 치 료` + `고액항암치료(표적,면역)` → 약물 3행 + 방사선 1행
    #     `세기조절 / 양성자 방사선` + `중입자 / 정위 방사선` → 세기조절·양성자·중입자 3행
    #   ★Q3 폐기: 신판은 구형 표기 `중 입 자 치료`를 쓴다. 287이 채택했던
    #     `중입자 / 정위 방사선`은 이제 **별칭**으로 내려간다(표기 결정이 뒤집혔다).
    CoverageRowV2("cancer_general", "암", "암 진 단 비(일반암)", aliases=("암진단금",)),
    CoverageRowV2("cancer_minor", "암", "유 사 암 진 단 비", aliases=("유사암진단금",)),
    CoverageRowV2("cancer_surgery", "암", "암 수 술 (레보아이 포함)",
                  aliases=("암수술", "암 수 술 / 로 봇 암 수 술")),
    # BOHUMFIT-290(S2·Human 확정): 유사암 수술 — 다빈치(갑상선) 체인의 상위 행.
    CoverageRowV2("cancer_minor_surgery", "암", "유사암 수술", aliases=("유사암수술",)),  # 292(S4): 통합치료 내역 항목
    CoverageRowV2("cancer_surgery_davinci", "암", "다빈치 로봇 수술",
                  aliases=("다빈치(일반암)", "다빈치(종별 미상)")),  # 292(S4): 종별 미상은 확인 필요 표기
    # BOHUMFIT-290(S2·Human 확정): 다빈치 특정암 — 전립선·갑상선 다빈치의 착지 행.
    CoverageRowV2("cancer_surgery_davinci_specific", "암", "다빈치 특정암",
                  aliases=("다빈치(전립선)", "다빈치(갑상선)", "다빈치(특정암)")),  # 292(S4)
    CoverageRowV2("cancer_drug", "암", "항암 약물 치료", aliases=("항암약물치료비",)),  # 292(S4): 상세·내역 라벨
    CoverageRowV2("cancer_drug_targeted", "암", "표적 약물 치료", aliases=("표적항암치료",)),
    CoverageRowV2("cancer_drug_immune", "암", "면역 약물 치료", aliases=("면역항암치료",)),
    CoverageRowV2("cancer_radiation", "암", "방사선 치료", aliases=("항암방사선치료비",)),  # 292(S4): 상세·내역 라벨
    CoverageRowV2("radio_imrt", "암", "세기조절 방사선 치료",
                  aliases=("세기조절 / 양성자 방사선", "세기조절방사선")),  # 292(S4): 상세 라벨 별칭
    CoverageRowV2("radio_proton", "암", "양성자 방사선 치료", aliases=("양성자방사선",)),  # 292(S4)
    CoverageRowV2("radio_carbon", "암", "중 입 자 치료",
                  aliases=("중입자방사선", "중입자 / 정위 방사선")),
    # ── 뇌 ──────────────────────────────────────────────────────────────────
    CoverageRowV2("cerebral_disease", "뇌", "뇌 혈 관 질 환", aliases=("뇌혈관질환",)),
    CoverageRowV2("stroke", "뇌", "뇌 졸 중", aliases=("뇌졸중",)),
    CoverageRowV2("cerebral_hemorrhage", "뇌", "뇌 출 혈", aliases=("뇌출혈",)),
    # ── 심 장 ───────────────────────────────────────────────────────────────
    CoverageRowV2("cardiac_disease", "심 장", "심 장 질 환", aliases=("심혈관질환",)),
    CoverageRowV2("ischemic_heart", "심 장", "허혈성 심장질환", aliases=("허혈성심장질환",)),
    CoverageRowV2("acute_mi", "심 장", "급성심근경색", aliases=("급성심근경색",)),
    # BOHUMFIT-290(S2·Human 확정): 순환계 치료비 — Q8형 분배의 **본체** 착지 행.
    #   심장 대분류 말미 · ★케스케이드 밖 독립 행(체인 없음).
    CoverageRowV2("circulatory_treatment", "심 장", "순환계 치료비"),
    # ── 입 원 ───────────────────────────────────────────────────────────────
    CoverageRowV2("inpatient_injury", "입 원", "상 해 입 원", aliases=("상해입원",)),
    CoverageRowV2("inpatient_disease", "입 원", "질 병 입 원", aliases=("질병입원",)),
    CoverageRowV2("inpatient_private_room", "입 원", "1 인 실 입 원"),
    # ★병합: 구 기타의 간병 2행 → 1행.
    # BOHUMFIT-290(S2·Human)·296: 간병인은 **질병|상해 2열 병기**(종수술과 같은 방식).
    #   상해일당·질병일당 두 원천을 한 행에 합치지 않고 열로 나눈다.
    CoverageRowV2("caregiver", "입 원", "간 병 인", dual_column=True,
                  aliases=("간병인/간호간병상해일당", "간병인/간호간병질병일당")),
    # ── 사 망 ───────────────────────────────────────────────────────────────
    # BOHUMFIT-290: 별칭 = 246 사망 승격 extras 라벨(`일반사망`).
    CoverageRowV2("death_general", "사 망", "일 반 사 망", aliases=("일반사망",)),
    # ★Q9: 기본계약 상해사망도 [후]에 표시한다 — 제외 규칙을 만들지 않는다.
    # ★Human Q6 ③: `재해사망`은 별칭이 아니라 독립 합산 원천 — v2_mapping의 명시 규칙으로 더한다.
    CoverageRowV2("death_injury", "사 망", "상 해 사 망", aliases=("상해사망",)),
    CoverageRowV2("death_disease", "사 망", "질 병 사 망", aliases=("질병사망",)),
    # ── 후유장해 ────────────────────────────────────────────────────────────
    # ★Q2 + 243: 행은 신설하되 **합계에서 뺀다**. 243의 "집계 제외"와 수기표의 "행 존재"를
    #   동시에 지키는 유일한 형태다 — 보이되 더해지지 않는다.
    # BOHUMFIT-290: 별칭 = 파서 extras 라벨(288 실측 — 정본 2건에 실재: 이인숙 2,000만·라금실 200만).
    CoverageRowV2("disability_80", "후유장해", "상해 질병 후 유 장 해 80%", sum_excluded=True,
                  aliases=("80%이상 후유장해",)),
    CoverageRowV2("disability_injury_3", "후유장해", "상 해 후 유 장 해 3%",
                  aliases=("상해후유장해",)),
    CoverageRowV2("disability_disease_3", "후유장해", "질 병 후 유 장 해 3%",
                  aliases=("질병후유장해",)),
    # ── 골 절 ───────────────────────────────────────────────────────────────
    CoverageRowV2("fracture_diagnosis", "골 절", "골 절 진 단 비", aliases=("골절진단비",)),
    # BOHUMFIT-290: 별칭 = 파서 extras 라벨(EXTRA_PATTERNS `골절수술` → "골절수술비").
    CoverageRowV2("fracture_surgery", "골 절", "골 절 수 술 비", aliases=("골절수술비",)),
    CoverageRowV2("cast_treatment", "골 절", "깁스치료비"),
    # ── 배상책임 (Q5 판정 원천) ─────────────────────────────────────────────
    CoverageRowV2("liability_daily", "배상책임", "일 상 생 활 배 상 책 임", yn_source=True,
                  aliases=("가족/일상/자녀배상",)),
    # ── 운전자 (Q5 판정 원천) ───────────────────────────────────────────────
    CoverageRowV2("driver_settlement", "운전자", "형 사 합 의 금", yn_source=True,
                  aliases=("교통사고처리지원금",)),
    # BOHUMFIT-296: 비고 → 정규 행 이관(Human 확정) — 형사합의금 하단. 구 EXTRA(sum) 유지. yn_source 아님(별도 담보).
    CoverageRowV2("driver_settlement_6w", "운전자", "형사합의금(6주미만)", aliases=("교통사고처리지원금(6주미만)",)),
    CoverageRowV2("driver_lawyer", "운전자", "변 호 사 선 임", yn_source=True,
                  aliases=("변호사선임비용",)),
    CoverageRowV2("driver_fine", "운전자", "벌 금", yn_source=True,
                  aliases=("벌금(대인/스쿨존/대물)",)),
    CoverageRowV2("driver_injury_grade", "운전자", "자 부 상", yn_source=True,
                  aliases=("자동차사고부상",)),
)

STANDARD_COUNT_V2 = len(KB_COVERAGES_V2)

#: Q4 + BOHUMFIT-289 — 46행에 자리가 없는 항목은 **비고행(부록)** 으로 내린다. 삭제는 정보 손실이다.
#:   ★289에서 `장기요양간병비`·`경증치매진단` 2건이 보류에서 **부록으로 확정**됐다(Human).
#: ★BOHUMFIT-296(Human 확정): `3대비급여실손`은 정규 행(actual_3major_nonpay)으로 이관돼 비고에서 빠졌다.
#:   `고액암`·`경증치매진단`은 **비고 유지**(Human 스펙 확정 · 289 암 재설계로 고액항암치료 행 소멸·287 PENDING→Q4 확장).
#:   남는 비고 7항목 = 아래 4 + 동적(양성종양·폴립·응급실) — 문서는 §대조표 참조.
APPENDIX_ITEMS_V2: tuple[str, ...] = (
    "고액암", "보철치료비", "화재벌금",
    "장기요양간병비", "경증치매진단",
)

#: ★BOHUMFIT-289: `암 주요치료비`는 부록이 아니라 **분배 규칙으로 해소**된다(Human 확정).
#:   담보 하나가 여러 행으로 갈라지므로 1:1 대응표에 넣을 수 없어 별도 구분을 둔다.
DISTRIBUTED_ITEMS_V2: tuple[str, ...] = ("암 주요치료비",)

#: 287의 보류 목록 — ★289에서 **전부 해소**됐다(부록 2 + 분배 1). 빈 튜플을 유지해
#:   "보류가 없다"는 상태를 코드로 남긴다(다음에 생기면 여기 다시 쌓인다).
PENDING_DISPOSITION_V2: tuple[str, ...] = ()

LEGACY_APPENDIX_V2 = "APPENDIX"
LEGACY_PENDING_V2 = "PENDING"
LEGACY_DISTRIBUTED_V2 = "DISTRIBUTED"

#: 구 40행 → V2 대응. 값은 `row_id` 또는 처리 구분(`APPENDIX`/`PENDING`/`DISTRIBUTED`).
#:   ★40행 **전 항목**이 여기에 있어야 한다(테스트로 고정) — 조용히 사라지는 담보가 없게.
LEGACY_TO_V2: dict[str, str] = {
    **{alias: row.row_id for row in KB_COVERAGES_V2 for alias in row.aliases},
    **{name: LEGACY_APPENDIX_V2 for name in APPENDIX_ITEMS_V2},
    **{name: LEGACY_PENDING_V2 for name in PENDING_DISPOSITION_V2},
    **{name: LEGACY_DISTRIBUTED_V2 for name in DISTRIBUTED_ITEMS_V2},
}

_LEGACY_NAMES_V2 = frozenset(name for name, _group, _group12, _agg in KB_COVERAGES)

#: BOHUMFIT-290(Q5): Y/N 파생 항목 — **항목 5종·원천 담보명은 구 `YN_ITEMS`와 동일**하다.
#:   내부 플래그는 유지하고 원천의 착지만 V2 행(`LEGACY_TO_V2`)으로 바뀐다. 상해실손·질병실손은
#:   같은 V2 행(실비 2행)에 합쳐지지만 원천 상세(`sources`)로 계속 구분한다.
#: ★BOHUMFIT-293: 종전에는 구 `YN_ITEMS`를 그대로 복사(`tuple(YN_ITEMS)`)했으나, 구 상수를 제거하며
#:   **같은 값을 리터럴로 정착**시켰다(양식 원본 수식 `=IF(COUNTA(범위)=0,"N","Y")`와 등가 · 246 이식분).
#:   값은 한 글자도 바뀌지 않았고, 293 테스트가 항목 5종·원천 담보명을 문자열로 고정한다.
YN_ITEMS_V2: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("운전자특약", ("벌금(대인/스쿨존/대물)", "교통사고처리지원금", "변호사선임비용")),
    ("자동차부상치료비", ("자동차사고부상",)),
    ("가족일상배상책임", ("가족/일상/자녀배상",)),
    ("상해실손의료비", ("상해입원의료비", "상해통원의료비")),
    ("질병실손의료비", ("질병입원의료비", "질병통원의료비")),
)

#: V2에서 새로 생긴 행 = **구 40행에 원천이 없는** 행 — S4가 매칭 규칙을 만들어야 할 대상.
#:   ★`aliases`가 비었는지로 판정하면 안 된다. 종수술 5행의 별칭(`N종수술비(질병 1종)` 등)은
#:     파서·238 환산 라벨이지 구 40행 이름이 아니라서, 그렇게 세면 신설 행을 놓친다.
NEW_ROWS_V2: tuple[str, ...] = tuple(
    row.row_id
    for row in KB_COVERAGES_V2
    if not any(alias in _LEGACY_NAMES_V2 for alias in row.aliases)
)


# ── BOHUMFIT-289: 시트명·표시 관례 (S3 반영 예고 — 여기서는 기록만) ─────────
#   신판은 시트명을 `기존`/`리모델링` → **`컨설팅 전`/`컨설팅 후`** 로 바꿨다.
SHEET_NAME_BEFORE_V2 = "컨설팅 전"
SHEET_NAME_AFTER_V2 = "컨설팅 후"
SHEET_NAME_FINAL_V2 = "최종"

#: ★케스케이드 **하위 행** 앞에 붙는 접두. 신판 `최종` 시트 실측에서 확인했다 —
#:   `L 뇌 졸 중`·`L 뇌 출 혈`·`L 급 성 심 근 경 색`. 체인의 **루트**(뇌혈관질환·허혈성
#:   심장질환)와 **독립 행**(심장질환)에는 붙지 않는다 — 아래 `PAYOUT_CASCADE_V2`와 정확히 맞물린다.
CASCADE_CHILD_PREFIX_V2 = "L "


# ── BOHUMFIT-289: 지급 케스케이드 (Human 확정 · ★정의만, 어디에도 배선하지 않는다) ──
#
#   ★읽는 법: `PAYOUT_CASCADE_V2[진단명] = (그 진단이 발생했을 때 **함께 지급되는 행들**)`
#     체인은 **자기 자신을 마지막에 포함**하고, 상위(넓은) 행부터 나열한다.
#     예) 뇌출혈이 나면 뇌혈관질환·뇌졸중·뇌출혈 담보가 **모두** 지급된다.
#
#   ★형제는 누적되지 않는다: 세기조절·양성자·중입자는 각자 `방사선 치료`만 물고 올라가고
#     서로를 포함하지 않는다. 약물(표적·면역)은 계층이라 누적된다.
#
#   ★체인이 **없는** 행: `심 장 질 환`(Human 확정 — 케스케이드 밖 독립 행) ·
#     `암 진 단 비(일반암)` · `유 사 암 진 단 비`. 여기에 체인을 만들면 안 된다.
PAYOUT_CASCADE_V2: dict[str, tuple[str, ...]] = {
    # 뇌 — 3단
    "cerebral_disease": ("cerebral_disease",),
    "stroke": ("cerebral_disease", "stroke"),
    "cerebral_hemorrhage": ("cerebral_disease", "stroke", "cerebral_hemorrhage"),
    # 심장 — 2단(★`cardiac_disease`는 참여하지 않는다)
    "ischemic_heart": ("ischemic_heart",),
    "acute_mi": ("ischemic_heart", "acute_mi"),
    # 암수술 — 2단 · ★BOHUMFIT-290: 다빈치를 **종별 3분류**로 개정(Human 확정)
    #   289의 단일 체인 `다빈치→[암수술,다빈치]`는 **일반암 케이스**로 흡수됐다.
    #   ★키가 row_id가 아닌 **케이스 id**인 항목은 `CASCADE_CASE_ROW_V2`가 착지 행을 준다.
    "cancer_surgery": ("cancer_surgery",),
    "cancer_minor_surgery": ("cancer_minor_surgery",),
    "davinci_general": ("cancer_surgery", "cancer_surgery_davinci"),
    "davinci_prostate": ("cancer_surgery", "cancer_surgery_davinci_specific"),
    "davinci_thyroid": ("cancer_minor_surgery", "cancer_surgery_davinci_specific"),
    # 항암 약물 — 3단
    "cancer_drug": ("cancer_drug",),
    "cancer_drug_targeted": ("cancer_drug", "cancer_drug_targeted"),
    "cancer_drug_immune": ("cancer_drug", "cancer_drug_targeted", "cancer_drug_immune"),
    # 방사선 — 2단 · ★형제 비누적
    "cancer_radiation": ("cancer_radiation",),
    "radio_imrt": ("cancer_radiation", "radio_imrt"),
    "radio_proton": ("cancer_radiation", "radio_proton"),
    "radio_carbon": ("cancer_radiation", "radio_carbon"),
}

#: 케스케이드에 참여하지 않는 것이 **의도**인 행(테스트가 이 목록을 지킨다).
CASCADE_INDEPENDENT_V2: tuple[str, ...] = (
    "cardiac_disease", "cancer_general", "cancer_minor",
    "circulatory_treatment",  # BOHUMFIT-290: 순환계 치료비 — 독립(Human 확정)
)

#: BOHUMFIT-290: 케스케이드 키 중 **row_id가 아닌 케이스 id** → 착지(마지막) 행.
#:   다빈치는 진단 종별(일반암·전립선·갑상선)에 따라 체인이 갈리므로 행 하나로 키를 삼을 수 없다.
CASCADE_CASE_ROW_V2: dict[str, str] = {
    "davinci_general": "cancer_surgery_davinci",
    "davinci_prostate": "cancer_surgery_davinci_specific",
    "davinci_thyroid": "cancer_surgery_davinci_specific",
}
#: 케이스 표시명(종합 판정 블록·S3 표시용).
CASCADE_CASE_LABEL_V2: dict[str, str] = {
    "davinci_general": "다빈치(일반암)",
    "davinci_prostate": "다빈치(전립선)",
    "davinci_thyroid": "다빈치(갑상선)",
}


# ── BOHUMFIT-289: 분배 규칙 (★S4가 배선할 데이터. 여기서는 정의만) ──────────
#
#   ★배경: 담보 하나가 여러 행으로 갈라지는 형태가 실제로 있다. 1:1 대응표로는 못 담는다.
#     ①주요치료비형 — `암 주요치료비` 한 담보가 암수술·항암약물·방사선 3행을 **동액**으로 채운다.
#     ②Q8형(통합치료비) — 통합치료비 담보의 **약관 내역 중 "수술" 항목**이 뇌혈관·심장 수술비로 간다.
#
#   ★★분배분과 개별 특약이 **같은 행에 함께 올 때의 합산 규칙은 여기서 정하지 않는다.**
#     기존 sum/rep 의미론(`AGG_SUM`/`AGG_REP`)과 함께 S4에서 결정한다 — 패킷이 명시적으로 금지했다.
DISTRIBUTION_EQUAL_V2 = "EQUAL"


class DistributionRuleV2(NamedTuple):
    rule_id: str
    #: 분배 원천을 가리키는 라벨(구 담보명 또는 원문 담보 계열).
    source: str
    #: 채워질 `row_id`들.
    targets: tuple[str, ...]
    mode: str = DISTRIBUTION_EQUAL_V2


DISTRIBUTION_RULES_V2: tuple[DistributionRuleV2, ...] = (
    DistributionRuleV2(
        "major_treatment",
        source="암 주요치료비",
        targets=("cancer_surgery", "cancer_drug", "cancer_radiation"),
    ),
    DistributionRuleV2(
        "integrated_treatment_surgery",
        source="통합치료비 약관 내역 — 수술 항목",
        targets=("surgery_cerebral", "surgery_cardiac"),
    ),
    # BOHUMFIT-290: 289 미해결분 해소 — Q8형 **본체**는 `순환계 치료비` 신규 행으로(Human 확정).
    #   288 실증: 알파Plus #169 본체 5,000만 → 이 행 / 내역 "수술 1,000만" → 위 규칙.
    DistributionRuleV2(
        "integrated_treatment_body",
        source="특정순환계질환 통합치료비 — 본체(연간 총 지급 한도)",
        targets=("circulatory_treatment",),
    ),
)

#: BOHUMFIT-290: 암 통합치료비 **패턴 자동 판정 규칙**(Human 확정 · ★배선은 S4).
#:   내역 치료별 금액이 **상이**하면 Q8형(내역 분해) / **동액이거나 미기재**면 주요치료비형(3행 동액).
#:   288 실측: 알파Plus #117·#119는 본문에 내역 금액이 **없다** → 이 규칙으로는 주요치료비형.
DISTRIBUTION_PATTERN_RULE_V2 = (
    "내역 치료별 금액 상이 → Q8형(내역 분해) / 동액 또는 미기재 → 주요치료비형(3행 동액)"
)

#: 289가 주차했던 미해결분 — ★BOHUMFIT-290에서 **해소**(본체 착지 = `circulatory_treatment`).
#:   빈 튜플을 유지해 "미해결이 없다"를 코드로 남긴다.
DISTRIBUTION_UNRESOLVED_V2: tuple[str, ...] = ()
