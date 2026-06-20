# BOHUMFIT-070 토스페이먼츠 — 웹훅 HMAC 서명검증·Basic 인증헤더·환경변수 가드 유닛 테스트.
#   (issue_billing_key·charge_billing 네트워크 호출은 실 토스 API 필요 → 여기선 미검증.)
import base64
import hashlib
import hmac
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("httpx")

import tosspayments as tp


SECRET = "whsec_test"
PAYLOAD = b'{"eventType":"PAYMENT_STATUS_CHANGED","data":{"status":"DONE","customerKey":"u1"}}'


def _hex(secret, payload):
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def _b64(secret, payload):
    return base64.b64encode(hmac.new(secret.encode(), payload, hashlib.sha256).digest()).decode()


# ── 웹훅 서명검증: hex/base64 모두 허용 ──────────────────────────────────────
def test_verify_signature_hex_ok():
    assert tp.verify_webhook_signature(SECRET, PAYLOAD, _hex(SECRET, PAYLOAD)) is True


def test_verify_signature_base64_ok():
    assert tp.verify_webhook_signature(SECRET, PAYLOAD, _b64(SECRET, PAYLOAD)) is True


def test_verify_signature_str_payload_ok():
    # payload가 str여도 동작(encode).
    assert tp.verify_webhook_signature(SECRET, PAYLOAD.decode(), _hex(SECRET, PAYLOAD)) is True


# ── 서명 불일치·빈 입력 → False(상수시간 비교) ──────────────────────────────
def test_verify_signature_reject():
    assert tp.verify_webhook_signature(SECRET, PAYLOAD, "deadbeef") is False
    assert tp.verify_webhook_signature(SECRET, PAYLOAD, "") is False
    assert tp.verify_webhook_signature("", PAYLOAD, _hex(SECRET, PAYLOAD)) is False
    # 다른 시크릿 → 불일치
    assert tp.verify_webhook_signature("other", PAYLOAD, _hex(SECRET, PAYLOAD)) is False


# ── Basic 인증헤더(시크릿키 뒤 ':' base64) ───────────────────────────────────
def test_auth_header():
    h = tp._auth_header("sk_test_123")
    assert h == "Basic " + base64.b64encode(b"sk_test_123:").decode()


# ── 환경변수 미설정 → TossConfigError(graceful) ─────────────────────────────
def test_secret_key_missing_raises(monkeypatch):
    monkeypatch.delenv("TOSS_SECRET_KEY", raising=False)
    with pytest.raises(tp.TossConfigError):
        tp._secret_key()


def test_secret_key_present(monkeypatch):
    monkeypatch.setenv("TOSS_SECRET_KEY", "sk_live_x")
    assert tp._secret_key() == "sk_live_x"


def test_api_base_constant():
    assert tp.TOSS_API_BASE == "https://api.tosspayments.com/v1"
