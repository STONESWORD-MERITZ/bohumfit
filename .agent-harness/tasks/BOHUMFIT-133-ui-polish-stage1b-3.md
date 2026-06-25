# BOHUMFIT-133 UI 폴리시 1단계-b + 3단계
## 133a: Disclosure Q배지 일괄 교체
- 131에서 만든 Badge(variant)로 Disclosure 인라인 Q/손해·생명/고지 배지 교체.
- 매핑: Q1=danger·Q2=warning·Q3=info·Q4=outline / 수술·입원=danger / 고지권고=warning / 고지불필요=outline.
- 클래스 교체만, 로직/상태/분석 무변경.
## 133b: 메인(Home) 3단계 효과
1) 배경: 히어로에 dot pattern(radial-gradient) 또는 그린→화이트 그라디언트(분석 화면 적용 금지).
2) 헤드라인: gradient text(그린→다크그린 bg-clip-text) 또는 fade-in-up(keyframes).
3) Features: 3카드(고지의무 분석/보장 비교분석/보험사 링크) lucide 아이콘+제목+설명, hover 효과(131~132 동일), 히어로 아래.
## 작업: Step1 메인 파일 확인 → Step2 배경 → Step3 텍스트 → Step4 Features.
## 수정 금지: 분석 로직·backend·메인 외 페이지 레이아웃.
## 완료: tsc/build pass, pytest 회귀 없음, 133a 배지 통일·133b 효과, handoff 통합 기록.
