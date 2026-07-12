# BOHUMFIT-069/072 구독·사용량·무료체험 게이트 회귀 — Supabase admin을 가짜로 주입.
#
# /api/analyze와 /coverage/analyze:
#   admin=무제한, internal=월 100회, 활성 구독은 기존 플랜 한도(basic 30·pro 100),
#   미구독 customer/기타는 최초 누적 무료 분석 5회까지 통과·초과 시 402.
#   Supabase 미설정 → 게이트 비활성(무료 동작). main 의존
#   (slowapi/fastapi/supabase) → 미설치 시 자동 skip(Codex/Windows 권위).
import asyncio
import importlib
import os
import sys
from types import SimpleNamespace

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
    def gte(self, column, value):
        self._filters.append(("gte", column, value))
        return self
    def lte(self, column, value):
        self._filters.append(("lte", column, value))
        return self
    def lt(self, column, value):
        self._filters.append(("lt", column, value))
        return self
    def single(self): return self

    def insert(self, payload):
        self._insert = payload
        return self

    def execute(self):
        if self._insert is not None:
            self._admin.inserted.append((self._name, self._insert))
            return _Resp([{"id": "x"}])
        if self._name == "usage_logs" and self._admin.usage_rows is not None:
            rows = list(self._admin.usage_rows)
            for item in self._filters:
                if len(item) == 2:
                    column, value = item
                    rows = [row for row in rows if row.get(column) == value]
                else:
                    op, column, value = item
                    if op == "gte":
                        rows = [row for row in rows if row.get(column, "") >= value]
                    elif op == "lte":
                        rows = [row for row in rows if row.get(column, "") <= value]
                    elif op == "lt":
                        rows = [row for row in rows if row.get(column, "") < value]
            return _Resp([], count=len(rows))
        r = self._admin.responses.get(self._name)
        if isinstance(r, Exception):
            raise r
        if isinstance(r, _Resp) and isinstance(r.data, dict):
            for column, value in self._filters:
                if column in r.data and r.data.get(column) != value:
                    return _Resp(None)
        return r if r is not None else _Resp(None)


class _FakeAdmin:
    def __init__(self, responses, usage_rows=None):
        self.responses = responses
        self.usage_rows = usage_rows
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


# ── ① admin → 무제한(사용량 초과여도 통과, 차감 없음) ────────────────────────
def test_admin_unlimited_passes_and_does_not_log(monkeypatch):
    main = _load_main(monkeypatch)
    admin = _FakeAdmin({
        "profiles": _Resp({"role": "admin"}),
        "usage_logs": _Resp([], count=999),
    })
    _patch_admin(monkeypatch, main, admin)
    ctx = asyncio.run(main._enforce_subscription("admin-1"))
    assert ctx["enabled"] is True
    assert ctx["is_admin"] is True
    assert ctx["quota_scope"] == "unlimited"
    asyncio.run(main._log_usage("admin-1", ctx))
    assert admin.inserted == []


def test_admin_billing_status_reports_unlimited(monkeypatch):
    main = _load_main(monkeypatch)
    _patch_admin(monkeypatch, main, _FakeAdmin({
        "profiles": _Resp({"role": "admin"}),
        "usage_logs": _Resp([], count=999),
    }))
    status = asyncio.run(main.billing_status("admin-2"))
    assert status["is_admin"] is True
    assert status["role"] == "admin"
    assert status["quota_scope"] == "unlimited"
    assert status["limit"] is None


# ── ② internal → pro 동일 월 100회(한도 내 통과) ─────────────────────────────
def test_internal_under_100_passes(monkeypatch):
    main = _load_main(monkeypatch)
    _patch_admin(monkeypatch, main, _FakeAdmin({
        "profiles": _Resp({"role": "internal"}),
        "usage_logs": _Resp([], count=30),
    }))
    ctx = asyncio.run(main._enforce_subscription("u1"))
    assert ctx["is_internal"] is True and ctx["enabled"] is True and ctx["plan"] == "internal"
    assert ctx["quota_scope"] == "monthly"


# ── ②' internal 100회 초과 → 429(BOHUMFIT-110/212) ──────────────────────────
def test_internal_over_100_429(monkeypatch):
    main = _load_main(monkeypatch)
    _patch_admin(monkeypatch, main, _FakeAdmin({
        "profiles": _Resp({"role": "internal"}),
        "usage_logs": _Resp([], count=100),
    }))
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main._enforce_subscription("u1b"))
    assert ei.value.status_code == 429 and "100" in ei.value.detail


