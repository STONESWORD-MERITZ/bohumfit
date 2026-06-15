# BOHUMFIT-062: 수술로 오분류되는 '비수술' 코드명 전역 제외 집합.
# - 수술 감지 알고리즘은 불변. 이 집합에 든 코드명만 수술 분류에서 제외한다.
# - 항목 추가는 NON_SURGERY_NAMES 한 곳에만 추가하면 된다(확장 용이).
# - 매칭: 공백 제거 후 exact 비교(표기 공백 차이에 견고).
import re


def _norm(name: str) -> str:
    return re.sub(r"\s+", "", name or "")


# 비수술 코드명(원문) — 공백은 _norm 에서 제거되므로 가독성 위해 원문 그대로 둔다.
NON_SURGERY_NAMES = {
    _norm("수액제주입로를통한주사"),                    # 수액 경로 주사(주입), 수술 아님
    _norm("치관수복물또는보철물의 제거[1치당]-간단한것"),  # 치과 보철물 제거 처치
    _norm("치관수복물또는보철물의 제거[1치당]-복잡한것"),  # 치과 보철물 제거 처치
    _norm("후두내주입"),                                # 후두 내 약물 주입, 수술 아님
}


def is_non_surgery_excluded(name: str) -> bool:
    """수술 분류에서 전역 제외할 비수술 코드명인지."""
    return _norm(name) in NON_SURGERY_NAMES
