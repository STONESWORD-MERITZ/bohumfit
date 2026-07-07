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


def _sheet_before(ws, before: dict) -> None:
    companies = before.get("companies", [])  # 월납 내림차순(백엔드 정렬)
    coverages = before.get("coverages", [])
    ws["A1"] = "회사별 세부 (전)"
    ws["A1"].font = Font(bold=True, size=14, color=INK)

    r = 3
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

    # 하단 계약 비고
    r += 1
    note = ws.cell(row=r, column=1, value="계약 비고")
    note.font = Font(bold=True, color=INK, size=10)
    r += 1
    for co in companies:
        parts = [f"{co.get('insurer') or '계약'} {co.get('idx')}"]
        if co.get("product"):
            parts.append(str(co["product"]))
        if co.get("pay_years"):
            parts.append(f"{co['pay_years']}년납" + (f"/{co.get('maturity')}" if co.get("maturity") else ""))
        if co.get("monthly_premium") is not None:
            parts.append(f"월 {int(co['monthly_premium']):,}원")
        if co.get("remark"):
            parts.append(str(co["remark"]))
        ws.cell(row=r, column=1, value=" · ".join(parts)).font = Font(color=GRAY_TX, size=9)
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=max(3, 3 + len(companies) - 1))
        r += 1

    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 22
    for j in range(3, 4 + len(companies)):
        ws.column_dimensions[get_column_letter(j)].width = 14
    ws.freeze_panes = "D4"


def build_workbook_bytes(analysis: dict) -> bytes:
    """[전]/[최종] dict → xlsx 바이트."""
    before = analysis.get("before", {}) or {}
    final = analysis.get("final", {}) or {}
    wb = Workbook()
    _sheet_final(wb.active, final, before)
    _sheet_before(wb.create_sheet("전 회사별세부"), before)
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()
