from __future__ import annotations

from copy import deepcopy

from coverage.aggregator import build_before, build_final
from coverage.consulting import apply_consulting_plan, build_after, build_after_result


SUM_COVERAGE = "상해사망"
SUM_COVERAGE_2 = "일반암"
REP_COVERAGE = "상해입원의료비"


def _analysis() -> dict:
    raw = {
        "customer": {"name": None, "age": None, "sex": None},
        "contracts": [
            {
                "idx": 1,
                "insurer": "A손보",
                "product": "기존계약A",
                "contract_date": "2020-01-01",
                "pay_cycle": "월납",
                "pay_years": 10,
                "pay_months": 120,
                "maturity": "90세",
                "monthly_premium": 100_000,
            },
            {
                "idx": 2,
                "insurer": "B손보",
                "product": "기존계약B",
                "contract_date": "2021-01-01",
                "pay_cycle": "월납",
                "pay_years": 10,
                "pay_months": 120,
                "maturity": "90세",
                "monthly_premium": 50_000,
            },
        ],
        "notes": {},
        "matrix": {
            SUM_COVERAGE: {"by_company": {"1": 100_000_000, "2": 200_000_000}},
            SUM_COVERAGE_2: {"by_company": {"1": 50_000_000, "2": 50_000_000}},
            REP_COVERAGE: {"by_company": {"1": 10_000_000, "2": 20_000_000}},
        },
        "extra": {},
    }
    before = build_before(raw)
    diagnosis = {
        SUM_COVERAGE: {"recommended": 250_000_000, "gap": 50_000_000, "status": "충분"},
        SUM_COVERAGE_2: {"recommended": 100_000_000, "gap": 0, "status": "충분"},
        REP_COVERAGE: {"recommended": 10_000_000, "gap": 10_000_000, "status": "충분"},
    }
    return {"before": before, "final": build_final(before, diagnosis), "warnings": []}


def _coverage(rows: list[dict], name: str) -> dict:
    return next(row for row in rows if row["kb_name"] == name)


def _diagnosis(analysis: dict) -> dict:
    return {row["kb_name"]: row for row in analysis["final"]["coverages"]}


def test_cancel_contract_excludes_premium_and_coverages_and_recalculates_status() -> None:
    analysis = _analysis()
    result = build_after(
        analysis["before"],
        {"version": 1, "source": "coverage-remodel", "existing": [{"contract_idx": 2, "disposition": "cancel"}]},
        _diagnosis(analysis),
    )

    assert result["before"]["premium"]["monthly_total"] == 100_000
    assert result["before"]["premium"]["paid_total"] == 12_000_000
    assert [company["idx"] for company in result["before"]["companies"]] == [1]
    assert _coverage(result["before"]["coverages"], SUM_COVERAGE)["summary"] == 100_000_000
    assert _coverage(result["final"]["coverages"], SUM_COVERAGE)["gap"] == -150_000_000
    assert _coverage(result["final"]["coverages"], SUM_COVERAGE)["status"] == "부족"


def test_keep_plan_preserves_premium_and_coverages_without_mutating_before() -> None:
    analysis = _analysis()
    original = deepcopy(analysis["before"])

    after = apply_consulting_plan(
        analysis["before"],
        {
            "version": 1,
            "source": "coverage-remodel",
            "existing": [{"contract_idx": 1, "disposition": "keep"}],
        },
    )

    assert after["premium"] == analysis["before"]["premium"]
    assert _coverage(after["coverages"], SUM_COVERAGE)["summary"] == 300_000_000
    assert _coverage(after["coverages"], REP_COVERAGE)["summary"] == 20_000_000
    assert analysis["before"] == original


def test_empty_plan_keeps_before_shape_and_build_after_result_wraps_current_result() -> None:
    analysis = _analysis()
    result = build_after_result(analysis, {"version": 1, "source": "coverage-remodel", "existing": [], "proposals": []})

    assert result["after"]["before"]["premium"] == analysis["before"]["premium"]
    assert _coverage(result["after"]["before"]["coverages"], SUM_COVERAGE)["summary"] == 300_000_000
    assert result["consulting_plan"]["version"] == 1
    assert result["comparison"]["premium"]["delta_monthly"] == 0


def test_unknown_contract_warns_and_lower_level_helper_ignores_proposals() -> None:
    analysis = _analysis()
    after = apply_consulting_plan(
        analysis["before"],
        {
            "version": 1,
            "source": "coverage-remodel",
            "existing": [{"contract_idx": 99, "disposition": "cancel"}],
            "proposals": [{"proposal_id": "proposal-1", "monthly_premium": 10_000}],
        },
    )

    assert any("계약 99" in warning for warning in after["warnings"])
    assert after["premium"]["monthly_total"] == analysis["before"]["premium"]["monthly_total"]
    assert all(not str(company["idx"]).startswith("P") for company in after["companies"])
