"""BOHUMFIT-268b — 분석 진행 상태 저장소(프로세스 메모리).

왜 메모리인가: uvicorn 워커가 1개로 확정돼(268a 조사) 프로세스 간 공유가 필요 없다.
Supabase 테이블을 만들면 스키마·보존정책·PII 관리가 따라붙는데, 진행 표시는
**분석이 끝나면 버려도 되는 값**이라 그만한 무게가 필요 없다.

★PII 원칙: 원본 파일명도 고객명을 포함할 수 있어 저장하지 않고 완료 순서 기반
  익명 라벨(`서류 N`)만 둔다. 환자명·상병코드·병명 등 건강정보도 저장하지 않는다.

★TTL: 완료 후 일정 시간이 지나면 자동 삭제한다. 어떤 경로로 끝나든(성공·실패·중단)
  메모리가 무한히 늘지 않아야 한다.

★스레드 안전: `analyzer`의 병렬 파싱 루프가 `asyncio.to_thread`(워커 스레드)에서 기록하고,
  조회는 이벤트 루프 스레드에서 일어난다. 그래서 단일 락으로 감싼다.
"""
from __future__ import annotations

import threading
import time
from typing import Any

# 완료·미완료 무관하게 이만큼 지나면 버린다(폴링 간격 1.5초 대비 충분히 길다).
TTL_SECONDS = 15 * 60
# 방어선 — 동시에 이보다 많은 작업이 쌓이면 오래된 것부터 정리한다.
MAX_JOBS = 200

_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def _now() -> float:
    return time.monotonic()


def _purge_locked(now: float) -> None:
    """만료분 삭제 + 상한 초과 시 오래된 것부터 정리. ★락을 이미 잡은 상태에서 호출한다."""
    expired = [jid for jid, job in _jobs.items() if now - job["created_at"] > TTL_SECONDS]
    for jid in expired:
        _jobs.pop(jid, None)
    if len(_jobs) > MAX_JOBS:
        oldest = sorted(_jobs.items(), key=lambda kv: kv[1]["created_at"])
        for jid, _ in oldest[: len(_jobs) - MAX_JOBS]:
            _jobs.pop(jid, None)


def start(job_id: str, owner: str, total_files: int) -> None:
    """작업을 등록한다. job_id가 비어 있으면 아무것도 하지 않는다(하위 호환)."""
    if not job_id or not owner:
        return
    now = _now()
    with _lock:
        _jobs[job_id] = {
            "owner": owner,
            "total_files": max(0, int(total_files or 0)),
            "files": [],          # 완료 순서대로 쌓인다(★파일 순서가 아니다)
            "created_at": now,
            "finished_at": None,
            "failed": False,
        }
        # ★새로 넣은 뒤에 정리한다 — 넣기 전에만 정리하면 상한을 1개씩 넘긴다.
        #   방금 등록한 작업은 가장 최신이라 상한 정리 대상이 되지 않는다.
        _purge_locked(now)


def record_file(job_id: str, filename: str, records: int, ftypes: dict[str, int], errors: int = 0) -> None:
    """파일 하나의 파싱 완료를 기록한다.

    ★여기 들어오는 값은 전부 "무엇이 얼마나 처리됐는지"일 뿐 건강정보가 아니다.
    등록되지 않은 job_id는 조용히 무시한다(진행 표시가 분석을 방해하면 안 된다).
    """
    if not job_id:
        return
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job["files"].append(
            {
                "filename": f"서류 {len(job['files']) + 1}",  # 원본 파일명은 고객명 PII 가능 — 저장 금지
                "records": max(0, int(records or 0)),
                # 유형별 건수(basic/detail/pharma 등) — 값은 정수만 담는다.
                "ftypes": {str(k)[:20]: int(v or 0) for k, v in (ftypes or {}).items()},
                "errors": max(0, int(errors or 0)),
            }
        )


def finish(job_id: str, failed: bool = False) -> None:
    """분석 종료를 표시한다(성공·실패 모두). 클라이언트는 이걸 보고 폴링을 멈춘다."""
    if not job_id:
        return
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job["finished_at"] = _now()
        job["failed"] = bool(failed)


def snapshot(job_id: str, owner: str) -> dict[str, Any] | None:
    """진행 상황을 읽는다.

    ★소유자가 다르면 **없는 것처럼** None을 돌려준다 — 남의 작업 존재 여부조차 알려주지 않는다.
    """
    if not job_id or not owner:
        return None
    now = _now()
    with _lock:
        _purge_locked(now)
        job = _jobs.get(job_id)
        if job is None or job["owner"] != owner:
            return None
        return {
            "job_id": job_id,
            "total_files": job["total_files"],
            "done_files": len(job["files"]),
            "files": [dict(f) for f in job["files"]],
            "total_records": sum(f["records"] for f in job["files"]),
            "finished": job["finished_at"] is not None,
            "failed": job["failed"],
        }


def drop(job_id: str) -> None:
    """명시적 삭제(테스트·정리용)."""
    if not job_id:
        return
    with _lock:
        _jobs.pop(job_id, None)


def _reset_for_test() -> None:
    """테스트 전용 — 저장소를 비운다."""
    with _lock:
        _jobs.clear()


def _job_count() -> int:
    """테스트 전용 — 누수 확인."""
    with _lock:
        return len(_jobs)