def test_internal_monthly_window_resets_at_month_boundary(monkeypatch):
    main = _load_main(monkeypatch)
    monkeypatch.setattr(
        main,
        "_month_bounds",
        lambda: ("2026-07-01T00:00:00+00:00", "2026-08-01T00:00:00+00:00"),
    )
    rows = (
        [{"user_id": "u1c", "used_at": "2026-06-30T23:59:59+00:00"} for _ in range(100)]
        + [{"user_id": "u1c", "used_at": "2026-07-01T00:00:00+00:00"} for _ in range(99)]
        + [{"user_id": "u1c", "used_at": "2026-08-01T00:00:00+00:00"}]
    )
    _patch_admin(monkeypatch, main, _FakeAdmin({
        "profiles": _Resp({"role": "internal"}),
    }, usage_rows=rows))
    ctx = asyncio.run(main._enforce_subscription("u1c"))
    assert ctx["enabled"] is True and ctx["quota_scope"] == "monthly"


# ── ③ 미구독 + 누적 무료 분석 한도 내 → 통과(plan=trial) ─────────────────────
def test_trial_under_limit_passes(monkeypatch):
    main = _load_main(monkeypatch)
    _patch_admin(monkeypatch, main, _FakeAdmin({
        "profiles": _Resp({"role": "customer"}),
        "subscriptions": _Resp(None),
        "usage_logs": _Resp([], count=2),
    }))
    ctx = asyncio.run(main._enforce_subscription("u2"))
    assert ctx["enabled"] is True and ctx["is_internal"] is False and ctx["plan"] == "trial"
    assert ctx["quota_scope"] == "lifetime"


# ── ④ 미구독 + 누적 무료 분석 5회 소진 → 402 ───────────────────────────────
def test_trial_exhausted_402(monkeypatch):
    main = _load_main(monkeypatch)
    _patch_admin(monkeypatch, main, _FakeAdmin({
        "profiles": _Resp({"role": "customer"}),
        "subscriptions": _Resp(None),
        "usage_logs": _Resp([], count=5),
    }))
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main._enforce_subscription("u3"))
    assert ei.value.status_code == 402 and "무료 분석" in ei.value.detail


def test_customer_lifetime_trial_does_not_reset_next_month(monkeypatch):
    main = _load_main(monkeypatch)
    monkeypatch.setattr(
        main,
        "_month_bounds",
        lambda: ("2026-07-01T00:00:00+00:00", "2026-08-01T00:00:00+00:00"),
    )
    rows = [{"user_id": "u3m", "used_at": "2026-06-15T00:00:00+00:00"} for _ in range(5)]
    _patch_admin(monkeypatch, main, _FakeAdmin({
        "profiles": _Resp({"role": "customer"}),
        "subscriptions": _Resp(None),
    }, usage_rows=rows))
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main._enforce_subscription("u3m"))
    assert ei.value.status_code == 402


def test_customer_billing_status_uses_lifetime_trial_count(monkeypatch):
    main = _load_main(monkeypatch)
    rows = [
        {"user_id": "u3s", "used_at": "2026-05-01T00:00:00+00:00"},
        {"user_id": "u3s", "used_at": "2026-06-01T00:00:00+00:00"},
    ]
    _patch_admin(monkeypatch, main, _FakeAdmin({
        "profiles": _Resp({"role": "customer"}),
        "subscriptions": _Resp(None),
    }, usage_rows=rows))
    status = asyncio.run(main.billing_status("u3s"))
    assert status["quota_scope"] == "lifetime"
    assert status["trial_used"] == 2
    assert status["trial_limit"] == 5


# ── ④' inactive 구독도 누적 무료 분석 경로(소진 시 402) ──────────────────────
def test_inactive_subscription_falls_to_trial(monkeypatch):
    main = _load_main(monkeypatch)
    _patch_admin(monkeypatch, main, _FakeAdmin({
        "profiles": _Resp({"role": "customer"}),
        "subscriptions": _Resp({"status": "inactive", "plan": "basic", **PERIODS}),
        "usage_logs": _Resp([], count=5),
    }))
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main._enforce_subscription("u3i"))
    assert ei.value.status_code == 402


# ── ⑤ 활성 베이직 30회 초과 → 429 ───────────────────────────────────────────
def test_active_basic_over_limit_429(monkeypatch):
    main = _load_main(monkeypatch)
    _patch_admin(monkeypatch, main, _FakeAdmin({
        "profiles": _Resp({"role": "customer"}),
        "subscriptions": _Resp({"status": "active", "plan": "basic", **PERIODS}),
        "usage_logs": _Resp([], count=30),
    }))
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main._enforce_subscription("u4"))
    assert ei.value.status_code == 429 and "30" in ei.value.detail


# ── ⑤' 활성 프로 → 30회는 통과(한도 100), 100회 초과 → 429 ───────────────────
def test_active_pro_limit_100(monkeypatch):
    main = _load_main(monkeypatch)
    _patch_admin(monkeypatch, main, _FakeAdmin({
        "profiles": _Resp({"role": "customer"}),
        "subscriptions": _Resp({"status": "active", "plan": "pro", **PERIODS}),
        "usage_logs": _Resp([], count=30),
    }))
    ctx = asyncio.run(main._enforce_subscription("u4p"))
    assert ctx["plan"] == "pro" and ctx["enabled"] is True


