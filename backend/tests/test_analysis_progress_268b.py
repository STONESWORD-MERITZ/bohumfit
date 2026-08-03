"""BOHUMFIT-268b — 분석 진행 저장소·조회 엔드포인트.

★핵심 가드: ①job_id 미전송 시 기존과 100% 동일(무동작) ②타인 작업 조회 차단
③TTL·상한으로 메모리 누수 없음 ④PII(환자명·상병코드·병명) 미저장 ⑤완료 순서 무관.
"""
import time
from pathlib import Path

import pytest

import progress

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _clean():
    progress._reset_for_test()
    yield
    progress._reset_for_test()


# ── ★하위 호환: job_id 없으면 아무 일도 없다 ─────────────────────────────────
def test_no_job_id_is_noop():
    progress.start("", "user-1", 3)
    progress.record_file("", "a.pdf", 10, {"basic": 10})
    progress.finish("")
    assert progress._job_count() == 0
    assert progress.snapshot("", "user-1") is None


def test_record_on_unknown_job_is_ignored():
    """등록되지 않은 ID로 기록해도 조용히 무시한다(진행 표시가 분석을 방해하면 안 된다)."""
    progress.record_file("ghost", "a.pdf", 10, {"basic": 10})
    assert progress._job_count() == 0


# ── 진행 누적·조회 ──────────────────────────────────────────────────────────
def test_records_accumulate_in_completion_order():
    """★완료 순서대로 쌓인다 — 파일 순서와 무관해도 정상이다(병렬 파싱 전제)."""
    progress.start("j1", "user-1", 3)
    progress.record_file("j1", "c.pdf", 5, {"pharma": 5})
    progress.record_file("j1", "a.pdf", 20, {"basic": 20})

    snap = progress.snapshot("j1", "user-1")
    assert snap["total_files"] == 3
    assert snap["done_files"] == 2
    assert [f["filename"] for f in snap["files"]] == ["서류 1", "서류 2"]
    assert snap["total_records"] == 25
    assert snap["finished"] is False


def test_finish_marks_done():
    progress.start("j1", "user-1", 1)
    progress.record_file("j1", "a.pdf", 3, {"basic": 3})
    progress.finish("j1")
    snap = progress.snapshot("j1", "user-1")
    assert snap["finished"] is True
    assert snap["failed"] is False


def test_finish_failed_is_visible():
    progress.start("j1", "user-1", 1)
    progress.finish("j1", failed=True)
    snap = progress.snapshot("j1", "user-1")
    assert snap["finished"] is True and snap["failed"] is True


# ── ★소유자 격리 ───────────────────────────────────────────────────────────
def test_other_user_cannot_read():
    progress.start("j1", "user-1", 2)
    progress.record_file("j1", "a.pdf", 10, {"basic": 10})
    # ★남의 작업은 "없는 것"으로 보인다 — 존재 여부조차 알려주지 않는다.
    assert progress.snapshot("j1", "user-2") is None
    assert progress.snapshot("j1", "") is None


def test_jobs_are_isolated_by_id():
    progress.start("j1", "user-1", 1)
    progress.start("j2", "user-2", 2)
    progress.record_file("j1", "a.pdf", 1, {})
    progress.record_file("j2", "b.pdf", 2, {})
    assert progress.snapshot("j1", "user-1")["files"][0]["filename"] == "서류 1"
    assert progress.snapshot("j2", "user-2")["files"][0]["filename"] == "서류 1"


# ── ★TTL·메모리 누수 ───────────────────────────────────────────────────────
def test_ttl_purges_old_jobs(monkeypatch):
    progress.start("old", "user-1", 1)
    # 시간을 TTL 너머로 민다.
    base = time.monotonic()
    monkeypatch.setattr(progress, "_now", lambda: base + progress.TTL_SECONDS + 1)
    assert progress.snapshot("old", "user-1") is None
    assert progress._job_count() == 0


def test_job_count_is_capped():
    for i in range(progress.MAX_JOBS + 20):
        progress.start(f"j{i}", "user-1", 1)
    assert progress._job_count() <= progress.MAX_JOBS


def test_drop_removes_job():
    progress.start("j1", "user-1", 1)
    progress.drop("j1")
    assert progress._job_count() == 0


# ── ★PII 미저장 ────────────────────────────────────────────────────────────
def test_snapshot_contains_no_health_info():
    progress.start("j1", "user-1", 1)
    source_filename = "고객명 포함 원본.pdf"
    progress.record_file("j1", source_filename, 120, {"basic": 120}, errors=0)
    snap = progress.snapshot("j1", "user-1")
    entry = snap["files"][0]
    # 저장 키가 화이트리스트 그대로다 — 코드·병명·환자명이 끼어들 자리가 없다.
    assert set(entry.keys()) == {"filename", "records", "ftypes", "errors"}
    assert set(snap.keys()) == {
        "job_id", "total_files", "done_files", "files", "total_records", "finished", "failed",
    }
    assert source_filename not in str(snap)


def test_recorder_coerces_types_and_truncates():
    """이상한 입력이 들어와도 저장소가 깨지지 않는다."""
    progress.start("j1", "user-1", 1)
    progress.record_file("j1", "x" * 500, -5, {"a" * 50: "3"}, errors=-1)
    entry = progress.snapshot("j1", "user-1")["files"][0]
    assert entry["filename"] == "서류 1"
    assert entry["records"] == 0 and entry["errors"] == 0
    assert list(entry["ftypes"].values()) == [3]


# ── analyzer 접합(무동작 보장) ──────────────────────────────────────────────
def test_log_parsed_without_job_id_writes_nothing():
    from analyzer import _log_parsed

    _log_parsed("a.pdf", {"records": [{"_ftype": "basic"}], "parse_errors": []})
    assert progress._job_count() == 0


def test_log_parsed_with_job_id_records():
    from analyzer import _log_parsed

    progress.start("j1", "user-1", 1)
    _log_parsed("a.pdf", {"records": [{"_ftype": "basic"}, {"_ftype": "detail"}], "parse_errors": ["x"]}, "j1")
    entry = progress.snapshot("j1", "user-1")["files"][0]
    assert entry["filename"] == "서류 1"
    assert entry["records"] == 2 and entry["errors"] == 1
    assert entry["ftypes"] == {"basic": 1, "detail": 1}


# ── 보호 영역 diff 0 ───────────────────────────────────────────────────────
def test_protected_modules_untouched_by_268b():
    """★`pipeline/`·`filters.py`·`coverage/`에 268b 흔적이 없다."""
    for rel in ["backend/filters.py"]:
        assert "268b" not in (ROOT / rel).read_text(encoding="utf-8")
    for path in (ROOT / "backend" / "pipeline").glob("*.py"):
        assert "268b" not in path.read_text(encoding="utf-8"), path.name
    for path in (ROOT / "backend" / "coverage").glob("*.py"):
        assert "268b" not in path.read_text(encoding="utf-8"), path.name
