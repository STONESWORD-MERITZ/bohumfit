"""BOHUMFIT-248 P2: 비분양식 3시트 엑셀 생성 — 244 S3 실측 양식의 재현.

181 다운로드 동선(엔드포인트·build_workbook_bytes 시그니처)은 무파손 유지하고,
산출 구조를 비분양식(표지(세로)·비교분석표·최종비교분석표)으로 전면 교체한다.

확정 결정(246~248):
- 계약 열 ★전부 전개 — 양식은 [전] 3열·[후] 4열이나 실계약 수만큼 열을 확장한다
  (누락 0 > 레이아웃 보존). 병합·인쇄영역은 열 수에 맞춰 동적 조정.
- 값 기입 방식(수식 아님) — 패킷 허용 조항 채택. 근거: ①제1원칙(3계층 교차 대조 차이 0)의
  기계 검증은 openpyxl이 수식을 평가하지 못해 값 기입이어야 성립 ②[후]는 이월 결과값이
  정본(246)이라 재계산 수식이 오히려 비정합 위험. Y/N도 동일 근거로 값("Y"/"N") 기입
  (양식 COUNTA 수식 의미는 246 yn_flags 파생이 등가 구현 — 시트 수식 유지는 미채택·기록).
- 단위: 보장금액 **만원**(시트3 "만원" 서식 접미 근거 추정 — 244 결정 11 계류), 보험료 **원**.
- 차액 = 후−전(개선 +). H10 = "심장중기"(원본 오타 정정). K7 이중합산 미이식(값 기입이라 비해당).
- 종수술 estimated 행: 표시명 "(표준환산)" 유지 + 시트2 하단 "표준 환산 기준" 문구(238).
- overview(합계형) 문서: 계약 열 없이 합계 열만 + 특이사항에 246 경고 기재.
- 양식 밖 담보(기타 그룹·종수술비 버킷·(계약 미확인) 등)는 시트2 하단 "부록: 기타(정보 보존)"
  블록에 전량 수록 — 누락 0(양식 35행에 자리가 없어도 산출물에서 유실하지 않는다).

※ PII: 생성물은 응답 스트림 전용, 서버 미저장.
"""
from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .aggregator import compute_stage_totals, compute_yn_flags
from .compare import ensure_comparison
from .constants import GROUP13, GROUP_ETC
from .excel_style import (
    AMBER_TX,
    BORDER_BOX,
    BORDER_GRID,
    EMERALD,
    EMERALD_SOFT,
    GRAY_SOFT,
    GREENTEA,
    HIGHLIGHT_ITEMS,
    INK,
    LIME,
    PANEL_LABELS,
    SPECIAL_ITEMS,
    WHITE,
)

MAN = 10_000

# 비분양식 시트2 10~44행(35행) — 244 S3 실측 순서 그대로(양식이 곧 스키마).
FORM_ITEMS: tuple[str, ...] = (
    "일반사망", "재해사망", "질병사망", "상해사망",
    "상해후유장해", "질병후유장해",
    "암진단금", "유사암진단금", "암수술", "항암약물방사선", "표적항암치료",
    "면역항암치료", "중입자방사선", "암 주요치료비",
    "뇌혈관질환", "뇌졸중", "뇌출혈", "뇌혈관수술",
    "심혈관질환", "허혈성심장질환", "급성심근경색", "심혈관수술", "순환계 치료비",
    "일반종수술 1종(표준환산)", "일반종수술 2종(표준환산)", "일반종수술 3종(표준환산)",
    "일반종수술 4종(표준환산)", "일반종수술 5종(표준환산)",
    "상해수술", "질병수술",
    "응급실", "질병입원", "상해입원",
    "골절진단비", "깁스치료비",
)
YN_ROWS: tuple[str, ...] = ("운전자특약", "자동차부상치료비", "가족일상배상책임", "상해실손의료비", "질병실손의료비")
# ★H10 원본 오타("심장초기" 중복) 정정 — 수식 대역 실측 확정(244 S3).
STAGE_ROWS: tuple[str, ...] = ("암", "뇌초기", "뇌중기", "뇌말기", "심장초기", "심장중기", "심장말기")

