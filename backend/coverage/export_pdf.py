"""BOHUMFIT-181: 리모델링 보장분석표 PDF 생성 (FIT v1.1 브랜드, 보장분석 전용).

179/179b [전]/[최종] 데이터(dict) → 자체 완결 HTML → 헤드리스 Chromium(PDF).
- PDF 렌더러는 pipeline/report_pdf.html_to_pdf_bytes 재사용(무수정 import).
- 고지의무 리포트 템플릿(157)과 별개 HTML(표 구조 상이).
- 구 브랜드색(#15663D·#2E6B3E·#145C2A 등) 미사용, 에메랄드(#084734)·잉크(#0A0A0A)만.
※ PII: 생성물은 응답 스트림 전용, 서버 미저장.
"""
from __future__ import annotations

import html as _html
from datetime import datetime

from .constants import GROUP13

EMERALD = "#084734"
EMERALD_SOFT = "#EEF6F1"
INK = "#0A0A0A"
INK_BODY = "#1E293B"
GRAY = "#6D747D"
AMBER = "#B45309"
AMBER_SOFT = "#FBEEDD"
GRAY_SOFT = "#F1F1F1"
LINE = "#E8E8E4"

_STATUS = {
    "충분": (EMERALD, EMERALD_SOFT),
    "부족": (AMBER, AMBER_SOFT),
    "미가입": (GRAY, GRAY_SOFT),
}


def _fmt_krw(n) -> str:
    if n is None:
        return "-"
    if n == 0:
        return "0"
    n = int(n)
    eok, man = n // 100_000_000, (n % 100_000_000) // 10_000
    parts = []
    if eok:
        parts.append(f"{eok}억")
    if man:
        parts.append(f"{man:,}만")
    return " ".join(parts) if parts else f"{n:,}"


def _won(n) -> str:
    return "-" if n is None else f"{int(n):,}원"


def _premium_label(n) -> str:
    return f"{int(n):,}원" if isinstance(n, (int, float)) else "미제공"


def _period_label(contract: dict) -> str:
    years = contract.get("pay_years")
    return f"{int(years)}년납" if isinstance(years, (int, float)) else "미제공"


def _grp_key(g: str) -> int:
    return GROUP13.index(g) if g in GROUP13 else len(GROUP13)


def _esc(s) -> str:
    return _html.escape(str(s)) if s is not None else ""


