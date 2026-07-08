"""BOHUMFIT-188 before/after coverage comparison and summary builders."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any

from .aggregator import aggregate_coverage_values
from .constants import GROUP13

STATUS_SUFFICIENT = "충분"
STATUS_SHORT = "부족"
STATUS_MISSING = "미가입"

_STATUS_RANK = {
    None: 0,
    "": 0,
    STATUS_MISSING: 1,
    STATUS_SHORT: 2,
    STATUS_SUFFICIENT: 3,
}
_IMPROVEMENT_FROM = {STATUS_SHORT, STATUS_MISSING}


def _contract_id(value: Any) -> str:
    return str(value).strip()


def _disposition(value: Any) -> str:
    raw = str(value or "keep").strip()
    lowered = raw.lower()
    if raw == "유지":
        return "keep"
    if raw == "해지":
        return "cancel"
    return lowered


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _paid_total(contract: dict) -> int | None:
    premium = _to_int(contract.get("monthly_premium"))
    months = _to_int(contract.get("pay_months"))
    if premium is None or months is None:
        return None
    return premium * months


def _gap_and_status(value: int | None, recommended: int | None) -> tuple[int | None, str | None]:
    if recommended is None:
        return None, None
    if value is None:
        return -recommended, STATUS_MISSING
    gap = value - recommended
    return gap, STATUS_SUFFICIENT if gap >= 0 else STATUS_SHORT


def _status_counts(rows: list[dict]) -> dict[str, int]:
    counts = {STATUS_SUFFICIENT: 0, STATUS_SHORT: 0, STATUS_MISSING: 0}
    for row in rows:
        status = row.get("status")
        if status in counts:
            counts[status] += 1
    return counts


def _group_key(group: str | None) -> int:
    return GROUP13.index(group) if group in GROUP13 else len(GROUP13)


def _sort_contracts(contracts: list[dict]) -> list[dict]:
    return sorted(
        contracts,
        key=lambda contract: (
            not bool(contract.get("insurer")),
            str(contract.get("insurer") or ""),
            str(contract.get("product") or ""),
            _contract_id(contract.get("idx")),
        ),
    )


def compare_before_after(before_final: dict, after_final: dict) -> dict:
    """Build side-by-side final diagnosis comparison and consulting summary."""
    before_premium = before_final.get("premium") or {}
    after_premium = after_final.get("premium") or {}
    before_paid = before_premium.get("paid_total")
    after_paid = after_premium.get("paid_total")
    before_monthly = before_premium.get("monthly_total") or 0
    after_monthly = after_premium.get("monthly_total") or 0

    before_rows = {
        (row.get("group12"), row.get("kb_name")): row
        for row in before_final.get("coverages", [])
    }
    after_rows = {
        (row.get("group12"), row.get("kb_name")): row
        for row in after_final.get("coverages", [])
    }
    keys = sorted(
        set(before_rows) | set(after_rows),
        key=lambda key: (_group_key(key[0]), key[1] or ""),
    )

    rows: list[dict] = []
    group_rollup: dict[str, dict] = {}
    improved_count = 0
    worsened_count = 0
    missing_to_sufficient = 0
    short_to_sufficient = 0

    for key in keys:
        before = before_rows.get(key, {})
        after = after_rows.get(key, {})
        group12, kb_name = key
        before_status = before.get("status")
        after_status = after.get("status")
        improved = before_status in _IMPROVEMENT_FROM and after_status == STATUS_SUFFICIENT
        worsened = _STATUS_RANK.get(after_status, 0) < _STATUS_RANK.get(before_status, 0)
        if improved:
            improved_count += 1
            if before_status == STATUS_MISSING:
                missing_to_sufficient += 1
            elif before_status == STATUS_SHORT:
                short_to_sufficient += 1
        if worsened:
            worsened_count += 1

        before_value = before.get("value")
        after_value = after.get("value")
        delta_value = (
            after_value - before_value
            if isinstance(before_value, (int, float)) and isinstance(after_value, (int, float))
            else None
        )
        row = {
            "group12": group12,
            "kb_name": kb_name,
            "recommended": after.get("recommended", before.get("recommended")),
            "before_value": before_value,
            "after_value": after_value,
            "before_gap": before.get("gap"),
            "after_gap": after.get("gap"),
            "before_status": before_status,
            "after_status": after_status,
            "status_change": f"{before_status or '-'} -> {after_status or '-'}",
            "delta_value": delta_value,
            "improved": improved,
            "worsened": worsened,
        }
        rows.append(row)

        if group12 not in group_rollup:
            group_rollup[group12] = {
                "group12": group12,
                "before_status_counts": {STATUS_SUFFICIENT: 0, STATUS_SHORT: 0, STATUS_MISSING: 0},
                "after_status_counts": {STATUS_SUFFICIENT: 0, STATUS_SHORT: 0, STATUS_MISSING: 0},
                "improved_count": 0,
                "worsened_count": 0,
                "missing_to_sufficient": 0,
                "short_to_sufficient": 0,
            }
        group = group_rollup[group12]
        if before_status in group["before_status_counts"]:
            group["before_status_counts"][before_status] += 1
        if after_status in group["after_status_counts"]:
            group["after_status_counts"][after_status] += 1
        if improved:
            group["improved_count"] += 1
        if worsened:
            group["worsened_count"] += 1
        if before_status == STATUS_MISSING and after_status == STATUS_SUFFICIENT:
            group["missing_to_sufficient"] += 1
        if before_status == STATUS_SHORT and after_status == STATUS_SUFFICIENT:
            group["short_to_sufficient"] += 1

    paid_delta = (
        after_paid - before_paid
        if isinstance(before_paid, (int, float)) and isinstance(after_paid, (int, float))
        else None
    )
    premium = {
        "before_monthly": before_monthly,
        "after_monthly": after_monthly,
        "delta_monthly": after_monthly - before_monthly,
        "before_paid_total": before_paid,
        "after_paid_total": after_paid,
        "delta_paid_total": paid_delta,
    }
    summary = {
        "improved_count": improved_count,
        "worsened_count": worsened_count,
        "missing_to_sufficient": missing_to_sufficient,
        "short_to_sufficient": short_to_sufficient,
        "before_status_counts": _status_counts(before_final.get("coverages", [])),
        "after_status_counts": _status_counts(after_final.get("coverages", [])),
        "by_group12": sorted(group_rollup.values(), key=lambda item: _group_key(item.get("group12"))),
    }
    improvements = []
    if improved_count:
        improvements.append({
            "level": "info",
            "message": f"부족·미가입에서 충분으로 개선된 담보 {improved_count}개",
        })
    if premium["delta_monthly"]:
        direction = "증가" if premium["delta_monthly"] > 0 else "감소"
        improvements.append({
            "level": "info",
            "message": f"월납 보험료 {abs(premium['delta_monthly']):,}원 {direction}",
        })
    cautions = []
    if worsened_count:
        cautions.append({
            "level": "warning",
            "message": f"컨설팅 후 상태가 낮아진 담보 {worsened_count}개",
        })

    return {
        "premium": premium,
        "coverages": rows,
        "summary": summary,
        "improvements": improvements,
        "cautions": cautions,
    }


def build_after_analysis(analysis: dict, plan: dict | None = None) -> dict:
    """Apply a session consulting plan and return analysis + after + comparison.

    This keeps the original [전] payload intact and recomputes [후] with the same
    sum/representative aggregation rule used by the KB before matrix.
    """
    plan = plan or {}
    warnings = list(analysis.get("warnings") or [])
    before = deepcopy(analysis.get("before") or {})
    before_final = deepcopy(analysis.get("final") or {})
    decisions = {
        _contract_id(item.get("contract_idx")): item
        for item in plan.get("existing", [])
        if item.get("contract_idx") is not None
    }
    source_contracts = before.get("contract_list") or before.get("companies") or []
    known_contracts = {_contract_id(contract.get("idx")) for contract in source_contracts}
    for contract_id in decisions:
        if contract_id not in known_contracts:
            warnings.append(f"알 수 없는 계약 번호 {contract_id} 결정은 제외했습니다.")

    kept_contract_ids: set[str] = set()
    after_companies: list[dict] = []
    paid_unknown = False
    for contract in source_contracts:
        contract_id = _contract_id(contract.get("idx"))
        decision = decisions.get(contract_id) or {}
        disposition = _disposition(decision.get("disposition"))
        if disposition == "cancel":
            continue
        if disposition != "keep":
            warnings.append(f"계약 {contract_id}의 알 수 없는 유지/해지 값은 유지로 처리했습니다.")
        updated = deepcopy(contract)
        updated["consulting_status"] = "유지"
        updated["paid_total"] = _paid_total(updated)
        kept_contract_ids.add(contract_id)
        after_companies.append(updated)

    proposal_contracts = []
    proposal_values: defaultdict[str, dict[str, int | None]] = defaultdict(dict)
    proposal_meta: dict[str, dict] = {}
    known_coverages = {row.get("kb_name") for row in before.get("coverages", [])}
    for seq, proposal in enumerate(plan.get("proposals", []), start=1):
        proposal_id = _contract_id(proposal.get("proposal_id") or f"P{seq}") or f"P{seq}"
        if not proposal_id.startswith("P"):
            proposal_id = f"P{seq}"
        monthly = _to_int(proposal.get("monthly_premium"))
        if monthly is None or monthly < 0:
            warnings.append(f"신규제안 {proposal_id}의 월보험료가 없어 제외했습니다.")
            continue
        pay_months = _to_int(proposal.get("pay_months"))
        paid_total = monthly * pay_months if pay_months is not None else None
        if paid_total is None:
            paid_unknown = True
            warnings.append(f"신규제안 {proposal_id}의 납입기간이 없어 총납입 증감은 표시하지 않습니다.")
        contract = {
            "idx": proposal_id,
            "insurer": proposal.get("insurer") or "신규제안",
            "product": proposal.get("product") or proposal_id,
            "contract_date": None,
            "pay_cycle": proposal.get("pay_cycle") or "월납",
            "pay_years": proposal.get("pay_years"),
            "pay_months": pay_months,
            "maturity": proposal.get("maturity"),
            "monthly_premium": monthly,
            "paid_total": paid_total,
            "remark": proposal.get("remark") or "신규가입 제안",
            "consulting_status": "신규제안",
            "is_proposal": True,
        }
        proposal_contracts.append(contract)
        for coverage in proposal.get("coverages", []):
            kb_name = coverage.get("kb_name")
            amount = _to_int(coverage.get("amount"))
            if amount is None or amount < 0:
                warnings.append(f"신규제안 {proposal_id}의 담보 {kb_name} 금액이 없어 제외했습니다.")
                continue
            if kb_name not in known_coverages:
                group12 = coverage.get("group12")
                agg = coverage.get("agg")
                if not group12 or not agg:
                    warnings.append(f"신규제안 {proposal_id}의 미매핑 담보 {kb_name or '-'}는 제외했습니다.")
                    continue
                proposal_meta.setdefault(
                    kb_name,
                    {
                        "kb_name": kb_name,
                        "kb_group": coverage.get("kb_group") or group12,
                        "group12": group12,
                        "agg": agg,
                    },
                )
            current = proposal_values[kb_name].get(proposal_id)
            proposal_values[kb_name][proposal_id] = amount if current is None else max(current, amount)

    after_companies = _sort_contracts(after_companies + proposal_contracts)
    after_coverages = []
    for row in before.get("coverages", []):
        kb_name = row.get("kb_name")
        by_company = {
            contract_id: amount
            for contract_id, amount in (row.get("by_company") or {}).items()
            if contract_id in kept_contract_ids
        }
        by_company.update(proposal_values.get(kb_name, {}))
        summary = aggregate_coverage_values(by_company, row.get("agg"))
        after_coverages.append({
            **deepcopy(row),
            "summary": summary,
            "by_company": by_company,
            "enrolled": any(value is not None for value in by_company.values()),
        })
    for kb_name, meta in sorted(proposal_meta.items(), key=lambda item: (_group_key(item[1].get("group12")), item[0])):
        by_company = proposal_values.get(kb_name, {})
        summary = aggregate_coverage_values(by_company, meta.get("agg"))
        after_coverages.append({
            **deepcopy(meta),
            "summary": summary,
            "by_company": dict(by_company),
            "enrolled": any(value is not None for value in by_company.values()),
        })

    paid_total = None if paid_unknown else sum((contract.get("paid_total") or 0) for contract in after_companies)
    after_before = {
        **before,
        "premium": {
            "monthly_total": sum((contract.get("monthly_premium") or 0) for contract in after_companies),
            "paid_total": paid_total,
            "currency": (before.get("premium") or {}).get("currency", "KRW"),
        },
        "companies": after_companies,
        "contract_list": after_companies,
        "coverages": after_coverages,
    }

    final_rows_by_name = {row.get("kb_name"): row for row in before_final.get("coverages", [])}
    after_final_rows = []
    rollup_counts = defaultdict(lambda: {STATUS_SUFFICIENT: 0, STATUS_SHORT: 0, STATUS_MISSING: 0})
    for coverage in after_coverages:
        base = final_rows_by_name.get(coverage.get("kb_name"), {})
        recommended = base.get("recommended")
        value = coverage.get("summary")
        gap, status = _gap_and_status(value, recommended)
        row = {
            "group12": coverage.get("group12"),
            "kb_name": coverage.get("kb_name"),
            "agg": coverage.get("agg"),
            "value": value,
            "recommended": recommended,
            "gap": gap,
            "status": status,
        }
        after_final_rows.append(row)
        if status in rollup_counts[coverage.get("group12")]:
            rollup_counts[coverage.get("group12")][status] += 1

    after_final = {
        "premium": after_before["premium"],
        "coverages": after_final_rows,
        "rollup_by_group12": [
            {"group12": group, "status_counts": dict(rollup_counts[group])}
            for group in GROUP13
        ],
    }
    comparison = compare_before_after(before_final, after_final)

    return {
        **deepcopy(analysis),
        "consulting_plan": deepcopy(plan),
        "after": {"before": after_before, "final": after_final},
        "comparison": comparison,
        "warnings": warnings,
    }


def ensure_comparison(analysis: dict) -> dict:
    """Return a comparison payload when analysis already contains after/final."""
    if analysis.get("comparison"):
        return analysis["comparison"]
    after = analysis.get("after") or {}
    after_final = after.get("final")
    if after_final:
        return compare_before_after(analysis.get("final") or {}, after_final)
    return {}
