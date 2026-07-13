"""NHN Cloud SMS 공용 유틸.

BOHUMFIT-216: 207 OTP와 비밀번호 찾기가 같은 SMS 발송 인터페이스를 재사용하도록 분리한다.
실 키/발신번호 승인 전에는 네트워크 호출 없이 명확히 미설정 오류를 반환한다.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import httpx


class SMSNotConfigured(RuntimeError):
    """NHN SMS 환경변수 또는 발신번호가 아직 준비되지 않은 상태."""


class SMSSendError(RuntimeError):
    """NHN SMS API 호출 실패."""


@dataclass(frozen=True)
class NHNSMSConfig:
    app_key: str
    secret_key: str
    sender: str
    endpoint: str


def get_nhn_sms_config() -> NHNSMSConfig | None:
    app_key = os.environ.get("NHN_SMS_APP_KEY", "").strip()
    secret_key = os.environ.get("NHN_SMS_SECRET_KEY", "").strip()
    sender = os.environ.get("NHN_SMS_SENDER", "").strip()
    endpoint = os.environ.get("NHN_SMS_ENDPOINT", "").strip()
    if not (app_key and secret_key and sender):
        return None
    if not endpoint:
        endpoint = f"https://api-sms.cloud.toast.com/sms/v3.0/appKeys/{app_key}/sender/sms"
    return NHNSMSConfig(app_key=app_key, secret_key=secret_key, sender=sender, endpoint=endpoint)


async def send_sms(phone: str, message: str) -> dict:
    config = get_nhn_sms_config()
    if config is None:
        raise SMSNotConfigured("NHN SMS 키 또는 발신번호가 설정되지 않았습니다.")

    payload = {
        "body": message,
        "sendNo": config.sender,
        "recipientList": [{"recipientNo": phone}],
    }
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "X-Secret-Key": config.secret_key,
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(config.endpoint, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise SMSSendError("NHN SMS 발송 요청에 실패했습니다.") from exc
    if response.status_code >= 400:
        raise SMSSendError(f"NHN SMS 발송 실패: {response.status_code}")
    try:
        return response.json()
    except ValueError:
        return {"status_code": response.status_code}