def build_coverage_html(analysis: dict, generated_at: datetime | None = None) -> str:
    before = analysis.get("before", {}) or {}
    final = analysis.get("final", {}) or {}
    prem = final.get("premium") or before.get("premium") or {}
    customer = before.get("customer") or {}
    companies = before.get("contract_list") or before.get("companies", [])
    gen = generated_at.strftime("%Y-%m-%d") if generated_at else ""

    # [최종] 담보 그룹 순서
    fcovs = sorted(final.get("coverages", []), key=lambda c: _grp_key(c.get("group12", "")))
    final_rows = []
    for c in fcovs:
        st = c.get("status")
        color, bg = _STATUS.get(st, (GRAY, GRAY_SOFT))
        gap = c.get("gap")
        gap_txt = "-" if gap is None else (("+" if gap > 0 else "−" if gap < 0 else "") + _fmt_krw(abs(gap)))
        gap_color = AMBER if (isinstance(gap, (int, float)) and gap < 0) else EMERALD if (isinstance(gap, (int, float)) and gap > 0) else GRAY
        final_rows.append(
            f'<tr><td class="grp">{_esc(c.get("group12"))}</td>'
            f'<td class="nm">{_esc(c.get("kb_name"))}</td>'
            f'<td class="num">{_fmt_krw(c.get("recommended"))}</td>'
            f'<td class="num strong">{_fmt_krw(c.get("value"))}</td>'
            f'<td class="num" style="color:{gap_color}">{gap_txt}</td>'
            f'<td class="st"><span class="badge" style="color:{color};background:{bg}">{_esc(st) or "-"}</span></td></tr>'
        )

    # [전] 회사별 매트릭스
    comp_head = "".join(
        f'<th class="num">{_esc(co.get("insurer") or "계약")} {_esc(co.get("idx"))}<br><span class="sub">{_won(co.get("monthly_premium"))}</span></th>'
        for co in companies
    )
    before_rows = []
    for c in sorted(before.get("coverages", []), key=lambda x: _grp_key(x.get("group12", ""))):
        by = c.get("by_company", {})
        cells = "".join(f'<td class="num">{_fmt_krw(by.get(str(co.get("idx"))))}</td>' for co in companies)
        before_rows.append(
            f'<tr><td class="grp">{_esc(c.get("group12"))}</td>'
            f'<td class="nm">{_esc(c.get("kb_name"))}</td>'
            f'<td class="num strong">{_fmt_krw(c.get("summary"))}</td>{cells}</tr>'
        )
    notes = []
    for co in companies:
        notes.append(
            "<tr>"
            f"<td>{_esc(co.get('idx'))}</td>"
            f"<td>{_esc(co.get('insurer') or '미제공')}</td>"
            f"<td class=\"nm\">{_esc(co.get('product') or '미제공')}</td>"
            f"<td>{_esc(_period_label(co))}</td>"
            f"<td>{_esc(co.get('maturity') or '미제공')}</td>"
            f"<td class=\"num\">{_esc(_premium_label(co.get('monthly_premium')))}</td>"
            f"<td>{_esc(co.get('remark') or '')}</td>"
            "</tr>"
        )

    cust = ""
    if customer.get("name"):
        cust = f'{_esc(customer.get("name"))}' + (f' ({_esc(customer.get("age"))}세)' if customer.get("age") else "")

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ font-family: 'Noto Sans KR','Noto Sans CJK KR','Malgun Gothic',sans-serif; color: {INK_BODY}; font-size: 10pt; line-height: 1.5; word-break: keep-all; }}
.head {{ display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid {EMERALD}; padding-bottom: 10px; margin-bottom: 16px; }}
.brand {{ display: flex; align-items: center; gap: 8px; }}
.logo-mark {{ display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px; background: {EMERALD}; color: #fff; border-radius: 7px; font-weight: 800; font-size: 15pt; }}
.wordmark {{ font-size: 17pt; font-weight: 800; color: {INK}; letter-spacing: .2px; }}
.wordmark small {{ display: block; font-size: 8pt; font-weight: 700; color: {GRAY}; letter-spacing: 1.2px; }}
.head-meta {{ text-align: right; font-size: 8.5pt; color: {GRAY}; line-height: 1.6; }}
h1 {{ font-size: 14pt; color: {INK}; margin: 4px 0 12px; }}
h2 {{ font-size: 11.5pt; color: {EMERALD}; margin: 18px 0 8px; }}
.cards {{ display: flex; gap: 10px; margin-bottom: 8px; }}
.card {{ flex: 1; border: 1px solid {LINE}; border-radius: 8px; padding: 8px 12px; }}
.card .k {{ font-size: 8.5pt; color: {GRAY}; }}
.card .v {{ font-size: 13pt; font-weight: 800; color: {INK}; margin-top: 2px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 4px; }}
th, td {{ border: 1px solid {LINE}; padding: 4px 6px; font-size: 9pt; }}
th {{ background: {EMERALD}; color: #fff; font-weight: 700; }}
td.grp {{ color: {GRAY}; font-size: 8pt; }}
td.nm {{ color: {INK}; font-weight: 600; }}
td.num {{ text-align: right; }}
td.strong {{ font-weight: 800; color: {INK}; }}
td.st {{ text-align: center; }}
.badge {{ display: inline-block; border-radius: 10px; padding: 1px 8px; font-size: 8pt; font-weight: 700; }}
.notes {{ margin-top: 8px; font-size: 8pt; color: {GRAY}; }}
.notes li {{ list-style: none; margin: 1px 0; }}
.contract-list th, .contract-list td {{ font-size: 8.3pt; }}
.contract-list td {{ text-align: center; }}
.contract-list td.nm {{ text-align: left; }}
.disclaimer {{ margin-top: 16px; font-size: 7.5pt; color: {GRAY}; line-height: 1.5; }}
</style></head><body>
<div class="head">
  <div class="brand"><span class="logo-mark">ㅍ</span><span class="wordmark">BohumFit<small>보험핏 · 보장분석 리모델링</small></span></div>
  <div class="head-meta">{('고객 ' + cust + '<br>') if cust else ''}작성일 {gen}</div>
</div>
<h1>보장분석 리모델링표</h1>

<h2>최종 보장진단</h2>
<div class="cards">
  <div class="card"><div class="k">월 납입보험료 합계</div><div class="v">{_won(prem.get('monthly_total'))}</div></div>
  <div class="card"><div class="k">총 납입액(만기까지)</div><div class="v">{_won(prem.get('paid_total'))}</div></div>
</div>
<table><thead><tr><th>대분류</th><th>담보</th><th class="num">권장</th><th class="num">가입</th><th class="num">과부족</th><th>준비</th></tr></thead>
<tbody>{''.join(final_rows)}</tbody></table>

<h2>회사별 세부 (전)</h2>
<table class="contract-list"><thead><tr><th>번호</th><th>회사명</th><th>상품명</th><th>납입기간</th><th>만기</th><th class="num">월보험료</th><th>비고</th></tr></thead>
<tbody>{''.join(notes)}</tbody></table>
<table><thead><tr><th>대분류</th><th>담보</th><th class="num">합산/대표</th>{comp_head}</tr></thead>
<tbody>{''.join(before_rows)}</tbody></table>

<p class="disclaimer">본 리모델링표는 업로드한 KB 신정원 보장분석 제안서를 기준으로 정리한 참고용 자료입니다. 실제 보장 내용·보험금 지급 여부는 각 보험사 약관과 증권을 따르며, 본 자료는 보험 모집·중개·상품추천·가입권유를 목적으로 하지 않습니다.</p>
</body></html>"""


async def generate_coverage_pdf(analysis: dict, generated_at: datetime | None = None) -> bytes:
    """[전]/[최종] dict → PDF 바이트. 렌더러는 report_pdf.html_to_pdf_bytes 재사용(무수정)."""
    from pipeline.report_pdf import html_to_pdf_bytes, build_doc_no, _now_kst  # 지연 import
    gen = generated_at or _now_kst()
    html = build_coverage_html(analysis, gen)
    return await html_to_pdf_bytes(html, build_doc_no(gen))
