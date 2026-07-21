"""Consulting-plan transforms for BOHUMFIT coverage remodeling.

BOHUMFIT-190 keeps the existing-contract step deliberately small: a consulting
plan can only keep or cancel contracts, then the ordinary ``build_final``
diagnosis path is run again. Proposal contracts are handled by
``compare.build_after_analysis`` through ``build_after_result``.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .aggregator import aggregate_coverage_values, build_final

VALID_DISPOSITIONS = {"keep", "cancel", "유지", "해지"}
STATUS_ORDER = {"미가입": 0, "부족": 1, "충분": 2}


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _paid_total(company: dict) -> int | None:
    monthly = _as_int(company.get("monthly_premium"))
    months = _as_int(company.get("pay_months"))
    return monthly * months if monthly is not None and months is not None else None


def _contract_key(company: dict) -> str:
    return str(company.get("idx"))


def _normalize_decisions(plan: dict, warnings: list[str]) -> dict[str, dict]:
    decisions: dict[str, dict] = {}
    for raw in plan.get("existing") or []:
        idx = raw.get("contract_idx")
        if idx is None:
            warnings.append("contract_idx 없는 기존계약 결정은 무시했습니다.")
            continue
        key = str(idx)
        raw_disposition = str(raw.get("disposition") or "keep").strip()
        disposition = raw_disposition.lower()
        if raw_disposition == "유지":
            disposition = "keep"
        elif raw_disposition == "해지":
            disposition = "cancel"
        if disposition not in VALID_DISPOSITIONS:
            warnings.append(f"계약 {key}: disposition={disposition!r}은 지원하지 않아 유지로 처리했습니다.")
            disposition = "keep"
        decisions[key] = {
            "disposition": disposition,
            "reason": raw.get("reason"),
        }
    return decisions


def _company_sort_key(company: dict) -> tuple[bool, str, str, str]:
    return (
        not bool(company.get("insurer")),
        str(company.get("insurer") or ""),
        str(company.get("product") or ""),
        str(company.get("idx") or ""),
    )


def apply_consulting_plan(before: dict, plan: dict | None) -> dict:
    """Return a before-shaped payload after applying existing-contract decisions.

    Existing keep/cancel decisions are applied here, so [후] can keep the exact
    same aggregation and diagnosis path as [전].
    """
    plan = plan or {}
    warnings: list[str] = []
    decisions = _normalize_decisions(plan, warnings)
    source_companies = before.get("contract_list") or before.get("companies") or []
    known_contracts = {_contract_key(company) for company in source_companies}

    for key in decisions:
        if key not in known_contracts:
            warnings.append(f"계약 {key}은(는) [전] 분석 결과에 없어 무시했습니다.")

    kept_companies: list[dict] = []
    for company in source_companies:
        key = _contract_key(company)
        decision = decisions.get(key, {"disposition": "keep"})
        if decision.get("disposition") == "cancel":
            continue
        updated = deepcopy(company)
        updated["paid_total"] = _paid_total(updated)
        updated["consulting_status"] = "keep"
        updated["consulting_reason"] = decision.get("reason")
        kept_companies.append(updated)

    kept_keys = {_contract_key(company) for company in kept_companies}

    coverages: list[dict] = []
    for row in before.get("coverages", []):
        kb_name = row.get("kb_name")
        by_company = {
            str(key): value
            for key, value in (row.get("by_company") or {}).items()
            if str(key) in kept_keys and value is not None
        }

        updated = deepcopy(row)
        updated["by_company"] = by_company
        updated["summary"] = aggregate_coverage_values(by_company, row.get("agg"))
        updated["enrolled"] = any(value is not None for value in by_company.values())
        coverages.append(updated)

    # BOHUMFIT-234/236: 일시납 월납 합산 제외 + 납입완료 제외 부값 병기(build_before와 동일 규칙).
    monthly_total = sum(
        company.get("monthly_premium") or 0
        for company in kept_companies
        if company.get("pay_cycle") != "일시납"
    )
    monthly_total_active = sum(
        company.get("monthly_premium") or 0
        for company in kept_companies
        if company.get("pay_cycle") != "일시납" and not company.get("paid_up")
    )
    paid_values = [company.get("paid_total") for company in kept_companies if company.get("paid_total") is not None]
    paid_total = sum(paid_values) if paid_values else 0
    sorted_companies = sorted(kept_companies, key=_company_sort_key)
    return {
        "customer": deepcopy(before.get("customer")),
        "premium": {
            "monthly_total": monthly_total,
            "monthly_total_active": monthly_total_active,
            "paid_total": paid_total,
            "currency": "KRW",
        },
        "companies": sorted_companies,
        "contract_list": sorted_companies,
        "coverages": coverages,
        "warnings": warnings,
    }


def _diagnosis_from_final(final: dict | None) -> dict:
    diagnosis: dict[str, dict] = {}
    for row in (final or {}).get("coverages", []):
        name = row.get("kb_name")
        if not name:
            continue
        diagnosis[name] = {
            "recommended": row.get("recommended"),
            "gap": row.get("gap"),
            "status": row.get("status"),
        }
    return diagnosis


def _recalculate_diagnosis(after_before: dict, diagnosis: dict) -> dict:
    recalculated: dict[str, dict] = {}
    for row in after_before.get("coverages", []):
        name = row.get("kb_name")
        reference = diagnosis.get(name, {})
        recommended = reference.get("recommended")
        value = row.get("summary")
        if recommended is None:
            gap = None
            status = reference.get("status")
        elif value is None or value <= 0:
            gap = -recommended
            status = "미가입"
        else:
            gap = value - recommended
            status = "충분" if gap >= 0 else "부족"
        recalculated[name] = {
            "recommended": recommended,
            "gap": gap,
            "status": status,
        }
    return recalculated


def build_after(before: dict, plan: dict | None, diagnosis: dict | None = None) -> dict:
    """Build a BOHUMFIT-186 after payload from a before payload and plan."""
    base_diagnosis = diagnosis or {}
    after_before = apply_consulting_plan(before, plan)
    recalculated = _recalculate_diagnosis(after_before, base_diagnosis)
    after_final = build_final(after_before, recalculated)
    warnings = after_before.pop("warnings", [])
    return {"before": after_before, "final": after_final, "warnings": warnings}


def _status_rank(status: str | None) -> int:
    return STATUS_ORDER.get(status or "", -1)


def compare_before_after(before_final: dict, after_final: dict) -> dict:
    """Return small premium and coverage deltas for the UI."""
    before_premium = before_final.get("premium") or {}
    after_premium = after_final.get("premium") or {}
    before_rows = {row.get("kb_name"): row for row in before_final.get("coverages", []) if row.get("kb_name")}
    coverage_deltas = []
    for row in after_final.get("coverages", []):
        name = row.get("kb_name")
        before_row = before_rows.get(name, {})
        before_value = before_row.get("current")
        after_value = row.get("current")
        coverage_deltas.append(
            {
                "kb_name": name,
                "group12": row.get("group12"),
                "before_current": before_value,
                "after_current": after_value,
                "delta_current": (
                    after_value - before_value
                    if isinstance(before_value, (int, float)) and isinstance(after_value, (int, float))
                    else None
                ),
                "before_status": before_row.get("status"),
                "after_status": row.get("status"),
            }
        )
    before_paid = before_premium.get("paid_total")
    after_paid = after_premium.get("paid_total")
    return {
        "premium": {
            "before_monthly": before_premium.get("monthly_total") or 0,
            "after_monthly": after_premium.get("monthly_total") or 0,
            "delta_monthly": (after_premium.get("monthly_total") or 0) - (before_premium.get("monthly_total") or 0),
            "before_paid_total": before_paid,
            "after_paid_total": after_paid,
            "delta_paid_total": (
                after_paid - before_paid
                if isinstance(before_paid, (int, float)) and isinstance(after_paid, (int, float))
                else None
            ),
        },
        "coverages": coverage_deltas,
    }


def build_after_result(analysis: dict, plan: dict | None) -> dict:
    """Wrap the original analysis with the current after/comparison result."""
    from .compare import build_after_analysis

    consulting_plan = {"version": 1, "source": "coverage-remodel", "existing": [], "proposals": []}
    consulting_plan.update(plan or {})
    return build_after_analysis(analysis, consulting_plan)
