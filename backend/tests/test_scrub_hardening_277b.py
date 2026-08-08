# -*- coding: utf-8 -*-
"""BOHUMFIT-277b — 277 Codex 반려 2건 보정.

R1: scrub이 **파일명만** 지우고 상병코드·기관명 등 건강정보를 남겼다.
R2: 겹치는 파일명(`a.pdf` / `a long.pdf`)에서 짧은 이름을 먼저 치환해 조각이 남았다.
"""
from __future__ import annotations

import pytest

from pii import (
    REDACTED,
    anonymize_parse_errors,
    contains_any_filename,
    mask_filenames,
    safe_error_summary,
    scrub_health_terms,
    scrub_text,
)


# ── R2: 겹치는 파일명 ─────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "text,names",
    [
        ("🔒 a long.pdf: 오류", ["a.pdf", "a long.pdf"]),                    # Codex 재현 케이스
        ("🔒 a.pdf: X / a long.pdf: Y", ["a.pdf", "a long.pdf"]),
        ("⚠️ 보고서 최종.pdf: e", ["보고서.pdf", "보고서 최종.pdf"]),         # 완전 부분집합
        ("x 가상고객A.pdf y 가상고객A 최근.pdf z", ["가상고객A.pdf", "가상고객A 최근.pdf"]),
        ("a.pdf.pdf 처리 실패", ["a.pdf", "a.pdf.pdf"]),                     # 확장자 중복
        ("보 고 서.pdf 실패", ["보 고 서.pdf"]),                              # 공백 포함
    ],
)
def test_overlapping_filenames_leave_no_fragment(text, names):
    """★전역 길이 내림차순 치환 — 짧은 이름이 긴 이름을 갉아먹지 않는다."""
    out = mask_filenames(text, names)
    assert not contains_any_filename(out, names), out
    assert ".pdf" not in out, out


def test_slot_number_keeps_original_index():
    """★정렬은 치환 순서만 바꾼다 — slot 번호는 **원본 파일 index**를 유지한다."""
    out = mask_filenames("🔒 a long.pdf: 오류", ["a.pdf", "a long.pdf"])
    assert "서류 2" in out  # `a long.pdf`는 두 번째 파일
    assert "서류 1" not in out


def test_anonymize_parse_errors_uses_same_fix():
    out = anonymize_parse_errors(["🔒 a long.pdf: 오류"], ["a.pdf", "a long.pdf"])
    assert out == ["🔒 서류 2: 오류"]


# ── R1: 건강정보 ──────────────────────────────────────────────────────────
def test_icd_codes_are_removed():
    """★상병코드는 건강정보 그 자체다 — 파일명보다 민감하다."""
    for code in ("I10", "M51.9", "S83.2", "C00"):
        assert code not in scrub_health_terms(f"진단 {code} 확인")


def test_icd_pattern_does_not_eat_normal_tokens():
    """★과잉 scrub 금지 — 일반 토큰·버전 문자열은 남는다."""
    keep = "PDF 비밀번호 해제 실패 — 생년월일을 확인해 주세요."
    assert scrub_text(keep) == keep
    assert "2607" in scrub_text("상품 2607(2.0)")


def test_medical_org_names_are_removed():
    for org in ("서울병원", "강남한의원", "행복의원", "튼튼클리닉", "중앙보건소"):
        assert org not in scrub_health_terms(f"{org} 방문")
        assert REDACTED in scrub_health_terms(f"{org} 방문")


def test_backend_sentry_scrubs_health_terms():
    """★Codex 재현 케이스 — 파일명만 지우던 상태가 해소된다."""
    from main import _scrub_sensitive_event_values

    out = str(_scrub_sensitive_event_values({"extra": {"n": "가상고객A 최근 3개월.pdf I10 고혈압 서울병원"}}))
    assert "I10" not in out
    assert "서울병원" not in out


# ── ★raw 비전송 계약(병명 사전 부재 대응) ─────────────────────────────────
def test_safe_error_summary_carries_no_raw_body():
    """★병명은 사전이 없어 패턴으로 못 지운다 → 원문을 아예 담지 않는다."""
    summary = safe_error_summary(ValueError("가상고객A 최근 3개월.pdf I10 고혈압 서울병원"), 0)
    text = str(summary)
    for secret in ("가상고객A", "I10", "고혈압", "서울병원", ".pdf"):
        assert secret not in text, secret
    # ★운영 진단 정보는 남는다.
    assert summary["kind"] == "ValueError"
    assert summary["slot"] == "서류 1"
    assert summary["length"] > 0


def test_diagnostic_info_is_preserved():
    """277이 확보한 진단 가능성을 되돌리지 않는다."""
    kept = scrub_text("🔒 서류 1: PDF 비밀번호 해제 실패 — 생년월일을 확인해 주세요.")
    assert "서류 1" in kept
    assert "비밀번호 해제 실패" in kept


def test_scrub_text_is_idempotent():
    once = scrub_text("가상고객A 최근 3개월.pdf I10 서울병원")
    assert scrub_text(once) == once


# ── 277 무회귀 ────────────────────────────────────────────────────────────
def test_277_contracts_still_hold():
    from pii import document_slot, scrub_pdf_filenames_deep

    assert document_slot(0) == "서류 1"                       # 268b 규칙
    assert "가상고객A" not in str(scrub_pdf_filenames_deep({"e": ["🔒 가상고객A 최근 3개월.pdf: 비번"]}))
