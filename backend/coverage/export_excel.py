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


def _mask_name(name: str | None) -> str:
    raw = "".join(str(name or "").split())
    if not raw:
        return ""
    if "*" in raw:
        return raw
    if len(raw) == 1:
        return raw
    if len(raw) == 2:
        return f"{raw[0]}*"
    return f"{raw[0]}*{raw[-1]}"


def _group_value_summary(comparison: dict) -> list[dict]:
    groups: dict[str, dict] = {}
    for row in comparison.get("coverages", []):
        group = row.get("group12") or "기타"
        item = groups.setdefault(group, {"group12": group, "before_value": 0, "after_value": 0, "improved_count": 0})
        item["before_value"] += row.get("before_value") or 0
        item["after_value"] += row.get("after_value") or 0
        if row.get("improved"):
            item["improved_count"] += 1
    rows = []
    for item in groups.values():
        item["delta_value"] = item["after_value"] - item["before_value"]
        if item["delta_value"] or item["improved_count"]:
            rows.append(item)
    return sorted(rows, key=lambda item: _grp_key(item.get("group12")))


def _consulting_plan(analysis: dict) -> dict:
    plan = analysis.get("consulting_plan")
    return plan if isinstance(plan, dict) else {}


def _sheet_cover(ws, analysis: dict) -> None:
    ws.title = "① 표지"
    cover = analysis.get("report_cover") if isinstance(analysis.get("report_cover"), dict) else {}
    ws["A1"] = "① 표지"
    ws["A1"].font = Font(bold=True, size=14, color=INK)
    rows = [
        ("고객명", _mask_name(cover.get("customer_name"))),
        ("보험나이", cover.get("insurance_age")),
        ("상령일", cover.get("age_change_date")),
        ("소속(GA)", cover.get("ga_name")),
        ("설계사명", cover.get("planner_name")),
        ("작성일자", cover.get("written_date")),
        ("GA 로고", "슬롯 준비"),
    ]
    r = 3
    for label, value in rows:
        ws.cell(row=r, column=1, value=label).font = Font(bold=True, color=GRAY_TX, size=9)
        ws.cell(row=r, column=1).border = _BORDER
        ws.cell(row=r, column=2, value=value or "-").font = Font(color=INK, size=10)
        ws.cell(row=r, column=2).border = _BORDER
        r += 1
    ws.column_dimensions["A"].width = 16
    ws.column_dimensions["B"].width = 28


