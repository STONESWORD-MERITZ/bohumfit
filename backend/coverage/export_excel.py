"""BOHUMFIT-181: 리모델링 보장분석표 엑셀(.xlsx) 생성.

179/179b [전]/[최종] 데이터(dict)를 입력받아 렌더만 한다(파싱 재실행 X).
- [최종] 시트: 상단 월납합계·총납입 + 담보별 권장/가입/과부족/준비상태(색상).
- [전] 시트: 회사(월납 내림차순) × 담보 매트릭스 + 좌측 합산/대표 요약열 + 하단 계약 비고.
※ PII: 생성물은 응답 스트림 전용, 서버 미저장.
"""
from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .compare import ensure_comparison
from .constants import GROUP13

# FIT v1.1 (openpyxl ARGB, 앞 FF=불투명)
EMERALD = "FF084734"
EMERALD_SOFT = "FFEEF6F1"
INK = "FF0A0A0A"
AMBER_SOFT = "FFFBEEDD"
AMBER_TX = "FFB45309"
GRAY_SOFT = "FFF1F1F1"
GRAY_TX = "FF7A7A78"
WHITE = "FFFFFFFF"

_STATUS_FILL = {"충분": EMERALD_SOFT, "부족": AMBER_SOFT, "미가입": GRAY_SOFT}
_thin = Side(style="thin", color="FFE8E8E4")
_BORDER = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)


def _grp_key(g: str) -> int:
    return GROUP13.index(g) if g in GROUP13 else len(GROUP13)


def _hdr(cell, text, fill=EMERALD, color=WHITE):
    cell.value = text
    cell.font = Font(bold=True, color=color, size=10)
    cell.fill = PatternFill("solid", fgColor=fill)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = _BORDER


def _num(cell, value, fmt="#,##0"):
    cell.value = value
    if isinstance(value, (int, float)):
        cell.number_format = fmt
    cell.alignment = Alignment(horizontal="right", vertical="center")
    cell.border = _BORDER


def _premium_label(value) -> str:
    return f"{int(value):,}원" if isinstance(value, (int, float)) else "미제공"


def _period_label(contract: dict) -> str:
    years = contract.get("pay_years")
    if years:
        return f"{years}년납"
    return "미제공"