# BOHUMFIT-250: 양식 원색 → FIT 브랜드 치환(비분양식 강조 "위치"는 원본 실측 그대로).
#   헤더(원본 연노랑) = 에메랄드 면 + 흰 글자 / 강조 행 = 그린 티 면 / 특수 = 라임 면 /
#   시트3 라벨 기본 = 에메랄드 소프트 / [후]·차액 빨강 → 에메랄드(개선)·앰버(악화) 텍스트.
FORM_YELLOW = EMERALD          # 헤더 면(라벨 셀) — 흰 글자와 짝
FORM_BLUE = EMERALD_SOFT       # 시트3 라벨 기본 면
FORM_GRAY = GRAY_SOFT
RED_TX = EMERALD               # 개선 강조 텍스트(FIT 팔레트에 빨강 부재 — 250 S0 근거)
_BORDER = BORDER_GRID


def _grp_key(g: str) -> int:
    return GROUP13.index(g) if g in GROUP13 else len(GROUP13)


def _company_label(co: dict, companies: list) -> str:
    """BOHUMFIT-240 P1: 계약 라벨 = 회사명, 동일 회사 복수 계약은 '회사명 (n)'."""
    insurer = co.get("insurer")
    if not insurer:
        return f"계약 {co.get('idx')}"
    same = [c for c in companies if c.get("insurer") == insurer]
    if len(same) <= 1:
        return insurer
    ordinal = [str(c.get("idx")) for c in same].index(str(co.get("idx"))) + 1
    return f"{insurer} ({ordinal})"


def _man(value):
    """원 → 만원(정수 반올림). None은 None 유지(미가입 공란)."""
    if value is None:
        return None
    return round(value / MAN)


def _cell(ws, row, col, value=None, *, bold=False, fill=None, fmt=None, align="center",
          color=None, size=10, border=True, wrap=False, name="돋움"):
    c = ws.cell(row=row, column=col)
    if value is not None:
        c.value = value
    # BOHUMFIT-250: 에메랄드 면 위 텍스트는 흰색(대비 10.7:1 — 브랜드 규칙).
    auto_color = WHITE if fill == EMERALD else (color or INK)
    c.font = Font(name=name, bold=bold, size=size, color=auto_color)
    if fill:
        c.fill = PatternFill("solid", fgColor=fill)
    if fmt:
        c.number_format = fmt
    c.alignment = Alignment(horizontal=align, vertical="center", wrap_text=wrap)
    if border:
        c.border = _BORDER
    return c


def _coverage_maps(before_like: dict) -> dict:
    return {row.get("kb_name"): row for row in (before_like or {}).get("coverages", [])}


def _yn_map(before_like: dict) -> dict:
    flags = (before_like or {}).get("yn_flags")
    if not flags:
        coverages = (before_like or {}).get("coverages", [])
        flags = compute_yn_flags(coverages) if coverages else []
    return {f["item"]: f["value"] for f in flags}


def _stage_map(before_like: dict) -> dict:
    stages = (before_like or {}).get("stage_totals")
    if stages:
        return stages
    coverages = (before_like or {}).get("coverages", [])
    return compute_stage_totals(coverages) if coverages else {}


def _is_overview(before_like: dict) -> bool:
    return any(row.get("overview") for row in (before_like or {}).get("coverages", []))


# BOHUMFIT-252(재개): '?'(계약 미상 — 246/253 데이터 모델) 버킷 렌더 정책.
#   253 귀속 복원 후 실 5케이스 '?' 잔존 0(Codex 권위 실측) — 평시에는 열 미출력.
#   단, 동일 보험료 계약 등 모호 문서에서 '?'가 남으면(253은 오귀속 대신 '?' 유지가 설계)
#   회사 열 합 ≠ 합계로 다시 오독되므로, ★잔존 시에만 "계약 미확인" 열을 명시 출력한다.
def _unknown_bucket_present(before_like: dict, companies: list) -> bool:
    ids = {str(c.get("idx")) for c in companies}
    form_names = set(FORM_ITEMS)
    for row in (before_like or {}).get("coverages", []):
        if row.get("overview") or not row.get("enrolled") or row.get("kb_name") not in form_names:
            continue
        if any(k not in ids and v is not None for k, v in (row.get("by_company") or {}).items()):
            return True
    return False