def _sheet_contract_decisions(ws, before: dict, plan: dict) -> None:
    ws.title = "② 전 계약"
    ws["A1"] = "② 컨설팅 전 계약 - 유지/해지"
    ws["A1"].font = Font(bold=True, size=14, color=INK)
    canceled = {
        str(item.get("contract_idx"))
        for item in plan.get("existing", [])
        if isinstance(item, dict) and item.get("disposition") == "cancel"
    }
    headers = ["번호", "처리", "회사명", "상품명", "납입기간", "만기", "월보험료", "비고"]
    r = 3
    for col, header in enumerate(headers, start=1):
        _hdr(ws.cell(row=r, column=col), header)
    r += 1
    for co in before.get("contract_list") or before.get("companies", []):
        is_cancel = str(co.get("idx")) in canceled
        values = [
            co.get("idx"),
            "해지" if is_cancel else "유지",
            co.get("insurer") or "미제공",
            co.get("product") or "미제공",
            _period_label(co),
            co.get("maturity") or "미제공",
            co.get("monthly_premium"),
            co.get("remark") or "",
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            cell.border = _BORDER
            cell.alignment = Alignment(horizontal="right" if col == 7 else "center" if col in (1, 2, 5, 6) else "left", vertical="center", wrap_text=True)
            if col == 7 and isinstance(value, (int, float)):
                cell.number_format = '#,##0"원"'
            if is_cancel:
                cell.font = Font(color=GRAY_TX, strike=True, size=9)
            elif col == 2:
                cell.fill = PatternFill("solid", fgColor=EMERALD_SOFT)
                cell.font = Font(bold=True, color=EMERALD)
            else:
                cell.font = Font(color=INK if col in (3, 4) else GRAY_TX, size=9)
        r += 1
    for col, width in enumerate((10, 10, 16, 24, 12, 12, 14, 24), start=1):
        ws.column_dimensions[get_column_letter(col)].width = width


def _sheet_proposals(ws, plan: dict) -> None:
    ws.title = "③ 신규제안"
    ws["A1"] = "③ 신규가입 제안서"
    ws["A1"].font = Font(bold=True, size=14, color=INK)
    ws["A2"] = "가입제안서 PDF 파싱 결과와 수기 보완값을 함께 표시합니다."
    ws["A2"].font = Font(color=GRAY_TX, size=9)
    headers = ["번호", "보험사", "상품명", "월보험료", "납입개월", "만기", "수기 입력 담보"]
    r = 4
    for col, header in enumerate(headers, start=1):
        _hdr(ws.cell(row=r, column=col), header)
    r += 1
    proposals = [item for item in plan.get("proposals", []) if isinstance(item, dict)]
    if not proposals:
        ws.cell(row=r, column=1, value="수기 입력된 신규 제안이 없습니다.").border = _BORDER
    for index, proposal in enumerate(proposals, start=1):
        coverage_label = ", ".join(
            f"{item.get('kb_name')} {item.get('amount'):,}" if isinstance(item.get("amount"), (int, float)) else str(item.get("kb_name"))
            for item in proposal.get("coverages", [])
            if isinstance(item, dict) and item.get("kb_name")
        )
        values = [
            proposal.get("proposal_id") or f"P{index}",
            proposal.get("insurer") or "신규제안",
            proposal.get("product") or "상품명 미입력",
            proposal.get("monthly_premium"),
            proposal.get("pay_months"),
            proposal.get("maturity") or "-",
            coverage_label or "-",
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            cell.border = _BORDER
            cell.alignment = Alignment(horizontal="right" if col in (4, 5) else "left", vertical="center", wrap_text=True)
            if col == 4 and isinstance(value, (int, float)):
                cell.number_format = '#,##0"원"'
            cell.font = Font(color=INK if col in (2, 3, 7) else GRAY_TX, size=9)
        r += 1
    for col, width in enumerate((10, 16, 24, 14, 12, 12, 36), start=1):
        ws.column_dimensions[get_column_letter(col)].width = width


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
    companies = before.get("contract_list") or before.get("companies", [])  # 보험사 가나다순(백엔드 정렬)
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


def _sheet_before_diagnosis(ws, final: dict, before: dict) -> None:
    ws.title = "⑥ 전 진단세부"
    prem = final.get("premium") or before.get("premium") or {}
    ws["A1"] = "⑥ 컨설팅 전 진단 세부"
    ws["A1"].font = Font(bold=True, size=14, color=INK)
    ws.merge_cells("A1:F1")
    ws["A2"] = "전 월납 보험료 합계"
    ws["B2"] = prem.get("monthly_total")
    ws["D2"] = "전 총 납입 예정액"
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
    for c in sorted(final.get("coverages", []), key=lambda row: _grp_key(row.get("group12", ""))):
        ws.cell(row=r, column=1, value=c.get("group12")).border = _BORDER
        ws.cell(row=r, column=1).font = Font(color=GRAY_TX, size=9)
        name_cell = ws.cell(row=r, column=2, value=c.get("kb_name"))
        name_cell.border = _BORDER
        name_cell.font = Font(color=INK, size=10)
        _num(ws.cell(row=r, column=3), c.get("recommended"))
        _num(ws.cell(row=r, column=4), c.get("value"))
        gap = c.get("gap")
        gap_cell = ws.cell(row=r, column=5)
        _num(gap_cell, gap)
        if isinstance(gap, (int, float)):
            gap_cell.font = Font(color=(AMBER_TX if gap < 0 else EMERALD if gap > 0 else GRAY_TX))
        status = c.get("status")
        status_cell = ws.cell(row=r, column=6, value=status or "-")
        status_cell.border = _BORDER
        status_cell.alignment = Alignment(horizontal="center", vertical="center")
        if status in _STATUS_FILL:
            status_cell.fill = PatternFill("solid", fgColor=_STATUS_FILL[status])
            status_cell.font = Font(bold=True, color=(EMERALD if status == "충분" else AMBER_TX if status == "부족" else GRAY_TX))
        r += 1
    for col, width in zip("ABCDEF", (12, 24, 14, 14, 14, 10)):
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "A5"


def _sheet_compare(ws, comparison: dict) -> None:
    ws["A1"] = "④ 최종 전 VS 후 - 특약별 보장 비교"
    ws["A1"].font = Font(bold=True, size=14, color=INK)
    premium = comparison.get("premium") or {}
    premium_rows = [
        ("전 월납", premium.get("before_monthly"), "후 월납", premium.get("after_monthly"), "월납 증감", premium.get("delta_monthly")),
        (
            "전 총납입",
            premium.get("before_paid_total"),
            "후 총납입",
            premium.get("after_paid_total"),
            "총납입 증감",
            premium.get("delta_paid_total"),
        ),
    ]
    for row_index, values in enumerate(premium_rows, start=2):
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=row_index, column=col, value=value)
            cell.font = Font(bold=col in (2, 4, 6), color=INK if col in (2, 4, 6) else GRAY_TX, size=9)
            if col in (2, 4, 6) and isinstance(value, (int, float)):
                cell.number_format = '#,##0"원"'

    r = 5
    ws.cell(row=r, column=1, value="대분류별 보장 변화").font = Font(bold=True, color=INK, size=11)
    r += 1
    for col, header in enumerate(["대분류", "전 보장금액", "후 보장금액", "증감", "개선 수"], start=1):
        _hdr(ws.cell(row=r, column=col), header)
    r += 1
    for group in _group_value_summary(comparison):
        values = [
            group.get("group12"),
            group.get("before_value"),
            group.get("after_value"),
            group.get("delta_value"),
            group.get("improved_count"),
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            cell.border = _BORDER
            cell.alignment = Alignment(horizontal="right" if col > 1 else "left", vertical="center")
            if col in (2, 3, 4) and isinstance(value, (int, float)):
                cell.number_format = '#,##0'
            if col == 4 and isinstance(value, (int, float)):
                cell.font = Font(color=(EMERALD if value > 0 else AMBER_TX if value < 0 else GRAY_TX))
        r += 1
    if r == 7:
        ws.cell(row=r, column=1, value="대분류별 확대 변화가 없습니다.").border = _BORDER
        r += 1

    r += 2
    for c in ("B2", "D2", "F2", "B3", "D3", "F3"):
        ws[c].number_format = '#,##0"원"'
        ws[c].font = Font(bold=True, color=INK)
    for c in ("F2", "F3"):
        value = ws[c].value
        if isinstance(value, (int, float)):
            ws[c].font = Font(bold=True, color=(EMERALD if value < 0 else AMBER_TX if value > 0 else GRAY_TX))

    header_row = r
    for col, header in ((1, "대분류"), (2, "담보"), (3, "권장"), (8, "증감"), (9, "변화")):
        ws.merge_cells(start_row=header_row, start_column=col, end_row=header_row + 1, end_column=col)
        _hdr(ws.cell(row=header_row, column=col), header)

    ws.merge_cells(start_row=header_row, start_column=4, end_row=header_row, end_column=5)
    _hdr(ws.cell(row=header_row, column=4), "전")
    ws.merge_cells(start_row=header_row, start_column=6, end_row=header_row, end_column=7)
    _hdr(ws.cell(row=header_row, column=6), "후")
    for col, header in ((4, "가입"), (5, "상태"), (6, "가입"), (7, "상태")):
        _hdr(ws.cell(row=header_row + 1, column=col), header)
    r += 2
    for row in comparison.get("coverages", []):
        values = [
            row.get("group12"),
            row.get("kb_name"),
            row.get("recommended"),
            row.get("before_value"),
            row.get("before_status"),
            row.get("after_value"),
            row.get("after_status"),
            row.get("delta_value"),
            row.get("status_change"),
        ]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            cell.border = _BORDER
            cell.alignment = Alignment(
                horizontal="right" if col in (3, 4, 6, 8) else "center" if col in (5, 7, 9) else "left",
                vertical="center",
                wrap_text=True,
            )
            if col in (3, 4, 6, 8) and isinstance(value, (int, float)):
                cell.number_format = '#,##0'
            if col == 9 and value:
                if row.get("improved"):
                    cell.fill = PatternFill("solid", fgColor=EMERALD_SOFT)
                    cell.font = Font(bold=True, color=EMERALD)
                elif row.get("worsened"):
                    cell.fill = PatternFill("solid", fgColor=AMBER_SOFT)
                    cell.font = Font(bold=True, color=AMBER_TX)
                else:
                    cell.font = Font(color=GRAY_TX, size=9)
            elif col in (5, 7):
                status = str(value or "")
                if status in _STATUS_FILL:
                    cell.fill = PatternFill("solid", fgColor=_STATUS_FILL[status])
                    cell.font = Font(bold=True, color=(EMERALD if status == "충분" else AMBER_TX if status == "부족" else GRAY_TX))
            else:
                cell.font = Font(color=INK if col == 2 else GRAY_TX, size=9)
        r += 1

    widths = (12, 22, 14, 14, 10, 14, 10, 14, 16)
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
    plan = _consulting_plan(analysis)
    wb = Workbook()
    if after_before and comparison:
        _sheet_cover(wb.active, analysis)
        _sheet_contract_decisions(wb.create_sheet("② 전 계약"), before, plan)
        _sheet_proposals(wb.create_sheet("③ 신규제안"), plan)
        _sheet_compare(wb.create_sheet("④ 전후 특약별"), comparison)
        _sheet_before(wb.create_sheet("⑤ 전후 회사별"), after_before, "⑤ 최종 전 VS 후 - 회사별 보장 세부")
        _sheet_before_diagnosis(wb.create_sheet("⑥ 전 진단세부"), final, before)
    else:
        _sheet_final(wb.active, final, before)
        _sheet_before(wb.create_sheet("전 회사별세부"), before)
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()
