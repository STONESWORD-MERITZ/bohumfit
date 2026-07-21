"""Aggregate KB coverage proposal rows into before/final report dictionaries."""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date

from .constants import AGG_SUM, EXTRA_LABEL_GROUP, GROUP13, GROUP_ETC, GROUP_EXCLUDED, KB_COVERAGES
from .schema import before_coverage, final_coverage


def aggregate_coverage_values(by_company: dict, agg: str):
    vals = [v for v in by_company.values() if v is not None]
    if not vals:
        return None
    return sum(vals) if agg == AGG_SUM else max(vals)


def _aggregate(by_company: dict, agg: str):
    return aggregate_coverage_values(by_company, agg)


def _paid(contract: dict):
    premium = contract.get("monthly_premium")
    months = contract.get("pay_months")
    # BOHUMFIT-234: 일시납은 표기 금액이 1회 납입 총액 — 개월 수를 곱하지 않는다.
    if contract.get("pay_cycle") == "일시납":
        return premium
    return premium * months if premium is not None and months is not None else None


def _remark(note: dict | None):
    if not note:
        return None
    if note.get("kp_differs"):
        return f"계피상이(계약자 {note.get('contractor')}·피보험자 {note.get('insured')})"
    return "계피동일"


def _company_sort_key(contract: dict):
    # BOHUMFIT-236 B: 계약 번호 숫자 오름차순으로 통일 — KB 원본 번호 순서를 보존해
    # 산출물 대조를 쉽게 하고, 과거 보험사 가나다 + str(idx) 사전식("1,10,11,…,2") 정렬을 대체.
    idx = contract.get("idx")
    try:
        return (0, int(idx))
    except (TypeError, ValueError):
        return (1, 0)


_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def _pay_end_date(contract: dict) -> str | None:
    """납입 종료(예정)일 ISO 문자열 — contract_date + pay_months. 판별 불가 시 None."""
    match = _DATE_RE.match(str(contract.get("contract_date") or ""))
    months = contract.get("pay_months")
    if not match or not months:
        return None
    year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    total = (month - 1) + int(months)
    return f"{year + total // 12:04d}-{total % 12 + 1:02d}-{day:02d}"


def _is_paid_up(contract: dict, today_iso: str) -> bool:
    """BOHUMFIT-236 A: 납입완료 판별 — 일시납은 즉시 완료, 월납·연납은 납입기간 경과 시 완료.
    (234 실측: KB 원본 헤더의 월납 합계 = 납입 중 계약만 합산 — 부값 산식의 근거)"""
    if contract.get("pay_cycle") == "일시납":
        return True
    end = _pay_end_date(contract)
    return end is not None and end <= today_iso


def build_before(raw: dict, today: str | None = None) -> dict:
    contracts = raw.get("contracts", [])
    today_iso = today or date.today().isoformat()
    # BOHUMFIT-234 ⑥: 일시납 계약의 표기 금액은 월 보험료가 아니다 — 월납 합산에서 제외
    # (KB 원본 헤더 월납 합계와 정합 — 234 실사용 케이스 실측: 일시납 혼입 시 합계 왜곡).
    monthly_total = sum(
        c["monthly_premium"]
        for c in contracts
        if c.get("monthly_premium") and c.get("pay_cycle") != "일시납"
    )
    # BOHUMFIT-236 A: 병기 부값 — 납입완료 계약까지 제외한 합(KB 원본 헤더 산식과 일치).
    monthly_total_active = sum(
        c["monthly_premium"]
        for c in contracts
        if c.get("monthly_premium")
        and c.get("pay_cycle") != "일시납"
        and not _is_paid_up(c, today_iso)
    )
    paid_total = sum((_paid(c) or 0) for c in contracts)
    notes = raw.get("notes", {})
    companies = sorted(contracts, key=_company_sort_key)
    companies = [
        {
            **c,
            "paid_total": _paid(c),
            "paid_up": _is_paid_up(c, today_iso),
            "remark": _remark(notes.get(c.get("idx"))) or c.get("remark"),
        }
        for c in companies
    ]

    matrix = raw.get("matrix", {})
    coverages = []
    for kb_name, kb_group, group12, agg in KB_COVERAGES:
        if group12 == GROUP_EXCLUDED:
            continue
        row = matrix.get(kb_name)
        by_company = row["by_company"] if row else {}
        summary = _aggregate(by_company, agg)
        enrolled = any(v is not None for v in by_company.values())
        coverages.append(before_coverage(kb_name, kb_group, group12, agg, summary, by_company, enrolled))

    for label, extra in raw.get("extra", {}).items():
        by_company = extra.get("by_company", {})
        agg = extra.get("agg", AGG_SUM)
        group12 = EXTRA_LABEL_GROUP.get(label, GROUP_ETC)
        summary = _aggregate(by_company, agg)
        display_label = label
        # BOHUMFIT-237 C: N대수술비는 원문의 N을 병기 — 복수면 나열(정보 무손실 표기.
        # 최대값 단일 표기는 계약별 상이 정보를 잃어 나열을 대표 규칙으로 채택).
        n_values = extra.get("n_values") or []
        if label == "N대수술비" and n_values:
            display_label = f"N대수술비({'·'.join(str(n) for n in sorted(set(n_values)))}대)"
        coverages.append(
            before_coverage(
                display_label,
                group12,
                group12,
                agg,
                summary,
                by_company,
                any(value is not None for value in by_company.values()),
            )
        )

    return {
        "customer": raw.get("customer"),
        "premium": {
            "monthly_total": monthly_total,
            "monthly_total_active": monthly_total_active,
            "paid_total": paid_total,
            "currency": "KRW",
        },
        "companies": companies,
        "contract_list": companies,
        "coverages": coverages,
    }


def build_final(before: dict, diagnosis: dict) -> dict:
    coverages = []
    rollup_counts = defaultdict(lambda: {"충분": 0, "부족": 0, "미가입": 0})
    for coverage in before["coverages"]:
        if coverage.get("group12") == GROUP_EXCLUDED:
            continue
        diagnosis_row = diagnosis.get(coverage["kb_name"], {})
        status = diagnosis_row.get("status")
        coverages.append(
            final_coverage(
                coverage["group12"],
                coverage["kb_name"],
                coverage["agg"],
                coverage["summary"],
                diagnosis_row.get("recommended"),
                diagnosis_row.get("gap"),
                status,
            )
        )
        if status in rollup_counts[coverage["group12"]]:
            rollup_counts[coverage["group12"]][status] += 1
    rollup = [{"group12": group, "status_counts": dict(rollup_counts[group])} for group in GROUP13]
    return {"premium": before["premium"], "coverages": coverages, "rollup_by_group12": rollup}
