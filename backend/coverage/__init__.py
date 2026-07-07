"""BOHUMFIT-179: KB 신정원 보장분석 제안서 파서(신규·격리 모듈).

고지의무 분석 파이프라인(backend/pipeline/)과 완전 분리된다.
KB 신정원 "보장분석 제안서" PDF(규칙 기반·표준 양식 전용)를 파싱해
리모델링 보장분석표 [전](회사별 세부)·[최종](합산) 데이터를 생성한다.
공개 진입점: `from coverage.service import analyze_kb_coverage, KBFormatError`.
※ PII(실계약 데이터)는 요청-응답 내에서만 처리, 서버 미저장.
※ 패키지명 'coverage'는 code-coverage 도구(coverage.py)와 동일 — 현재 미설치라 무충돌.
   향후 pytest-cov 도입 시 셰도 위험 → handoff FYI(必要 시 rename).
"""
