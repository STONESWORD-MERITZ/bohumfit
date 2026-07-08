"""BOHUMFIT-181: 리모델링 보장분석표 PDF 생성 (FIT v1.1 브랜드, 보장분석 전용).

179/179b [전]/[최종] 데이터(dict) → 자체 완결 HTML → 헤드리스 Chromium(PDF).
- PDF 렌더러는 pipeline/report_pdf.html_to_pdf_bytes 재사용(무수정 import).
- 고지의무 리포트 템플릿(157)과 별개 HTML(표 구조 상이).
- 구 브랜드색 미사용, 에메랄드(#084734)·잉크(#0A0A0A)만.
※ PII: 생성물은 응답 스트림 전용, 서버 미저장.
"""
from __future__ import annotations

import html as _html
from datetime import datetime

from .compare import ensure_comparison
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


def _mask_known_names(text: str | None, *names: str | None) -> str:
    result = str(text or "")
    for name in names:
        raw = "".join(str(name or "").split())
        if raw:
            result = result.replace(raw, _mask_name(raw))
    return result


def _delta_won(n) -> str:
    if n is None:
        return "-"
    if n == 0:
        return "변동 없음"
    direction = "절감" if n < 0 else "증가"
    return f"{abs(int(n)):,}원 {direction}"


def _fmt_delta_krw(n) -> str:
    if n is None:
        return "-"
    if n == 0:
        return "0"
    return ("+" if n > 0 else "−") + _fmt_krw(abs(n))


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


def _cover_html(analysis: dict, generated_date: str) -> str:
    cover = analysis.get("report_cover") or {}
    if not isinstance(cover, dict):
        cover = {}
    customer_name = _mask_name(cover.get("customer_name"))
    fields = [
        ("고객명", customer_name),
        ("보험나이", cover.get("insurance_age")),
        ("상령일", cover.get("age_change_date")),
        ("소속(GA)", cover.get("ga_name")),
        ("설계사명", cover.get("planner_name")),
        ("작성일자", cover.get("written_date") or generated_date),
    ]
    rows = "".join(
        f'<div class="cover-field"><span>{_esc(label)}</span><strong>{_esc(value)}</strong></div>'
        for label, value in fields
        if value
    )
    return f"""
<section class="cover-page">
  <div class="cover-brand">
    <span class="cover-logo">ㅍ</span>
    <span class="cover-word">BohumFit<small>보험핏</small></span>
  </div>
  <div class="cover-title">
    <p>FIT 보장분석</p>
    <h1>보장분석 리포트</h1>
  </div>
  <div class="cover-grid">
    <div class="ga-logo-slot">GA LOGO</div>
    <div class="cover-fields">{rows}</div>
  </div>
  <p class="cover-note">고객 설명용 요약 리포트 · 실제 보장 및 지급 여부는 보험사 약관과 증권을 따릅니다.</p>
</section>
"""


