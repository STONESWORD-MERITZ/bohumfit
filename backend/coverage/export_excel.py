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
- overview(합계형) 문서: BOHUMFIT-259부터 by_company가 귀속되면 표준 문서와 동일하게 회사 열을
  전개한다(가드 기준 = overview 여부 → ★by_company 유무). 미귀속·부분 귀속이면 종전대로
  합계 열만 + 특이사항에 246 경고 기재.
- 양식 밖 담보(기타 그룹·종수술비 버킷·(계약 미확인) 등)는 시트2 하단 "부록: 기타(정보 보존)"
  블록에 전량 수록 — 누락 0(양식 35행에 자리가 없어도 산출물에서 유실하지 않는다).

※ PII: 생성물은 응답 스트림 전용, 서버 미저장.
"""
from __future__ import annotations

import io
from datetime import datetime

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
    GRAY_TX,
    GREENTEA,
    HIGHLIGHT_ITEMS,
    INK,
    LIME,
    PANEL_LABELS,
    SPECIAL_ITEMS,
    WHITE,
    section_border,
)

MAN = 10_000
# BOHUMFIT-261 P2: 상담 임팩트용 '20년 동일 기준' 총납입 환산 개월(12개월 × 20년).
#   실제 납만기 기준 총납입(paid_total)과는 성격이 다른 별개 지표다 — 대체가 아니라 병기.
MONTHS_20Y = 240

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


def _yn_flags(before_like: dict) -> list:
    """Y/N 플래그 — ★담보 행(coverages)에서 항상 재파생한다(payload 값 신뢰 금지).

    BOHUMFIT-254: 실사용 동선의 [후] payload는 클라이언트 `buildAfterResult`가
    `{...analysis.before}` 스프레드로 만들어 `yn_flags`가 **[전] 값 그대로 남는다**
    (coverages만 해지 반영). 그대로 쓰면 해지해도 [후] Y/N이 안 바뀌어 개정3의 목적
    ("어느 회사 담보가 빠지는지")이 깨진다. 파생 규칙은 246/254와 동일 단일 소스
    (compute_yn_flags)이므로 서버 생성 payload에서는 결과가 완전히 동일하다.
    """
    coverages = (before_like or {}).get("coverages") or []
    if coverages:
        return compute_yn_flags(coverages)
    return (before_like or {}).get("yn_flags") or []


def _yn_map(before_like: dict) -> dict:
    return {f["item"]: f["value"] for f in _yn_flags(before_like)}


def _yn_company_map(before_like: dict) -> dict:
    """BOHUMFIT-254 개정3: 담보 → {계약 idx: "Y"} — 회사별 Y 표기용.

    구 payload(by_company 없는 yn_flags)는 빈 dict로 폴백해 합계 열만 표기(하위호환).
    """
    return {f["item"]: (f.get("by_company") or {}) for f in _yn_flags(before_like)}


def _stage_map(before_like: dict) -> dict:
    stages = (before_like or {}).get("stage_totals")
    if stages:
        return stages
    coverages = (before_like or {}).get("coverages", [])
    return compute_stage_totals(coverages) if coverages else {}


def _company_columns_available(before_like: dict) -> bool:
    """BOHUMFIT-259: 회사 열을 전개해도 되는지 — ★가드 기준을 "overview 여부"가 아니라
    "by_company 유무"로 전환한다.

    256~258이 overview 문서의 by_company를 채운 뒤부터 합계형 문서도 표준 문서와 동일하게
    회사별 전개가 가능하다. 단 **부분 귀속**(귀속된 행과 빈 행이 섞인 상태)에서는 빈 회사 열이
    "어느 회사에도 없음"으로 오독되므로(252 반려 사유와 동종) 합계만 유지한다.
    overview 행이 없는 표준 문서는 항상 True(기존 경로 무변경).
    """
    rows = [
        row for row in (before_like or {}).get("coverages", [])
        if row.get("overview") and row.get("enrolled")
    ]
    if not rows:
        return True
    return all(
        any(value is not None for value in (row.get("by_company") or {}).values())
        for row in rows
    )


# BOHUMFIT-252(재개): '?'(계약 미상 — 246/253 데이터 모델) 버킷 렌더 정책.
#   253 귀속 복원 후 실 5케이스 '?' 잔존 0(Codex 권위 실측) — 평시에는 열 미출력.
#   단, 동일 보험료 계약 등 모호 문서에서 '?'가 남으면(253은 오귀속 대신 '?' 유지가 설계)
#   회사 열 합 ≠ 합계로 다시 오독되므로, ★잔존 시에만 "계약 미확인" 열을 명시 출력한다.
def _unknown_bucket_present(before_like: dict, companies: list) -> bool:
    ids = {str(c.get("idx")) for c in companies}
    form_names = set(FORM_ITEMS)
    for row in (before_like or {}).get("coverages", []):
        # BOHUMFIT-259: overview 배제 제거 — 귀속되지 않은 overview 행은 by_company가 비어
        #   있어 자동으로 미해당이고, 귀속된 행에 '?'가 남으면 미확인 열을 정직하게 노출한다.
        if not row.get("enrolled") or row.get("kb_name") not in form_names:
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
def _sheet_cover(ws, analysis: dict, generated_at=None) -> None:
    """BOHUMFIT-261 P1: 표지 리디자인 — 브랜드 밴드 + 고객명 대제목 + 작성일 + 설계사 블록
    + 하단 고지 문구. PDF 표지(export_pdf._cover_page)와 항목·문구를 맞춘다(자료 일관성).
    ★값·집계와 무관한 표시 계층이며 A4 세로 1장 인쇄에 맞춘다.
    """
    ws.title = "표지(세로)"
    cover = analysis.get("report_cover") or {}
    customer = ((analysis.get("before") or {}).get("customer") or {}).get("name")
    display_name = cover.get("customer_name") or customer or "OOO"
    written = cover.get("written_date") or (generated_at.strftime("%Y-%m-%d") if generated_at else "")

    ws.column_dimensions["A"].width = 2.0
    for col in "BCDEFGHIJKLMNOP":
        ws.column_dimensions[col].width = 6.4
    for merge in ("B2:P4", "B7:P7", "B8:P9", "B11:P11",
                  "C13:F13", "G13:P13", "C14:F14", "G14:P14",
                  "C15:F15", "G15:P15", "C16:F16", "G16:P16",
                  "C17:F17", "G17:P17", "B20:P22"):
        ws.merge_cells(merge)

    # ── 브랜드 밴드(에메랄드 면 + 흰 글자) ────────────────────────────────
    ws.row_dimensions[2].height = 26
    ws.row_dimensions[3].height = 20
    ws.row_dimensions[4].height = 14
    band = _cell(ws, 2, 2, "BohumFit  보험핏", size=22, bold=True, fill=EMERALD,
                 align="left", border=False, name="맑은 고딕")
    band.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    for col in range(3, 17):  # 병합 셀 면 색 채우기(테두리 없는 밴드)
        _cell(ws, 2, col, None, fill=EMERALD, border=False)

    # ── 고객명 대제목 ─────────────────────────────────────────────────────
    ws.row_dimensions[7].height = 34
    ws.row_dimensions[8].height = 40
    _cell(ws, 7, 2, f"{display_name} 님을 위한", size=20, align="left", border=False, name="맑은 고딕")
    _cell(ws, 8, 2, "보험 보장 분석 리포트", size=30, bold=True, align="left", border=False,
          name="맑은 고딕", color=EMERALD)
    if written:
        _cell(ws, 11, 2, f"작성일  {written}", size=11, align="left", border=False,
              color=GRAY_TX, fmt="@")

    # ── 설계사 정보 블록(라벨 + 기입란) ───────────────────────────────────
    #   제공된 값은 채우고 미제공은 빈 기입란(밑줄)으로 남긴다 — 설계사 수기 보완용.
    planner_fields = (
        ("소속(GA)", cover.get("ga_name")),
        ("설계사명", cover.get("planner_name")),
        ("연락처", cover.get("planner_tel")),
        ("E-MAIL", cover.get("planner_email")),
    )
    _cell(ws, 12, 2, "담당 설계사", size=12, bold=True, align="left", border=False, color=EMERALD)
    for offset, (label, value) in enumerate(planner_fields):
        row = 13 + offset
        ws.row_dimensions[row].height = 22
        _cell(ws, row, 3, label, size=11, bold=True, fill=EMERALD_SOFT, align="left")
        _cell(ws, row, 7, value or "", size=11, align="left", fmt="@")

    # ── 하단 고지 문구(PDF 표지와 동일 취지) ──────────────────────────────
    note = _cell(ws, 20, 2,
                 "고객 설명용 요약 리포트입니다. 실제 보장 내용과 보험금 지급 여부는 각 보험사 "
                 "약관과 증권을 따르며, 본 자료는 보험 모집·중개·상품추천·가입권유를 목적으로 "
                 "하지 않습니다.", size=9, align="left", border=False, color=GRAY_TX, wrap=True)
    note.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_area = "A1:P23"


# ── 시트2: 비교분석표 — 계약 열 전부 전개(동적) ─────────────────────────────────
def _sheet_compare_form(ws, analysis: dict, before: dict, after_before: dict | None) -> None:
    ws.title = "비교분석표"
    customer = (before.get("customer") or {}).get("name") or ""
    # BOHUMFIT-259: 회사 열 전개 여부는 by_company 유무로 판단(overview도 귀속되면 전개).
    #   [전]·[후]를 각각 판정한다 — 해지로 [후] 귀속 상태가 달라질 수 있다.
    b_companies = (
        (before.get("contract_list") or before.get("companies") or [])
        if _company_columns_available(before) else []
    )
    a_companies = (
        (after_before.get("contract_list") or after_before.get("companies") or [])
        if (after_before is not None and _company_columns_available(after_before)) else []
    )
    n, m = len(b_companies), len(a_companies)
    # BOHUMFIT-252 B: [후] 신규 계약 열 골격 — 가입제안서 트랙 미착수 상태에서는 헤더 자리만
    #   두고 값은 공란("신규 설계 반영 대상"). 제안 계약(신규제안)이 페이로드에 있으면 일반
    #   회사 열로 이미 전개되므로 골격 열은 만들지 않는다. overview는 회사 열 자체가 없음(246).
    has_proposal = any(
        (co.get("consulting_status") == "신규제안") or (co.get("remark") == "신규제안")
        for co in a_companies
    )
    #   BOHUMFIT-259: overview 기준 → ★[후] 회사 열 존재 기준으로 전환(귀속된 overview도
    #   표준 문서와 동일하게 골격 열을 갖는다. 회사 열이 없으면 종전대로 미생성).
    new_slot = 1 if (after_before is not None and m and not has_proposal) else 0
    # BOHUMFIT-252(재개): '?' 버킷 잔존 시에만 "계약 미확인" 열 — 회사합=합계 대사가 눈에
    #   보이도록(모호 문서 오독 방지). 실 5케이스는 253 복원으로 잔존 0 → 열 미출력(현행 동일).
    b_ids = {str(c.get("idx")) for c in b_companies}
    a_ids = {str(c.get("idx")) for c in a_companies}
    b_unk = 1 if (n and _unknown_bucket_present(before, b_companies)) else 0
    a_unk = 1 if (after_before is not None and m
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
    # BOHUMFIT-254 개정4: 가독 밸런스 — 회사명(4행)·상품명(5행) 랩 여유, 메타/보험료 행은
    #   촘촘하게(장식 없이 밀도만 조정. 값·색 무변경).
    ws.row_dimensions[3].height = 20
    ws.row_dimensions[4].height = 28
    ws.row_dimensions[5].height = 30  # 상품명 2줄 랩 대응
    for meta_row in (6, 7, 8, 9):
        ws.row_dimensions[meta_row].height = 17
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

    # 6~9행 계약 메타 — BOHUMFIT-254 개정2: 9행을 "월보험료"로 전환(하단 50행에서 상단
    #   계약 메타 블록으로 이동 — Human 실무 가독 요청). 밀려나는 "계피관계"는 "구 분" 행에
    #   병기해 정보를 보존한다(236 납입완료 병기와 동일 패턴). ★담보 10~44·Y/N 45~49 좌표
    #   불변(하단 50행만 비움 — 행 삭제 아님·51/53 좌표 보존). 값 자체는 이동일 뿐 불변.
    def _meta(co: dict, kind: str) -> str:
        if kind == "구 분":
            # BOHUMFIT-236 A 보존: 납입완료 병기(구 시트의 배지 표기를 메타 행으로 이관).
            status = co.get("consulting_status") or "유지"
            if co.get("paid_up"):
                status = f"{status}(납입완료)"
            # 254: 계피관계 행 → 구 분 행 병기(★상이/동일 양쪽 보존 — 정보 손실 0).
            remark = co.get("remark") or ""
            if "계피상이" in remark:
                status = f"{status}·계피상이"
            elif remark:
                status = f"{status}·계피동일"
            return status
        if kind == "가입일":
            return co.get("contract_date") or "-"
        return f"{co.get('pay_years') or '-'}년납/{co.get('maturity') or '-'}"

    for offset, kind in enumerate(("구 분", "가입일", "납만기")):
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

    # 9행: 보험료 합계(원 단위) — 구 50행의 라벨·값 그대로(★위치만 이동, 라벨도 원본 정본
    #   표기 "보험료 합계" 유지 — 레이아웃 정본 r43 라벨과 동일).
    ws.merge_cells(start_row=9, start_column=col_name0, end_row=9, end_column=col_name0 + 2)
    _cell(ws, 9, col_name0, "보험료 합계", bold=True, fill=FORM_YELLOW)
    _cell(ws, 9, col_bsum, (before.get("premium") or {}).get("monthly_total"), bold=True, fmt="#,##0")
    for idx, co in enumerate(b_companies):
        _cell(ws, 9, col_b0 + idx, co.get("monthly_premium"), fmt="#,##0")
    if b_unk:
        _cell(ws, 9, col_b0 + n, None, fmt="#,##0")  # 미확인 열 — 보험료 개념 없음(공란)
    if after_before:
        _cell(ws, 9, col_asum, (after_before.get("premium") or {}).get("monthly_total"), bold=True, fmt="#,##0")
        for idx, co in enumerate(a_companies):
            _cell(ws, 9, col_a0 + idx, co.get("monthly_premium"), fmt="#,##0")
        if a_unk:
            _cell(ws, 9, col_a0 + m, None, fmt="#,##0")
        if new_slot:
            _cell(ws, 9, col_a0 + m + a_unk, None, fmt="#,##0")

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
    #   BOHUMFIT-254 개정3: 합계 열에 더해 ★회사별 열에도 Y 표기(해지 시 어느 회사 담보가
    #   빠지는지 식별 — 누락 방지). 원천 by_company에 값이 있는 계약만 "Y", 없으면 공란
    #   (compute_yn_flags 파생 — 금액 무변경·합계 Y/N 규칙 불변). 레이아웃 정본도 회사 열 Y 표기.
    yn_before = _yn_map(before)
    yn_after = _yn_map(after_before) if after_before else {}
    yn_co_before = _yn_company_map(before)
    yn_co_after = _yn_company_map(after_before) if after_before else {}
    for offset, item in enumerate(YN_ROWS):
        row = 45 + offset
        ws.merge_cells(start_row=row, start_column=col_name0, end_row=row, end_column=col_name0 + 2)
        _cell(ws, row, col_name0, item, bold=True, fill=FORM_YELLOW)
        _cell(ws, row, col_bsum, yn_before.get(item, "N"), bold=True, fmt="@")
        for idx, co in enumerate(b_companies):
            _cell(ws, row, col_b0 + idx, yn_co_before.get(item, {}).get(str(co.get("idx"))), fmt="@")
        if after_before:
            _cell(ws, row, col_asum, yn_after.get(item, "N"), bold=True, fmt="@")
            for idx, co in enumerate(a_companies):
                _cell(ws, row, col_a0 + idx, yn_co_after.get(item, {}).get(str(co.get("idx"))), fmt="@")
        # 미확인·신규 골격 열은 Y/N 판정 대상이 아니다(공란 — 셀 테두리만 유지).
        if b_unk:
            _cell(ws, row, col_b0 + n, None, fmt="@")
        if a_unk:
            _cell(ws, row, col_a0 + m, None, fmt="@")
        if new_slot:
            _cell(ws, row, col_a0 + m + a_unk, None, fmt="@")

    # 50행: (254 개정2) 보험료 합계는 상단 9행으로 이동 — 이 행은 블록 구분 여백으로 비운다.

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

    # BOHUMFIT-254 개정1: 구획 테두리 — 블록 경계에만 굵은 선을 덧댄다(값·구조 무변경).
    #   세로: [전] 회사 열군 ↔ 합계 ↔ 담보명 ↔ [후] 합계 ↔ [후] 회사 열군 경계.
    #   가로: 헤더/메타 블록(3~9행) 하단, 담보 블록(10~44) 하단, Y/N 블록(45~49) 하단,
    #        대분류 선두 강조 행(HIGHLIGHT_ITEMS) 상단 = 섹션 구분선.
    body_last = 49
    section_left_cols = {col_bsum, col_name0, col_asum, col_a0} | (
        {col_b0} if n or b_unk else set()
    )
    section_right_cols = {col_bsum, col_name0 + 2, col_asum, col_end - 1}
    section_bottom_rows = {9, 44, body_last}
    # 섹션 구분선 = ★대분류(group12) 전환 행 상단(패킷 "대분류 섹션 구분선").
    #   강조 행 기준으로 그으면 같은 대분류 안(후유장해 2행·종수술 5행)에도 줄이 생겨
    #   구획이 아니라 소음이 된다. 대분류는 payload 담보 행에서 읽는다(값 무관·표시 전용).
    section_top_rows = {10}
    _prev_group = None
    for offset, item in enumerate(FORM_ITEMS):
        group = (before_rows.get(item) or {}).get("group12")
        if _prev_group is not None and group and group != _prev_group:
            section_top_rows.add(10 + offset)
        if group:
            _prev_group = group
    for row in range(3, body_last + 1):
        for col in range(col_b0, col_end):
            cell = ws.cell(row=row, column=col)
            if cell.border is None:
                continue
            cell.border = section_border(
                left=col in section_left_cols,
                right=col in section_right_cols,
                top=row in section_top_rows,
                bottom=row in section_bottom_rows,
            )

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
    ws.merge_cells("H14:K14")
    delta = (after_monthly - before_monthly) if (after_monthly is not None and before_monthly is not None) else None
    # 250: 절감(음수)=에메랄드·증가=앰버(FIT 상태 색 선례 — 빨강 대체 근거는 태스크 문서).
    delta_color = EMERALD if (delta is None or delta <= 0) else AMBER_TX
    delta_cell = _cell(ws, 14, 8, delta, bold=True, fmt='#,##0"원"', color=delta_color, size=12)
    delta_cell.border = BORDER_BOX

    # BOHUMFIT-261 P2: ★20년 납부 시 총납입 차액 — 월납 차액 × 240개월(상담 임팩트용 동일
    #   기준 지표). 실제 납만기 기준 총납입 차액(PDF ④ "총납입보험료" 카드)과는 성격이 달라
    #   대체가 아니라 ★병기한다(라벨로 기준을 명시).
    ws.merge_cells("H15:K15")
    _cell(ws, 15, 8, "20년 납부 시 총납입 차액", bold=True, size=10, fill=FORM_BLUE)
    ws.merge_cells("H16:K16")
    delta_20y = delta * MONTHS_20Y if delta is not None else None
    delta20_cell = _cell(ws, 16, 8, delta_20y, bold=True, fmt='#,##0"원"',
                         color=(EMERALD if (delta_20y is None or delta_20y <= 0) else AMBER_TX), size=12)
    delta20_cell.border = BORDER_BOX

    ws.merge_cells("H18:K18")
    notes_header = _cell(ws, 18, 8, "특이사항", bold=True, size=12, fill=FORM_YELLOW)
    notes_header.border = BORDER_BOX
    ws.merge_cells("H19:K45")
    notes = _special_notes(analysis)
    note_cell = _cell(ws, 19, 8, "\n".join(f"- {n}" for n in notes) if notes else None, align="left", wrap=True)
    note_cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
    ws.print_area = "A1:L46"


def build_workbook_bytes(analysis: dict, generated_at=None) -> bytes:
    """분석 dict([전]만 또는 전후 비교 결과) → 비분양식 3시트 xlsx 바이트.

    BOHUMFIT-261: generated_at은 표지 작성일 표기용(미지정 시 호출 시각).
    """
    before = analysis.get("before", {}) or {}
    after = analysis.get("after") or {}
    after_before = after.get("before") or None
    try:
        ensure_comparison(analysis)  # comparison 부재 시 파생(특이사항 cautions 노출용)
    except Exception:
        pass  # 비교 파생 실패는 특이사항 축소일 뿐 — 생성 자체는 진행(정보 보존)
    wb = Workbook()
    _sheet_cover(wb.active, analysis, generated_at or datetime.now())
    _sheet_compare_form(wb.create_sheet(), analysis, before, after_before)
    _sheet_final_form(wb.create_sheet(), analysis, before, after_before)
    stream = io.BytesIO()
    wb.save(stream)
    return stream.getvalue()
