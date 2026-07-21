# -*- coding: utf-8 -*-
"""BOHUMFIT-239 매트릭스 페이지 감지 회귀 — 익명 합성 픽스처(홍길동)만 사용.

핵심: '상품별 가입현황' 매트릭스가 있으면 기존대로(회귀 0), 없는 변형 문서는
'전체 보장현황'의 담보별 합계로 fallback한다. 실 PDF·실명은 저장하지 않는다.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import coverage.parser as parser_mod  # noqa: E402
from coverage.aggregator import build_before  # noqa: E402
from coverage.parser import classify_page, parse_document, parse_overview  # noqa: E402

EOK = 100_000_000
MAN = 10_000

CONTRACTS_PAGE = """홍길동 님의 전체 계약리스트 2026-07-21
 (51세 ,여자)
※ 기준담보/권장금액 : 기본형(37개)/표준형
1 KB손보 합성건강보험 2023-01-01 월납 20년 100세 50,000원
2 삼성화재 합성상해보험 2024-02-01 월납 15년 90세 30,000원
""".splitlines()

# '전체 보장현황' — 담보명 + [합계, 그룹집계…]. 첫 셀만 신뢰(계약별 아님).
# ※ 금액은 단일 단위로 둔다(실 문서의 "1억 6,000만"은 억+만이 한 셀로 병합되므로
#   합성 픽스처에서는 셀 경계가 모호해지지 않게 억 또는 만만 사용).
OVERVIEW_PAGE = """홍길동 님의 전체 보장현황 2026-07-21
 (51세 ,여자)
※ 기준담보/권장금액 : 기본형(37개)/표준형
2 80,000
1 1
상해사망 3억 2억 1억
일반암 5,000만 3,000만 2,000만
상해수술비 500만 300만 200만
""".splitlines()

# '상품별 가입현황' 매트릭스 — (1)(2) 계약별 열. 표준 문서 경로.
MATRIX_PAGE = """홍길동 님의 상품별 가입현황 2026-07-21
 (51세 ,여자)
※ 기준담보/권장금액 : 기본형(37개)/표준형
(1) KB손보 (2) 삼성화재
상해사망 3억 2억 1억
일반암 5,000만 3,000만 2,000만
""".splitlines()

DETAIL_PAGE = """홍길동 님의 상품별 가입담보상세 2026-07-21
 (51세 ,여자)
KB손보 | 가입일자 : 2023-01-01 |
합성건강보험
홍길동/홍길동 월납/20년/100세만기
2023-01-01~2043-01-01 50,000원
""".splitlines()

DIAGNOSIS_PAGE = """홍길동 님의 전체 담보 진단 현황 2026-07-21
 (51세 ,여자)
""".splitlines()


def _doc(monkeypatch, pages):
    monkeypatch.setattr(parser_mod, "_extract_pages", lambda _b: pages)
    return parse_document(b"synthetic")


# ── classify_page: 헤더 기반 감지 ────────────────────────────────────────────
def test_classify_overview_and_matrix_by_header():
    assert classify_page(OVERVIEW_PAGE) == "overview"
    assert classify_page(MATRIX_PAGE) == "matrix"
    assert classify_page(CONTRACTS_PAGE) == "contracts"
    assert classify_page(DIAGNOSIS_PAGE) == "diagnosis"
    # '전체 보장현황'은 '전체 담보 진단 현황'·'전체 계약리스트'와 혼동되지 않는다.
    assert classify_page(OVERVIEW_PAGE) != classify_page(DIAGNOSIS_PAGE)


# ── parse_overview: 담보별 합계(첫 셀)만·by_company 비움·플래그 ──────────────
def test_parse_overview_summary_only():
    acc = parse_overview([OVERVIEW_PAGE])
    assert acc["상해사망"]["summary"] == 3 * EOK
    assert acc["일반암"]["summary"] == 5000 * MAN
    assert acc["상해사망"]["by_company"] == {}       # 계약별 열 없음
    assert acc["상해사망"]["overview"] is True


def test_parse_overview_multipage_accumulates():
    page_a = OVERVIEW_PAGE
    page_b = """홍길동 님의 전체 보장현황 2026-07-21
뇌혈관질환 4,000만 3,000만 1,000만
""".splitlines()
    acc = parse_overview([page_a, page_b])
    assert "상해사망" in acc and "뇌혈관질환" in acc
    assert acc["뇌혈관질환"]["summary"] == 4000 * MAN


# ── 변형 문서(매트릭스 없음) → overview fallback ────────────────────────────
def test_overview_fallback_when_no_matrix(monkeypatch):
    raw = _doc(monkeypatch, [CONTRACTS_PAGE, OVERVIEW_PAGE, DETAIL_PAGE, DIAGNOSIS_PAGE])
    assert raw["matrix"]["상해사망"]["overview"] is True
    assert raw["matrix"]["상해사망"]["summary"] == 3 * EOK
    # 경고: '찾지 못했습니다'(데이터 손실)가 아니라 대체 안내.
    assert any("전체 보장현황" in w and "대체" in w for w in raw["warnings"])
    assert not any("찾지 못했습니다" in w for w in raw["warnings"])
    # build_before: overview 담보는 summary·enrolled 산출, by_company 비움.
    before = build_before(raw, today="2026-07-21")
    sang = next(c for c in before["coverages"] if c["kb_name"] == "상해사망")
    assert sang["summary"] == 3 * EOK and sang["enrolled"] is True
    assert sang["by_company"] == {}


# ── 표준 문서(매트릭스 존재) → overview 무시·기존 경로 불변 ─────────────────
def test_matrix_present_ignores_overview(monkeypatch):
    raw = _doc(monkeypatch, [CONTRACTS_PAGE, OVERVIEW_PAGE, MATRIX_PAGE, DETAIL_PAGE, DIAGNOSIS_PAGE])
    # 매트릭스가 있으면 계약별 by_company가 채워지고 overview 플래그는 없다.
    assert "overview" not in raw["matrix"]["상해사망"]
    assert raw["matrix"]["상해사망"]["by_company"] == {"1": 2 * EOK, "2": 1 * EOK}
    assert raw["matrix"]["일반암"]["by_company"] == {"1": 3000 * MAN, "2": 2000 * MAN}
    # fallback 안내·매트릭스 미검출 경고 모두 없다.
    assert not any("대체" in w for w in raw["warnings"])
    assert not any("찾지 못했습니다" in w for w in raw["warnings"])
    before = build_before(raw, today="2026-07-21")
    sang = next(c for c in before["coverages"] if c["kb_name"] == "상해사망")
    assert sang["by_company"] == {"1": 2 * EOK, "2": 1 * EOK}
    assert sang["summary"] == 3 * EOK  # sum(2억+1억)


# ── 매트릭스·overview 둘 다 없으면 기존 '찾지 못했습니다' 경고 유지 ─────────
def test_no_matrix_no_overview_keeps_original_warning(monkeypatch):
    raw = _doc(monkeypatch, [CONTRACTS_PAGE, DETAIL_PAGE, DIAGNOSIS_PAGE])
    assert raw["matrix"] == {}
    assert any("찾지 못했습니다" in w for w in raw["warnings"])