def _unknown_sum(row: dict, ids: set):
    """실계약 키가 아닌 by_company 값 합(만원 변환 전 원 단위) — 없으면 None(공란)."""
    vals = [v for k, v in (row.get("by_company") or {}).items()
            if k not in ids and isinstance(v, (int, float))]
    return sum(vals) if vals else None


def _special_notes(analysis: dict) -> list[str]:
    notes: list[str] = list(analysis.get("warnings") or [])
    comparison = analysis.get("comparison") or {}
    for caution in comparison.get("cautions") or []:
        message = caution.get("message")
        if message:
            notes.append(message)
    seen: set[str] = set()
    unique: list[str] = []
    for note in notes:
        if note not in seen:
            seen.add(note)
            unique.append(note)
    return unique


# ── 시트1: 표지(세로) — S3 실측(병합 9·문구 원문) ────────────────────────────────
def _sheet_cover(ws, analysis: dict) -> None:
    ws.title = "표지(세로)"
    cover = analysis.get("report_cover") or {}
    customer = ((analysis.get("before") or {}).get("customer") or {}).get("name")
    display_name = cover.get("customer_name") or customer or "OOO"
    for merge in ("A1:A22", "B1:P1", "B2:P2", "B4:P4", "B5:P5", "B6:P6", "B7:P7", "B8:P9", "B10:P22"):
        ws.merge_cells(merge)
    ws.column_dimensions["A"].width = 1.5
    ws.column_dimensions["B"].width = 10.8
    ws.column_dimensions["C"].width = 9.0
    ws.row_dimensions[1].height = 75
    ws.row_dimensions[2].height = 42
    for row in (4, 5, 6, 7):
        ws.row_dimensions[row].height = 28.9
    _cell(ws, 1, 2, f"{display_name}님을 위한", size=28, align="left", border=False, name="바탕")
    _cell(ws, 2, 2, "보험 보장 분석 리포트", size=28, align="left", border=False, bold=True,
          name="바탕", color=EMERALD)  # 250: 브랜드 타이포 강조
    # 설계사 4항목 — 제공 데이터 채움·미제공은 양식 placeholder 유지(244 S3 문구).
    planner_rows = [
        (f"● {cover['planner_name']}" if cover.get("planner_name") else "● 본인이름", "나눔고딕"),
        (f"● 직급: {cover['ga_name']}" if cover.get("ga_name") else "● 직급:", "Cambria"),
        ("● E-MAIL : ", "Cambria"),
        ("● TEL : ", "Cambria"),
    ]
    for offset, (text, font_name) in enumerate(planner_rows):
        _cell(ws, 4 + offset, 2, text, size=20, align="left", border=False, bold=True, name=font_name)


