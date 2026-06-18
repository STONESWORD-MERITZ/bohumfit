# BOHUMFIT-058 동적 AI 예산(남은시간 기반·최대 20초) 회귀 — 익명·합성 픽스처(실데이터 아님).
#
# 사양: AI 예산 = clamp(SERVER_DEADLINE - 경과 - 안전마진, 0, 상한).
#   · 파싱 빠름(경과 적음) → 상한(기본 20초) 풀 적용 → 041 Q2 주석 보존.
#   · 파싱 느림(남은시간 < 20) → 남은시간으로 수축.
#   · 남은시간 ≤ 0 → 0초(AI 우아하게 skip, 결정론 결과 정상·고지 누락 0·크래시 0).
#   · BOHUMFIT_AI_BUDGET_SECONDS 설정 시 그 값이 상한(override). 동적 clamp 는 항상 적용.
#   서버 300초·프런트 350초·분석 판정 로직은 무변경(이 태스크 범위 외).
import asyncio
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import analyzer
from analyzer import (
    SERVER_ANALYZE_DEADLINE_SECONDS,
    _MAX_AI_BUDGET_SECONDS,
    _AI_BUDGET_SAFETY_MARGIN,
    _ai_budget_ceiling,
    _dynamic_ai_budget,
)


class _FakePdfFile:
    def __init__(self, name: str = "fake.pdf"):
        self.name = name

    def read(self) -> bytes:
        return b""


def _basic_row(date_str: str, code: str, name: str) -> dict:
    return {
        "_ftype": "basic", "_fname": "fake.pdf",
        "진료시작일": date_str, "주상병코드": code, "주상병명": name,
        "병·의원": "OO의원", "입원/외래": "외래", "내원일수": "1", "진단과": "내과",
    }


def _mock_parse(monkeypatch, records):
    def fake_parse(uploaded, birthdate_pw: str) -> dict:
        return {"filename": getattr(uploaded, "name", "fake.pdf"),
                "records": records, "parse_errors": []}
    monkeypatch.setattr(analyzer, "parse_single_pdf", fake_parse)


def _clear_env(monkeypatch):
    monkeypatch.delenv("BOHUMFIT_AI_BUDGET_SECONDS", raising=False)


# ── ① 파싱이 빠를 때(경과 적음) → AI 예산 = 상한(20초) ──────────────────────
def test_fast_parse_uses_full_ceiling(monkeypatch):
    _clear_env(monkeypatch)
    # 경과 1초 → 가용 = 300 - 1 - 30 = 269 → min(20, 269) = 20.
    assert _dynamic_ai_budget(1.0) == _MAX_AI_BUDGET_SECONDS == 20


# ── ② 파싱이 느려 남은시간 < 20 → AI 예산 = 남은시간으로 수축 ────────────────
def test_slow_parse_shrinks_budget(monkeypatch):
    _clear_env(monkeypatch)
    # 경과 265초 → 가용 = 300 - 265 - 30 = 5 → min(20, 5) = 5.
    assert _dynamic_ai_budget(265.0) == 5
    # 경과 285초 → 가용 = 300 - 285 - 30 = -15 → 0 직전 경계.
    assert _dynamic_ai_budget(283.0) == 0  # 가용 -13 → 0


# ── ③ 남은시간 ≤ 0 → AI 예산 0(skip) ─────────────────────────────────────
def test_no_time_left_budget_zero(monkeypatch):
    _clear_env(monkeypatch)
    assert _dynamic_ai_budget(290.0) == 0      # 가용 -20 → 0
    assert _dynamic_ai_budget(float(SERVER_ANALYZE_DEADLINE_SECONDS)) == 0
    # 경과가 마진 직전(=deadline-margin)이면 정확히 0.
    assert _dynamic_ai_budget(SERVER_ANALYZE_DEADLINE_SECONDS - _AI_BUDGET_SAFETY_MARGIN) == 0


# ── ④ env(BOHUMFIT_AI_BUDGET_SECONDS) 설정 시 그 값이 상한(override) ─────────
def test_env_sets_ceiling_override(monkeypatch):
    monkeypatch.setenv("BOHUMFIT_AI_BUDGET_SECONDS", "8")
    assert _ai_budget_ceiling() == 8
    # 가용(269)이 충분해도 상한 8로 제한.
    assert _dynamic_ai_budget(1.0) == 8
    assert _dynamic_ai_budget(1.0, _ai_budget_ceiling()) == 8
    # env 상한이 커도 남은시간으로 한 번 더 clamp.
    monkeypatch.setenv("BOHUMFIT_AI_BUDGET_SECONDS", "60")
    assert _dynamic_ai_budget(285.0) == 0      # 가용 -15 → 0 (상한 60 무관)
    # env 미설정 → 기본 상한 20.
    _clear_env(monkeypatch)
    assert _ai_budget_ceiling() == _MAX_AI_BUDGET_SECONDS
    # env=0 → 상한 0 → 항상 skip(비활성화).
    monkeypatch.setenv("BOHUMFIT_AI_BUDGET_SECONDS", "0")
    assert _ai_budget_ceiling() == 0 and _dynamic_ai_budget(1.0) == 0
    # 비정상 입력 → 기본 상한 폴백.
    monkeypatch.setenv("BOHUMFIT_AI_BUDGET_SECONDS", "abc")
    assert _ai_budget_ceiling() == _MAX_AI_BUDGET_SECONDS


# ── ⑤ AI skip(남은시간 0)돼도 결정론 항목·고지 누락 0·크래시 0 ──────────────
def test_ai_skip_preserves_deterministic_result(monkeypatch):
    _clear_env(monkeypatch)
    records = [_basic_row("2026-04-01", "K297", "위염")]
    _mock_parse(monkeypatch, records)

    # 동적 예산이 0을 반환(남은시간 없음)하도록 강제 — 상한>0 경로(env 0 아님).
    monkeypatch.setattr(analyzer, "_dynamic_ai_budget", lambda *a, **k: 0)

    async def boom(*_args, **_kwargs):
        raise AssertionError("budget 0 이면 Gemini helper 를 호출하면 안 됨")

    monkeypatch.setattr(analyzer, "analyze_single_pdf", boom)
    monkeypatch.setattr(analyzer, "_call_medical_judgment", boom)
    monkeypatch.setattr(analyzer, "_call_q2_health_findings", boom)

    result = asyncio.run(analyzer.run_analysis(
        active_files=[_FakePdfFile()],
        product_type="건강체/표준체 (일반심사)",
        reference_date=date(2026, 6, 17),
        birthdate_pw="",
        api_key="fake",
    ))

    # 결정론 결과는 정상 반환(크래시 0). 남은시간 부족 안내 경고 포함, "비활성화" 아님.
    assert result["standard_reports"]
    assert any("시간이 촉박" in w for w in result["retry_warnings"])
    assert not any("비활성화" in w for w in result["retry_warnings"])


# ── ⑥ main.py 와 상수 공유(단일 소스) — 두 타임아웃 어긋남 방지 ──────────────
def test_main_shares_deadline_constant():
    import pytest
    try:
        import main
    except Exception as e:  # sandbox app-import 제약(예: 마운트 view) → Codex/Windows 권위
        pytest.skip(f"main import unavailable in this env: {e}")
    assert main.ANALYZE_TIMEOUT_SECONDS == SERVER_ANALYZE_DEADLINE_SECONDS == 300
