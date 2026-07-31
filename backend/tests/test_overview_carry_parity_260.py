# -*- coding: utf-8 -*-
"""BOHUMFIT-260 — overview [후] 이월 서버측 골든(클라이언트 미러와 공유).

같은 골든 픽스처를 프런트 `coverageAfterDisplayCache.test.ts`가 대조한다(251 골든 선례).
규칙이 바뀌면 골든·양쪽 테스트를 함께 갱신한다. 익명 합성 — PII 0.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coverage.aggregator import OVERVIEW_CANCEL_WARNING
from coverage.compare import build_after_analysis

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "overview_carry_parity_260.json")


def _fixture() -> dict:
    with open(FIXTURE, encoding="utf-8") as handle:
        return json.load(handle)


def test_server_matches_overview_carry_golden():
    fixture = _fixture()
    for scenario in fixture["scenarios"]:
        analysis = json.loads(json.dumps(fixture["analysis"]))  # 시나리오 간 격리
        plan = {
            "existing": [{"contract_idx": idx, "disposition": "cancel"} for idx in scenario["cancel"]],
            "proposals": [],
        }
        result = build_after_analysis(analysis, plan)
        rows = {row["kb_name"]: row for row in result["after"]["before"]["coverages"]}
        for name, expected in scenario["expected"].items():
            row = rows[name]
            assert {k: v for k, v in (row.get("by_company") or {}).items()} == expected["by_company"], \
                f"{scenario['label']} / {name} by_company"
            assert row.get("summary") == expected["summary"], f"{scenario['label']} / {name} summary"
            assert bool(row.get("enrolled")) == expected["enrolled"], f"{scenario['label']} / {name} enrolled"
        messages = [c.get("message") for c in (result["comparison"].get("cautions") or [])]
        messages += list(result.get("warnings") or [])
        assert (OVERVIEW_CANCEL_WARNING in messages) is scenario["cancel_warning"], \
            f"{scenario['label']} / 해지 경고"


def test_golden_covers_attributed_and_unattributed_rows():
    """골든이 판정 분기를 모두 덮는지 — 귀속·미귀속·'?' 혼재·일반 행."""
    coverages = _fixture()["analysis"]["before"]["coverages"]
    kinds = {
        "attributed_overview": any(c.get("overview") and any(v is not None for v in c["by_company"].values())
                                   for c in coverages),
        "unattributed_overview": any(c.get("overview") and not c["by_company"] for c in coverages),
        "unknown_key": any("?" in (c.get("by_company") or {}) for c in coverages),
        "normal_row": any(not c.get("overview") for c in coverages),
    }
    assert all(kinds.values()), kinds
