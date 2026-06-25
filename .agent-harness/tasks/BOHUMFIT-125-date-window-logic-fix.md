# BOHUMFIT-125 건강체/간편 날짜 창 판정 로직 통일
## 배경
동일 질병 S63이 건강체와 간편에서 진료기간이 다르게 표시되는 버그.
- 건강체 Q4: 진료기간 2018-06-20~2018-06-21 (최초~최초+1일)
- 간편: 진료기간 2018-06-20~2021-07-20 (최초~실제 최종진료일)
## 확정 스펙
1. 최초진단일(first_date)이 창(90/365/1825/3650일) 안 → 고지 대상
2. 고지 대상이면 최종진료일(last_date)은 창 밖이어도 실제값 표시
3. first_date 창 밖·last_date만 창 안 → 고지 대상 아님
4. 건강체/간편 동일 적용
## 작업
- Step1 분석: filters.py(건강체 Q1~Q5·간편 Q1~Q3 창 판정 first vs last), result_builder.py(진료기간 start~end 구성), disease_aggregator.py(first/last 집계) → handoff "Step1 분석 결과".
- Step2 재현: ★오수영 PDF는 Desktop 미마운트로 접근 불가 → S63 시나리오 합성 재현(first=2018-06-20 창안, last=2021-07-20). 분기점 핀포인트.
- Step3 수정: 창 판정=first_date만, 진료기간 표시=first~last(last 창 무관), 건강체/간편 통일.
- Step4 검증: 합성 재현 동일성, pytest 전체, 신규 회귀(a first창안·last창밖→고지O·last표시 / b first창밖·last창안→고지X / c 건강체=간편).
## 수정 금지
- 명시 외 파일·프런트 수정 금지. 창 경계값(90/365/1825/3650) 변경 금지.
## 완료 조건
- S63 건강체/간편 진료기간 동일, pytest 통과, handoff 기록. ★실 PDF·PII 미커밋.

## 결과 (2026-06-25)
- 근본원인: result_builder._build_reports_for_product 의 `latest_date = _in_range[-1]`(창 필터된 종료일).
  Q4는 범위창 상한(d5y)이 있어 실제 최종진료일이 창 안쪽으로 잘림 → 건강체 Q4(2018-06-21) ≠ 간편 Q2(2021-07-20).
- 수정: 진료기간 종료일을 창과 무관한 실제 최종진료일(visit/inpatient/inpatient_end/surgery 최대)로 표시.
  창 판정(고지 대상 여부)·first_date(시작일)는 불변. 합성 재현으로 둘 다 2018-06-20~2021-07-20 확인.
- ★스펙 3번(최초진단일 창 밖이면 창 안 치료 있어도 고지 제외)은 **미적용**(사용자 결정).
  이유: 고지 질문('최근 N년 이내 입원·수술·통원·투약 있나요?')과 충돌해 고지 누락 위험. 플래깅 로직 현행 유지.
  → 테스트(b)는 추가하지 않음. 회귀는 (a)(c)만.
- filters.py 미수정(플래깅 불변). 변경: result_builder.py + tests/test_date_window_period_125.py.
