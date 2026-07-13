import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("slowapi")
pytest.importorskip("fastapi")

import main  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sms_nhn import SMSNotConfigured  # noqa: E402


class _Resp:
    def __init__(self, data=None):
        self.data = data


class _Query:
    def __init__(self, rows):
        self._rows = rows
        self._filters = []

    def select(self, *args, **kwargs):
        return self

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def execute(self):
        rows = list(self._rows)
        for column, value in self._filters:
            rows = [row for row in rows if row.get(column) == value]
        return _Resp(rows)


class _Admin:
    def __init__(self, profiles):
        self._profiles = profiles

    def table(self, name):
        assert name == "profiles"
        return _Query(self._profiles)


@pytest.fixture
def client(monkeypatch):
    main.limiter.enabled = False
    monkeypatch.setattr(main, "HCAPTCHA_SECRET", "")
    main._password_reset_codes.clear()
    main._password_reset_tokens.clear()
    yield TestClient(main.app)
    main._password_reset_codes.clear()
    main._password_reset_tokens.clear()
    main.limiter.enabled = True


def _email_user():
    return {
        "id": "user-email",
        "email": "user@example.test",
        "app_metadata": {"providers": ["email"]},
        "identities": [{"provider": "email"}],
    }


def _social_user(provider="kakao"):
    return {
        "id": "user-social",
        "email": "social@example.test",
        "app_metadata": {"providers": [provider]},
        "identities": [{"provider": provider}],
    }


def test_password_reset_reports_nhn_pending_when_sms_is_not_configured(client, monkeypatch):
    monkeypatch.setattr(
        main,
        "_get_supabase_admin",
        lambda: _Admin([{"id": "user-email", "phone": "01012345678", "phone_verified": True}]),
    )

    async def fake_user(user_id):
        assert user_id == "user-email"
        return _email_user()

    async def fake_send_sms(phone, message):
        raise SMSNotConfigured("missing env")

    monkeypatch.setattr(main, "_get_auth_user_record", fake_user)
    monkeypatch.setattr(main, "send_sms", fake_send_sms)

    res = client.post("/auth/password-reset/request", json={"phone": "010-1234-5678"})

    assert res.status_code == 503
    assert "NHN SMS" in res.json()["detail"]
    assert main._password_reset_codes == {}


def test_password_reset_email_user_roundtrip_is_server_verified(client, monkeypatch):
    sent = {}
    updated = {}
    monkeypatch.setattr(
        main,
        "_get_supabase_admin",
        lambda: _Admin([{"id": "user-email", "phone": "01012345678", "phone_verified": True}]),
    )
    monkeypatch.setattr(main.secrets, "randbelow", lambda _: 123456)
    monkeypatch.setattr(main.secrets, "token_urlsafe", lambda _: "reset-token-216")

    async def fake_user(user_id):
        assert user_id == "user-email"
        return _email_user()

    async def fake_send_sms(phone, message):
        sent["phone"] = phone
        sent["message"] = message

    async def fake_update_password(user_id, password):
        updated["user_id"] = user_id
        updated["password"] = password

    monkeypatch.setattr(main, "_get_auth_user_record", fake_user)
    monkeypatch.setattr(main, "send_sms", fake_send_sms)
    monkeypatch.setattr(main, "_update_supabase_user_password", fake_update_password)

    requested = client.post("/auth/password-reset/request", json={"phone": "010-1234-5678"})
    assert requested.status_code == 200, requested.text
    assert requested.json()["sent"] is True
    assert sent["phone"] == "01012345678"
    assert "123456" in sent["message"]

    wrong = client.post("/auth/password-reset/verify", json={"phone": "01012345678", "code": "000000"})
    assert wrong.status_code == 400

    verified = client.post("/auth/password-reset/verify", json={"phone": "01012345678", "code": "123456"})
    assert verified.status_code == 200, verified.text
    assert verified.json()["verified"] is True
    assert verified.json()["reset_token"] == "reset-token-216"

    reused = client.post("/auth/password-reset/verify", json={"phone": "01012345678", "code": "123456"})
    assert reused.status_code == 400

    short_password = client.post(
        "/auth/password-reset/confirm",
        json={"reset_token": "reset-token-216", "password": "short"},
    )
    assert short_password.status_code == 400

    confirmed = client.post(
        "/auth/password-reset/confirm",
        json={"reset_token": "reset-token-216", "password": "new-password-216"},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["updated"] is True
    assert updated == {"user_id": "user-email", "password": "new-password-216"}

    replay = client.post(
        "/auth/password-reset/confirm",
        json={"reset_token": "reset-token-216", "password": "new-password-216"},
    )
    assert replay.status_code == 400


def test_password_reset_rejects_social_only_accounts_before_sms(client, monkeypatch):
    sent = []
    monkeypatch.setattr(
        main,
        "_get_supabase_admin",
        lambda: _Admin([{"id": "user-social", "phone": "01087654321", "phone_verified": True}]),
    )

    async def fake_user(user_id):
        assert user_id == "user-social"
        return _social_user("kakao")

    async def fake_send_sms(phone, message):
        sent.append((phone, message))

    monkeypatch.setattr(main, "_get_auth_user_record", fake_user)
    monkeypatch.setattr(main, "send_sms", fake_send_sms)

    res = client.post("/auth/password-reset/request", json={"phone": "010-8765-4321"})

    assert res.status_code == 400
    assert sent == []


def test_password_reset_requires_verified_registered_phone(client, monkeypatch):
    monkeypatch.setattr(
        main,
        "_get_supabase_admin",
        lambda: _Admin([{"id": "user-email", "phone": "01012345678", "phone_verified": False}]),
    )

    res = client.post("/auth/password-reset/request", json={"phone": "010-1234-5678"})

    assert res.status_code == 404
