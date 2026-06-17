# BOHUMFIT-055 파싱 병렬 워커 수 결정 + picklable 입력 회귀.
#
# PHASE1: parse_single_pdf 의 ~95%가 page.extract_text()(CPU 바운드)·파일 독립 → 파일 단위
# 프로세스 병렬로 총 파싱시간 단축. 단 메모리 피크는 워커수×1파일분 → 안전 기본은 순차(1),
# 메모리 헤드룸/명시 override 시에만 병렬. 분석 카운트·판정·결과 순서는 불변(파일 순서 보존).
import os
import pickle

import analyzer


def _set_env(monkeypatch, val):
    if val is None:
        monkeypatch.delenv("BOHUMFIT_PARSE_WORKERS", raising=False)
    else:
        monkeypatch.setenv("BOHUMFIT_PARSE_WORKERS", val)


# ── ① 명시 override: 1/0 → 순차, 2 → min(2,cpu,nfiles) ────────────────────
def test_env_override_sequential(monkeypatch):
    _set_env(monkeypatch, "1")
    assert analyzer._parse_workers(10) == 1
    _set_env(monkeypatch, "0")
    assert analyzer._parse_workers(10) == 1          # 0/음수 → 최소 1
    _set_env(monkeypatch, "잘못")
    assert analyzer._parse_workers(10) == 1          # 파싱 실패 → 1


def test_env_override_parallel(monkeypatch):
    _set_env(monkeypatch, "2")
    cpu = os.cpu_count() or 1
    assert analyzer._parse_workers(10) == min(2, cpu, 10)
    # 파일 수가 워커보다 적으면 파일 수로 캡
    assert analyzer._parse_workers(1) == 1
    _set_env(monkeypatch, "8")
    assert analyzer._parse_workers(10) == min(8, cpu, 10)   # cpu 캡


# ── ② 기본(env 미설정): 메모리 부족이면 순차, 단일 파일은 항상 1 ───────────
def test_default_single_file_sequential(monkeypatch):
    _set_env(monkeypatch, None)
    assert analyzer._parse_workers(1) == 1            # 파일 1개 → 병렬 의미 없음


def test_default_low_memory_sequential(monkeypatch):
    _set_env(monkeypatch, None)
    monkeypatch.setattr(analyzer, "_container_mem_bytes", lambda: 512 * 1024 * 1024)
    assert analyzer._parse_workers(10) == 1           # 512MB → 순차(OOM 회피)


def test_default_ample_memory_big_job_parallel(monkeypatch):
    _set_env(monkeypatch, None)
    monkeypatch.setattr(analyzer, "_container_mem_bytes", lambda: 2 * 1024 * 1024 * 1024)
    cpu = os.cpu_count() or 1
    big = 5 * 1024 * 1024   # ≥ _MIN_PARALLEL_BYTES
    expected = min(2, cpu, 10) if cpu >= 2 else 1
    assert analyzer._parse_workers(10, big) == expected


def test_default_small_job_sequential_even_with_memory(monkeypatch):
    # BOHUMFIT-055: 메모리 충분해도 총 업로드가 작으면(소규모) spawn 오버헤드 회피 위해 순차.
    _set_env(monkeypatch, None)
    monkeypatch.setattr(analyzer, "_container_mem_bytes", lambda: 2 * 1024 * 1024 * 1024)
    assert analyzer._parse_workers(10, 500 * 1024) == 1          # 0.5MB < 임계 → 순차
    assert analyzer._parse_workers(10) == 1                       # total_bytes 미지정(0) → 순차


# ── ③ _ParseInput: picklable + .read() 동기 bytes ─────────────────────────
def test_parse_input_picklable():
    pi = analyzer._ParseInput(b"%PDF-1.4 ...", "a.pdf")
    assert pi.read() == b"%PDF-1.4 ..." and pi.name == "a.pdf"
    pi2 = pickle.loads(pickle.dumps(pi))               # 워커 전달 가능해야 함
    assert pi2.read() == b"%PDF-1.4 ..." and pi2.name == "a.pdf"
