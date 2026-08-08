# -*- coding: utf-8 -*-
"""BOHUMFIT-277 — PII 저장·로그 경계 봉인(B-F1·B-F2·B-F5 서버 측).

★설계 원칙: **서버에서 익명화한다.** 271이 화면 표시 직전만 처리해 응답 raw·운영 로그·DB 저장분이
  전부 열려 있었다(275 B-F1·B-F2). 이 파일은 그 경계가 다시 열리지 않도록 고정한다.
"""
from __future__ import annotations

import logging

import pytest

from pii import (
    DOCUMENT_SLOT_PREFIX,
    anonymize_parse_errors,
    contains_any_filename,
    document_slot,
    mask_filenames,
    scrub_pdf_filenames_deep,
)

# 실 PDF/PII는 쓰지 않는다 — 실명을 포함한 **합성** 파일명이다.
REAL_NAME_FILES = ["가상고객A 최근 3개월.pdf", "가상고객B 진료내역.pdf"]


# ── 익명 slot 규칙이 268b·271과 같은가 ────────────────────────────────────
def test_slot_rule_matches_268b_and_271():
    """★규칙이 갈라지면 같은 파일이 화면마다 다른 번호로 보인다."""
    assert document_slot(0) == "서류 1"
    assert document_slot(2) == "서류 3"
    assert DOCUMENT_SLOT_PREFIX == "서류"


def test_progress_store_uses_same_prefix():
    """268b 진행 저장소와 같은 접두어를 쓴다(소스 계약 고정)."""
    import pathlib

    src = pathlib.Path(__file__).resolve().parents[1] / "progress.py"
    assert '서류 ' in src.read_text(encoding="utf-8")


# ── B-F1: 응답 raw에서 파일명 제거 ────────────────────────────────────────
def test_parse_errors_are_anonymized_before_response():
    """★`🔒 {파일명}: {사유}`가 slot으로 정규화된다 — 파일명은 남지 않고 번호는 남는다."""
    errors = [
        "🔒 가상고객A 최근 3개월.pdf: 비밀번호가 필요합니다.",
        "⚠️ 가상고객B 진료내역.pdf: PDF 파싱 중 예외 — boom",
    ]
    out = anonymize_parse_errors(errors, REAL_NAME_FILES)
    assert not any(contains_any_filename(item, REAL_NAME_FILES) for item in out)
    assert "서류 1" in out[0] and "서류 2" in out[1]
    # ★사유는 남는다(사용자가 어느 서류를 다시 받아야 하는지 알아야 행동할 수 있다).
    assert "비밀번호" in out[0]


def test_masking_covers_name_without_extension():
    """확장자를 뗀 표기(로그 등)도 함께 지운다."""
    assert "가상고객A" not in mask_filenames("가상고객A 최근 3개월 처리 실패", REAL_NAME_FILES)


def test_deep_scrub_removes_nested_filenames():
    """★history 저장 전 deep scrub — 최상위 `customer_name`만 지우던 것을 중첩 전체로 넓혔다."""
    payload = {
        "customer_name": "가상고객A",
        "parse_errors": ["🔒 가상고객A 최근 3개월.pdf: 비밀번호가 필요합니다."],
        "nested": [{"deep": "⚠️ 가상고객B 진료내역.pdf: 손상"}],
    }
    scrubbed = scrub_pdf_filenames_deep(payload)
    assert "가상고객A 최근 3개월.pdf" not in str(scrubbed)
    assert "가상고객B 진료내역.pdf" not in str(scrubbed)
    # 접두 구간을 통째로 지우므로 앞의 실명도 함께 사라진다(한글 파일명은 공백을 포함한다).
    assert "가상고객A" not in str(scrubbed["parse_errors"])


def test_deep_scrub_is_idempotent():
    """이미 정규화된 문자열을 다시 훑어도 바뀌지 않는다(방어 2선과 충돌하지 않는다)."""
    already = {"parse_errors": ["서류 1: 비밀번호가 필요합니다."]}
    assert scrub_pdf_filenames_deep(already) == already


def test_history_save_paths_apply_deep_scrub():
    """recent(7일)·saved(90일) 두 경로 모두 deep scrub을 통과한다(소스 계약).

    ★BOHUMFIT-277b: Sentry 경로는 파일명만 지우던 `scrub_pdf_filenames_deep`에서
      건강정보까지 지우는 `scrub_text`로 **격상**됐다(반려 R1). 그래서 이 단언을
      "history 2경로 + Sentry 1경로"로 나눠 각각 고정한다 — 총합 카운트로 묶으면
      한쪽이 약해져도 통과해 버린다.
    """
    import pathlib

    src = (pathlib.Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
    assert src.count("scrub_pdf_filenames_deep(") >= 2   # recent + saved
    assert "scrub_text(value)" in src                     # Sentry 최종 문자열(277b 격상분)


# ── B-F2: 로그에 원본 파일명 0 ────────────────────────────────────────────
def test_parse_log_uses_slot_not_filename(caplog):
    """★정상 분석 로그에도 원본 파일명이 남지 않는다(Railway 로그 대상)."""
    from analyzer import _log_parsed

    with caplog.at_level(logging.INFO):
        _log_parsed(REAL_NAME_FILES[0], {"records": [], "parse_errors": []}, "", 0)
    text = caplog.text
    assert not contains_any_filename(text, REAL_NAME_FILES)
    assert "서류 1" in text


def test_analyzer_failure_paths_mask_filename_and_exception():
    """실패 경로(순차·병렬) 로그·문구 모두 slot + 예외 문자열 마스킹을 쓴다(소스 계약)."""
    import pathlib

    src = (pathlib.Path(__file__).resolve().parents[1] / "analyzer.py").read_text(encoding="utf-8")
    assert 'logger.error("BOHUMFIT-047 parse failed: file=%s error=%s",\n                             document_slot(_idx)' in src
    assert "document_slot(i)" in src  # 병렬 경로
    assert src.count("mask_filenames(") >= 3
    # 원본 파일명을 그대로 넘기던 옛 형태가 남아 있지 않다.
    assert 'file=%s records=%d ftype=%s errors=%d",\n        fn,' not in src


# ── B-F5: Sentry 문자열 scrub ─────────────────────────────────────────────
def test_backend_sentry_scrubs_final_strings():
    """키 기반만으로는 이미 포맷된 문자열의 파일명이 남는다 — 문자열까지 훑는다."""
    from main import _scrub_sensitive_event_values

    event = {"extra": {"note": "🔒 가상고객A 최근 3개월.pdf: 실패"}}
    out = _scrub_sensitive_event_values(event)
    assert "가상고객A" not in str(out)


# ── 보호 영역 ─────────────────────────────────────────────────────────────
def test_pipeline_and_coverage_untouched():
    """★`pipeline/` 판정 로직·`filters.py`·`coverage/`에 277 흔적이 없다."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1]
    assert "277" not in (root / "filters.py").read_text(encoding="utf-8")
    for path in (root / "pipeline").glob("*.py"):
        assert "BOHUMFIT-277" not in path.read_text(encoding="utf-8"), path.name
    for path in (root / "coverage").glob("*.py"):
        assert "BOHUMFIT-277" not in path.read_text(encoding="utf-8"), path.name


@pytest.mark.parametrize("text", ["", None])
def test_scrub_handles_empty(text):
    assert scrub_pdf_filenames_deep(text) in ("", None)
