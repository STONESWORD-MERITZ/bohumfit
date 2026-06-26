"""BOHUMFIT-138(항목4): 질병명 줄바꿈/공백 오삽입 보정 회귀."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.helpers import normalize_disease_name


def test_gallstone_broken_spacing():
    assert normalize_disease_name("폐 쇄에대한 언급이없 는기타담 석증") == "폐쇄에대한 언급이없는 기타담석증"


def test_normalize_strips_newline_and_cr():
    assert normalize_disease_name("폐\n쇄에대한\r언급이없는기타담석증") == "폐쇄에대한 언급이없는 기타담석증"
    # 미등록 명칭은 공백 제거본 그대로(127 정책 불변)
    assert normalize_disease_name("미 등록\n질환") == "미등록질환"
