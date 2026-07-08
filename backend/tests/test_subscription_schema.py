import os

import httpx
import pytest


def _supabase_schema_client() -> tuple[str, dict[str, str]]:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    service_key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE")
        or ""
    )
    if not url or not service_key:
        pytest.skip("Supabase service role connection is not configured")

    headers = {
        "apikey": service_key,
        "authorization": f"Bearer {service_key}",
        "accept": "application/json",
    }
    return url, headers


def _assert_rest_select_ok(url: str, headers: dict[str, str], table: str, select: str) -> None:
    endpoint = f"{url}/rest/v1/{table}"
    try:
        response = httpx.get(
            endpoint,
            headers=headers,
            params={"select": select, "limit": "1"},
            timeout=10.0,
        )
    except httpx.RequestError as exc:
        pytest.skip(f"Supabase is not reachable: {exc}")

    assert response.status_code == 200, response.text


def test_subscription_schema_tables_and_profile_role_exist():
    url, headers = _supabase_schema_client()

    _assert_rest_select_ok(url, headers, "subscriptions", "id,user_id,status,plan,price_krw")
    _assert_rest_select_ok(url, headers, "usage_logs", "id,user_id,used_at,period_start,period_end")
    _assert_rest_select_ok(url, headers, "profiles", "role")
