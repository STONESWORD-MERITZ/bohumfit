# BOHUMFIT-142 추가검사/재검사 소견 분리
## 배경
추가검사·재검사 항목이 소견 상세까지 메인에 노출. "있었다는 사실(배지)"만 메인, 소견 상세는 접기/펼치기 부록으로.
## 확정 스펙
- 메인: "추가검사·재검사 가능성 미확인" 배지 + 질병명/진료기간/최초진단(기존). 소견 상세 문구 제거.
- 부록: [상세 소견 확인 ▼] 토글(기본 접힘) → 소견 상세 + "검사 시행 여부와 관계없이…" 안내. 연한 amber 배경 유지.
## 위치
- `Disclosure.tsx` DiseaseCard: 배지=hasClinicalChips의 clinicalReview.label(메인 유지), 소견 상세=hasBottom의 '소견 확인'(clinicalReview.text)+※ 안내(부록으로 이동).
## 수정 금지: backend 분석 로직·[A] 일반 고지 항목·exam_check_only 플래그 로직.
## 완료: 메인 배지만, 부록 접기/펼치기, tsc/build pass, handoff 기록.