def test_active_pro_over_100_429(monkeypatch):
    main = _load_main(monkeypatch)
    _patch_admin(monkeypatch, main, _FakeAdmin({
        "profiles": _Resp({"role": "customer"}),
        "subscriptions": _Resp({"status": "active", "plan": "pro", **PERIODS}),
        "usage_logs": _Resp([], count=100),
    }))
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main._enforce_subscription("u4p2"))
    assert ei.value.status_code == 429 and "100" in ei.value.detail


# ── ⑥ 활성 베이직 한도 내 → 통과 + 차감 ─────────────────────────────────────
def test_active_under_limit_passes_and_logs(monkeypatch):
    main = _load_main(monkeypatch)
    admin = _FakeAdmin({
        "profiles": _Resp({"role": "customer"}),
        "subscriptions": _Resp({"status": "active", "plan": "basic", **PERIODS}),
        "usage_logs": _Resp([], count=5),
    })
    _patch_admin(monkeypatch, main, admin)
    ctx = asyncio.run(main._enforce_subscription("u5"))
    assert ctx["enabled"] is True and ctx["plan"] == "basic"
    assert ctx["period_start"] == PERIODS["current_period_start"]
    asyncio.run(main._log_usage("u5", ctx))
    assert admin.inserted and admin.inserted[0][0] == "usage_logs" and admin.inserted[0][1]["user_id"] == "u5"


# ── ⑦ Supabase 미설정 → 게이트 비활성 ───────────────────────────────────────
def test_disabled_when_no_supabase(monkeypatch):
    main = _load_main(monkeypatch)
    monkeypatch.setattr(main, "_get_supabase_admin", lambda: None)
    ctx = asyncio.run(main._enforce_subscription("u6"))
    assert ctx["enabled"] is False and ctx["is_internal"] is True
    asyncio.run(main._log_usage("u6", ctx))


# ── ⑧ internal ctx도 차감 적재(BOHUMFIT-110/212: 월 100회 → 사용량 기록) ──
def test_internal_logged(monkeypatch):
    main = _load_main(monkeypatch)
    admin = _FakeAdmin({})
    _patch_admin(monkeypatch, main, admin)
    asyncio.run(main._log_usage("u7", {"is_internal": True, "enabled": True,
                                       "period_start": "2026-06-01T00:00:00+00:00",
                                       "period_end": "2026-07-01T00:00:00+00:00"}))
    assert admin.inserted and admin.inserted[0][0] == "usage_logs"


# ── ⑨ trial ctx 차감 적재(미구독 무료 분석도 사용량 기록) ───────────────────
def test_trial_usage_logged(monkeypatch):
    main = _load_main(monkeypatch)
    admin = _FakeAdmin({})
    _patch_admin(monkeypatch, main, admin)
    asyncio.run(main._log_usage("u8", {"is_internal": False, "enabled": True,
                                       "period_start": "2026-06-01T00:00:00+00:00",
                                       "period_end": "2026-07-01T00:00:00+00:00"}))
    assert admin.inserted and admin.inserted[0][0] == "usage_logs"


# ── ⑩ coverage/analyze도 같은 서버 권위 게이트·성공 로그 사용 ────────────────
class _Upload:
    filename = "coverage.pdf"

    async def read(self):
        return b"%PDF-1.4\nsynthetic"


def test_coverage_analyze_logs_usage_on_success(monkeypatch):
    main = _load_main(monkeypatch)
    monkeypatch.setattr(main.limiter, "enabled", False)
    admin = _FakeAdmin({
        "profiles": _Resp({"role": "customer"}),
        "subscriptions": _Resp(None),
        "usage_logs": _Resp([], count=0),
    })
    _patch_admin(monkeypatch, main, admin)
    monkeypatch.setattr(main, "analyze_kb_coverage", lambda data: {"before": {}, "final": {}, "warnings": []})

    result = asyncio.run(main.coverage_analyze(SimpleNamespace(), _Upload(), "u9"))

    assert result["warnings"] == []
    assert admin.inserted and admin.inserted[0][0] == "usage_logs"


def test_coverage_analyze_blocks_before_parsing_when_quota_exhausted(monkeypatch):
    main = _load_main(monkeypatch)
    monkeypatch.setattr(main.limiter, "enabled", False)
    admin = _FakeAdmin({
        "profiles": _Resp({"role": "customer"}),
        "subscriptions": _Resp(None),
        "usage_logs": _Resp([], count=5),
    })
    _patch_admin(monkeypatch, main, admin)
    called = False

    def _boom(data):
        nonlocal called
        called = True
        return {"before": {}, "final": {}, "warnings": []}

    monkeypatch.setattr(main, "analyze_kb_coverage", _boom)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main.coverage_analyze(SimpleNamespace(), _Upload(), "u9b"))

    assert ei.value.status_code == 402
    assert called is False
