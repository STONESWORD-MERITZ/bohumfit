# BOHUMFIT-132 UI 폴리시 2단계 (Cards hover + Numbers 카운트업)
## 배경
1단계 후속. 카드 hover 효과 + 숫자 카운트업. 외부 라이브러리 없이 Tailwind+CSS+rAF.
## 스펙
1. 카드 hover: shadow 강화(→shadow-lg, transition-shadow 200)·-translate-y-0.5(transition-transform 200)·border-green-200(transition-colors 200)·클릭형 cursor-pointer. ★분석 결과 카드는 hover 있되 translate 제외(안정감).
   - 대상: InsuranceLinks 카드, Disclosure 질병 카드(+샘플 리포트 있으면).
2. 카운트업: src/hooks/useCountUp.ts(rAF, easeOut, 기본 800ms, IntersectionObserver 진입 시 시작, 0이면 그대로) + src/components/AnimatedNumber.tsx(value/duration?/className?).
   - 적용: Disclosure 결과 숫자(입원일/통원횟수/수술건수/투약일), InsuranceLinks "N개 보험사".
## 작업: Step1 분석 → Step2 hover → Step3 훅·컴포넌트 → Step4 적용 → Step5 검증.
## 수정 금지: backend·고지 분석 로직/상태·외부 라이브러리·Disclosure 분석 로직(숫자 표시 클래스/컴포넌트만 교체).
## 완료: tsc/build pass, 카드 hover, useCountUp+AnimatedNumber, 숫자 카운트업, handoff 기록.
