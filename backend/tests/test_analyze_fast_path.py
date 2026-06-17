import asyncio
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import analyzer


class _FakePdfFile:
    def __init__(self, records: list, name: str = "fake.pdf"):
        self.name = name
        self._records = records

    def read(self) -> bytes:
        return b""


def _basic_row(date_str: str, code: str, name: str) -> dict:
    return {
        "_ftype": "basic",
        "_fname": "fake.pdf",
        "진료시작일": date_str,
        "주상병코드": code,
        "주상병명": name,
        "병·의원": "OO의원",
        "입원/외래": "외래",
        "내원일수": "1",
        "진단과": "내과",
    }


def _mock_parse(monkeypatch, records):
    def fake_parse(uploaded, birthdate_pw: str) -> dict:
        return {
            "filename": getattr(uploaded, "name", "fake.pdf"),
            "records": records,
            "parse_errors": [],
        }

    monkeypatch.setattr(analyzer, "parse_single_pdf", fake_parse)


def test_run_analysis_does_not_call_pdf_level_gemini(monkeypatch):
    records = [_basic_row("2026-04-01", "K297", "위염")]
    _mock_parse(monkeypatch, records)
    monkeypatch.setenv("BOHUMFIT_AI_BUDGET_SECONDS", "1")

    async def boom_single(*_args, **_kwargs):
        raise AssertionError("PDF별 Gemini 전체 분석은 동기 분석 경로에서 호출되면 안 됨")

    async def fake_med(*_args, **_kwargs):
        return {"additional_tests": {}, "treatment_ongoing": {}}

    async def fake_q2(*_args, **_kwargs):
        return {"K29": "[추가검사·재검사 가능성 낮음] 위내시경 추적 확인"}

    monkeypatch.setattr(analyzer, "analyze_single_pdf", boom_single)
    monkeypatch.setattr(analyzer, "_call_medical_judgment", fake_med)
    monkeypatch.setattr(analyzer, "_call_q2_health_findings", fake_q2)

    result = asyncio.run(analyzer.run_analysis(
        active_files=[_FakePdfFile(records)],
        product_type="건강체/표준체 (일반심사)",
        reference_date=date(2026, 6, 17),
        birthdate_pw="",
        api_key="fake",
    ))

    assert result["record_counts"] == {"basic": 1}
    assert result["standard_reports"]


def test_ai_budget_zero_returns_deterministic_result(monkeypatch):
    records = [_basic_row("2026-04-01", "K297", "위염")]
    _mock_parse(monkeypatch, records)
    monkeypatch.setenv("BOHUMFIT_AI_BUDGET_SECONDS", "0")

    async def boom(*_args, **_kwargs):
        raise AssertionError("AI budget 0 should not call Gemini helpers")

    monkeypatch.setattr(analyzer, "analyze_single_pdf", boom)
    monkeypatch.setattr(analyzer, "_call_medical_judgment", boom)
    monkeypatch.setattr(analyzer, "_call_q2_health_findings", boom)

    result = asyncio.run(analyzer.run_analysis(
        active_files=[_FakePdfFile(records)],
        product_type="건강체/표준체 (일반심사)",
        reference_date=date(2026, 6, 17),
        birthdate_pw="",
        api_key="fake",
    ))

    assert result["standard_reports"]
    assert any("AI 보조 판단이 비활성화" in w for w in result["retry_warnings"])
