# BOHUMFIT-053 본문 표기 통일(BohumFit) + 홈 히어로 상단 간격 축소

## Owner
Cowork(Claude) — 구현. 검증·커밋은 Codex(Windows). 색·기능·구조·산식 불변(표시 텍스트 + 히어로 상단 여백만).

## A. 본문 표기 통일 (스캔 후 분류 — 052 워드마크와 일치)
### (바꿈) 화면 표시 텍스트 BOHUMFIT → BohumFit
- `Footer.tsx`: serviceName "BOHUMFIT"(L7)·본문 "BOHUMFIT이 제공…"(L32)·© BOHUMFIT(L36)
- `Disclosure.tsx`: 결과 안내 "BOHUMFIT 결과는…"(L541)·동의 "BOHUMFIT 서버에서 폐기"(L1443)·"BOHUMFIT 분석 목적"(L1457)
- `Home.tsx`: 히어로 본문 "BOHUMFIT은…"(L142)·"지금의 BOHUMFIT과 앞으로의 BOHUMFIT"(L189)
- `HomeMission.tsx`: "BOHUMFIT은…"(L45)
- `PrivacyPolicy.tsx`: "BOHUMFIT 개인정보 보호 담당자"(L4)·"본 개인정보처리방침은 BOHUMFIT(보험핏…"(L14)
- `Terms.tsx`: "본 약관은 BOHUMFIT(보험핏…"(L9)
- `InsuranceCalculator.tsx`: 에러 메시지 "BOHUMFIT 리포트 PDF 생성 환경…"(L183)

### (보존) 변경 금지
- 도메인 `BOHUMFIT.AI`/`bohumfit.ai`, task-ID 주석(`BOHUMFIT-0XX`), 콘솔 로그 태그 `console.error("[BOHUMFIT]…")`(Disclosure L15), 다운로드 파일명 `BOHUMFIT-insurance-…pdf`(InsuranceCalculator L176, 기능 문자열).
- **backend 전부 보존**: report 템플릿/`report_pdf.py`의 "BOHUMFIT"(분석도구 식별자·footer·wordmark)는 **pytest(test_report_pdf.py L157/241 `"BOHUMFIT" in html`)가 검사**하므로 미변경(테스트 호환 우선). 통일하려면 테스트 동시 갱신 필요 → 별도 후속.
- 프런트 테스트 의존: 변경 대상 문자열을 검사하는 프런트 테스트 없음(grep 확인).

## B. 홈 히어로 상단 간격 축소 (핏히어 결)
- 현재 `Home.tsx` 히어로 `<section class="bf-hero flex min-h-[88vh] items-center …">` + 내용 `py-20` → 세로 중앙정렬이 네비~첫 텍스트(eyebrow "Insurance Disclosure Intelligence") 사이 과도 공백 유발.
- 변경: `items-center` → `items-start`(상단 정렬), 내용 패딩 `py-20` → `pt-16 pb-20`(상단 64px ≈ 네비 직후, 하단 리듬 유지). min-h-[88vh](스크럽 지오메트리)·다른 섹션 불변.
- 핏히어 코드는 repo 부재 → 표준값(네비 아래 ~64px) 적용. 데스크탑·모바일 둘 다 자연스럽게.

## ENV
- Windows 원본 무결 기준, 마운트 git 금지, 검증 /tmp.

## 자체검증
- /tmp tsc + (바꿈) BohumFit·(보존) 미변경 grep + 프런트 테스트 39 호환·backend pytest 호환(미변경) + 히어로 클래스 전후 확인.

## 산출
- handoff: 치환/보존 목록·히어로 여백 전후·핏히어 참조 여부(부재). Next: Codex 검증·커밋·푸시 → Human 육안.
