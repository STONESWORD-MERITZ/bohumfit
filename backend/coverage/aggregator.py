"""Aggregate KB coverage proposal rows into before/final report dictionaries."""
from __future__ import annotations

from collections import defaultdict

from .constants import AGG_SUM, EXTRA_LABEL_GROUP, GROUP13, GROUP_ETC, GROUP_EXCLUDED, KB_COVERAGES
from .schema import before_coverage, final_coverage


def _aggregate(by_company: dict, agg: str):
    vals = [v for v in by_company.values() if v is not None]
    if not vals:
        return None
    return sum(vals) if agg == AGG_SUM else max(vals)


def _paid(contract: dict):
    premium = contract.get("monthly_premium")
    months = contract.get("pay_months")
    return premium * months if premium is not None and months is not None else None


def _remark(note: dict | None):
    if not note:
        return None
    if note.get("kp_differs"):
        return f"계피상이(계약자 {note.get('contractor')}·피보험자 {note.get('insured')})"
    return "계피동일"


def _company_sort_key(contract: dict):
    premium = contract.get("monthly_premium")
    return (premium is None, -(premium or 0), contract.get("idx") or 9999)


def build_before(raw: dict) -> dict:
    contracts = raw.get("contracts", [])
    monthly_total = sum(c["monthly_premium"] for c in contracts if c.get("monthly_premium"))
    paid_total = sum((_paid(c) or 0) for c in contracts)
    notes = raw.get("notes", {})
    companies = sorted(contracts, key=_company_sort_key)
    companies = [
        {**c, "paid_total": _paid(c), "remark": _remark(notes.get(c.get("idx"))) or c.get("remark")}
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
        coverages.append(
            before_coverage(
                label,
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
        "premium": {"monthly_total": monthly_total, "paid_total": paid_total, "currency": "KRW"},
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
