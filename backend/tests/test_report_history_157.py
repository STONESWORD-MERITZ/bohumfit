# BOHUMFIT-157 히스토리 리포트 PDF 다운로드 회귀 — 소유권·saved 전용·별칭 파일명.
#
# 케이스: (a) saved 항목 PDF 200 + 파일명(별칭 sanitize·YYYYMMDD) + payload 구성(실명 "")
#         (b) recent 항목 409 + "저장" 안내 (c) 타인 404 (d) 별칭 금지 문자 제거
#         (e) 만료(91일)·부재 404
# 렌더러(Chromium)는 monkeypatch — 분석 파이프라인·실PDF 무접촉.
import os
import sys
import urllib.parse
from datetime import date, datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("slowapi")
pytest.importorskip("fastapi")

try:
    import main
except Exception as e:  # pragma: no cover — 샌드박스 마운트 truncation 회피 (ENV-MOUNT-NOTES)
    pytest.skip(f"main import 불가(샌드박스 마운트 제약) — Windows 검증에서 수행: {e}", allow_module_level=True)

from fastapi.testclient import TestClient  # noqa: E402


# ── 상태 보존 가짜 Supabase (171 가짜의 축약판 — 본 테스트는 단건 select만 필요) ─
class _Resp:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class _FakeQuery:
    def __init__(self, admin, name):
        self._admin = admin
        self._name = name
        self._filters = []
        self._single = False

    def select(self, *a, **k): return self
    def eq(self, c, v):  self._filters.append(("eq", c, v));  return self
    def gte(self, c, v): self._filters.append(("gte", c, v)); return self
    def lt(self, c, v):  self._filters.append(("lt", c, v));  return self
    def order(self, *a, **k): return self
    def range(self, *a, **k): return self
    def single(self):
        self._single = True
        return self
    def insert(self, payload): return self
    def delete(self): return self
    def update(self, payload): return self
    def in_(self, c, v): return self

    def _match(self, row) -> bool:
        for op, c, v in self._filters:
            rv = row.get(c)
            if op == "eq" and rv != v:
                return False
            if op == "gte" and not (str(rv) >= str(v)):
                return False
            if op == "lt" and not (str(rv) < str(v)):
                return False
        return True

    def execute(self):
        if self._name != main.HISTORY_TABLE:
            return _Resp(None)
        matched = [dict(r) for r in self._admin.rows if self._match(r)]
        if self._single:
            return _Resp(matched[0] if matched else None)
        return _Resp(matched, count=len(matched))


class _FakeAdmin:
    def __init__(self, rows=None):
        self.rows = rows or []

    def table(self, name):
        return _FakeQuery(self, name)


RESULT = {
    "standard_reports": {"[1번질문] 3개월": []},
    "easy_reports": {},
    "all_disease_summary": [],
    "total_med_sum": 42,
    "reference_date": "2026-07-01",
}


def _row(user_id="user-a", track="saved", label="40대 남 고혈압", days_ago=0, rid="h1", result=None):
    return {
        "id": rid, "user_id": user_id, "label": label, "mode": "standard", "track": track,
        "result": RESULT if result is None else result,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat(),
    }


@pytest.fixture
def make_client(monkeypatch):
    created = {}
    captured = {}

    async def _fake_pdf(report_type, payload, generated_at=None):
        captured["report_type"] = report_type
        captured["payload"] = payload
        return b"%PDF-1.7 fake-157"

    def _make(admin, user_id="user-a"):
        monkeypatch.setattr(main, "_get_supabase_admin", lambda: admin)
        monkeypatch.setattr(main, "generate_report_pdf", _fake_pdf)
        main.app.dependency_overrides[main.verify_jwt] = lambda: user_id
        main.limiter.enabled = False
        created["done"] = True
        return TestClient(main.app)

    _make.captured = captured
    yield _make
    if created:
        main.app.dependency_overrides.pop(main.verify_jwt, None)
        main.limiter.enabled = True


# ── (a) saved 항목 → 200 PDF + 파일명 + payload 구성 ─────────────────────────
def test_saved_item_downloads_pdf(make_client):
    admin = _FakeAdmin(rows=[_row()])
    client = make_client(admin, "user-a")

    r = client.post("/history/h1/report-pdf")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content.startswith(b"%PDF-")
    assert r.headers.get("cache-control") == "no-store"

    date_part = "20260701"
    expected = urllib.parse.quote(f"BohumFit_고지의무리포트_40대남고혈압_{date_part}.pdf")
    assert expected in r.headers.get("content-disposition", "")

    # 렌더 payload: 실명은 빈 문자열(156a 미저장 정책), 저장된 result 키가 그대로 전달
    cap = make_client.captured
    assert cap["report_type"] == "disclosure"
    assert cap["payload"]["customer_name"] == ""
    assert cap["payload"]["standard_reports"] == RESULT["standard_reports"]
    assert cap["payload"]["reference_date"] == "2026-07-01"
    assert cap["payload"]["total_med_sum"] == 42


# ── (b) recent 항목 → 409 + 저장 안내 ────────────────────────────────────────
def test_recent_item_blocked_409(make_client):
    admin = _FakeAdmin(rows=[_row(track="recent", rid="h2")])
    client = make_client(admin, "user-a")

    r = client.post("/history/h2/report-pdf")
    assert r.status_code == 409
    assert "저장" in r.json()["detail"]


# ── (c) 타인 히스토리 → 404 (존재 비노출) ────────────────────────────────────
def test_other_user_blocked_404(make_client):
    admin = _FakeAdmin(rows=[_row(user_id="user-a", rid="h3")])
    client_b = make_client(admin, "user-b")

    assert client_b.post("/history/h3/report-pdf").status_code == 404


# ── (d) 별칭 금지 문자 제거 파일명 ───────────────────────────────────────────
def test_label_sanitized_in_filename(make_client):
    admin = _FakeAdmin(rows=[_row(label='김*고객/테스트<>:"|?! 별칭', rid="h4")])
    client = make_client(admin, "user-a")

    r = client.post("/history/h4/report-pdf")
    assert r.status_code == 200
    date_part = "20260701"
    # 금지 문자(*, /, <, >, :, ", |, ?, !, 공백)가 전부 제거된 별칭만 파일명에 남는다.
    expected = urllib.parse.quote(f"BohumFit_고지의무리포트_김고객테스트별칭_{date_part}.pdf")
    assert expected in r.headers.get("content-disposition", "")


# ── (e) 만료(saved 91일)·부재 → 404 ──────────────────────────────────────────
def test_expired_and_missing_404(make_client):
    admin = _FakeAdmin(rows=[_row(days_ago=91, rid="h5")])
    client = make_client(admin, "user-a")

    assert client.post("/history/h5/report-pdf").status_code == 404   # 만료
    assert client.post("/history/none/report-pdf").status_code == 404  # 부재
