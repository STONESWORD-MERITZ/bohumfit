# BOHUMFIT-171b 분석 히스토리 2트랙 회귀 — recent 자동 기록·10개 롤링·승격·track 필터·7일 만료.
#
# 케이스: (a) 분석 시 recent 자동 기록(+실명 제거·격리) (b) recent 11개째 롤링 삭제
#         (c) recent→saved 승격 + 한도 검사 (d) track 필터 (e) recent 7일 만료(saved 90일 불침범)
# main 의존(slowapi/fastapi) → 미설치·마운트 truncation 시 skip(Codex/Windows 권위).
import os
import sys
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


# ── 상태 보존 가짜 Supabase (track·update·in_ 지원 — 156 가짜의 확장판) ────────
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
        self._update = None
        self._filters = []      # (op, column, value) — op ∈ eq/gte/lt/in
        self._single = False
        self._range = None
        self._cols = None

    def select(self, *cols, **k):
        joined = ",".join(cols)
        self._cols = [c.strip() for c in joined.split(",") if c.strip() and c.strip() != "*"] or None
        return self

    def insert(self, payload):
        self._op, self._insert = "insert", payload
        return self

    def update(self, payload):
        self._op, self._update = "update", payload
        return self

    def delete(self):
        self._op = "delete"
        return self

    def eq(self, c, v):  self._filters.append(("eq", c, v));  return self
    def gte(self, c, v): self._filters.append(("gte", c, v)); return self
    def lt(self, c, v):  self._filters.append(("lt", c, v));  return self
    def in_(self, c, v): self._filters.append(("in", c, list(v))); return self
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
            if op == "in" and rv not in v:
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
            return _Resp({"bohumfit_tier": role} if role else None)
        if self._name == "usage_logs":
            if self._op == "insert":
                return _Resp([{"id": "u"}])
            return _Resp([], count=0)   # 무료 분석 카운트 0 → 게이트 통과
        if self._name == "subscriptions":
            return _Resp(None)          # 미구독
        if self._name != main.HISTORY_TABLE:
            return _Resp(None)
        rows = self._admin.rows
        if self._op == "insert":
            if self._admin.fail_history_insert:
                raise RuntimeError("고의 실패(격리 테스트)")
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
        if self._op == "update":
            for r in matched:
                r.update(self._update)
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
        self.roles = roles or {}
        self.rows = rows or []
        self.seq = 0
        self.fail_history_insert = False

    def table(self, name):
        return _FakeQuery(self, name)


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────
RESULT = {"flagged_count": 1, "standard_reports": {}, "easy_reports": {}, "customer_name": "홍길동"}


def _iso_ago(days: int = 0, minutes: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days, minutes=minutes)).isoformat()


def _seed(admin, user_id, track, label="별칭", days_ago=0, minutes_ago=0):
    admin.seq += 1
    row = {"id": f"h{admin.seq}", "user_id": user_id, "label": label, "mode": "standard",
           "result": {"flagged_count": 0}, "track": track,
           "created_at": _iso_ago(days_ago, minutes_ago)}
    admin.rows.append(row)
    return row


def _recent_rows(admin):
    return [r for r in admin.rows if r.get("track") == "recent"]


@pytest.fixture
def make_client(monkeypatch):
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


async def _fake_run_analysis(**kwargs):
    """분석 파이프라인 무접촉 — analyze 엔드포인트 조립 코드만 통과시키는 최소 결과."""
    return {
        "standard_reports": {}, "easy_reports": {}, "flagged_codes": [],
        "analysis_today": date(2026, 7, 6), "ai_result": {}, "meritz_easy": {},
        "record_counts": {}, "parse_errors": [], "retry_warnings": [],
        "all_disease_summary": [], "customer_name": "홍길동",
        "covered_self_pay_by_year": {}, "covered_self_pay_captured": False,
    }


def _post_analyze(client):
    return client.post(
        "/api/analyze",
        files=[("files", ("a.pdf", b"%PDF-1.4 test", "application/pdf"))],
        data={"reference_date": "2026-07-06"},
    )


# ── (a) 분석 시 recent 자동 기록 (+실명 제거) / 기록 실패 격리 ────────────────
def test_analyze_auto_records_recent(make_client, monkeypatch):
    admin = _FakeAdmin(roles={"user-a": "customer"})
    client = make_client(admin, "user-a")
    monkeypatch.setattr(main, "run_analysis", _fake_run_analysis)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    r = _post_analyze(client)
    assert r.status_code == 200, r.text
    assert r.json().get("customer_name") == "홍길동"   # 응답에는 이름 유지(파일명용)

    recents = _recent_rows(admin)
    assert len(recents) == 1
    row = recents[0]
    assert row["label"] == "2026-07-06 분석" and row["mode"] == "standard"
    assert "customer_name" not in row["result"]        # ★실명 저장 전 제거
    assert row["result"]["reference_date"] == "2026-07-06"


def test_analyze_ok_when_recording_fails(make_client, monkeypatch):
    """자동 기록 실패가 분석 응답을 막지 않는다(격리)."""
    admin = _FakeAdmin(roles={"user-a": "customer"})
    admin.fail_history_insert = True
    client = make_client(admin, "user-a")
    monkeypatch.setattr(main, "run_analysis", _fake_run_analysis)
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    r = _post_analyze(client)
    assert r.status_code == 200, r.text
    assert _recent_rows(admin) == []


