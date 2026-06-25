# BOHUMFIT-131 UI 폴리시 1단계 (Toasts / Spinner / Badges / Tabs)
## 배경
21st.dev 참고 UI 개선 1단계. 외부 라이브러리 추가 없이 Tailwind+인라인만.
## 스펙
1. Toast: src/components/Toast.tsx + ToastContext(useToast). 4종(success/error/warning/info), 우하단 고정, 3초 자동 fade-out, 닫기, 최대 3. App에 Provider. 연결: 복사 성공·분석 완료·업로드 오류.
2. Spinner: 분석 로딩(AnalysisProgress 등) 원형 spin(animate-spin), 브랜드 그린(#2d6a4f), 48px, "분석 중입니다..." 문구. 없으면 Spinner.tsx.
3. Badge: src/components/ui/Badge.tsx(기존) variant(default/success/warning/danger/info/outline) 정비 + 매핑(손해=info·생명=success·공식확인=success·Q1=danger·Q2=warning·Q3=info·Q4=outline·수술/입원=danger). 인라인 배지 교체(가능 범위).
4. Tabs: InsuranceLinks(+Disclosure 있으면) 탭 underline 슬라이드·hover bg-green-50·transition-all duration-200.
## 작업: Step1 분석 → Step2 Toast → Step3 Spinner → Step4 Badge → Step5 Tabs → Step6 검증.
## 수정 금지: backend/·고지의무 분석 로직·기존 기능 동작·외부 라이브러리 추가.
## 완료: tsc/build pass, Toast 4종·Spinner·Badge 통일·Tabs 애니메이션, handoff 기록.
