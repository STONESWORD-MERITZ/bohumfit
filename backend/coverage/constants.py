"""KB guaranteed-issue coverage proposal constants for BOHUMFIT-179/179b."""
from __future__ import annotations

import re

AGG_SUM = "sum"
AGG_REP = "rep"

# BOHUMFIT-246: 대분류를 비분양식(244 S3 실측) 섹션으로 전면 교체(정본화).
#   변수명 GROUP12/GROUP13은 역사적 명칭으로 유지(소비처 import 안정) — 항목 수와 무관.
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

STANDARD_COUNT = len(KB_COVERAGES)


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


# BOHUMFIT-246: 표시 순서 = 비분양식 시트2 10~49행 원문 순서(양식이 곧 스키마 — 244 S3 실측).
#   build_before가 (그룹 순서, 항목 순서)로 정렬한다. 목록 밖 라벨(기타 등)은 그룹 내 뒤에 붙는다.
NEW_ITEM_ORDER: tuple[str, ...] = (
    "일반사망", "재해사망", "질병사망", "상해사망",
    "상해후유장해", "질병후유장해",
    "암진단금", "유사암진단금", "암수술", "항암약물방사선", "표적항암치료",
    "면역항암치료", "중입자방사선", "암 주요치료비",
    "뇌혈관질환", "뇌졸중", "뇌출혈", "뇌혈관수술",
    "심혈관질환", "허혈성심장질환", "급성심근경색", "심혈관수술", "순환계 치료비",
    "일반종수술 1종(표준환산)", "일반종수술 2종(표준환산)", "일반종수술 3종(표준환산)",
    "일반종수술 4종(표준환산)", "일반종수술 5종(표준환산)", "종수술비", "종수술비(표 외)",
    "상해수술", "질병수술",
    "응급실", "질병입원", "상해입원",
    "골절진단비", "깁스치료비",
    "벌금(대인/스쿨존/대물)", "교통사고처리지원금", "변호사선임비용", "자동차사고부상",
    "가족/일상/자녀배상", "상해입원의료비", "상해통원의료비", "질병입원의료비", "질병통원의료비",
)

# BOHUMFIT-246: 양식 45~49행 Y/N 판정 — (항목명, 판정 원천 담보들). 원천 중 1건 이상
#   enrolled면 Y(양식 원본 수식 `=IF(COUNTA(범위)=0,"N", IF(COUNTA(범위),"Y"))`와 동일 의미).
YN_ITEMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("운전자특약", ("벌금(대인/스쿨존/대물)", "교통사고처리지원금", "변호사선임비용")),
    ("자동차부상치료비", ("자동차사고부상",)),
    ("가족일상배상책임", ("가족/일상/자녀배상",)),
    ("상해실손의료비", ("상해입원의료비", "상해통원의료비")),
    ("질병실손의료비", ("질병입원의료비", "질병통원의료비")),
)

# BOHUMFIT-246: 종합비교 단계 파생 — 비분양식 시트3 수식 이식(244 S3 실측이 정본).
#   공통 가산 = 일반종수술 5종(B32) + 질병수술(B34). H10 문구는 "심장초기" 중복이나 수식
#   대역(B24:B25)이 중기임을 실측으로 확정 → "심장중기"로 정정(Human 확정·244).
#   [후]도 동일 수식(I열 규칙)을 쓴다 — 원본 K7의 F22 이중합산은 오류로 판정, 미이식.
#   ★원본 수식 원문:
#     암       I5  = SUM($B$11:$B$17,$B$32,$B$34)  ※B18(암 주요치료비) 미포함 — 원본 그대로
#     뇌초기    I6  = SUM(B19:$B$21,$B$22,$B$32,$B$34)
#     뇌중기    I7  = SUM(B20:$B$21,$B$22,$B$32,$B$34)
#     뇌말기    I8  = SUM(B21:$B$21,$B$22,$B$32,$B$34)
#     심장초기  I9  = SUM(B$23:$B25,$B$26,$B$32,$B$34)
#     심장중기  I10 = SUM(B$24:$B25,$B$26,$B$32,$B$34)  (H10 원문 오타 "심장초기" → 중기)
#     심장말기  I11 = SUM(B$25:$B25,$B$26,$B$32,$B$34)
STAGE_COMMON_ADD: tuple[str, ...] = ("일반종수술 5종(표준환산)", "질병수술")
STAGE_COMPONENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("암", ("암진단금", "유사암진단금", "암수술", "항암약물방사선", "표적항암치료",
            "면역항암치료", "중입자방사선")),
    ("뇌초기", ("뇌혈관질환", "뇌졸중", "뇌출혈", "뇌혈관수술")),
    ("뇌중기", ("뇌졸중", "뇌출혈", "뇌혈관수술")),
    ("뇌말기", ("뇌출혈", "뇌혈관수술")),
    ("심장초기", ("심혈관질환", "허혈성심장질환", "급성심근경색", "심혈관수술")),
    ("심장중기", ("허혈성심장질환", "급성심근경색", "심혈관수술")),
    ("심장말기", ("급성심근경색", "심혈관수술")),
)

# BOHUMFIT-246: 사망 상호배타 — 일반/재해사망 상세 라인의 지급사유(KB분류) 행 금액을
#   해당 표준 매트릭스 행에서 차감한다(동일 담보 이중 계상 0). 차감 실적은 death_dedup으로
#   반환해 총액 대사(구총합 = 신총합 + 차감액)에 쓴다. A 실측: 일반사망 6,000만이
#   상해사망·질병사망 매트릭스 셀에 각 6,000만으로 반영돼 있었다.
DEATH_EXCLUSION_LABELS: tuple[str, ...] = ("일반사망", "재해사망")


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
