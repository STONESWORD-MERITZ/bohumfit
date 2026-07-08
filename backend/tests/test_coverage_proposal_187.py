# -*- coding: utf-8 -*-
"""BOHUMFIT-187 consulting proposal regressions.

Synthetic fixtures only. No real contract PDF or personal data is stored here.
"""
from __future__ import annotations

from coverage.consulting import build_after_result


def _analysis() -> dict:
    return {
        "before": {
            "customer": {"name": "테스트", "age": 40, "sex": "남"},
            "premium": {"monthly_total": 100_000, "paid_total": 24_000_000, "currency": "KRW"},
            "companies": [
                {
                    "idx": 1,
                    "insurer": "기존A",
                    "product": "기존상품A",
                    "contract_date": "2020-01-01",
                    "pay_cycle": "월납",
                    "pay_years": 20,
                    "pay_months": 240,
                    "maturity": "100세",
                    "monthly_premium": 60_000,
                    "paid_total": 14_400_000,
                    "remark": None,
                },
                {
                    "idx": 2,
                    "insurer": "기존B",
                    "product": "기존상품B",
                    "contract_date": "2021-01-01",
                    "pay_cycle": "월납",
                    "pay_years": 20,
                    "pay_months": 240,
                    "maturity": "100세",
                    "monthly_premium": 40_000,
                    "paid_total": 9_600_000,
                    "remark": None,
                },
            ],
            "contract_list": [],
            "coverages": [
                {
                    "kb_name": "암진단",
                    "kb_group": "암",
                    "group12": "암",
                    "agg": "sum",
                    "summary": 30_000_000,
                    "by_company": {"1": 30_000_000},
                    "enrolled": True,
                },
                {
                    "kb_name": "상해수술비",
                    "kb_group": "수술",
                    "group12": "수술",
                    "agg": "rep",
                    "summary": None,
                    "by_company": {},
                    "enrolled": False,
                },
            ],
        },
        "final": {
            "premium": {"monthly_total": 100_000, "paid_total": 24_000_000, "currency": "KRW"},
            "coverages": [
                {
                    "group12": "암",
                    "kb_name": "암진단",
                    "agg": "sum",
                    "value": 30_000_000,
                    "recommended": 50_000_000,
                    "gap": -20_000_000,
                    "status": "부족",
                },
                {
                    "group12": "수술",
                    "kb_name": "상해수술비",
                    "agg": "rep",
                    "value": None,
                    "recommended": 2_000_000,
                    "gap": -2_000_000,
                    "status": "미가입",
                },
            ],
            "rollup_by_group12": [],
        },
        "warnings": [],
    }


def _row(final: dict, kb_name: str) -> dict:
    return next(row for row in final["coverages"] if row["kb_name"] == kb_name)


def test_proposal_adds_company_premium_and_paid_total():
    result = build_after_result(
        _analysis(),
        {
            "existing": [],
            "proposals": [
                {
                    "proposal_id": "proposal-1",
                    "insurer": "제안보험",
                    "product": "제안상품",
                    "monthly_premium": 20_000,
                    "pay_months": 240,
                    "coverages": [{"kb_name": "암진단", "amount": 20_000_000}],
                }
            ],
        },
    )

    after = result["after"]["before"]
    assert after["premium"]["monthly_total"] == 120_000
    assert after["premium"]["paid_total"] == 28_800_000
    proposal = after["companies"][-1]
    assert proposal["idx"] == "P1"
    assert proposal["is_proposal"] is True
    assert proposal["remark"] == "신규가입 제안"


def test_proposal_improves_low_and_missing_coverages():
    result = build_after_result(
        _analysis(),
        {
            "proposals": [
                {
                    "proposal_id": "proposal-1",
                    "insurer": "제안보험",
                    "product": "제안상품",
                    "monthly_premium": 30_000,
                    "pay_months": 240,
                    "coverages": [
                        {"kb_name": "암진단", "amount": 20_000_000},
                        {"kb_name": "상해수술비", "amount": 3_000_000},
                    ],
                }
            ]
        },
    )

    after_final = result["after"]["final"]
    assert _row(after_final, "암진단")["value"] == 50_000_000
    assert _row(after_final, "암진단")["status"] == "충분"
    assert _row(after_final, "상해수술비")["value"] == 3_000_000
    assert _row(after_final, "상해수술비")["status"] == "충분"


def test_existing_cancel_and_proposal_coexist():
    result = build_after_result(
        _analysis(),
        {
            "existing": [{"contract_idx": 2, "disposition": "해지"}],
            "proposals": [
                {
                    "proposal_id": "proposal-1",
                    "insurer": "제안보험",
                    "product": "제안상품",
                    "monthly_premium": 15_000,
                    "pay_months": 120,
                    "coverages": [{"kb_name": "암진단", "amount": 20_000_000}],
                }
            ],
        },
    )

    after = result["after"]["before"]
    assert [company["idx"] for company in after["companies"]] == [1, "P1"]
    assert after["premium"]["monthly_total"] == 75_000
    assert _row(result["after"]["final"], "암진단")["status"] == "충분"


def test_unknown_proposal_coverage_warns_and_is_ignored():
    result = build_after_result(
        _analysis(),
        {
            "proposals": [
                {
                    "proposal_id": "proposal-1",
                    "insurer": "제안보험",
                    "product": "제안상품",
                    "monthly_premium": 10_000,
                    "coverages": [{"kb_name": "미매핑담보", "amount": 1_000_000}],
                }
            ]
        },
    )

    assert any("미매핑담보" in warning for warning in result["warnings"])
    assert _row(result["after"]["final"], "암진단")["status"] == "부족"