# ── (b) recent 11개째 → 오래된 것 롤링 삭제 ──────────────────────────────────
def test_recent_rolling_keeps_10(make_client):
    admin = _FakeAdmin(roles={"user-a": "customer"})
    oldest = _seed(admin, "user-a", "recent", label="가장 오래됨", minutes_ago=100)
    for i in range(main.HISTORY_RECENT_LIMIT - 1):
        _seed(admin, "user-a", "recent", label=f"r{i}", minutes_ago=99 - i)
    client = make_client(admin, "user-a")

    r = client.post("/history", json={"label": "11번째", "mode": "standard",
                                      "result": RESULT, "track": "recent"})
    assert r.status_code == 200, r.text
    assert r.json()["track"] == "recent" and r.json()["quota"]["max"] is None

    recents = _recent_rows(admin)
    assert len(recents) == main.HISTORY_RECENT_LIMIT          # 10개 유지
    assert all(row["id"] != oldest["id"] for row in recents)  # 가장 오래된 것 삭제
    assert any(row["label"] == "11번째" for row in recents)


# ── (c) recent → saved 승격 + 한도 검사 ──────────────────────────────────────
def test_promote_recent_to_saved(make_client):
    admin = _FakeAdmin(roles={"user-a": "customer"})
    row = _seed(admin, "user-a", "recent", label="2026-07-06 분석")
    client = make_client(admin, "user-a")

    r = client.patch(f"/history/{row['id']}/save", json={"label": "40대 남 고혈압"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["track"] == "saved" and body["label"] == "40대 남 고혈압"
    assert body["quota"] == {"used": 1, "max": main.HISTORY_FREE_LIMIT}
    stored = next(x for x in admin.rows if x["id"] == row["id"])
    assert stored["track"] == "saved" and stored["label"] == "40대 남 고혈압"
    # 이미 승격된 항목 재승격 → 404 (track=recent 조건 불일치)
    assert client.patch(f"/history/{row['id']}/save", json={"label": "다시"}).status_code == 404


def test_promote_blocked_by_saved_limit(make_client):
    admin = _FakeAdmin(roles={"user-a": "customer"})
    for i in range(main.HISTORY_FREE_LIMIT):
        _seed(admin, "user-a", "saved", label=f"기존{i}")
    row = _seed(admin, "user-a", "recent", label="승격 대상")
    client = make_client(admin, "user-a")

    r = client.patch(f"/history/{row['id']}/save", json={"label": "안 됨"})
    assert r.status_code == 409 and "10" in r.json()["detail"]
    stored = next(x for x in admin.rows if x["id"] == row["id"])
    assert stored["track"] == "recent"                        # 승격 안 됨
    # 타인 소유 승격 차단
    client_b = make_client(admin, "user-b")
    assert client_b.patch(f"/history/{row['id']}/save", json={"label": "탈취"}).status_code == 404


# ── (d) track 필터 ───────────────────────────────────────────────────────────
def test_list_track_filter(make_client):
    admin = _FakeAdmin(roles={"user-a": "customer"})
    _seed(admin, "user-a", "recent", label="r1", minutes_ago=2)
    _seed(admin, "user-a", "recent", label="r2", minutes_ago=1)
    _seed(admin, "user-a", "saved", label="s1")
    client = make_client(admin, "user-a")

    rec = client.get("/history?track=recent").json()
    assert rec["total"] == 2 and rec["track"] == "recent"
    assert rec["retention_days"] == main.HISTORY_RECENT_RETENTION_DAYS
    assert rec["quota"] == {"used": 2, "max": main.HISTORY_RECENT_LIMIT}
    assert all(i["track"] == "recent" for i in rec["items"])

    sav = client.get("/history?track=saved").json()
    assert sav["total"] == 1 and sav["items"][0]["label"] == "s1"
    assert sav["retention_days"] == main.HISTORY_RETENTION_DAYS

    assert client.get("/history?track=weird").status_code == 400
    assert client.post("/history", json={"label": "별", "mode": "easy",
                                         "result": RESULT, "track": "weird"}).status_code == 400


# ── (e) recent 7일 만료 — 조회 제외 + lazy 삭제, saved 90일 불침범 ─────────────
def test_recent_expires_after_7_days(make_client):
    admin = _FakeAdmin(roles={"user-a": "customer"})
    fresh = _seed(admin, "user-a", "recent", label="신선", days_ago=1)
    expired = _seed(admin, "user-a", "recent", label="만료", days_ago=8)
    saved_old = _seed(admin, "user-a", "saved", label="저장 8일", days_ago=8)
    client = make_client(admin, "user-a")

    rec = client.get("/history?track=recent").json()
    assert rec["total"] == 1 and rec["items"][0]["id"] == fresh["id"]
    assert all(r["id"] != expired["id"] for r in admin.rows)          # recent 8일 → lazy 삭제
    assert any(r["id"] == saved_old["id"] for r in admin.rows)        # saved 8일은 보존(90일 정책)
    assert client.get("/history?track=saved").json()["total"] == 1

    # 단건도 track 기준 만료: recent 8일 → 404
    expired2 = _seed(admin, "user-a", "recent", label="만료2", days_ago=9)
    assert client.get(f"/history/{expired2['id']}").status_code == 404
    assert all(r["id"] != expired2["id"] for r in admin.rows)