# ── 시트2: 비교분석표 — 계약 열 전부 전개(동적) ─────────────────────────────────
def _sheet_compare_form(ws, analysis: dict, before: dict, after_before: dict | None) -> None:
    ws.title = "비교분석표"
    customer = (before.get("customer") or {}).get("name") or ""
    overview = _is_overview(before)

    b_companies = [] if overview else (before.get("contract_list") or before.get("companies") or [])
    a_companies = [] if (after_before is None or overview) else (
        after_before.get("contract_list") or after_before.get("companies") or []
    )
    n, m = len(b_companies), len(a_companies)
    # BOHUMFIT-252 B: [후] 신규 계약 열 골격 — 가입제안서 트랙 미착수 상태에서는 헤더 자리만
    #   두고 값은 공란("신규 설계 반영 대상"). 제안 계약(신규제안)이 페이로드에 있으면 일반
    #   회사 열로 이미 전개되므로 골격 열은 만들지 않는다. overview는 회사 열 자체가 없음(246).
    has_proposal = any(
        (co.get("consulting_status") == "신규제안") or (co.get("remark") == "신규제안")
        for co in a_companies
    )
    new_slot = 1 if (after_before is not None and not overview and not has_proposal) else 0
    # BOHUMFIT-252(재개): '?' 버킷 잔존 시에만 "계약 미확인" 열 — 회사합=합계 대사가 눈에
    #   보이도록(모호 문서 오독 방지). 실 5케이스는 253 복원으로 잔존 0 → 열 미출력(현행 동일).
    b_ids = {str(c.get("idx")) for c in b_companies}
    a_ids = {str(c.get("idx")) for c in a_companies}
    b_unk = 1 if (not overview and _unknown_bucket_present(before, b_companies)) else 0
    a_unk = 1 if (after_before is not None and not overview
                  and _unknown_bucket_present(after_before, a_companies)) else 0

    # 열 배치(1-base): A 여백 | [전] n열(+미확인) | [전]합계 | 담보명 3열 | [후]합계 | [후] m열(+미확인+신규 골격) | 여백
    col_b0 = 2
    col_bsum = col_b0 + n + b_unk
    col_name0 = col_bsum + 1
    col_asum = col_name0 + 3
    col_a0 = col_asum + 1
    col_end = col_a0 + m + a_unk + new_slot
    ws.column_dimensions["A"].width = 1.6
    for col in range(col_b0, col_bsum):
        ws.column_dimensions[get_column_letter(col)].width = 14.4
    ws.column_dimensions[get_column_letter(col_bsum)].width = 14.0
    ws.column_dimensions[get_column_letter(col_name0)].width = 5.5
    ws.column_dimensions[get_column_letter(col_name0 + 1)].width = 12.0  # 250: 긴 라벨 겹침 해소
    ws.column_dimensions[get_column_letter(col_name0 + 2)].width = 5.5
    ws.column_dimensions[get_column_letter(col_asum)].width = 14.0
    for col in range(col_a0, col_end):
        ws.column_dimensions[get_column_letter(col)].width = 14.4

    ws.merge_cells(start_row=2, start_column=col_b0, end_row=2, end_column=col_end - 1)
    _cell(ws, 2, col_b0, f'"{customer}" 님을 위한 비교분석표', bold=True, size=13, fmt="@")

    # 3~5행 헤더
    if n:
        ws.merge_cells(start_row=3, start_column=col_b0, end_row=3, end_column=col_bsum)
    _cell(ws, 3, col_b0, "비교분석 전 보장", bold=True, fill=FORM_YELLOW)
    ws.merge_cells(start_row=3, start_column=col_name0, end_row=5, end_column=col_name0 + 2)
    _cell(ws, 3, col_name0, "담보내용", bold=True, fill=FORM_YELLOW)
    if m + new_slot:
        ws.merge_cells(start_row=3, start_column=col_asum, end_row=3, end_column=col_end - 1)
    _cell(ws, 3, col_asum, "비교분석 후 보장", bold=True, fill=FORM_YELLOW)
    ws.merge_cells(start_row=4, start_column=col_bsum, end_row=5, end_column=col_bsum)
    _cell(ws, 4, col_bsum, "합 계", bold=True, fill=FORM_YELLOW)
    ws.merge_cells(start_row=4, start_column=col_asum, end_row=5, end_column=col_asum)
    _cell(ws, 4, col_asum, "합 계", bold=True, fill=FORM_YELLOW)
    # BOHUMFIT-252 A: 2단 헤더(레이아웃 정본 실측) — 4행 회사명 / 5행 상품명. 회사별 월납은
    #   중복 기재를 없애고 양식대로 "보험료 합계"(50행) 한 곳에만 둔다(값 자체는 불변).
    #   ※레이아웃 정본의 구분(손해/생명 종목) 행은 원천 데이터 부재로 미기재 — 기존 메타(구 분=
    #   컨설팅 상태·가입일·납만기·계피관계) 유지(태스크 문서 기록).
    ws.row_dimensions[5].height = 30  # 상품명 2줄 랩 대응
    for idx, co in enumerate(b_companies):
        _cell(ws, 4, col_b0 + idx, _company_label(co, b_companies), bold=True, fill=FORM_YELLOW, wrap=True)
        _cell(ws, 5, col_b0 + idx, co.get("product") or "-", fill=FORM_YELLOW, wrap=True, size=8, fmt="@")
    for idx, co in enumerate(a_companies):
        _cell(ws, 4, col_a0 + idx, _company_label(co, a_companies), bold=True, fill=FORM_YELLOW, wrap=True)
        _cell(ws, 5, col_a0 + idx, co.get("product") or "-", fill=FORM_YELLOW, wrap=True, size=8, fmt="@")
    # 252(재개): 계약 미확인 열 헤더 — 회사 열 뒤·합계 앞([전]) / 회사 열 뒤([후]).
    if b_unk:
        _cell(ws, 4, col_b0 + n, "계약 미확인", bold=True, fill=FORM_YELLOW, wrap=True)
        _cell(ws, 5, col_b0 + n, "(원문 계약 특정 불가)", fill=FORM_YELLOW, wrap=True, size=8, fmt="@")
    if a_unk:
        _cell(ws, 4, col_a0 + m, "계약 미확인", bold=True, fill=FORM_YELLOW, wrap=True)
        _cell(ws, 5, col_a0 + m, "(원문 계약 특정 불가)", fill=FORM_YELLOW, wrap=True, size=8, fmt="@")
    if new_slot:
        col_new = col_a0 + m + a_unk
        _cell(ws, 4, col_new, "신규 설계 반영 대상", bold=True, fill=FORM_YELLOW, wrap=True)
        _cell(ws, 5, col_new, "(가입제안서 반영 전)", fill=FORM_YELLOW, wrap=True, size=8, fmt="@")

    # 6~9행 계약 메타(구 분·가입일·납만기·계피관계) — 합계열은 양식 리터럴 "-"
    def _meta(co: dict, kind: str) -> str:
        if kind == "구 분":
            # BOHUMFIT-236 A 보존: 납입완료 병기(구 시트의 배지 표기를 메타 행으로 이관).
            status = co.get("consulting_status") or "유지"
            return f"{status}(납입완료)" if co.get("paid_up") else status
        if kind == "가입일":
            return co.get("contract_date") or "-"
        if kind == "납만기":
            return f"{co.get('pay_years') or '-'}년납/{co.get('maturity') or '-'}"
        remark = co.get("remark") or ""
        return "상이" if "계피상이" in remark else ("동일" if remark else "-")

    for offset, kind in enumerate(("구 분", "가입일", "납만기", "계피관계")):
        row = 6 + offset
        ws.merge_cells(start_row=row, start_column=col_name0, end_row=row, end_column=col_name0 + 2)
        _cell(ws, row, col_name0, kind, bold=True, fill=FORM_YELLOW)
        _cell(ws, row, col_bsum, "-")
        _cell(ws, row, col_asum, "-")
        for idx, co in enumerate(b_companies):
            _cell(ws, row, col_b0 + idx, _meta(co, kind), fmt="@")
        for idx, co in enumerate(a_companies):
            _cell(ws, row, col_a0 + idx, _meta(co, kind), fmt="@")
        if b_unk:
            _cell(ws, row, col_b0 + n, "-", fmt="@")
        if a_unk:
            _cell(ws, row, col_a0 + m, "-", fmt="@")
        if new_slot:
            _cell(ws, row, col_a0 + m + a_unk, "-", fmt="@")  # 252 B: 신규 골격 열 메타 자리

    before_rows = _coverage_maps(before)
    after_rows = _coverage_maps(after_before) if after_before else {}

    # 10~44행: 담보 35행 — 값 기입(만원)
    estimated_present = False
    for offset, item in enumerate(FORM_ITEMS):
        row = 10 + offset
        # BOHUMFIT-250: 강조 행 fill — 원본 위치 실측 그대로(그린 티=대분류 선두·라임=특수).
        row_fill = GREENTEA if item in HIGHLIGHT_ITEMS else (LIME if item in SPECIAL_ITEMS else None)
        ws.merge_cells(start_row=row, start_column=col_name0, end_row=row, end_column=col_name0 + 2)
        _cell(ws, row, col_name0, item, bold=True, fill=FORM_YELLOW, wrap=True)
        if item.startswith("일반종수술"):
            ws.row_dimensions[row].height = 26  # 250: 긴 라벨(표준환산) 줄바꿈 겹침 해소
        b_row = before_rows.get(item) or {}
        a_row = after_rows.get(item) or {}
        if b_row.get("estimated") or a_row.get("estimated"):
            estimated_present = True
        _cell(ws, row, col_bsum, _man(b_row.get("summary")), bold=True, fmt="#,##0", fill=row_fill)
        for idx, co in enumerate(b_companies):
            _cell(ws, row, col_b0 + idx, _man((b_row.get("by_company") or {}).get(str(co.get("idx")))), fmt="#,##0", fill=row_fill)
        _cell(ws, row, col_asum, _man(a_row.get("summary")) if after_before else None, bold=True, fmt="#,##0", fill=row_fill)
        for idx, co in enumerate(a_companies):
            _cell(ws, row, col_a0 + idx, _man((a_row.get("by_company") or {}).get(str(co.get("idx")))), fmt="#,##0", fill=row_fill)
        if b_unk:
            _cell(ws, row, col_b0 + n, _man(_unknown_sum(b_row, b_ids)), fmt="#,##0", fill=row_fill)
        if a_unk:
            _cell(ws, row, col_a0 + m, _man(_unknown_sum(a_row, a_ids)), fmt="#,##0", fill=row_fill)
        if new_slot:
            _cell(ws, row, col_a0 + m + a_unk, None, fmt="#,##0", fill=row_fill)  # 252 B: 값 공란 골격

    # 45~49행: Y/N 5행 — 값 기입(COUNTA 수식 미채택 근거는 모듈 주석)
    yn_before = _yn_map(before)
    yn_after = _yn_map(after_before) if after_before else {}
    for offset, item in enumerate(YN_ROWS):
        row = 45 + offset
        ws.merge_cells(start_row=row, start_column=col_name0, end_row=row, end_column=col_name0 + 2)
        _cell(ws, row, col_name0, item, bold=True, fill=FORM_YELLOW)
        _cell(ws, row, col_bsum, yn_before.get(item, "N"), bold=True, fmt="@")
        if after_before:
            _cell(ws, row, col_asum, yn_after.get(item, "N"), bold=True, fmt="@")

    # 50행: 보험료 합계(원 단위)
    ws.merge_cells(start_row=50, start_column=col_name0, end_row=50, end_column=col_name0 + 2)
    _cell(ws, 50, col_name0, "보험료 합계", bold=True, fill=FORM_YELLOW)
    _cell(ws, 50, col_bsum, (before.get("premium") or {}).get("monthly_total"), bold=True, fmt="#,##0")
    for idx, co in enumerate(b_companies):
        _cell(ws, 50, col_b0 + idx, co.get("monthly_premium"), fmt="#,##0")
    if b_unk:
        _cell(ws, 50, col_b0 + n, None, fmt="#,##0")  # 미확인 열 — 보험료 개념 없음(공란)
    if after_before:
        _cell(ws, 50, col_asum, (after_before.get("premium") or {}).get("monthly_total"), bold=True, fmt="#,##0")
        for idx, co in enumerate(a_companies):
            _cell(ws, 50, col_a0 + idx, co.get("monthly_premium"), fmt="#,##0")
        if a_unk:
            _cell(ws, 50, col_a0 + m, None, fmt="#,##0")
        if new_slot:
            _cell(ws, 50, col_a0 + m + a_unk, None, fmt="#,##0")

    # 51행: 가설계(양식 문구 유지) + 단위·환산 안내(238 정직 표기)
    ws.merge_cells(start_row=51, start_column=col_b0, end_row=51, end_column=col_end - 1)
    note = "가설계 · 보장금액 단위: 만원 / 보험료: 원"
    if estimated_present:
        note += " · 일반종수술(표준환산)은 표준 환산 기준 — 상품별 실제와 상이할 수 있음"
    _cell(ws, 51, col_b0, note, bold=True, align="right", border=False, color=RED_TX, fmt="@")

    # 부록: 양식 밖 담보 전량 수록(누락 0)
    form_names = set(FORM_ITEMS)
    extras = [
        row for row in (before.get("coverages") or [])
        if row.get("kb_name") not in form_names and row.get("enrolled")
    ]
    appendix_row = 53
    last_row = 51
    if extras:
        ws.merge_cells(start_row=appendix_row, start_column=col_b0, end_row=appendix_row, end_column=col_end - 1)
        _cell(ws, appendix_row, col_b0, "부록: 기타(신 체계 미포섭 — 정보 보존, 단위 만원)", bold=True,
              fill=FORM_GRAY, align="left")
        ordered = sorted(extras, key=lambda r: (_grp_key(r.get("group12")), r.get("kb_name") or ""))
        for offset, row_data in enumerate(ordered):
            row = appendix_row + 1 + offset
            # 라벨 = col_b0~col_asum-1 병합, 값 = col_asum — overview(계약 0열)에서도 열이
            # 겹치지 않는다(248 P2 검증에서 라벨 덮임 결함 발견·수정: col_asum은 항상 +4 이상).
            ws.merge_cells(start_row=row, start_column=col_b0, end_row=row, end_column=col_asum - 1)
            _cell(ws, row, col_b0, f"[{row_data.get('group12') or GROUP_ETC}] {row_data.get('kb_name')}", align="left")
            _cell(ws, row, col_asum, _man(row_data.get("summary")), fmt="#,##0")
        last_row = appendix_row + len(extras)

    # BOHUMFIT-250: 우측 고객정보 패널(원본 O열 실측 재현 — 라벨+공란·PII 미기입·인쇄영역 밖).
    panel_col = col_end + 1
    ws.column_dimensions[get_column_letter(panel_col)].width = 22.0
    for panel_row, label, bold in PANEL_LABELS:
        panel_cell = _cell(ws, panel_row, panel_col, label, bold=bold, align="left", fmt="@")
        panel_cell.border = BORDER_GRID
    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1  # 250 D: 15계약 가로 인쇄 1장 폭 맞춤(사양 결정 3 잠정)
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_area = f"A1:{get_column_letter(col_end)}{last_row}"
    ws.freeze_panes = "B10"


