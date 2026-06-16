# BOHUMFIT-041 Q2 추가검사 Gemini 게이팅 완화·임상의사 프롬프트·가능성 출력 회귀(mock).
#  실제 Gemini 호출 불가 → genai.Client mock으로 게이팅/프롬프트/파싱/폴백 검증.
import asyncio
import json
import pathlib

import pipeline.ai_judgment as aij


class _FakeMsg:
    def __init__(self, text): self.text = text


class _FakeModels:
    def __init__(self, text, cap): self._t = text; self._cap = cap
    def generate_content(self, **kw): self._cap.update(kw); return _FakeMsg(self._t)


class _FakeClient:
    def __init__(self, text, cap): self.models = _FakeModels(text, cap)  # aio 없음 → to_thread 경로


def _run_with_mock(findings_json, raise_exc=False):
    cap = {}
    orig = aij.genai.Client
    class _BoomModels:
        def generate_content(self, **kw): raise RuntimeError("gemini down")
    class _BoomClient:
        def __init__(self, **kw): self.models = _BoomModels()
    if raise_exc:
        aij.genai.Client = lambda **kw: _BoomClient()
    else:
        aij.genai.Client = lambda **kw: _FakeClient(findings_json, cap)
    try:
        items = [{"code": "K29", "disease": "위염", "date": "2026-04-01", "hospital": "OO내과"}]
        out = asyncio.run(aij._call_q2_health_findings(items, "2026-06-15", "fake-key"))
        return out, cap
    finally:
        aij.genai.Client = orig


_HIGH = json.dumps({"findings": [{"disease_code": "K29", "possibility": "높음", "suspicion": "위내시경 재검"}]})
_NONE = json.dumps({"findings": [{"disease_code": "K29", "possibility": "해당없음", "suspicion": "없음"}]})
_LOW = json.dumps({"findings": [{"disease_code": "K29", "possibility": "낮음", "suspicion": "추적 위내시경 고려"}]})


# ── 가능성 높음 → 부착(화면 표시) ────────────────────────────────────────
def test_possibility_high_attached():
    out, _ = _run_with_mock(_HIGH)
    assert "K29" in out and out["K29"].startswith("[추가검사·재검사 가능성 높음]")


def test_possibility_low_attached():
    out, _ = _run_with_mock(_LOW)
    assert out.get("K29", "").startswith("[추가검사·재검사 가능성 낮음]")


# ── 해당없음 → 폴백(미부착) ──────────────────────────────────────────────
def test_possibility_none_fallback():
    out, _ = _run_with_mock(_NONE)
    assert out == {}


# ── Gemini 예외 → 폴백(빈 dict, 서비스 정상) ─────────────────────────────
def test_exception_fallback():
    out, _ = _run_with_mock(_HIGH, raise_exc=True)
    assert out == {}


# ── 프롬프트: 임상의사 역할 + 판단기준 + 가능성 스키마 ───────────────────
def test_prompt_clinician_role_and_criteria():
    _, cap = _run_with_mock(_HIGH)
    contents = cap.get("contents", "")
    cfg = cap.get("config")
    sysi = getattr(cfg, "system_instruction", "") or ""
    assert "임상의사" in sysi
    assert "추가검사" in contents and "재검사" in contents
    assert "보수적" in contents and "해당없음" in contents
    assert "possibility" in contents and "높음" in contents


# ── 결정성: 동일 입력 → 동일 출력 ────────────────────────────────────────
def test_determinism():
    a, _ = _run_with_mock(_HIGH)
    b, _ = _run_with_mock(_HIGH)
    assert a == b


# ── ★ 게이팅 완화: analyzer가 검사근거로 필터하지 않음 ───────────────────
def test_gate_relaxed_no_test_evidence_filter():
    import analyzer
    src = pathlib.Path(analyzer.__file__).read_text(encoding="utf-8-sig")
    assert "_suspicion_prompt_items = list(_q1_items + _q2_health_items)" in src
    # 검사근거로 prompt 항목을 거르던 구문이 사라졌는지
    assert "if (it.get(\"code\") or \"\").upper() in _test_evidence_codes" not in src


# ── ★ 038 가드 무회귀: result_builder의 AI=Q2 한정 가드 보존 ──────────────
def test_038_guard_intact():
    import pipeline.result_builder as rb
    src = pathlib.Path(rb.__file__).read_text(encoding="utf-8-sig")
    assert 'if source != "code" and q != "Q2":' in src
