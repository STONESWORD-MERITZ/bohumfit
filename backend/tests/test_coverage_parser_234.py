# -*- coding: utf-8 -*-
"""BOHUMFIT-234 coverage parser regressions.

실사용 4케이스 진단에서 확정된 결함의 회귀 고정 — 픽스처는 전부 익명 합성(홍길동).
실 PDF·실명·계약 원문은 저장하지 않는다(레이아웃 형태만 재현).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import coverage.parser as parser_mod  # noqa: E402
from coverage.aggregator import build_before  # noqa: E402
from coverage.parser import parse_contract_list, parse_detail_pages  # noqa: E402

MAN = 10_000

# ⑥ 멀티페이지 계약리스트 + 보험사명 세로 쪼개짐(윗줄+아랫줄 / 행내+아랫줄) 합성 재현.
P5_PAGE1 = """홍길동 님의 전체 계약리스트 2026-07-20 22:35:18
 (68세 ,여자)
※ 기준담보/권장금액 : 기본형(37개)/표준형
3 95,290
메리츠화
1 (무) 소나무 간편건강보험(1종) 2018-05-30 월납 20년 100세 85,290원
재
2 AIG손보 베스트 건강 상해보험 2026-02-04 일시납 1년 69세 1,131,720원
""".splitlines()

P5_PAGE2 = """홍길동 님의 전체 계약리스트 2026-07-20 22:35:18
 (68세 ,여자)
※ 기준담보/권장금액 : 기본형(37개)/표준형
라이나(에 (무)튼튼 간편한 나만의 종합보험(해약환급
3 2026-07-09 월납 42년 100세 10,000원
이스)손보 금 미지급형, 갱신형) 2종(355(6대
""".splitlines()


def test_split_insurer_fragments_previous_and_next_line():
    """'메리츠화'(윗줄)+'재'(아랫줄) 세로 쪼개짐 → 메리츠화재로 복원, 상품명 오염 0."""
    contracts = parse_contract_list(P5_PAGE1)
    c1 = next(c for c in contracts if c["idx"] == 1)
    assert c1["insurer"] == "메리츠화재"
    assert c1["monthly_premium"] == 85_290
    assert "재" != c1["product"].split()[-1]
    assert "메리츠화" not in c1["product"]


def test_split_insurer_fragments_row_and_next_line():
    """'라이나(에'(행 안)+'이스)손보'(아랫줄) → 접미 종결형으로 복원."""
    contracts = parse_contract_list(P5_PAGE2)
    c3 = next(c for c in contracts if c["idx"] == 3)
    assert c3["insurer"] == "라이나(에이스)손보"
    assert "이스)손보" not in (c3["product"] or "")


def test_multipage_contract_list_merged(monkeypatch):
    """계약리스트가 2페이지면 모두 누적한다(마지막 페이지만 남던 234 ⑥ 결함)."""
    pages = [
        P5_PAGE1,
        P5_PAGE2,
        ["홍길동 님의 상품별 가입현황"],
        ["홍길동 님의 전체 담보 진단 현황"],
    ]
    monkeypatch.setattr(parser_mod, "_extract_pages", lambda _b: pages)
    raw = parser_mod.parse_document(b"synthetic")
    assert [c["idx"] for c in raw["contracts"]] == [1, 2, 3]


def test_lump_sum_excluded_from_monthly_total():
    """일시납 표기 금액은 월 보험료가 아니다 — 월납 합산 제외, 납입 총액은 1회 금액."""
    contracts = parse_contract_list(P5_PAGE1) + parse_contract_list(P5_PAGE2)
    raw = {
        "customer": {"name": "홍길동", "age": 68, "sex": "여자"},
        "contracts": contracts,
        "matrix": {},
        "diagnosis": {},
        "notes": {},
        "extra": {},
        "warnings": [],
    }
    before = build_before(raw)
    assert before["premium"]["monthly_total"] == 85_290 + 10_000
    lump = next(c for c in before["companies"] if c["idx"] == 2)
    assert lump["paid_total"] == 1_131_720  # ×12 곱하지 않는다


DETAIL_BURN_MIX = """홍길동 님의 상품별 가입담보상세
튼튼손보 | 가입일자 : 2013-11-28 |
합성 종합보험
홍길동/홍길동 월납/15년/110세만기
2013-11-28~2123-11-28 85,290원
4 정액 Active 보험금 화상진단 1,500만
6 정액 [갱신형]교통사고 및 골절.화상 관련보장Ⅵ(만기시 보험가입금액의 5% 지급) 교통상해후유장해 1,500만
7 정액 [갱신형]교통사고 및 골절.화상 관련보장Ⅵ(만기시 보험가입금액의 5% 지급) 화상진단 375만
11 정액 화상진단비 화상진단 20만
14 정액 화상수술비 화상수술 50만
15 정액 골절화상수술비 기타수술 100만
17 정액 5대장기이식수술비 기타수술 1,000만
18 정액 간편심사[355(6대질병)] 질병1~5종수술(수술당1회한)(5종수술) 질병종수술 1,000만
19 정액 116대질병수술비Ⅰ(간편가입)(갱신형) 특정질병수술 150만
""".splitlines()


def test_detail_burn_and_surgery_labels_precise():
    """④⑤⑦⑨⑩ 회귀: 화상 진단/수술 분리, 분류-전용 화상 라인 제외, 종수술·장기이식 분리."""
    contracts = [{"idx": 1, "monthly_premium": 85_290}]
    _notes, extra = parse_detail_pages([DETAIL_BURN_MIX], contracts)
    assert extra["화상진단비"]["by_company"] == {"1": 375 * MAN + 20 * MAN}  # Active 1,500만 제외
    assert extra["화상수술비"]["by_company"] == {"1": 50 * MAN}
    assert extra["화상"]["by_company"] == {"1": 100 * MAN}  # 골절화상수술비(통합 라벨 유지)
    assert extra["장기이식수술비"]["by_company"] == {"1": 1000 * MAN}
    # BOHUMFIT-238: 종별 마커 없는 5종 기준 1,000만은 표준 환산으로 1~5종 세팅된다
    # (1,000만 행: 5종=1,000만). 상세 규칙은 test_coverage_jong_238이 담당.
    assert extra["종수술비(5종·표준환산)"]["by_company"] == {"1": 1000 * MAN}
    assert extra["종수술비(1종·표준환산)"]["by_company"] == {"1": 20 * MAN}
    assert extra["N대수술비"]["by_company"] == {"1": 150 * MAN}  # 116대만 — 종수술·장기이식 미포함
