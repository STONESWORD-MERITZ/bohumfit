# BOHUMFIT-156a 분석 히스토리 API 회귀 — Supabase admin을 상태 보존 가짜로 주입.
#
# 케이스: (a) 저장→목록→단건→삭제 왕복 (b) 타인 레코드 차단 (c) 무료 10건 초과 409
#         (d) internal 무제한 (e) 90일 초과 조회 제외 + lazy 삭제
# 추가:   입력 검증(label/mode/result), 실명(customer_name) 저장 전 제거.
# main 의존(slowapi/fastapi) → 미설치·마운트 truncation 시 skip(Codex/Windows 권위).
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytest.importorskip("slowapi")
pytest.importorskip("fastapi")

try:
    import main
except Exception as e:  # pragma: no cover — 샌드박스 마운트 truncation 회피 (ENV-MOUNT-NOTES)
    pytest.skip(f"main import 불가(샌드박스 마운트 제약) — Windows 검증에서 수행: {e}", allow_module_level=True)

from fastapi.testclient import TestClient  # noqa: E402


# ── 상태 보존 가짜 Supabase (bohumfit_analysis_history 인메모리 스토어) ────────
class _Resp:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class _FakeQuery:
    def __init__(self, admin, name):
        self._admin = admin
        self._name = name
        self._op = "select"
        self._insert = None
        self._filters = []      # (op, column, value) — op ∈ eq/gte/lt
        self._single = False
        self._range = None
        self._cols = None       # select 컬럼 프로젝션(실 Supabase 동작 재현)

    # 체이닝 API (main.py에서 쓰는 것만 구현)
    def select(self, *cols, **k):
        joined = ",".join(cols)
        self._cols = [c.strip() for c in joined.split(",") if c.strip() and c.strip() != "*"] or None
        return self
    def insert(self, payload):
        self._op, self._insert = "insert", payload
        return self
    def delete(self):
        self._op = "delete"
        return self
    def eq(self, c, v):  self._filters.append(("eq", c, v));  return self
    def gte(self, c, v): self._filters.append(("gte", c, v)); return self
    def lt(self, c, v):  self._filters.append(("lt", c, v));  return self
    def order(self, *a, **k): return self
    def range(self, start, end):
        self._range = (start, end)
        return self
    def single(self):
        self._single = True
        return self

    def _match(self, row) -> bool:
        for op, c, v in self._filters:
            rv = row.get(c)
            if op == "eq" and rv != v:
                return False
            # created_at은 main·테스트 모두 isoformat(+00:00) → 문자열 비교 = 시간 비교
            if op == "gte" and not (str(rv) >= str(v)):
                return False
            if op == "lt" and not (str(rv) < str(v)):
                return False
        return True

    def execute(self):
        if self._name == "profiles":
            uid = next((v for op, c, v in self._filters if c == "id"), None)
            role = self._admin.roles.get(uid)
            return _Resp({"role": role} if role else None)
        if self._name != main.HISTORY_TABLE:
            return _Resp(None)
        rows = self._admin.rows
        if self._op == "insert":
            self._admin.seq += 1
            row = {"id": f"h{self._admin.seq}",
                   "created_at": datetime.now(timezone.utc).isoformat(),
                   **self._insert}
            rows.append(row)
            return _Resp([dict(row)])
        matched = [r for r in rows if self._match(r)]
        if self._op == "delete":
            self._admin.rows = [r for r in rows if r not in matched]
            return _Resp([dict(r) for r in matched])
        # select
        matched.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        total = len(matched)
        if self._range:
            s, e = self._range
            matched = matched[s:e + 1]
        if self._cols:
            data = [{c: r.get(c) for c in self._cols} for r in matched]
        else:
            data = [dict(r) for r in matched]
        if self._single:
            return _Resp(data[0] if data else None, count=total)
        return _Resp(data, count=total)


class _FakeAdmin:
    def __init__(self, roles=None, rows=None):
        self.roles = roles or {}          # user_id -> profiles.role
        self.rows = rows or []            # bohumfit_analysis_history
        self.seq = 0

    def table(self, name):
        return _FakeQuery(self, name)


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────
RESULT = {"flagged_count": 1, "standard_reports": {"[Q1] 3개월": []},
          "easy_reports": {}, "customer_name": "홍길동"}


def _iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _seed_row(admin, user_id, label="별칭", days_ago=0, mode="standard"):
    admin.seq += 1
    # BOHUMFIT-171b: track 컬럼 도입(기본 'saved') — 기존 saved 트랙 시드에 반영(정책값 불변).
    row = {"id": f"h{admin.seq}", "user_id": user_id, "label": label, "mode": mode,
           "result": {"flagged_count": 0}, "created_at": _iso_days_ago(days_ago), "track": "saved"}
    admin.rows.append(row)
    return row


@pytest.fixture
def make_client(monkeypatch):
    """admin 주입 + verify_jwt 오버라이드 TestClient. 레이트리밋은 테스트 간 누적 방지로 off."""
    created = {}

    def _make(admin, user_id="user-a"):
        monkeypatch.setattr(main, "_get_supabase_admin", lambda: admin)
        main.app.dependency_overrides[main.verify_jwt] = lambda: user_id
        main.limiter.enabled = False
        created["done"] = True
        return TestClient(main.app)

    yield _make
    if created:
        main.app.dependency_overrides.pop(main.verify_jwt, None)
        main.limiter.enabled = True


