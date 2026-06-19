# BOHUMFIT-063 레이트리밋 키 전환(user id + IP fallback) 회귀.
#
# 060 한도·429 한국어 유지, 키 함수만 교체. 인증 사용자=Supabase JWT sub 키,
#   비인증/malformed=IP fallback(크래시 0). key_func 는 서명검증 없이 sub 만 디코드(경량).
# main 은 slowapi/sentry/fastapi 의존 → 미설치 시 자동 skip(Codex/Windows 권위).
import base64
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("slowapi")
pytest.importorskip("fastapi")

import main


def _b64(d: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")


def _jwt(claims: dict) -> str:
    return f"{_b64({'alg': 'HS256', 'typ': 'JWT'})}.{_b64(claims)}.sigpart"


def _req(auth: str | None = None, ip: str = "1.2.3.4"):
    from starlette.requests import Request
    headers = []
    if auth is not None:
        headers.append((b"authorization", auth.encode()))
    return Request({
        "type": "http", "method": "POST", "path": "/api/analyze",
        "headers": headers, "client": (ip, 5555),
    })


# ── ① 유효 Bearer 토큰(sub) → user 키 ────────────────────────────────────────
def test_valid_token_user_key():
    key = main._ratelimit_key(_req(auth=f"Bearer {_jwt({'sub': 'uuid-A', 'role': 'authenticated'})}"))
    assert key == "user:uuid-A"
    # 대소문자 무관(bearer)
    assert main._ratelimit_key(_req(auth=f"bearer {_jwt({'sub': 'uuid-A'})}")) == "user:uuid-A"


# ── ② 토큰 없음 → IP fallback ────────────────────────────────────────────────
def test_no_token_ip_fallback():
    assert main._ratelimit_key(_req(auth=None, ip="9.9.9.9")) == "ip:9.9.9.9"


# ── ③ malformed 토큰 → IP fallback, 크래시 0 ─────────────────────────────────
def test_malformed_token_ip_fallback():
    bad = [
        "Bearer garbage",                 # 점 없음
        "Bearer a.b",                     # 2 segment
        "Bearer a.@@@notbase64@@@.c",     # payload base64 깨짐
        "Bearer " + f"{_b64({'alg':'x'})}.{base64.urlsafe_b64encode(b'not-json').decode().rstrip('=')}.sig",  # payload non-JSON
        "Bearer " + _jwt({"role": "authenticated"}),  # sub 없음
        "Bearer ",                        # 빈 토큰
        "Basic abc",                      # Bearer 아님
        "",                               # 빈 헤더
    ]
    for a in bad:
        k = main._ratelimit_key(_req(auth=a, ip="8.8.8.8"))
        assert k == "ip:8.8.8.8", a


# ── ④ 같은 IP·다른 user → 키 분리(throttle 분리) ─────────────────────────────
def test_same_ip_different_user_keys_differ():
    a = main._ratelimit_key(_req(auth=f"Bearer {_jwt({'sub': 'user-A'})}", ip="5.5.5.5"))
    b = main._ratelimit_key(_req(auth=f"Bearer {_jwt({'sub': 'user-B'})}", ip="5.5.5.5"))
    assert a == "user:user-A" and b == "user:user-B" and a != b
    # 같은 user·다른 IP → 동일 키(사용자 단위 한도)
    c = main._ratelimit_key(_req(auth=f"Bearer {_jwt({'sub': 'user-A'})}", ip="7.7.7.7"))
    assert c == a


# ── ⑤ Limiter 가 새 키 함수 사용 + 429 한국어 핸들러 유지(060) ────────────────
def test_limiter_uses_new_keyfunc_and_korean_429():
    assert main.limiter._key_func is main._ratelimit_key
    resp = main._rate_limit_handler(_req(), Exception("x"))
    assert resp.status_code == 429
    assert "너무 잦" in resp.body.decode("utf-8")


# ── ⑥ key_func 경량성: 네트워크/DB 호출 없음(verify_jwt 미호출) ───────────────
def test_keyfunc_does_not_call_network(monkeypatch):
    called = {"n": 0}

    async def _boom(*a, **k):
        called["n"] += 1
        raise AssertionError("key_func must not verify token over network")

    monkeypatch.setattr(main, "verify_jwt", _boom)
    main._ratelimit_key(_req(auth=f"Bearer {_jwt({'sub': 'uuid-Z'})}"))
    assert called["n"] == 0
