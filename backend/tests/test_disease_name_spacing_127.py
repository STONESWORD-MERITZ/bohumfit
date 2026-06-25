"""BOHUMFIT-127: 질병명 한국어 띄어쓰기 정규화 회귀.

공백 제거 → 표준 KCD 질병명 사전 매칭 → 미등록은 공백 제거본(임의 재삽입 금지).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.helpers import normalize_disease_name, _clean_disease_name


def test_normalize_registered_broken_name():
    """(a) 잘못 띄어쓴 등록명 → 정규명 반환."""
    assert normalize_disease_name("손 목및손의 기타부분 의열린상 처") == "손목 및 손의 기타 부분의 열린 상처"


def test_normalize_unregistered_returns_compact():
    """(b) 사전 미등록 → 공백 제거본 그대로(임의 재삽입 없음)."""
    assert normalize_disease_name("듣 도보도 못한 질환 명") == "듣도보도못한질환명"


def test_normalize_normal_registered_name_unchanged():
    """(c) 정상(등록) 질병명 → 변경 없음."""
    assert normalize_disease_name("급성 위염") == "급성 위염"


def test_normalize_empty():
    assert normalize_disease_name("") == ""
    assert normalize_disease_name(None) == ""


def test_clean_disease_name_corrects_registered():
    """_clean_disease_name 경로에서도 등록명은 정규 띄어쓰기로 교정."""
    assert _clean_disease_name("손 목및손의 기타부분 의열린상 처") == "손목 및 손의 기타 부분의 열린 상처"


def test_clean_disease_name_unregistered_untouched():
    """미등록 정상명은 기존 동작 유지(공백 보존 — 무손상)."""
    assert _clean_disease_name("급성 비인두염") == "급성 비인두염"
