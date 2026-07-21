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

from .amount import format_krw, format_krw_delta
from .compare import ensure_comparison
from .constants import GROUP13

EMERALD = "#084734"
EMERALD_SOFT = "#EEF6F1"
INK = "#0A0A0A"
INK_BODY = "#1E293B"
GRAY = "#6D747D"
AMBER = "#B45309"
AMBER_SOFT = "#FBEEDD"
LINE = "#E8E8E4"

def _fmt_krw(n) -> str:
    # BOHUMFIT-237 A: 보장금액 한글 단위 표기 공용 포맷터로 통일("1억 2,000만원").
    return format_krw(n)


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
    return format_krw_delta(n)


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
    logo_fallback = cover.get("ga_name") or cover.get("planner_name") or ""
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
    <p>① 표지 · FIT 보장분석</p>
    <h1>보장분석 리포트</h1>
  </div>
  <div class="cover-grid">
    <div class="ga-logo-slot">{_esc(logo_fallback)}</div>
    <div class="cover-fields">{rows}</div>
  </div>
  <p class="cover-note">고객 설명용 요약 리포트 · 실제 보장 및 지급 여부는 보험사 약관과 증권을 따릅니다.</p>
</section>
"""


def build_coverage_html(analysis: dict, generated_at: datetime | None = None) -> str:
    before = analysis.get("before", {}) or {}
    after = analysis.get("after") or {}
    after_before = after.get("before") or {}
    after_final = after.get("final") or {}
    comparison = ensure_comparison(analysis)
    customer = before.get("customer") or {}
    companies = before.get("contract_list") or before.get("companies", [])
    gen = generated_at.strftime("%Y-%m-%d") if generated_at else ""
    cover_page = _cover_html(analysis, gen)
    cover_payload = analysis.get("report_cover") if isinstance(analysis.get("report_cover"), dict) else {}
    mask_names = (customer.get("name"), cover_payload.get("customer_name") if cover_payload else None)
    plan = analysis.get("consulting_plan") if isinstance(analysis.get("consulting_plan"), dict) else {}
    canceled_ids = {
        str(item.get("contract_idx"))
        for item in plan.get("existing", [])
        if isinstance(item, dict) and item.get("disposition") == "cancel"
    }
    proposal_plan = [item for item in plan.get("proposals", []) if isinstance(item, dict)] if plan else []

    after_section = ""
    if after_before and after_final:
        after_prem = after_final.get("premium") or after_before.get("premium") or {}
        after_companies = after_before.get("contract_list") or after_before.get("companies", [])
        # BOHUMFIT-236 B: 헤더 라벨 "계약 N" 통일(회사명은 상단 계약표 참조).
        after_comp_name_head = "".join(
            f'<th class="num company-name">계약 {_esc(co.get("idx"))}</th>'
            for co in after_companies
        )
        after_comp_premium_head = "".join(
            f'<th class="num company-premium">{_won(co.get("monthly_premium"))}</th>'
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
        after_contract_rows = []
        for co in after_companies:
            after_contract_rows.append(
                "<tr>"
                f"<td>{_esc(co.get('idx'))}</td>"
                f"<td>{_esc(co.get('consulting_status') or '유지')}</td>"
                f"<td>{_esc(co.get('insurer') or '미제공')}</td>"
                f"<td class=\"nm\">{_esc(co.get('product') or '미제공')}</td>"
                f"<td>{_esc(_period_label(co))}</td>"
                f"<td>{_esc(co.get('maturity') or '미제공')}</td>"
                f"<td class=\"num\">{_esc(_premium_label(co.get('monthly_premium')))}</td>"
                "</tr>"
            )
        after_section = f"""
<section class="report-section">
<h2>⑤ 최종 전 VS 후 — 회사별 보장 세부</h2>
<div class="cards">
  <div class="card"><div class="k">후 월납 보험료</div><div class="v">{_won(after_prem.get('monthly_total'))}</div></div>
  <div class="card"><div class="k">후 총납입</div><div class="v">{_won(after_prem.get('paid_total'))}</div></div>
