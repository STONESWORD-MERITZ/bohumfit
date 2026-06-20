# BOHUMFIT-069 구독·사용량 게이트 회귀 — Supabase admin 클라이언트를 가짜로 주입.
#
# /api/analyze: internal(profiles.role) 무제한, 미구독 402, 월 30회 초과 429, 한도 내 통과+차감.
#   Supabase 미설정/패키지 없음 → 게이트 비활성(기존 무료 동작 유지). main 의존(slowapi/fastapi/
#   supabase) → 미설치 시 자동 skip(Codex/Windows 권위).
import asyncio
import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("slowapi")
pytest.importorskip("fastapi")
pytest.importorskip("supabase")


# ── 가짜 Supabase 빌더 ────────────────────────────────────────────────────────
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


# ── ① internal 사용자 → 무제한 통과(구독/사용량 미조회) ──────────────────────
def test_internal_user_unlimited(monkeypatch):
    main = _load_main(monkeypatch)
    admin = _FakeAdmin({"profiles": _Resp({"role": "internal"})})
    _patch_admin(monkeypatch, main, admin)
    ctx = asyncio.run(main._enforce_subscription("u1"))
    assert ctx["is_internal"] is True and ctx["enabled"] is True


# ── ② 활성 구독 없음 → 402 ───────────────────────────────────────────────────
def test_no_active_subscription_402(monkeypatch):
    main = _load_main(monkeypatch)
    admin = _FakeAdmin({"profiles": _Resp({"role": "user"}), "subscriptions": _Resp(None)})
    _patch_admin(monkeypatch, main, admin)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main._enforce_subscription("u2"))
    assert ei.value.status_code == 402


def test_inactive_subscription_402(monkeypatch):
    main = _load_main(monkeypatch)
    admin = _FakeAdmin({
        "profiles": _Resp({"role": "user"}),
        "subscriptions": _Resp({"status": "inactive", **PERIODS}),
    })
    _patch_admin(monkeypatch, main, admin)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main._enforce_subscription("u2i"))
    assert ei.value.status_code == 402


# ── ②' 구독 조회 예외(.single() 0행)도 402로 안전 처리 ───────────────────────
def test_subscription_query_error_402(monkeypatch):
    main = _load_main(monkeypatch)
    admin = _FakeAdmin({"profiles": _Resp({"role": "user"}), "subscriptions": RuntimeError("no rows")})
    _patch_admin(monkeypatch, main, admin)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main._enforce_subscription("u2b"))
    assert ei.value.status_code == 402


# ── ③ 월 30회 초과 → 429 ─────────────────────────────────────────────────────
def test_over_limit_429(monkeypatch):
    main = _load_main(monkeypatch)
    admin = _FakeAdmin({
        "profiles": _Resp({"role": "user"}),
        "subscriptions": _Resp({"status": "active", **PERIODS}),
        "usage_logs": _Resp([], count=30),
    })
    _patch_admin(monkeypatch, main, admin)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main._enforce_subscription("u3"))
    assert ei.value.status_code == 429


# ── ④ 한도 내 → 통과 + 차감(usage_logs insert) ──────────────────────────────
def test_under_limit_passes_and_logs(monkeypatch):
    main = _load_main(monkeypatch)
    admin = _FakeAdmin({
        "profiles": _Resp({"role": "user"}),
        "subscriptions": _Resp({"status": "active", **PERIODS}),
        "usage_logs": _Resp([], count=5),
    })
    _patch_admin(monkeypatch, main, admin)
    ctx = asyncio.run(main._enforce_subscription("u4"))
    assert ctx["enabled"] is True and ctx["is_internal"] is False
    assert ctx["period_start"] == PERIODS["current_period_start"]
    asyncio.run(main._log_usage("u4", ctx))
    assert admin.inserted and admin.inserted[0][0] == "usage_logs"
    assert admin.inserted[0][1]["user_id"] == "u4"


# ── ⑤ Supabase 미설정(admin None) → 게이트 비활성(기존 무료 동작 유지) ───────
def test_disabled_when_no_supabase(monkeypatch):
    main = _load_main(monkeypatch)
    monkeypatch.setattr(main, "_get_supabase_admin", lambda: None)
    ctx = asyncio.run(main._enforce_subscription("u5"))
    assert ctx["enabled"] is False and ctx["is_internal"] is True   # bypass
    # 비활성 ctx로 _log_usage 호출해도 insert 안 함(크래시 0).
    asyncio.run(main._log_usage("u5", ctx))


# ── ⑥ internal ctx는 차감 안 함 ─────────────────────────────────────────────
def test_internal_not_logged(monkeypatch):
    main = _load_main(monkeypatch)
    admin = _FakeAdmin({})
    _patch_admin(monkeypatch, main, admin)
    asyncio.run(main._log_usage("u6", {"is_internal": True, "enabled": True}))
    assert admin.inserted == []