def build_coverage_html(analysis: dict, generated_at: datetime | None = None) -> str:
    before = analysis.get("before", {}) or {}
    final = analysis.get("final", {}) or {}
    after = analysis.get("after") or {}
    after_before = after.get("before") or {}
    after_final = after.get("final") or {}
    comparison = ensure_comparison(analysis)
    prem = final.get("premium") or before.get("premium") or {}
    customer = before.get("customer") or {}
    companies = before.get("contract_list") or before.get("companies", [])
    gen = generated_at.strftime("%Y-%m-%d") if generated_at else ""
    cover_page = _cover_html(analysis, gen)
    cover_payload = analysis.get("report_cover") if isinstance(analysis.get("report_cover"), dict) else {}
    mask_names = (customer.get("name"), cover_payload.get("customer_name") if cover_payload else None)

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

    after_section = ""
    if after_before and after_final:
        after_prem = after_final.get("premium") or after_before.get("premium") or {}
        after_final_rows = []
        for c in sorted(after_final.get("coverages", []), key=lambda row: _grp_key(row.get("group12", ""))):
            st = c.get("status")
            color, bg = _STATUS.get(st, (GRAY, GRAY_SOFT))
            gap = c.get("gap")
            gap_txt = "-" if gap is None else (("+" if gap > 0 else "−" if gap < 0 else "") + _fmt_krw(abs(gap)))
            gap_color = AMBER if (isinstance(gap, (int, float)) and gap < 0) else EMERALD if (isinstance(gap, (int, float)) and gap > 0) else GRAY
            after_final_rows.append(
                f'<tr><td class="grp">{_esc(c.get("group12"))}</td>'
                f'<td class="nm">{_esc(c.get("kb_name"))}</td>'
                f'<td class="num">{_fmt_krw(c.get("recommended"))}</td>'
                f'<td class="num strong">{_fmt_krw(c.get("value"))}</td>'
                f'<td class="num" style="color:{gap_color}">{gap_txt}</td>'
                f'<td class="st"><span class="badge" style="color:{color};background:{bg}">{_esc(st) or "-"}</span></td></tr>'
            )
        after_companies = after_before.get("contract_list") or after_before.get("companies", [])
        after_comp_head = "".join(
            f'<th class="num">{_esc(co.get("insurer") or "계약")} {_esc(co.get("idx"))}<br><span class="sub">{_won(co.get("monthly_premium"))}</span></th>'
            for co in after_companies
        )
        after_rows = []
        for c in sorted(after_before.get("coverages", []), key=lambda row: _grp_key(row.get("group12", ""))):
            by = c.get("by_company", {})
            cells = "".join(f'<td class="num">{_fmt_krw(by.get(str(co.get("idx"))))}</td>' for co in after_companies)
            after_rows.append(
                f'<tr><td class="grp">{_esc(c.get("group12"))}</td>'
                f'<td class="nm">{_esc(c.get("kb_name"))}</td>'
                f'<td class="num strong">{_fmt_krw(c.get("summary"))}</td>{cells}</tr>'
            )
        after_section = f"""
<h2>컨설팅 후 보장진단</h2>
<div class="cards">
  <div class="card"><div class="k">후 월납 보험료</div><div class="v">{_won(after_prem.get('monthly_total'))}</div></div>
  <div class="card"><div class="k">후 총납입</div><div class="v">{_won(after_prem.get('paid_total'))}</div></div>
</div>
<table><thead><tr><th>대분류</th><th>담보</th><th class="num">권장</th><th class="num">가입</th><th class="num">과부족</th><th>준비</th></tr></thead>
<tbody>{''.join(after_final_rows)}</tbody></table>
<h2>회사별 세부 (후)</h2>
<table><thead><tr><th>대분류</th><th>담보</th><th class="num">합산/대표</th>{after_comp_head}</tr></thead>
<tbody>{''.join(after_rows)}</tbody></table>
"""

    comparison_section = ""
    if comparison:
        cp = comparison.get("premium") or {}
        cs = comparison.get("summary") or {}
        delta_monthly = cp.get("delta_monthly")
        delta_paid = cp.get("delta_paid_total")
        group_rows = []
        for group in _group_value_summary(comparison):
            delta = group.get("delta_value")
            delta_cls = "good" if isinstance(delta, (int, float)) and delta > 0 else "warn" if isinstance(delta, (int, float)) and delta < 0 else ""
            group_rows.append(
                f'<tr><td class="grp">{_esc(group.get("group12"))}</td>'
                f'<td class="num">{_fmt_krw(group.get("before_value"))}</td>'
                f'<td class="num strong">{_fmt_krw(group.get("after_value"))}</td>'
                f'<td class="num {delta_cls}">{_fmt_delta_krw(delta)}</td>'
                f'<td class="num">{int(group.get("improved_count") or 0)}개</td></tr>'
            )
        if not group_rows:
            group_rows.append('<tr><td colspan="5" class="empty">대분류별 확대 변화가 없습니다.</td></tr>')
        compare_rows = []
        for row in comparison.get("coverages", []):
            if not (row.get("improved") or row.get("worsened")):
                continue
            cls = "good" if row.get("improved") else "warn"
            compare_rows.append(
                f'<tr><td class="grp">{_esc(row.get("group12"))}</td>'
                f'<td class="nm">{_esc(row.get("kb_name"))}</td>'
                f'<td class="num">{_fmt_krw(row.get("before_value"))}</td>'
                f'<td class="num strong">{_fmt_krw(row.get("after_value"))}</td>'
                f'<td class="{cls}">{_esc(row.get("status_change"))}</td></tr>'
            )
        if not compare_rows:
            compare_rows.append('<tr><td colspan="5" class="empty">상태 변화가 큰 담보가 없습니다.</td></tr>')
        comparison_section = f"""
<h2>컨설팅 전 VS 후 요약</h2>
<div class="cards">
  <div class="card highlight"><div class="k">월납입보험료</div><div class="v">{_won(cp.get('before_monthly'))} → {_won(cp.get('after_monthly'))}</div><div class="delta {'good' if isinstance(delta_monthly, (int, float)) and delta_monthly < 0 else 'warn' if delta_monthly else ''}">{_delta_won(delta_monthly)}</div></div>
  <div class="card"><div class="k">총납입보험료</div><div class="v">{_won(cp.get('before_paid_total'))} → {_won(cp.get('after_paid_total'))}</div><div class="delta {'good' if isinstance(delta_paid, (int, float)) and delta_paid < 0 else 'warn' if delta_paid else ''}">{_delta_won(delta_paid)}</div></div>
  <div class="card"><div class="k">부족·미가입 → 충분</div><div class="v">{int(cs.get('improved_count') or 0)}개</div></div>
</div>
<h3>대분류별 보장 변화</h3>
<table><thead><tr><th>대분류</th><th class="num">전 보장금액</th><th class="num">후 보장금액</th><th class="num">증감</th><th class="num">개선</th></tr></thead>
<tbody>{''.join(group_rows)}</tbody></table>
<h3>개선 담보</h3>
<table><thead><tr><th>대분류</th><th>담보</th><th class="num">전</th><th class="num">후</th><th>상태 변화</th></tr></thead>
<tbody>{''.join(compare_rows)}</tbody></table>
"""
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
            f"<td>{_esc(_mask_known_names(co.get('remark'), *mask_names))}</td>"
            "</tr>"
        )

    cust = ""
    if customer.get("name"):
        cust = f'{_esc(_mask_name(customer.get("name")))}' + (f' ({_esc(customer.get("age"))}세)' if customer.get("age") else "")

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ font-family: 'Pretendard','Noto Sans KR','Noto Sans CJK KR','Malgun Gothic',sans-serif; color: {INK_BODY}; font-size: 10pt; line-height: 1.5; word-break: keep-all; }}
.cover-page {{ min-height: 270mm; page-break-after: always; display: flex; flex-direction: column; justify-content: space-between; padding: 20mm 18mm 18mm; background: #fff; }}
.cover-brand {{ display: flex; align-items: center; gap: 10px; }}
.cover-logo {{ display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px; background: {EMERALD}; color: #fff; border-radius: 8px; font-weight: 900; font-size: 19pt; }}
.cover-word {{ font-size: 19pt; font-weight: 900; color: {INK}; }}
.cover-word small {{ display: block; font-size: 8pt; color: {GRAY}; letter-spacing: 1.5px; }}
.cover-title p {{ color: {EMERALD}; font-weight: 800; font-size: 10pt; margin-bottom: 6px; }}
.cover-title h1 {{ font-size: 34pt; line-height: 1.15; color: {INK}; margin: 0; }}
.cover-grid {{ display: grid; grid-template-columns: 120px 1fr; gap: 24px; align-items: start; margin-top: 26mm; }}
.ga-logo-slot {{ height: 74px; border: 1px dashed {LINE}; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: {GRAY}; font-size: 8pt; font-weight: 800; letter-spacing: 1.4px; }}
.cover-fields {{ border-top: 2px solid {EMERALD}; }}
.cover-field {{ display: flex; justify-content: space-between; gap: 24px; border-bottom: 1px solid {LINE}; padding: 9px 0; }}
.cover-field span {{ color: {GRAY}; font-size: 9pt; font-weight: 700; }}
.cover-field strong {{ color: {INK}; font-size: 11pt; }}
.cover-note {{ color: {GRAY}; font-size: 8pt; }}
.head {{ display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 2px solid {EMERALD}; padding-bottom: 10px; margin-bottom: 16px; }}
.brand {{ display: flex; align-items: center; gap: 8px; }}
.logo-mark {{ display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px; background: {EMERALD}; color: #fff; border-radius: 7px; font-weight: 800; font-size: 15pt; }}
.wordmark {{ font-size: 17pt; font-weight: 800; color: {INK}; letter-spacing: .2px; }}
.wordmark small {{ display: block; font-size: 8pt; font-weight: 700; color: {GRAY}; letter-spacing: 1.2px; }}
.head-meta {{ text-align: right; font-size: 8.5pt; color: {GRAY}; line-height: 1.6; }}
h1 {{ font-size: 14pt; color: {INK}; margin: 4px 0 12px; }}
h2 {{ font-size: 11.5pt; color: {EMERALD}; margin: 18px 0 8px; }}
h3 {{ font-size: 9.5pt; color: {INK}; margin: 12px 0 6px; }}
.cards {{ display: flex; gap: 10px; margin-bottom: 8px; }}
.card {{ flex: 1; border: 1px solid {LINE}; border-radius: 8px; padding: 8px 12px; }}
.card.highlight {{ border-color: {EMERALD}; background: {EMERALD_SOFT}; }}
.card .k {{ font-size: 8.5pt; color: {GRAY}; }}
.card .v {{ font-size: 13pt; font-weight: 800; color: {INK}; margin-top: 2px; }}
.card .delta {{ margin-top: 2px; font-size: 8.5pt; font-weight: 800; color: {GRAY}; }}
.card .delta.good {{ color: {EMERALD}; }}
.card .delta.warn {{ color: {AMBER}; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 4px; }}
th, td {{ border: 1px solid {LINE}; padding: 4px 6px; font-size: 9pt; }}
th {{ background: {EMERALD}; color: #fff; font-weight: 700; }}
td.grp {{ color: {GRAY}; font-size: 8pt; }}
td.nm {{ color: {INK}; font-weight: 600; }}
td.num {{ text-align: right; }}
td.strong {{ font-weight: 800; color: {INK}; }}
td.st {{ text-align: center; }}
.badge {{ display: inline-block; border-radius: 10px; padding: 1px 8px; font-size: 8pt; font-weight: 700; }}
.good {{ color: {EMERALD}; font-weight: 800; text-align: center; }}
.warn {{ color: {AMBER}; font-weight: 800; text-align: center; }}
.empty {{ text-align: center; color: {GRAY}; }}
.notes {{ margin-top: 8px; font-size: 8pt; color: {GRAY}; }}
.notes li {{ list-style: none; margin: 1px 0; }}
.contract-list th, .contract-list td {{ font-size: 8.3pt; }}
.contract-list td {{ text-align: center; }}
.contract-list td.nm {{ text-align: left; }}
.disclaimer {{ margin-top: 16px; font-size: 7.5pt; color: {GRAY}; line-height: 1.5; }}
</style></head><body>
{cover_page}
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

{after_section}
{comparison_section}

<p class="disclaimer">본 리모델링표는 업로드한 KB 신정원 보장분석 제안서를 기준으로 정리한 참고용 자료입니다. 실제 보장 내용·보험금 지급 여부는 각 보험사 약관과 증권을 따르며, 본 자료는 보험 모집·중개·상품추천·가입권유를 목적으로 하지 않습니다.</p>
</body></html>"""


async def generate_coverage_pdf(analysis: dict, generated_at: datetime | None = None) -> bytes:
    """[전]/[최종] dict → PDF 바이트. 렌더러는 report_pdf.html_to_pdf_bytes 재사용(무수정)."""
    from pipeline.report_pdf import html_to_pdf_bytes, build_doc_no, _now_kst  # 지연 import
    gen = generated_at or _now_kst()
    html = build_coverage_html(analysis, gen)
    return await html_to_pdf_bytes(html, build_doc_no(gen))