# ── 시트3: 최종비교분석표 — 좌측 항목 블록 + 우측 종합비교(S3 구조) ─────────────────
def _sheet_final_form(ws, analysis: dict, before: dict, after_before: dict | None) -> None:
    ws.title = "최종비교분석표"
    customer = (before.get("customer") or {}).get("name") or ""
    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "portrait"
    widths = {"A": 3.0, "B": 16.0, "C": 15.2, "D": 17.0, "E": 14.0, "F": 16.0,
              "G": 3.0, "H": 14.0, "I": 16.0, "J": 5.0, "K": 16.0}
    for col, width in widths.items():
        ws.column_dimensions[col].width = width

    ws.merge_cells("B2:L2")
    _cell(ws, 2, 2, f"주요보장분석({customer})", bold=True, size=20, border=False)

    # BOHUMFIT-252 C: 표 헤더는 시트2와 동일하게 에메랄드 면+흰 글자(250 헤더 규칙으로 승격 —
    #   레이아웃 정본의 색 헤더 행을 FIT 팔레트로 재현).
    _cell(ws, 4, 2, "리모델링 전", bold=True, fill=FORM_YELLOW, size=12)
    ws.merge_cells("C4:E4")
    _cell(ws, 4, 3, "주요보장", bold=True, fill=FORM_YELLOW, size=12)
    _cell(ws, 4, 6, "리모델링 후", bold=True, fill=FORM_YELLOW, size=12)

    before_rows = _coverage_maps(before)
    after_rows = _coverage_maps(after_before) if after_before else {}
    for offset, item in enumerate(FORM_ITEMS):
        row = 5 + offset
        # BOHUMFIT-250: 라벨 기본=에메랄드 소프트, 강조=그린 티/라임(시트2와 동일 세트 —
        # 원본 시트3의 불규칙 파스텔(행35 누락 등)을 섹션 규칙으로 정규화·근거는 태스크 문서).
        label_fill = GREENTEA if item in HIGHLIGHT_ITEMS else (LIME if item in SPECIAL_ITEMS else FORM_BLUE)
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=5)
        _cell(ws, row, 3, item, bold=True, fill=label_fill, wrap=True)
        _cell(ws, row, 2, _man((before_rows.get(item) or {}).get("summary")), fmt='#,##0"만원"', align="right")
        if after_before:
            _cell(ws, row, 6, _man((after_rows.get(item) or {}).get("summary")), fmt='#,##0"만원"',
                  align="right", color=EMERALD, bold=True)

    yn_before = _yn_map(before)
    yn_after = _yn_map(after_before) if after_before else {}
    for offset, item in enumerate(YN_ROWS):
        row = 5 + len(FORM_ITEMS) + offset
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=5)
        _cell(ws, row, 3, item, bold=True, fill=FORM_BLUE)
        _cell(ws, row, 2, yn_before.get(item, "N"), fmt="@")
        if after_before:
            _cell(ws, row, 6, yn_after.get(item, "N"), fmt="@")

    total_row = 5 + len(FORM_ITEMS) + len(YN_ROWS)
    before_monthly = (before.get("premium") or {}).get("monthly_total")
    after_monthly = (after_before.get("premium") or {}).get("monthly_total") if after_before else None
    ws.merge_cells(start_row=total_row, start_column=3, end_row=total_row, end_column=5)
    _cell(ws, total_row, 3, "보험료 합계(원)", bold=True, fill=FORM_GRAY)
    _cell(ws, total_row, 2, before_monthly, bold=True, fmt='#,##0"원"', align="right")
    if after_before:
        _cell(ws, total_row, 6, after_monthly, bold=True, fmt='#,##0"원"', align="right")

    # 우측: 종합비교(값 기입 — I열 규칙 파생값·K7 이중합산 미이식)
    # BOHUMFIT-252 C: 레이아웃 정본 디자인 정합 — 헤더(종합/전/비교/후)=에메랄드+흰 글자,
    #   단계 라벨=에메랄드 소프트(시트2 라벨 규칙과 동일 세트).
    _cell(ws, 4, 8, "종합", bold=True, size=12, fill=FORM_YELLOW)
    _cell(ws, 4, 9, "전", bold=True, size=12, fill=FORM_YELLOW)
    _cell(ws, 4, 10, "비교", bold=True, size=12, fill=FORM_YELLOW)
    _cell(ws, 4, 11, "후", bold=True, size=12, fill=FORM_YELLOW)
    stages_before = _stage_map(before)
    stages_after = _stage_map(after_before) if after_before else {}
    for offset, key in enumerate(STAGE_ROWS):
        row = 5 + offset
        _cell(ws, row, 8, key, bold=True, fill=FORM_BLUE)
        _cell(ws, row, 9, _man(stages_before.get(key, 0)), fmt='#,##0"만원"', align="right")
        _cell(ws, row, 10, "→")
        if after_before:
            _cell(ws, row, 11, _man(stages_after.get(key, 0)), fmt='#,##0"만원"', align="right",
                  color=RED_TX, bold=True)

    ws.merge_cells("H13:K13")
    _cell(ws, 13, 8, "보험료 차액(후−전)", bold=True, size=12, fill=FORM_YELLOW)
    ws.merge_cells("H14:K15")
    delta = (after_monthly - before_monthly) if (after_monthly is not None and before_monthly is not None) else None
    # 250: 절감(음수)=에메랄드·증가=앰버(FIT 상태 색 선례 — 빨강 대체 근거는 태스크 문서).
    delta_color = EMERALD if (delta is None or delta <= 0) else AMBER_TX
    delta_cell = _cell(ws, 14, 8, delta, bold=True, fmt='#,##0"원"', color=delta_color, size=12)
    delta_cell.border = BORDER_BOX

    ws.merge_cells("H17:K18")
    notes_header = _cell(ws, 17, 8, "특이사항", bold=True, size=12, fill=FORM_YELLOW)
    notes_header.border = BORDER_BOX
    ws.merge_cells("H19:K45")
    notes = _special_notes(analysis)
    note_cell = _cell(ws, 19, 8, "\n".join(f"- {n}" for n in notes) if notes else None, align="left", wrap=True)
    note_cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
    ws.print_area = "A1:L46"


def build_workbook_bytes(analysis: dict) -> bytes:
    """분석 dict([전]만 또는 전후 비교 결과) → 비분양식 3시트 xlsx 바이트."""
    before = analysis.get("before", {}) or {}
    after = analysis.get("after") or {}
    after_before = after.get("before") or None
    try:
        ensure_comparison(analysis)  # comparison 부재 시 파생(특이사항 cautions 노출용)
    except Exception:
        pass  # 비교 파생 실패는 특이사항 축소일 뿐 — 생성 자체는 진행(정보 보존)
    wb = Workbook()
    _sheet_cover(wb.active, analysis)
    _sheet_compare_form(wb.create_sheet(), analysis, before, after_before)
    _sheet_final_form(wb.create_sheet(), analysis, before, after_before)
    stream = io.BytesIO()
    wb.save(stream)
    return stream.getvalue()
