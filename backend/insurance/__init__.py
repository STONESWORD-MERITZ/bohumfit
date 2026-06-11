# -*- coding: utf-8 -*-
"""BOHUMFIT 실비(실손) 청구 안내 — 백엔드 계산 모듈 (BOHUMFIT-022 1단계).

기준 문서: .agent-harness/docs/BOHUMFIT_실비기능_설계_v3.md
- constants: 수치 상수(세대별 자기부담률·실손 연 상한·건보 본인부담상한제 2026)
- calculator: 순수 계산 함수(추정 안내형, 공제 미적용 → 동일 입력=동일 출력)

알릴의무(고지) 로직과 독립된 모듈이다. UI는 2단계(별도 태스크).
"""