def _sheet_final(ws, final: dict, before: dict) -> None:
    ws.title = "최종 보장진단"
    prem = (final.get("premium") or before.get("premium") or {})
    ws["A1"] = "보장분석 리모델링표 — 최종 보장진단"
    ws["A1"].font = Font(bold=True, size=14, color=INK)
    ws.merge_cells("A1:F1")
    ws["A2"] = "월 납입보험료 합계"
    ws["B2"] = prem.get("monthly_total")
    ws["D2"] = "총 납입액(만기까지)"
    ws["E2"] = prem.get("paid_total")
    for c in ("B2", "E2"):
        ws[c].number_format = '#,##0"원"'
        ws[c].font = Font(bold=True, color=INK)
    for c in ("A2", "D2"):
        ws[c].font = Font(color=GRAY_TX, size=9)

    r = 4
    headers = ["대분류", "담보", "권장", "가입", "과부족", "준비"]
    for i, h in enumerate(headers, start=1):
        _hdr(ws.cell(row=r, column=i), h)
    r += 1

    covs = sorted(final.get("coverages", []), key=lambda c: (_grp_key(c.get("group12", "")),))
    for c in covs:
        ws.cell(row=r, column=1, value=c.get("group12")).border = _BORDER
        ws.cell(row=r, column=1).font = Font(color=GRAY_TX, size=9)
        b = ws.cell(row=r, column=2, value=c.get("kb_name")); b.border = _BORDER; b.font = Font(color=INK, size=10)
        _num(ws.cell(row=r, column=3), c.get("recommended"))
        _num(ws.cell(row=r, column=4), c.get("value"))
        gap = c.get("gap")
        gcell = ws.cell(row=r, column=5); _num(gcell, gap)
        if isinstance(gap, (int, float)):
            gcell.font = Font(color=(AMBER_TX if gap < 0 else EMERALD if gap > 0 else GRAY_TX))
        st = c.get("status")
        scell = ws.cell(row=r, column=6, value=st or "-")
        scell.alignment = Alignment(horizontal="center", vertical="center")
        scell.border = _BORDER
        if st in _STATUS_FILL:
            scell.fill = PatternFill("solid", fgColor=_STATUS_FILL[st])
            scell.font = Font(bold=True, color=(EMERALD if st == "충분" else AMBER_TX if st == "부족" else GRAY_TX))
        r += 1

    for col, w in zip("ABCDEF", (12, 22, 14, 14, 14, 8)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A5"


def _sheet_before(ws, before: dict, title: str = "회사별 세부 (전)") -> None:
    companies = before.get("contract_list") or before.get("companies", [])  # 월납 내림차순(백엔드 정렬)
    coverages = before.get("coverages", [])
    ws["A1"] = title
    ws["A1"].font = Font(bold=True, size=14, color=INK)

    r = 3
    contract_headers = ["번호", "회사명", "상품명", "납입기간", "만기", "월보험료", "비고"]
    for col, h in enumerate(contract_headers, start=1):
        _hdr(ws.cell(row=r, column=col), h)
    r += 1
    for co in companies:
        values = [
            co.get("idx"),
            co.get("insurer") or "미제공",
            co.get("product") or "미제공",
            _period_label(co),
            co.get("maturity") or "미제공",
            _premium_label(co.get("monthly_premium")),
            co.get("remark") or "",
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            cell.border = _BORDER
            cell.alignment = Alignment(horizontal="center" if col in (1, 4, 5, 6) else "left", vertical="center", wrap_text=True)
            cell.font = Font(color=INK if col in (1, 2, 3) else GRAY_TX, size=9)
        r += 1

    r += 2
    _hdr(ws.cell(row=r, column=1), "대분류")
    _hdr(ws.cell(row=r, column=2), "담보")
    _hdr(ws.cell(row=r, column=3), "합산/대표")
    for j, co in enumerate(companies, start=4):
        label = f"{co.get('insurer') or '계약'} {co.get('idx')}"
        _hdr(ws.cell(row=r, column=j), label)
    r += 1

    for c in sorted(coverages, key=lambda x: (_grp_key(x.get("group12", "")),)):
        ws.cell(row=r, column=1, value=c.get("group12")).font = Font(color=GRAY_TX, size=9)
        ws.cell(row=r, column=1).border = _BORDER
        nm = ws.cell(row=r, column=2, value=c.get("kb_name")); nm.border = _BORDER; nm.font = Font(color=INK, size=10)
        sc = ws.cell(row=r, column=3); _num(sc, c.get("summary")); sc.font = Font(bold=True, color=INK)
        by = c.get("by_company", {})
        for j, co in enumerate(companies, start=4):
            _num(ws.cell(row=r, column=j), by.get(str(co.get("idx"))))
        r += 1

    for j in range(3, 4 + len(companies)):
        ws.column_dimensions[get_column_letter(j)].width = 14
    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 28
    ws.column_dimensions["D"].width = 12
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].width = 14
    ws.column_dimensions["G"].width = 22
    ws.freeze_panes = "D4"


def _sheet_compare(ws, comparison: dict) -> None:
    ws["A1"] = "전후 비교"
    ws["A1"].font = Font(bold=True, size=14, color=INK)
    premium = comparison.get("premium") or {}
    ws["A2"] = "월납 증감"
    ws["B2"] = premium.get("delta_monthly")
    ws["D2"] = "총납입 증감"
    ws["E2"] = premium.get("delta_paid_total")
    for c in ("B2", "E2"):
        ws[c].number_format = '#,##0"원"'
        ws[c].font = Font(bold=True, color=INK)
    for c in ("A2", "D2"):
        ws[c].font = Font(color=GRAY_TX, size=9)

    headers = ["대분류", "담보", "권장", "전 가입", "후 가입", "전 상태", "후 상태", "상태 변화", "증감", "개선"]
    r = 4
    for col, header in enumerate(headers, start=1):
        _hdr(ws.cell(row=r, column=col), header)
    r += 1
    for row in comparison.get("coverages", []):
        values = [
            row.get("group12"),
            row.get("kb_name"),
            row.get("recommended"),
            row.get("before_value"),
            row.get("after_value"),
            row.get("before_status"),
            row.get("after_status"),
            row.get("status_change"),
            row.get("delta_value"),
            "개선" if row.get("improved") else "",
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            cell.border = _BORDER
            cell.alignment = Alignment(
                horizontal="right" if col in (3, 4, 5, 9) else "center" if col in (6, 7, 8, 10) else "left",
                vertical="center",
                wrap_text=True,
            )
            if col in (3, 4, 5, 9) and isinstance(value, (int, float)):
                cell.number_format = '#,##0'
            if col == 10 and value:
                cell.fill = PatternFill("solid", fgColor=EMERALD_SOFT)
                cell.font = Font(bold=True, color=EMERALD)
            elif col in (6, 7):
                status = str(value or "")
                if status in _STATUS_FILL:
                    cell.fill = PatternFill("solid", fgColor=_STATUS_FILL[status])
                    cell.font = Font(bold=True, color=(EMERALD if status == "충분" else AMBER_TX if status == "부족" else GRAY_TX))
            else:
                cell.font = Font(color=INK if col == 2 else GRAY_TX, size=9)
        r += 1

    widths = (12, 22, 14, 14, 14, 10, 10, 16, 14, 8)
    for col, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(col)].width = width
    ws.freeze_panes = "A5"


def _sheet_summary(ws, comparison: dict, plan: dict | None = None) -> None:
    ws["A1"] = "컨설팅 요약"
    ws["A1"].font = Font(bold=True, size=14, color=INK)
    premium = comparison.get("premium") or {}
    summary = comparison.get("summary") or {}
    rows = [
        ("전 월납", premium.get("before_monthly")),
        ("후 월납", premium.get("after_monthly")),
        ("월납 증감", premium.get("delta_monthly")),
        ("전 총납입", premium.get("before_paid_total")),
        ("후 총납입", premium.get("after_paid_total")),
        ("총납입 증감", premium.get("delta_paid_total")),
        ("부족·미가입 → 충분", summary.get("improved_count")),
        ("미가입 → 충분", summary.get("missing_to_sufficient")),
        ("부족 → 충분", summary.get("short_to_sufficient")),
    ]
    r = 3
    for label, value in rows:
        ws.cell(row=r, column=1, value=label).font = Font(color=GRAY_TX, size=9)
        ws.cell(row=r, column=1).border = _BORDER
        _num(ws.cell(row=r, column=2), value)
        r += 1

    r += 1
    _hdr(ws.cell(row=r, column=1), "대분류")
    _hdr(ws.cell(row=r, column=2), "전 부족")
    _hdr(ws.cell(row=r, column=3), "후 부족")
    _hdr(ws.cell(row=r, column=4), "전 미가입")
    _hdr(ws.cell(row=r, column=5), "후 미가입")
    _hdr(ws.cell(row=r, column=6), "개선 수")
    r += 1
    for group in summary.get("by_group12", []):
        before_counts = group.get("before_status_counts") or {}
        after_counts = group.get("after_status_counts") or {}
        values = [
            group.get("group12"),
            before_counts.get("부족", 0),
            after_counts.get("부족", 0),
            before_counts.get("미가입", 0),
            after_counts.get("미가입", 0),
            group.get("improved_count", 0),
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            cell.border = _BORDER
            cell.alignment = Alignment(horizontal="right" if col > 1 else "left", vertical="center")
        r += 1

    r += 1
    _hdr(ws.cell(row=r, column=1), "구분")
    _hdr(ws.cell(row=r, column=2), "내용")
    r += 1
    for item in (comparison.get("improvements") or []) + (comparison.get("cautions") or []):
        ws.cell(row=r, column=1, value=item.get("level")).border = _BORDER
        ws.cell(row=r, column=2, value=item.get("message")).border = _BORDER
        r += 1
    if plan and plan.get("notes"):
        for note in plan.get("notes", []):
            ws.cell(row=r, column=1, value=note.get("scope") or "memo").border = _BORDER
            ws.cell(row=r, column=2, value=note.get("message") or "").border = _BORDER
            r += 1

    for col, width in zip("ABCDEF", (18, 18, 12, 12, 12, 10)):
        ws.column_dimensions[col].width = width


def build_workbook_bytes(analysis: dict) -> bytes:
    """[전]/[최종] dict → xlsx 바이트."""
    before = analysis.get("before", {}) or {}
    final = analysis.get("final", {}) or {}
    after = analysis.get("after") or {}
    after_before = after.get("before") or {}
    comparison = ensure_comparison(analysis)
    wb = Workbook()
    _sheet_final(wb.active, final, before)
    _sheet_before(wb.create_sheet("전 회사별세부"), before)
    if after_before and comparison:
        _sheet_before(wb.create_sheet("후 회사별세부"), after_before, "회사별 세부 (후)")
        _sheet_compare(wb.create_sheet("전후 비교"), comparison)
        _sheet_summary(wb.create_sheet("컨설팅 요약"), comparison, analysis.get("consulting_plan"))
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()
