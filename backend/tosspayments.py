"""BOHUMFIT-070: 토스페이먼츠 자동결제(빌링) 연동.

빌링키 발급·자동결제·웹훅 HMAC 검증을 담당한다(키/네트워크 외 부수효과 없음).
환경변수: TOSS_SECRET_KEY(서버 비밀키), TOSS_WEBHOOK_SECRET(웹훅 서명검증).
인증: Authorization: Basic base64(secret_key + ":").
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

import httpx

TOSS_API_BASE = "https://api.tosspayments.com/v1"
TIMEOUT_SECONDS = 20.0


class TossError(Exception):
    """토스 API 호출 실패(결제·발급)."""


class TossConfigError(TossError):
    """토스 환경변수 미설정."""


def _secret_key() -> str:
    key = os.environ.get("TOSS_SECRET_KEY", "")
    if not key:
        raise TossConfigError("TOSS_SECRET_KEY 미설정 — 결제 기능을 사용할 수 없습니다.")
    return key


def _auth_header(secret_key: str) -> str:
    """Basic 인증 헤더(시크릿키 뒤 ':' 붙여 base64)."""
    token = base64.b64encode(f"{secret_key}:".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def _err_message(resp: httpx.Response) -> str:
    try:
        data = resp.json()
        return f"토스 오류({resp.status_code}): {data.get('message') or data.get('code') or '알 수 없음'}"
    except Exception:
        return f"토스 오류: HTTP {resp.status_code}"


async def issue_billing_key(auth_key: str, customer_key: str) -> dict:
    """authKey + customerKey 로 빌링키 발급. 반환 dict(billingKey 포함)."""
    secret = _secret_key()
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        resp = await client.post(
            f"{TOSS_API_BASE}/billing/authorizations/issue",
            headers={"Authorization": _auth_header(secret), "Content-Type": "application/json"},
            json={"authKey": auth_key, "customerKey": customer_key},
        )
    if resp.status_code != 200:
        raise TossError(_err_message(resp))
    return resp.json()


async def charge_billing(billing_key: str, customer_key: str, amount: int,
                         order_id: str, order_name: str) -> dict:
    """빌링키로 자동결제 실행. 반환 dict(status: DONE 등)."""
    secret = _secret_key()
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        resp = await client.post(
            f"{TOSS_API_BASE}/billing/{billing_key}",
            headers={"Authorization": _auth_header(secret), "Content-Type": "application/json"},
            json={
                "customerKey": customer_key,
                "amount": amount,
                "orderId": order_id,
                "orderName": order_name,
            },
        )
    if resp.status_code != 200:
        raise TossError(_err_message(resp))
    return resp.json()


def verify_webhook_signature(secret: str, payload, signature: str) -> bool:
    """웹훅 HMAC-SHA256 서명 검증(hex 또는 base64 형식 모두 허용). 상수시간 비교."""
    if not secret or not signature:
        return False
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    mac = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256)
    hex_sig = mac.hexdigest()
    b64_sig = base64.b64encode(mac.digest()).decode("ascii")
    return hmac.compare_digest(hex_sig, signature) or hmac.compare_digest(b64_sig, signature)
