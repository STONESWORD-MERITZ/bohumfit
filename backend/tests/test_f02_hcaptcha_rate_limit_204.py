# -*- coding: utf-8 -*-
"""BOHUMFIT-204 F-02 hCaptcha·IP 레이트리밋 회귀.

실 hCaptcha 키·토큰·외부 네트워크를 사용하지 않는다.
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("slowapi")
pytest.importorskip("fastapi")

import main
from fastapi import HTTPException
from slowapi.util import get_remote_address
from starlette.requests import Request


def _request(token: str | None = None, ip: str = "203.0.113.7") -> Request:
    headers = [(b"x-hcaptcha-token", token.encode())] if token is not None else []
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/auth/verify-phone",
            "headers": headers,
            "client": (ip, 443),
        }
    )


def _route_limits(endpoint):
    name = f"{endpoint.__module__}.{endpoint.__name__}"
    return main.limiter._route_limits[name]


def _has_ip_limit(endpoint, text: str) -> bool:
    return any(str(item.limit) == text and item.key_func is get_remote_address for item in _route_limits(endpoint))


def test_hcaptcha_is_optional_without_server_secret(monkeypatch):
    monkeypatch.setattr(main, "HCAPTCHA_SECRET", "")

    asyncio.run(main._verify_hcaptcha_token(_request()))


def test_hcaptcha_requires_token_when_server_secret_is_configured(monkeypatch):
    monkeypatch.setattr(main, "HCAPTCHA_SECRET", "test-secret")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(main._verify_hcaptcha_token(_request()))

    assert exc_info.value.status_code == 400
    assert "test-secret" not in str(exc_info.value.detail)


def test_hcaptcha_accepts_valid_token_without_exposing_secret(monkeypatch):
    calls: list[dict] = []

    class FakeResponse:
        is_success = True

        @staticmethod
        def json():
            return {"success": True}

    class FakeClient:
        def __init__(self, *, timeout: float):
            assert timeout == 5.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, url: str, *, data: dict):
            calls.append({"url": url, "data": data})
            return FakeResponse()

    monkeypatch.setattr(main, "HCAPTCHA_SECRET", "test-secret")
    monkeypatch.setattr(main.httpx, "AsyncClient", FakeClient)

    asyncio.run(main._verify_hcaptcha_token(_request("test-token", "198.51.100.4")))

    assert calls == [
        {
            "url": main.HCAPTCHA_VERIFY_URL,
            "data": {"secret": "test-secret", "response": "test-token", "remoteip": "198.51.100.4"},
        }
    ]


def test_hcaptcha_rejects_unsuccessful_verification(monkeypatch):
    class FakeResponse:
        is_success = True

        @staticmethod
        def json():
            return {"success": False, "error-codes": ["invalid-input-response"]}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, *_args, **_kwargs):
            return FakeResponse()

    monkeypatch.setattr(main, "HCAPTCHA_SECRET", "test-secret")
    monkeypatch.setattr(main.httpx, "AsyncClient", FakeClient)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(main._verify_hcaptcha_token(_request("invalid-token")))

    assert exc_info.value.status_code == 400
    assert "test-secret" not in str(exc_info.value.detail)


def test_hcaptcha_verification_failure_is_retryable(monkeypatch):
    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, *_args, **_kwargs):
            raise main.httpx.ConnectError("offline")

    monkeypatch.setattr(main, "HCAPTCHA_SECRET", "test-secret")
    monkeypatch.setattr(main.httpx, "AsyncClient", FakeClient)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(main._verify_hcaptcha_token(_request("test-token")))

    assert exc_info.value.status_code == 503


def test_sensitive_triggers_keep_user_limits_and_add_ip_limits():
    assert main.PHONE_VERIFY_IP_RATE_LIMIT == "5/minute,20/hour"
    assert main.COVERAGE_ANALYZE_IP_RATE_LIMIT == "10/minute,60/hour"
    assert main.ANALYZE_IP_RATE_LIMIT == "15/minute,90/hour"

    assert _has_ip_limit(main.verify_phone, "5 per 1 minute")
    assert _has_ip_limit(main.verify_phone, "20 per 1 hour")
    assert _has_ip_limit(main.coverage_analyze, "10 per 1 minute")
    assert _has_ip_limit(main.coverage_analyze, "60 per 1 hour")
    assert _has_ip_limit(main.analyze, "15 per 1 minute")
    assert _has_ip_limit(main.analyze, "90 per 1 hour")
    assert any(item.key_func is main._ratelimit_key for item in _route_limits(main.verify_phone))
    assert any(item.key_func is main._ratelimit_key for item in _route_limits(main.coverage_analyze))
    assert any(item.key_func is main._ratelimit_key for item in _route_limits(main.analyze))
