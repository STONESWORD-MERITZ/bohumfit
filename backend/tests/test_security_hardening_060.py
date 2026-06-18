# BOHUMFIT-060 백엔드 보안 강화 회귀 — 운영모드·문서비활성·헬스최소화·레이트리밋 한국어.
#
# 분석 판정/파싱/result_builder 무변경. 보안 표면만 검증한다.
#   BF-01 운영 debug=False·전역 예외 일반화 / BF-02 운영 문서 비활성(개발은 유지) /
#   BF-05 /api/health 최소화 / BF-03 레이트리밋 한국어 429·기존 한도·업로드 제한 유지.
# main 은 slowapi/sentry/fastapi 의존 → 미설치 환경에선 자동 skip(Codex/Windows 권위).
import asyncio
import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("slowapi")
pytest.importorskip("fastapi")


def _load_main(monkeypatch, env=None):
    if env is None:
        monkeypatch.delenv("SERVICE_ENV", raising=False)
    else:
        monkeypatch.setenv("SERVICE_ENV", env)
    import main
    importlib.reload(main)
    return main


def _client(main):
    from fastapi.testclient import TestClient
    return TestClient(main.app)


def _fake_request():
    from starlette.requests import Request
    return Request({"type": "http", "method": "GET", "path": "/x", "headers": []})


# ── BF-05 헬스 최소화 ────────────────────────────────────────────────────────
def test_health_minimized(monkeypatch):
    main = _load_main(monkeypatch, "production")
    r = _client(main).get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body == {"status": "ok"}                 # env·deps·version 노출 0
    assert "env" not in body and "version" not in body and "deps" not in body


# ── BF-02 문서: 운영 비활성 / 개발 유지 ──────────────────────────────────────
def test_docs_disabled_in_production(monkeypatch):
    main = _load_main(monkeypatch, "production")
    assert main.IS_PRODUCTION is True
    c = _client(main)
    assert c.get("/docs").status_code == 404
    assert c.get("/redoc").status_code == 404
    assert c.get("/openapi.json").status_code == 404


def test_docs_enabled_in_development(monkeypatch):
    main = _load_main(monkeypatch, "development")
    assert main.IS_DEVELOPMENT is True
    c = _client(main)
    assert c.get("/docs").status_code == 200
    assert c.get("/openapi.json").status_code == 200


# ── BF-01 안전 기본: ENV 미설정/오타 → production ────────────────────────────
def test_missing_env_treated_as_production(monkeypatch):
    main = _load_main(monkeypatch, None)
    assert main.IS_PRODUCTION is True and main.IS_DEVELOPMENT is False


def test_unknown_env_treated_as_production(monkeypatch):
    main = _load_main(monkeypatch, "staging-typo")
    assert main.IS_PRODUCTION is True


# ── BF-01 전역 예외 핸들러: 일반화 메시지·트레이스백 미노출 ───────────────────
def test_unhandled_exception_generic_message(monkeypatch):
    main = _load_main(monkeypatch, "production")
    resp = asyncio.run(main._unhandled_exception_handler(_fake_request(), RuntimeError("DB secret boom")))
    assert resp.status_code == 500
    text = resp.body.decode("utf-8")
    assert "처리 중 오류" in text
    assert "boom" not in text and "RuntimeError" not in text   # 상세 미노출


# ── BF-03 레이트리밋: 한국어 429 핸들러 ──────────────────────────────────────
def test_rate_limit_handler_korean_429(monkeypatch):
    main = _load_main(monkeypatch, "production")
    resp = main._rate_limit_handler(_fake_request(), Exception("limit"))
    assert resp.status_code == 429
    assert "너무 잦" in resp.body.decode("utf-8")


# ── BF-03 비용 엔드포인트에 레이트리밋 적용 + 업로드 제한 유지 ────────────────
def test_cost_endpoints_have_rate_limit(monkeypatch):
    main = _load_main(monkeypatch, "production")
    paths = {r.path for r in main.app.routes}
    assert "/api/analyze" in paths and "/api/report/pdf" in paths
    assert main.app.state.limiter is main.limiter
    from slowapi.errors import RateLimitExceeded
    assert RateLimitExceeded in main.app.exception_handlers


def test_upload_limits_preserved(monkeypatch):
    main = _load_main(monkeypatch, "production")
    assert main.MAX_FILE_COUNT == 10
    assert main.MAX_FILE_SIZE == 15 * 1024 * 1024
    assert main.MAX_TOTAL_SIZE == 40 * 1024 * 1024
