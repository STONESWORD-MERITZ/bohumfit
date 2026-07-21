# BOHUMFIT-233 관리자 tier 관리 API 회귀 — Supabase admin(테이블+auth admin)을 가짜로 주입.
#   /admin/tier/list: admin만 200(이메일·tier만 반환), 비admin 403.
#   /admin/tier/set: internal/customer만 허용(admin 지정 422), 미가입 404,
#   자기 자신 400, 대상 admin 400, 지정→해제 왕복 upsert 검증.
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

from fastapi import HTTPException  # noqa: E402


class _Resp:
    def __init__(self, data=None):
        self.data = data


class _ProfilesQuery:
    """profiles 전용 가짜 빌더 — eq(id)/single 및 in_(bohumfit_tier) 지원."""

    def __init__(self, admin):
        self._admin = admin
        self._eq_id = None
        self._in_tiers = None
        self._upsert = None

    def select(self, *a, **k):
        return self

    def eq(self, column, value):
        if column == "id":
            self._eq_id = value
        return self

    def in_(self, column, values):
        if column == "bohumfit_tier":
            self._in_tiers = list(values)
        return self

    def single(self):
        return self

    def upsert(self, payload, **k):
        self._upsert = payload
        return self

    def execute(self):
        if self._upsert is not None:
            self._admin.upserted.append(self._upsert)
            self._admin.profiles[self._upsert["id"]] = {
                **self._admin.profiles.get(self._upsert["id"], {}),
                **{k: v for k, v in self._upsert.items() if k != "id"},
            }
            return _Resp([{"id": self._upsert["id"]}])
        if self._in_tiers is not None:
            rows = [
                {"id": uid, "bohumfit_tier": row.get("bohumfit_tier")}
                for uid, row in self._admin.profiles.items()
                if row.get("bohumfit_tier") in self._in_tiers
            ]
            return _Resp(rows)
        if self._eq_id is not None:
            row = self._admin.profiles.get(self._eq_id)
            if row is None:
                raise RuntimeError("row not found")
            return _Resp({"bohumfit_tier": row.get("bohumfit_tier")})
        return _Resp(None)


class _FakeAuthAdmin:
    def __init__(self, users):
        self._users = users  # list[SimpleNamespace(id, email)]

    def list_users(self, page=1, per_page=200):
        start = (page - 1) * per_page
        return self._users[start:start + per_page]

    def get_user_by_id(self, uid):
        for u in self._users:
            if u.id == uid:
                return SimpleNamespace(user=u)
        raise RuntimeError("user not found")


class _FakeAdmin:
    def __init__(self, profiles, users):
        self.profiles = profiles          # id -> {"bohumfit_tier": ...}
        self.upserted = []
        self.auth = SimpleNamespace(admin=_FakeAuthAdmin(users))

    def table(self, name):
        assert name == "profiles", f"unexpected table: {name}"
        return _ProfilesQuery(self)


def _load_main(monkeypatch):
    monkeypatch.setenv("SERVICE_ENV", "production")
    import main
    importlib.reload(main)
    return main


def _setup(monkeypatch):
    main = _load_main(monkeypatch)
    admin = _FakeAdmin(
        profiles={
            "admin-1": {"bohumfit_tier": "admin"},
            "admin-2": {"bohumfit_tier": "admin"},
            "staff-1": {"bohumfit_tier": "internal"},
            "cust-1": {"bohumfit_tier": "customer"},
        },
        users=[
            SimpleNamespace(id="admin-1", email="boss@bohumfit.ai"),
            SimpleNamespace(id="admin-2", email="boss2@bohumfit.ai"),
            SimpleNamespace(id="staff-1", email="staff1@bohumfit.ai"),
            SimpleNamespace(id="cust-1", email="cust1@example.com"),
        ],
    )
    monkeypatch.setattr(main, "_get_supabase_admin", lambda: admin)
    return main, admin


# ── list ──────────────────────────────────────────────────────────────────────
def test_list_admin_returns_members_email_and_tier_only(monkeypatch):
    main, _ = _setup(monkeypatch)
    res = asyncio.run(main.admin_tier_list("admin-1"))
    members = res["members"]
    assert {m["email"] for m in members} == {"boss@bohumfit.ai", "boss2@bohumfit.ai", "staff1@bohumfit.ai"}
    # admin 우선 정렬 + 필드는 email/tier 뿐(PII 최소화)
    assert members[0]["tier"] == "admin"
    assert all(set(m.keys()) == {"email", "tier"} for m in members)


def test_list_internal_and_customer_403(monkeypatch):
    main, _ = _setup(monkeypatch)
    for uid in ("staff-1", "cust-1"):
        with pytest.raises(HTTPException) as ei:
            asyncio.run(main.admin_tier_list(uid))
        assert ei.value.status_code == 403


# ── set ───────────────────────────────────────────────────────────────────────
def test_set_unknown_email_404_with_signup_guidance(monkeypatch):
    main, _ = _setup(monkeypatch)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main.admin_tier_set({"email": "nobody@example.com", "tier": "internal"}, "admin-1"))
    assert ei.value.status_code == 404 and "가입" in ei.value.detail


def test_set_admin_tier_rejected_422(monkeypatch):
    main, _ = _setup(monkeypatch)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main.admin_tier_set({"email": "cust1@example.com", "tier": "admin"}, "admin-1"))
    assert ei.value.status_code == 422


def test_set_bad_email_or_tier_422(monkeypatch):
    main, _ = _setup(monkeypatch)
    for payload in ({"email": "notanemail", "tier": "internal"}, {"email": "cust1@example.com", "tier": "vip"}):
        with pytest.raises(HTTPException) as ei:
            asyncio.run(main.admin_tier_set(payload, "admin-1"))
        assert ei.value.status_code == 422


def test_set_self_rejected_400(monkeypatch):
    main, _ = _setup(monkeypatch)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main.admin_tier_set({"email": "boss@bohumfit.ai", "tier": "customer"}, "admin-1"))
    assert ei.value.status_code == 400


def test_set_target_admin_rejected_400(monkeypatch):
    """다른 admin 강등도 API 불가 — 상호 강등·마지막 admin 잠금 사고 방지."""
    main, _ = _setup(monkeypatch)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main.admin_tier_set({"email": "boss2@bohumfit.ai", "tier": "customer"}, "admin-1"))
    assert ei.value.status_code == 400


def test_set_non_admin_requester_403(monkeypatch):
    main, _ = _setup(monkeypatch)
    with pytest.raises(HTTPException) as ei:
        asyncio.run(main.admin_tier_set({"email": "cust1@example.com", "tier": "internal"}, "staff-1"))
    assert ei.value.status_code == 403


def test_set_promote_then_demote_roundtrip(monkeypatch):
    main, admin = _setup(monkeypatch)
    res1 = asyncio.run(main.admin_tier_set({"email": "cust1@example.com", "tier": "internal"}, "admin-1"))
    assert res1["ok"] is True and res1["tier"] == "internal"
    assert admin.upserted[-1] == {"id": "cust-1", "bohumfit_tier": "internal"}
    # 지정 직후 목록에 나타나고, 해제하면 원복된다.
    listed = asyncio.run(main.admin_tier_list("admin-1"))
    assert any(m["email"] == "cust1@example.com" and m["tier"] == "internal" for m in listed["members"])
    res2 = asyncio.run(main.admin_tier_set({"email": "CUST1@EXAMPLE.COM", "tier": "customer"}, "admin-1"))
    assert res2["ok"] is True and res2["tier"] == "customer"
    assert admin.upserted[-1] == {"id": "cust-1", "bohumfit_tier": "customer"}