</div>
<table class="contract-list"><thead><tr><th>번호</th><th>구분</th><th>회사명</th><th>상품명</th><th>납입기간</th><th>만기</th><th class="num">월보험료</th></tr></thead>
<tbody>{''.join(after_contract_rows)}</tbody></table>
<table><thead>
<tr><th rowspan="2">대분류</th><th rowspan="2">담보</th><th rowspan="2" class="num">후 보장금액</th>{after_comp_name_head}</tr>
<tr>{after_comp_premium_head}</tr>
</thead>
<tbody>{''.join(after_rows)}</tbody></table>
</section>
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
                f'<td class="num {delta_cls}">{_fmt_delta_krw(delta)}</td></tr>'
            )
        if not group_rows:
            group_rows.append('<tr><td colspan="4" class="empty">대분류별 보장금액 변화가 없습니다.</td></tr>')
        compare_rows = []
        for row in comparison.get("coverages", []):
            delta = row.get("delta_value")
            delta_cls = "good" if isinstance(delta, (int, float)) and delta > 0 else "warn" if isinstance(delta, (int, float)) and delta < 0 else ""
            compare_rows.append(
                f'<tr><td class="grp">{_esc(row.get("group12"))}</td>'
                f'<td class="nm">{_esc(row.get("kb_name"))}</td>'
                f'<td class="num">{_fmt_krw(row.get("before_value"))}</td>'
                f'<td class="num strong">{_fmt_krw(row.get("after_value"))}</td>'
                f'<td class="num {delta_cls}">{_fmt_delta_krw(delta)}</td></tr>'
            )
        if not compare_rows:
            compare_rows.append('<tr><td colspan="5" class="empty">보장금액 변화가 큰 담보가 없습니다.</td></tr>')
        comparison_section = f"""
<section class="report-section">
<h2>④ 최종 전 VS 후 — 특약별 보장 비교</h2>
<h3>컨설팅 전 VS 후 요약</h3>
<div class="cards">
  <div class="card highlight"><div class="k">월납입보험료</div><div class="v">{_won(cp.get('before_monthly'))} → {_won(cp.get('after_monthly'))}</div><div class="delta {'good' if isinstance(delta_monthly, (int, float)) and delta_monthly < 0 else 'warn' if delta_monthly else ''}">{_delta_won(delta_monthly)}</div></div>
  <div class="card"><div class="k">총납입보험료</div><div class="v">{_won(cp.get('before_paid_total'))} → {_won(cp.get('after_paid_total'))}</div><div class="delta {'good' if isinstance(delta_paid, (int, float)) and delta_paid < 0 else 'warn' if delta_paid else ''}">{_delta_won(delta_paid)}</div></div>
</div>
<h3>대분류별 보장 변화</h3>
<table><thead><tr><th>대분류</th><th class="num">전 보장금액</th><th class="num">후 보장금액</th><th class="num">증감</th></tr></thead>
<tbody>{''.join(group_rows)}</tbody></table>
<h3>특약별 보장금액 비교</h3>
<table><thead><tr><th>대분류</th><th>담보</th><th class="num">전 보장금액</th><th class="num">후 보장금액</th><th class="num">증감</th></tr></thead>
<tbody>{''.join(compare_rows)}</tbody></table>
</section>
"""
    contract_rows = []
    for co in companies:
        is_cancelled = str(co.get("idx")) in canceled_ids
        status = "해지" if is_cancelled else "유지"
        row_class = ' class="cancelled"' if is_cancelled else ""
        # BOHUMFIT-236 A: 납입완료 배지 — 금액 표기는 유지하고 배지로만 구분.
        paid_up_chip = '<span class="status-chip paid-bg">납입완료</span> ' if co.get("paid_up") else ""
        contract_rows.append(
            f"<tr{row_class}>"
            f"<td>{_esc(co.get('idx'))}</td>"
            f"<td><span class=\"status-chip {'warn-bg' if is_cancelled else 'good-bg'}\">{status}</span></td>"
            f"<td>{_esc(co.get('insurer') or '미제공')}</td>"
            f"<td class=\"nm\">{_esc(co.get('product') or '미제공')}</td>"
            f"<td>{_esc(_period_label(co))}</td>"
            f"<td>{_esc(co.get('maturity') or '미제공')}</td>"
            f"<td class=\"num\">{paid_up_chip}{_esc(_premium_label(co.get('monthly_premium')))}</td>"
            f"<td>{_esc(_mask_known_names(co.get('remark'), *mask_names))}</td>"
            "</tr>"
        )
    # BOHUMFIT-236 A: ② 월납 합계 병기(주값=전체, 부값=납입완료 제외 — KB 원본 헤더 산식).
    before_premium = before.get("premium") or {}
    monthly_total = before_premium.get("monthly_total")
    monthly_active = before_premium.get("monthly_total_active")
    premium_note = ""
    if isinstance(monthly_total, (int, float)):
        premium_note = f"월납 합계 {int(monthly_total):,}원"
        if isinstance(monthly_active, (int, float)) and monthly_active != monthly_total:
            premium_note += f" <small>(납입완료 제외 시 {int(monthly_active):,}원)</small>"
        premium_note = f'<p class="premium-note">{premium_note}</p>'

    proposal_rows = []
    for index, proposal in enumerate(proposal_plan, start=1):
        coverages = proposal.get("coverages") or []
        coverage_label = ", ".join(
            f"{_esc(item.get('kb_name'))} {_fmt_krw(item.get('amount'))}"
            for item in coverages
            if isinstance(item, dict) and item.get("kb_name")
        )
        proposal_rows.append(
            "<tr>"
            f"<td>P{index}</td>"
            f"<td>{_esc(proposal.get('insurer') or '신규제안')}</td>"
            f"<td class=\"nm\">{_esc(proposal.get('product') or '상품명 미입력')}</td>"
            f"<td class=\"num\">{_esc(_premium_label(proposal.get('monthly_premium')))}</td>"
            f"<td>{_esc(proposal.get('maturity') or '-')}</td>"
            f"<td class=\"nm\">{coverage_label or '-'}</td>"
            "</tr>"
        )
    if not proposal_rows:
        proposal_rows.append('<tr><td colspan="6" class="empty">신규 제안이 없습니다.</td></tr>')
    proposal_section = f"""
<section class="report-section">
<h2>③ 신규가입 제안서</h2>
<div class="proposal-slot">신규 가입제안서 PDF 파싱 결과 · 핵심 보장금액 보완 가능</div>
<table class="contract-list"><thead><tr><th>번호</th><th>보험사</th><th>상품명</th><th class="num">월보험료</th><th>만기</th><th>핵심 보장금액</th></tr></thead>
<tbody>{''.join(proposal_rows)}</tbody></table>
</section>
"""

    cust = ""
    if customer.get("name"):
        cust = f'{_esc(_mask_name(customer.get("name")))}' + (f' ({_esc(customer.get("age"))}세)' if customer.get("age") else "")

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ font-family: 'Pretendard','Noto Sans KR','Noto Sans CJK KR','Malgun Gothic',sans-serif; color: {INK_BODY}; font-size: 10pt; line-height: 1.5; word-break: keep-all; }}
.cover-page {{ min-height: 248mm; page-break-after: always; display: flex; flex-direction: column; justify-content: space-between; padding: 18mm 18mm 16mm; background: #fff; }}
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
.report-section {{ margin-top: 18px; padding-top: 14px; border-top: 2px solid {LINE}; }}
.report-section h2 {{ margin-top: 0; }}
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
th.company-premium {{ background: {EMERALD_SOFT}; color: {EMERALD}; font-size: 8pt; }}
td.grp {{ color: {GRAY}; font-size: 8pt; }}
td.nm {{ color: {INK}; font-weight: 600; }}
td.num {{ text-align: right; }}
td.strong {{ font-weight: 800; color: {INK}; }}
td.st {{ text-align: center; }}
.badge {{ display: inline-block; border-radius: 10px; padding: 1px 8px; font-size: 8pt; font-weight: 700; }}
.good {{ color: {EMERALD}; font-weight: 800; text-align: center; }}
.warn {{ color: {AMBER}; font-weight: 800; text-align: center; }}
.empty {{ text-align: center; color: {GRAY}; }}
.cancelled td {{ color: {GRAY}; text-decoration: line-through; }}
.status-chip {{ display: inline-block; border-radius: 10px; padding: 1px 8px; font-size: 8pt; font-weight: 800; }}
.good-bg {{ color: {EMERALD}; background: {EMERALD_SOFT}; }}
.warn-bg {{ color: {AMBER}; background: {AMBER_SOFT}; }}
.proposal-slot {{ border: 1px dashed {EMERALD}; border-radius: 8px; background: {EMERALD_SOFT}; color: {EMERALD}; padding: 8px 10px; margin-bottom: 8px; font-size: 8.5pt; font-weight: 800; text-align: center; }}
.notes {{ margin-top: 8px; font-size: 8pt; color: {GRAY}; }}
.notes li {{ list-style: none; margin: 1px 0; }}
.contract-list th, .contract-list td {{ font-size: 8.3pt; }}
/* BOHUMFIT-236 B: 헤더 줄바꿈 불일치 해소 — 헤더 nowrap + 셀 세로 중앙 통일. */
th {{ white-space: nowrap; vertical-align: middle; }}
td {{ vertical-align: middle; }}
.contract-list td {{ text-align: center; }}
.contract-list td:first-child {{ white-space: nowrap; }}
.contract-list td.nm {{ text-align: left; }}
.paid-bg {{ color: {GRAY}; background: {LINE}; }}
.premium-note {{ margin: 2px 0 6px; font-size: 9.5pt; font-weight: 800; color: {INK}; }}
.premium-note small {{ color: {GRAY}; font-weight: 700; font-size: 8.5pt; }}
.disclaimer {{ margin-top: 16px; font-size: 7.5pt; color: {GRAY}; line-height: 1.5; }}
</style></head><body>
{cover_page}
<div class="head">
  <div class="brand"><span class="logo-mark">ㅍ</span><span class="wordmark">BohumFit<small>보험핏 · 보장분석 리모델링</small></span></div>
  <div class="head-meta">{('고객 ' + cust + '<br>') if cust else ''}작성일 {gen}</div>
</div>
<h1>보장분석 리모델링표</h1>

<section class="report-section">
<h2>② 컨설팅 전 계약 — 유지/해지</h2>
{premium_note}
<table class="contract-list"><thead><tr><th>번호</th><th>처리</th><th>회사명</th><th>상품명</th><th>납입기간</th><th>만기</th><th class="num">월보험료</th><th>비고</th></tr></thead>
<tbody>{''.join(contract_rows)}</tbody></table>
</section>

{proposal_section}
{comparison_section}
{after_section}

<p class="disclaimer">본 리모델링표는 업로드한 KB 신정원 보장분석 제안서를 기준으로 정리한 참고용 자료입니다. 실제 보장 내용·보험금 지급 여부는 각 보험사 약관과 증권을 따르며, 본 자료는 보험 모집·중개·상품추천·가입권유를 목적으로 하지 않습니다.</p>
</body></html>"""


async def generate_coverage_pdf(analysis: dict, generated_at: datetime | None = None) -> bytes:
    """[전]/[최종] dict → PDF 바이트. 렌더러는 report_pdf.html_to_pdf_bytes 재사용(무수정)."""
    from pipeline.report_pdf import html_to_pdf_bytes, build_doc_no, _now_kst  # 지연 import
    gen = generated_at or _now_kst()
    html = build_coverage_html(analysis, gen)
    return await html_to_pdf_bytes(html, build_doc_no(gen))
