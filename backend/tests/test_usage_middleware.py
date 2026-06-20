# BOHUMFIT-069/072 구독·사용량·무료체험 게이트 회귀 — Supabase admin을 가짜로 주입.
#
# /api/analyze: internal 무제한, 활성 구독은 플랜 한도(basic 30·pro 100), 미구독은 이번 달 무료
#   체험 5회까지 통과·초과 시 402. Supabase 미설정 → 게이트 비활성(무료 동작). main 의존
#   (slowapi/fastapi/supabase) → 미설치 시 자동 skip(Codex/Windows 권위).
import asyncio
import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("slowapi")
pytest.importorskip("fastapi")
pytest.importorskip("supabase")


# ── 가짜 Supabase 빌더(.eq 필터 반영) ─────────────────────────────────────────
class _Resp:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class _Query:
    def __init__(self, admin, name):
        self._admin = admin
        self._name = name
        self._insert = None
        self._filters = []

    def select(self, *a, **k): return self
    def eq(self, column, value):
        self._filters.append((column, value))
        return self
    def gte(self, *a, **k): return self
    def lte(self, *a, **k): return self
    def single(self): return self

    def insert(self, payload):
        self._insert = payload
        return self

    def execute(self):
        if self._insert is not None:
            self._admin.inserted.append((self._name, self._insert))
            return _Resp([{"id": "x"}])
        r = self._admin.responses.get(self._name)
        if isinstance(r, Exception):
            raise r
        if isinstance(r, _Resp) and isinstance(r.data, dict):
            for column, value in self._filters:
                if column in r.data and r.data.get(column) != value:
                    return _Resp(None)
        return r if r is not None else _Resp(None)


class _FakeAdmin:
    def __init__(self, responses):
        self.responses = responses
        self.inserted = []

    def table(self, name):
        return _Query(self, name)


def _load_main(monkeypatch):
    monkeypatch.setenv("SERVICE_ENV", "production")
    import main
    importlib.reload(main)
    return main


def _patch_admin(monkeypatch, main, admin):
    monkeypatch.setattr(main, "_get_supabase_admin", lambda: admin)


from fastapi import HTTPException  # noqa: E402

PERIODS = {"current_period_start": "2026-06-01T00:00:00Z", "current_period_end": "2026-06-30T23:59:59Z"}


# ── ① internal → 무제한 ──────────────────────────────────────────────────────
def test_internal_user_unlimited(monkeypatch):
    main = _load_main(monkeypatch)
    _patch_admin(monkeypatch, main, _FakeAdmin({"profiles": _Resp({"role": "internal"})}))
    ctx = asyncio.run(main._enforce_subscription("u1"))
    assert ctx["is_internal"] is True and ctx["enabled"] is True


# ── ② 미구독 + 무료체험 한도 내 → 통과(plan=trial) ───────────────────────────
def test_trial_under_limit_passes(monkeypatch):
    main = _load_main(monkeypatch)
    _patch_admin(monkeypatch, main, _FakeAdmin({
        "profiles": _Resp({"role": "user"}),
        "subscriptions": _Resp(None),
        "usage_logs": _Resp([], count=2),
    }))
    ctx = asyncio.run(main._enforce_subscription("u2"))
    assert ctx["enabled"] is True and ctx["is_internal"] is False and ctx["plan"] == "trial"


# ── ③ 미구독 + 무료체험 5회 소진 → 402 ───────────────────────────────────────
def test_trial_exhausted_402(monkeypatch):
    main = _load_main(monkeypatch)
    _patch_admin(monkeypatch, main, _FakeAdmin({
        "profiles": _Resp({"role": "user"}),
        "subscriptions": _Resp(None),
        "usage_logs": _Resp([], count=5),
    }))
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main._enforce_subscription("u3"))
    assert ei.value.status_code == 402 and "체험" in ei.value.detail


# ── ③' inactive 구독도 체험 경로(소진 시 402) ────────────────────────────────
def test_inactive_subscription_falls_to_trial(monkeypatch):
    main = _load_main(monkeypatch)
    _patch_admin(monkeypatch, main, _FakeAdmin({
        "profiles": _Resp({"role": "user"}),
        "subscriptions": _Resp({"status": "inactive", "plan": "basic", **PERIODS}),
        "usage_logs": _Resp([], count=5),
    }))
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main._enforce_subscription("u3i"))
    assert ei.value.status_code == 402


