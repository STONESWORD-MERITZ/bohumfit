from __future__ import annotations

from coverage.consulting import build_after_result


SUM_COVERAGE = "상해사망"
REP_COVERAGE = "상해입원의료비"


def _analysis() -> dict:
    before = {
        "customer": {"name": None, "age": None, "sex": None},
        "premium": {"monthly_total": 150_000, "paid_total": 18_000_000, "currency": "KRW"},
        "companies": [
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
                "paid_total": 12_000_000,
                "remark": None,
            },
            {
                "idx": 2,
                "insurer": "B손보",
                "product": "해지후보",
                "contract_date": "2021-01-01",
                "pay_cycle": "월납",
                "pay_years": 10,
                "pay_months": 120,
                "maturity": "90세",
                "monthly_premium": 50_000,
                "paid_total": 6_000_000,
                "remark": None,
            },
        ],
        "coverages": [
            {
                "kb_name": SUM_COVERAGE,
                "kb_group": "사망",
                "group12": "사망",
                "agg": "sum",
                "summary": 300_000_000,
                "by_company": {"1": 100_000_000, "2": 200_000_000},
                "enrolled": True,
            },
            {
                "kb_name": REP_COVERAGE,
                "kb_group": "실손",
                "group12": "실손",
                "agg": "rep",
                "summary": 20_000_000,
                "by_company": {"1": 10_000_000, "2": 20_000_000},
                "enrolled": True,
            },
        ],
    }
    before["contract_list"] = before["companies"]
    final = {
        "premium": before["premium"],
        "coverages": [
            {
                "group12": "사망",
                "kb_name": SUM_COVERAGE,
                "agg": "sum",
                "value": 300_000_000,
                "recommended": 250_000_000,
                "gap": 50_000_000,
                "status": "충분",
            },
            {
                "group12": "실손",
                "kb_name": REP_COVERAGE,
                "agg": "rep",
                "value": 20_000_000,
                "recommended": 10_000_000,
                "gap": 10_000_000,
                "status": "충분",
            },
        ],
        "rollup_by_group12": [],
    }
    return {"before": before, "final": final, "warnings": []}


def _before_row(result: dict, kb_name: str) -> dict:
    return next(row for row in result["after"]["before"]["coverages"] if row["kb_name"] == kb_name)


def test_cancel_contract_removes_contract_premium_and_reaggregates_coverages() -> None:
    result = build_after_result(
        _analysis(),
        {"existing": [{"contract_idx": 2, "disposition": "cancel"}], "proposals": []},
    )

    after = result["after"]["before"]
    assert [company["idx"] for company in after["companies"]] == [1]
    assert after["premium"]["monthly_total"] == 100_000
    assert after["premium"]["paid_total"] == 12_000_000
    assert _before_row(result, SUM_COVERAGE)["summary"] == 100_000_000
    assert _before_row(result, REP_COVERAGE)["summary"] == 10_000_000


def test_hold_cancel_and_new_proposal_are_the_only_after_inputs() -> None:
    result = build_after_result(
        _analysis(),
        {
            "existing": [{"contract_idx": 2, "disposition": "해지"}],
            "proposals": [
                {
                    "proposal_id": "proposal-1",
                    "insurer": "제안보험",
                    "product": "제안상품",
                    "monthly_premium": 20_000,
                    "pay_months": 120,
                    "coverages": [{"kb_name": SUM_COVERAGE, "amount": 200_000_000}],
                }
            ],
        },
    )

    after = result["after"]["before"]
    assert [company["idx"] for company in after["companies"]] == [1, "P1"]
    assert after["premium"]["monthly_total"] == 120_000
    assert after["premium"]["paid_total"] == 14_400_000
    assert _before_row(result, SUM_COVERAGE)["summary"] == 300_000_000
    assert result["comparison"]["premium"]["delta_monthly"] == -30_000
    assert result["comparison"]["premium"]["delta_paid_total"] == -3_600_000


def test_legacy_adjustment_fields_do_not_change_after_result() -> None:
    result = build_after_result(
        _analysis(),
        {
            "existing": [
                {
                    "contract_idx": 1,
                    "disposition": "keep",
                    "adjusted_monthly_premium": 1,
                    "coverage_overrides": [{"kb_name": SUM_COVERAGE, "mode": "reduce", "amount": 1}],
                }
            ],
            "proposals": [],
        },
    )

    after = result["after"]["before"]
    assert after["premium"]["monthly_total"] == 150_000
    assert after["premium"]["paid_total"] == 18_000_000
    assert _before_row(result, SUM_COVERAGE)["summary"] == 300_000_000
    assert _before_row(result, REP_COVERAGE)["summary"] == 20_000_000