# ── (a) 저장→목록→단건→삭제 왕복 ─────────────────────────────────────────────
def test_roundtrip_create_list_get_delete(make_client):
    admin = _FakeAdmin(roles={"user-a": "customer"})
    client = make_client(admin, "user-a")

    r = client.post("/history", json={"label": "40대 남 고혈압", "mode": "standard", "result": RESULT})
    assert r.status_code == 200, r.text
    body = r.json()
    hid = body["id"]
    assert hid and body["label"] == "40대 남 고혈압"
    assert body["quota"] == {"used": 1, "max": main.HISTORY_FREE_LIMIT}

    r = client.get("/history")
    assert r.status_code == 200
    lst = r.json()
    assert lst["total"] == 1 and len(lst["items"]) == 1
    item = lst["items"][0]
    assert item["id"] == hid and item["label"] == "40대 남 고혈압" and item["mode"] == "standard"
    assert "result" not in item                      # 목록은 result 제외
    assert lst["retention_days"] == 90

    r = client.get(f"/history/{hid}")
    assert r.status_code == 200
    row = r.json()
    assert row["result"]["flagged_count"] == 1
    assert "customer_name" not in row["result"]      # ★실명 필드는 저장 전 제거

    r = client.delete(f"/history/{hid}")
    assert r.status_code == 200 and r.json()["ok"] is True
    assert client.get("/history").json()["total"] == 0
    assert client.get(f"/history/{hid}").status_code == 404


# ── (b) 타인 레코드 차단 (단건 조회·삭제 모두 404 — 존재 비노출) ──────────────
def test_other_users_record_blocked(make_client):
    admin = _FakeAdmin(roles={"user-a": "customer", "user-b": "customer"})
    row = _seed_row(admin, "user-a", label="A의 기록")

    client_b = make_client(admin, "user-b")
    assert client_b.get(f"/history/{row['id']}").status_code == 404
    assert client_b.delete(f"/history/{row['id']}").status_code == 404
    assert client_b.get("/history").json()["total"] == 0
    assert any(r["id"] == row["id"] for r in admin.rows)   # 원본 보존(삭제 안 됨)


# ── (c) 무료 10건 초과 → 409 + 안내 ──────────────────────────────────────────
def test_free_limit_10_returns_409(make_client):
    admin = _FakeAdmin(roles={"user-a": "customer"})
    for i in range(main.HISTORY_FREE_LIMIT):
        _seed_row(admin, "user-a", label=f"기존{i}")
    client = make_client(admin, "user-a")

    r = client.post("/history", json={"label": "11번째", "mode": "standard", "result": RESULT})
    assert r.status_code == 409
    assert "10" in r.json()["detail"]
    assert len(admin.rows) == main.HISTORY_FREE_LIMIT   # 초과 저장 없음


# ── (d) internal 무제한 ──────────────────────────────────────────────────────
def test_internal_unlimited(make_client):
    admin = _FakeAdmin(roles={"user-i": "internal"})
    for i in range(main.HISTORY_FREE_LIMIT + 5):
        _seed_row(admin, "user-i", label=f"기존{i}")
    client = make_client(admin, "user-i")

    r = client.post("/history", json={"label": "16번째", "mode": "easy", "result": RESULT})
    assert r.status_code == 200
    assert r.json()["quota"]["max"] is None
    assert client.get("/history").json()["quota"]["max"] is None


# ── (e) 90일 초과 → 조회 제외 + lazy 삭제 ────────────────────────────────────
def test_expired_excluded_and_lazy_purged(make_client):
    admin = _FakeAdmin(roles={"user-a": "customer"})
    fresh = _seed_row(admin, "user-a", label="신선", days_ago=1)
    expired = _seed_row(admin, "user-a", label="만료", days_ago=91)
    client = make_client(admin, "user-a")

    lst = client.get("/history").json()
    assert lst["total"] == 1
    assert [i["id"] for i in lst["items"]] == [fresh["id"]]
    # lazy 삭제: 목록 접근 시 본인 만료 레코드가 실제로 제거됨
    assert all(r["id"] != expired["id"] for r in admin.rows)

    # 단건도 만료면 404 (재시드 후 확인)
    expired2 = _seed_row(admin, "user-a", label="만료2", days_ago=120)
    assert client.get(f"/history/{expired2['id']}").status_code == 404
    assert all(r["id"] != expired2["id"] for r in admin.rows)


# ── 입력 검증 ────────────────────────────────────────────────────────────────
def test_create_validation(make_client):
    admin = _FakeAdmin(roles={"user-a": "customer"})
    client = make_client(admin, "user-a")

    assert client.post("/history", json={"label": "  ", "mode": "standard", "result": RESULT}).status_code == 400
    assert client.post("/history", json={"label": "별", "mode": "premium", "result": RESULT}).status_code == 400
    assert client.post("/history", json={"label": "별", "mode": "easy", "result": {}}).status_code == 400
    assert client.post("/history", json={"label": "가" * 41, "mode": "easy", "result": RESULT}).status_code == 400
    assert admin.rows == []


# ── Supabase 미설정 → 503 graceful ───────────────────────────────────────────
def test_disabled_admin_503(make_client, monkeypatch):
    client = make_client(_FakeAdmin(), "user-a")
    monkeypatch.setattr(main, "_get_supabase_admin", lambda: None)
    assert client.get("/history").status_code == 503
    assert client.post("/history", json={"label": "별", "mode": "easy", "result": RESULT}).status_code == 503
