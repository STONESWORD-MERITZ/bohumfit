"""SURIT-LAUNCH-001: BOHUMFIT 오픈 전 도메인/면책 가드레일."""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main


def test_default_cors_origins_include_bohumfit_domain():
    assert "https://bohumfit.ai" in main.ALLOWED_ORIGINS
    assert "https://www.bohumfit.ai" in main.ALLOWED_ORIGINS


def test_kakao_message_always_includes_bohumfit_disclaimer():
    msg = main._with_kakao_disclaimer(
        main._build_kakao_message("건강체/표준체 (일반심사)", date(2026, 5, 30), {})
    )
    assert "BOHUMFIT" in msg
    assert "보험 가입·인수·보험금 지급을 보장하지 않는" in msg
