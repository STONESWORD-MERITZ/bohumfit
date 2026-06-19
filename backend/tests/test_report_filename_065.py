# BOHUMFIT-065 PDF 파일명(고객이름+분석기준일) 회귀 — 서버 Content-Disposition.
#   파일명 = 보험핏-고지내역-{성명}-{기준일}.pdf, 이름 없으면 날짜만(폴백). 비ASCII는 RFC5987.
# main 은 slowapi/fastapi 의존 → 미설치 시 자동 skip(Codex/Windows 권위).
import importlib
import os
import sys
import urllib.parse

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("slowapi")
pytest.importorskip("fastapi")


def _client(monkeypatch):
    monkeypatch.setenv("SERVICE_ENV", "production")
    import main
    importlib.reload(main)
    from fastapi.testclient import TestClient

    async def _fake_gen(report_type, payload, *a, **k):
        return b"%PDF-1.4 fake-bytes"

    monkeypatch.setattr(main, "generate_report_pdf", _fake_gen)
    main.app.dependency_overrides[main.verify_jwt] = lambda: "user-test"
    return main, TestClient(main.app)


def _post(client, body):
    return client.post("/api/report/pdf", json=body, headers={"Authorization": "Bearer x"})


def test_filename_with_name_and_refdate(monkeypatch):
    main, c = _client(monkeypatch)
    r = _post(c, {"report_type": "disclosure", "reference_date": "2026-06-11", "customer_name": "홍길동"})
    assert r.status_code == 200
    cd = r.headers["content-disposition"]
    assert urllib.parse.quote("보험핏-고지내역-홍길동-2026-06-11.pdf") in cd   # RFC5987
    assert 'filename="BF-disclosure-2026-06-11.pdf"' in cd                      # ASCII 폴백
    main.app.dependency_overrides.clear()


def test_filename_fallback_no_name(monkeypatch):
    main, c = _client(monkeypatch)
    r = _post(c, {"report_type": "disclosure", "reference_date": "2026-06-11"})
    assert r.status_code == 200
    cd = r.headers["content-disposition"]
    assert urllib.parse.quote("보험핏-고지내역-2026-06-11.pdf") in cd   # 날짜만(폴백)
    assert "홍길동" not in cd
    main.app.dependency_overrides.clear()


def test_filename_sanitizes_special_chars(monkeypatch):
    main, c = _client(monkeypatch)
    r = _post(c, {"report_type": "disclosure", "reference_date": "2026-06-11", "customer_name": "홍 길/동*"})
    cd = r.headers["content-disposition"]
    assert urllib.parse.quote("보험핏-고지내역-홍길동-2026-06-11.pdf") in cd   # 공백·특수문자 제거
    main.app.dependency_overrides.clear()