# ── ④ 활성 베이직 30회 초과 → 429 ───────────────────────────────────────────
def test_active_basic_over_limit_429(monkeypatch):
    main = _load_main(monkeypatch)
    _patch_admin(monkeypatch, main, _FakeAdmin({
        "profiles": _Resp({"role": "user"}),
        "subscriptions": _Resp({"status": "active", "plan": "basic", **PERIODS}),
        "usage_logs": _Resp([], count=30),
    }))
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main._enforce_subscription("u4"))
    assert ei.value.status_code == 429 and "30" in ei.value.detail


# ── ④' 활성 프로 → 30회는 통과(한도 100), 100회 초과 → 429 ───────────────────
def test_active_pro_limit_100(monkeypatch):
    main = _load_main(monkeypatch)
    _patch_admin(monkeypatch, main, _FakeAdmin({
        "profiles": _Resp({"role": "user"}),
        "subscriptions": _Resp({"status": "active", "plan": "pro", **PERIODS}),
        "usage_logs": _Resp([], count=30),
    }))
    ctx = asyncio.run(main._enforce_subscription("u4p"))
    assert ctx["plan"] == "pro" and ctx["enabled"] is True


def test_active_pro_over_100_429(monkeypatch):
    main = _load_main(monkeypatch)
    _patch_admin(monkeypatch, main, _FakeAdmin({
        "profiles": _Resp({"role": "user"}),
        "subscriptions": _Resp({"status": "active", "plan": "pro", **PERIODS}),
        "usage_logs": _Resp([], count=100),
    }))
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main._enforce_subscription("u4p2"))
    assert ei.value.status_code == 429 and "100" in ei.value.detail


# ── ⑤ 활성 베이직 한도 내 → 통과 + 차감 ─────────────────────────────────────
def test_active_under_limit_passes_and_logs(monkeypatch):
    main = _load_main(monkeypatch)
    admin = _FakeAdmin({
        "profiles": _Resp({"role": "user"}),
        "subscriptions": _Resp({"status": "active", "plan": "basic", **PERIODS}),
        "usage_logs": _Resp([], count=5),
    })
    _patch_admin(monkeypatch, main, admin)
    ctx = asyncio.run(main._enforce_subscription("u5"))
    assert ctx["enabled"] is True and ctx["plan"] == "basic"
    assert ctx["period_start"] == PERIODS["current_period_start"]
    asyncio.run(main._log_usage("u5", ctx))
    assert admin.inserted and admin.inserted[0][0] == "usage_logs" and admin.inserted[0][1]["user_id"] == "u5"


# ── ⑥ Supabase 미설정 → 게이트 비활성 ───────────────────────────────────────
def test_disabled_when_no_supabase(monkeypatch):
    main = _load_main(monkeypatch)
    monkeypatch.setattr(main, "_get_supabase_admin", lambda: None)
    ctx = asyncio.run(main._enforce_subscription("u6"))
    assert ctx["enabled"] is False and ctx["is_internal"] is True
    asyncio.run(main._log_usage("u6", ctx))


# ── ⑦ internal ctx는 차감 안 함 ─────────────────────────────────────────────
def test_internal_not_logged(monkeypatch):
    main = _load_main(monkeypatch)
    admin = _FakeAdmin({})
    _patch_admin(monkeypatch, main, admin)
    asyncio.run(main._log_usage("u7", {"is_internal": True, "enabled": True}))
    assert admin.inserted == []


# ── ⑧ trial ctx 차감 적재(미구독 무료체험도 사용량 기록) ─────────────────────
def test_trial_usage_logged(monkeypatch):
    main = _load_main(monkeypatch)
    admin = _FakeAdmin({})
    _patch_admin(monkeypatch, main, admin)
    asyncio.run(main._log_usage("u8", {"is_internal": False, "enabled": True,
                                       "period_start": "2026-06-01T00:00:00+00:00",
                                       "period_end": "2026-07-01T00:00:00+00:00"}))
    assert admin.inserted and admin.inserted[0][0] == "usage_logs"
