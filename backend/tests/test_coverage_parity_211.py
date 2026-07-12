# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from coverage.compare import build_after_analysis


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPO_ROOT / "backend" / "tests" / "fixtures" / "coverage_after_parity_211.json"


def _load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _row_key(row: dict[str, Any]) -> str:
    return f"{row.get('group12') or ''}::{row.get('kb_name') or ''}"


def _normalize_company(company: dict[str, Any]) -> dict[str, Any]:
    return {
        "idx": company.get("idx"),
        "insurer": company.get("insurer"),
        "product": company.get("product"),
        "pay_months": company.get("pay_months"),
        "maturity": company.get("maturity"),
        "monthly_premium": company.get("monthly_premium"),
        "paid_total": company.get("paid_total"),
        "consulting_status": company.get("consulting_status"),
    }


def _normalize_coverage(coverage: dict[str, Any]) -> dict[str, Any]:
    return {
        "group12": coverage.get("group12"),
        "kb_name": coverage.get("kb_name"),
        "agg": coverage.get("agg"),
        "summary": coverage.get("summary"),
        "by_company": coverage.get("by_company"),
        "enrolled": coverage.get("enrolled"),
    }


def _normalize_final(coverage: dict[str, Any]) -> dict[str, Any]:
    return {
        "group12": coverage.get("group12"),
        "kb_name": coverage.get("kb_name"),
        "agg": coverage.get("agg"),
        "value": coverage.get("value"),
        "recommended": coverage.get("recommended"),
        "gap": coverage.get("gap"),
        "status": coverage.get("status"),
    }


def _normalize_comparison(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "group12": row.get("group12"),
        "kb_name": row.get("kb_name"),
        "recommended": row.get("recommended"),
        "before_value": row.get("before_value"),
        "after_value": row.get("after_value"),
        "before_gap": row.get("before_gap"),
        "after_gap": row.get("after_gap"),
        "before_status": row.get("before_status"),
        "after_status": row.get("after_status"),
        "status_change": row.get("status_change"),
        "delta_value": row.get("delta_value"),
        "improved": row.get("improved"),
        "worsened": row.get("worsened"),
    }


def _normalize_after_result(result: dict[str, Any]) -> dict[str, Any]:
    after_before = result["after"]["before"]
    return {
        "premium": result["comparison"]["premium"],
        "after_premium": after_before["premium"],
        "companies": [_normalize_company(company) for company in after_before.get("contract_list", [])],
        "coverages": [
            _normalize_coverage(coverage)
            for coverage in sorted(after_before.get("coverages", []), key=_row_key)
        ],
        "final_coverages": [
            _normalize_final(coverage)
            for coverage in sorted(result["after"]["final"].get("coverages", []), key=_row_key)
        ],
        "comparison_coverages": [
            _normalize_comparison(row)
            for row in sorted(result["comparison"].get("coverages", []), key=_row_key)
        ],
        "comparison_summary": result["comparison"]["summary"],
    }


def test_frontend_display_cache_matches_backend_after_analysis() -> None:
    fixture = _load_fixture()
    backend_result = build_after_analysis(fixture["analysis"], fixture["plan"])
    expected = _normalize_after_result(backend_result)

    assert expected["premium"] == {
        "before_monthly": 170000,
        "after_monthly": 150000,
        "delta_monthly": -20000,
        "before_paid_total": 20400000,
        "after_paid_total": 18000000,
        "delta_paid_total": -2400000,
    }
    final_by_name = {row["kb_name"]: row for row in expected["final_coverages"]}
    assert final_by_name["일반사망"]["value"] == 180000000
    assert final_by_name["암진단"]["status"] == "충분"
    assert final_by_name["자동차사고부상"]["value"] == 200000
    assert final_by_name["표적항암치료비"]["status"] is None

    npm = shutil.which("npm")
    if not npm:
        pytest.skip("npm is not available for frontend parity check")
    if not (REPO_ROOT / "node_modules" / "vitest").exists():
        pytest.skip("frontend dependencies are not installed")

    env = {
        **os.environ,
        "BOHUMFIT_PARITY_EXPECTED": json.dumps(expected, ensure_ascii=False),
    }
    completed = subprocess.run(
        [npm, "test", "--", "src/lib/coverageAfterDisplayCache.test.ts"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout
