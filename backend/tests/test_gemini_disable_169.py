"""BOHUMFIT-169: Q2 소견용 Gemini 호출 플래그(ENABLE_Q2_AI_JUDGMENT) — 기본 off.

- (a) 플래그 off(기본) → Gemini(genai.Client) 미호출, 빈 dict('의심 없음') 반환.
- (b) 플래그 off → 항목이 있어도 빈 dict (168 이후 결과와 동일).
- (c) 플래그 on  → 기존 Gemini 경로 정상(mock).
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pipeline.ai_judgment as aij  # noqa: E402

_ITEMS = [{"code": "K29", "disease": "위염", "date": "2026-04-01", "hospital": "OO내과"}]


def _set_flag(val):
    if val is None:
        os.environ.pop("ENABLE_Q2_AI_JUDGMENT", None)
    else:
        os.environ["ENABLE_Q2_AI_JUDGMENT"] = val


def test_a_flag_default_off_no_gemini_call():
    """(a) 플래그 미설정(기본 off) → genai.Client 미호출, 빈 dict."""
    _set_flag(None)
    orig = aij.genai.Client
    called = {"n": 0}

    def _boom(**kw):
        called["n"] += 1
        raise AssertionError("플래그 off인데 genai.Client가 호출됨")

    aij.genai.Client = _boom
    try:
        out = asyncio.run(aij._call_q2_health_findings(_ITEMS, "2026-06-15", "fake-key"))
    finally:
        aij.genai.Client = orig
    assert out == {}
    assert called["n"] == 0


def test_b_flag_off_returns_empty_even_with_items():
    """(b) 플래그 off → 항목이 있어도 '의심 없음'(빈 dict) — 168 이후 결과와 동일."""
    _set_flag("false")
    try:
        out = asyncio.run(aij._call_q2_health_findings(_ITEMS, "2026-06-15", "fake-key"))
    finally:
        _set_flag(None)
    assert out == {}


def test_c_flag_on_uses_gemini_path():
    """(c) 플래그 on → 기존 Gemini 경로 정상(mock), 소견 파싱 부착."""
    _set_flag("true")
    orig = aij.genai.Client
    _high = json.dumps({"findings": [{"disease_code": "K29", "possibility": "높음", "suspicion": "위내시경 재검"}]})

    class _Models:
        def generate_content(self, **kw):
            class _R:
                text = _high
            return _R()

    class _Client:
        def __init__(self, **kw):
            self.models = _Models()

    aij.genai.Client = lambda **kw: _Client()
    try:
        out = asyncio.run(aij._call_q2_health_findings(_ITEMS, "2026-06-15", "fake-key"))
    finally:
        aij.genai.Client = orig
        _set_flag(None)
    assert "K29" in out and out["K29"].startswith("[추가검사·재검사 가능성 높음]")


def test_d_flag_parsing():
    """플래그 파싱: 1/true/yes/on = 활성, 그 외/미설정 = 비활성(기본 off)."""
    try:
        for v in ("1", "true", "TRUE", "yes", "on"):
            _set_flag(v)
            assert aij._q2_ai_judgment_enabled() is True, v
        for v in ("0", "false", "no", "off", ""):
            _set_flag(v)
            assert aij._q2_ai_judgment_enabled() is False, v
    finally:
        _set_flag(None)
    assert aij._q2_ai_judgment_enabled() is False
