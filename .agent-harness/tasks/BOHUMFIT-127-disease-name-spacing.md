# BOHUMFIT-127 질병명 한국어 띄어쓰기 정규화
## 배경
파싱 질병명이 "손 목및손의 기타부분 의열린상 처"처럼 공백 오삽입.
## 스펙
- helpers.py에 `normalize_disease_name()` 추가: 1) 공백 전부 제거 2) 표준 KCD 질병명 사전 매칭→정규명 3) 미등록→공백제거본 그대로(임의 재삽입 금지).
## 작업
- Step1 분석: pdf_parser 질병명 추출·공백 처리, keywords.json 사전 구조, result_builder 출력.
- Step2 수정: helpers.normalize_disease_name() 추가, 질병명 경로(_clean_disease_name/get_diagnosis_name)에서 적용.
- Step3 검증: pytest 전체 + 신규(a 오공백명→정규명 / b 미등록→공백제거본 / c 정상명→불변).
## 수정 금지: 명시 외 파일·프런트.
