# BOHUMFIT-248 — 신 체계 완결(빌드 수리·엑셀·PDF) + 심층 QA 스위프 + 디벨롭 옵션 카탈로그

Owner flow: Claude Chat -> Claude Code -> Codex -> Human
Current owner: Claude Code (장시간 자율 세션 — 파트 독립 진행)
Risk tier: 혼합 — 풀 하네스. git 쓰기(add/commit/push/stash) 전면 금지(완료 후 Codex 일괄).
프로덕션 DB 0. 실 PDF·엑셀 원본 로컬 참조만·stage 금지. PII 0(픽스처 익명 합성).
Date: 2026-07-26

## 전체 취지 (Human 지시)
비분양식 정본화(244~247)를 산출물 전 계층에서 완결하고, 최소 1시간 이상의 심층 QA로
결함·개선 여지를 하나하나 뜯어 확인한다. 제1원칙 유지: ★정확도 — 담보·금액 누락 0.
버그 확정분은 수정, 사양 결정 필요분은 보고, 개선 아이디어는 카탈로그로 산출한다.

## 파트 구성 (요약 — 전문은 패킷)
- P1 로컬 빌드 수리(클린 재생성+vite 상향+build:verify 게이트+기준선 정정) — 최우선
- P2 엑셀 양식 재현(244-S3 실측 기반 export_excel 재작성 — 3시트·계약 열 전부 전개)
- P3 PDF 리포트 신 체계 재작성(247 화면과 의미 동일)
- P4 심층 QA 스위프(A 3계층 교차 대조 ~ H preview 실화면 QA — 판정+증거)
- P5 P4 결함 수정(버그 확정분만 — 사양 결정 필요분은 수정 금지·보고)
- P6 디벨롭 옵션 카탈로그(QA 증거 기반 전수)

## 진행 기록 (Claude Code · 2026-07-26 — 파트별 갱신)

### P1 — 로컬 빌드 수리 [★클린 재생성 실패 → 패킷 실패 경로 처리 완료]

- 사전 실측: vite 8.0.10(rolldown 1.0.0-rc.17·win32 바인딩 부재), npm audit **5 high**,
  로컬 번들 343,225 B(앱 코드 부재), 프로덕션 참조치 786,541 B. lock 백업 → 스크래치.
- **클린 재생성 수행**: node_modules 격리 + lock 삭제 → `npm install` → vite **8.1.5**·
  rolldown **1.1.5** + ★`@rolldown/binding-win32-x64-msvc` 정상 설치(241의 결손 해소),
  audit 5→2 high.
- **★실패 원인 2중 확정(신규 실측)**:
  ① **Windows Application Control이 신규 다운로드 네이티브 바이너리를 전면 차단** —
     `rolldown-binding.win32-x64-msvc.node`·`tailwindcss-oxide...node`(4.3.3) 로드 시
     "An Application Control policy has blocked this file". **구 설치본(oxide 4.2.4)은
     LOAD-OK** → 정책은 기존 파일 그랜드파더링·신규 유입 차단형(233 mypyc .pyd 차단과 동일 계열).
     241의 ERR_DLOPEN_FAILED 진범이 이것이었음(당시 npm 배선 문제로 판정 — 바인딩이 설치된
     지금도 차단됨을 확인).
  ② **rolldown WASI(wasm) 대체도 불가** — `@rolldown/binding-wasm32-wasi` 강제 설치 +
     `NAPI_RS_FORCE_WASI=1`로 wasm 엔진은 기동하나 Windows 절대경로(`C:\...`)를 해석하지
     못해 config/엔트리 `UNRESOLVED_ENTRY`. `--configLoader runner`로 config 번들링을
     우회하면 다음 네이티브(oxide)에서 재차단 — 네이티브 체인(rolldown→oxide→lightningcss)
     전체가 동일 정책에 걸려 wasm 전환 실익 없음.
  ③ 신 환경에서는 **vitest까지 파손**(rolldown config 번들링 의존) — 테스트 게이트 우선
     원칙에 따라 즉시 롤백 판단.
- **롤백 완료**: 구 node_modules 복원 + lock 백업 복원 + package.json 원복 → `npm test`
  **89 passed**·tsc OK(재검증). 신 환경 트리는 스크래치로 격리(레포 밖 — lint 오염 방지).
- **P1.3 산출물 스모크 게이트 신설(완료)**: `scripts/build-verify.mjs`(①크기 하한 600 kB
  ②필수 앱 문자열 3종 — 원문·\\uXXXX 이스케이프 양쪽 ③index.html 참조 무결) +
  `package.json`에 `build:verify` 등록. 로컬 껍데기에 대해 **정직 FAIL 확인**(①② 검출).
- **P1.4 기준선 정정(완료)**: verify.md·CLAUDE.md·AGENTS.md — "343 kB대 정상" 폐기,
  프로덕션 786 kB대 참조치 + build:verify 판정으로 교체, 240 조사 오판 이력 명기,
  로컬 Windows의 정책 차단 상태와 대체 검증 체계(소스 게이트 + Codex 프로덕션 번들) 명시.
- **잔여(Human 조치 필요 — 카탈로그 수록)**: 근본 해결은 ① 정책 예외 등록(관리자 —
  rolldown·oxide 바이너리 허용) 또는 ② WSL/CI Linux 빌드 검증 경로 구축. 도구 수준으로는
  이 머신에서 해결 불가(시스템 보안 설정 변경은 AI 권한 밖).
- P4의 빌드 의존 항목(H preview 실화면 QA)은 패킷 실패 경로대로 소스 게이트+테스트 기준으로 대체.

### P2 — 엑셀 양식 재현 [완료]
- `export_excel.py` 전면 재작성: 비분양식 3시트(표지(세로)·비교분석표·최종비교분석표).
  계약 열 ★전부 전개(동적 병합·인쇄영역·B 15열 실증), overview는 합계 열만, [후] 이월 값,
  차액=후−전, H10 심장중기, 238 표준환산 문구, 부록 블록(양식 밖 담보 전량 — 누락 0),
  236 납입완료는 "구 분" 메타로 이관. **값 기입 방식 채택**(패킷 허용 — 근거: 기계 검증
  가능성(제1원칙 대조) + [후] 이월값 정본성. Y/N COUNTA 수식 미채택 — 모듈 주석 기록).
  단위: 보장 만원·보험료 원(추정 — 244 결정 11 확정 대기).
- 구 시트 구조를 고정하던 테스트 8건 → 신 양식 등가 검증으로 갱신(근거 주석).
- ★검증: 실 PDF 5건 생성→openpyxl 재판독 전수 대조(35행 합계+계약별 셀+Y/N+보험료+시트3
  항목/단계) **차이 0**. 이 과정에서 결함 1건 발견·수정(하단 P5).

### P3 — PDF 신 체계 재작성 [완료]
- `export_pdf.py`: 그룹 내 정렬=시트2 항목순, 종합비교 블록(전→후·개선 +·H10 정정),
  Y/N 블록, 특이사항(warnings+cautions·마스킹), 증감(후−전) 라벨, 신담보 "[신규 설계
  반영 대상]" 표기, 기타 그룹 "정보 보존" 문구, 분류표 부록 삽입 지점 주석(에셋 보류).
- ★검증: 실 PDF 5건 HTML 대조(월납·부값·단계 값·Y/N·차액 라벨·기타 문구·신담보·마스킹)
  전 항목 OK. Chromium 렌더는 Windows 정책 차단 대비 HTML/텍스트 검증 대체(패킷 명시 경로).

### P4 — 심층 QA 스위프 [완료 — tasks/BOHUMFIT-248-qa-report.md]
- A 3계층 교차 대조 5건 차이 0(부록 결함 1건 발견·수정 포함) / B [후] 시나리오 매트릭스
  12조합+overview 대사 전부 0 / C 경계값 / D 견고성 / E 236~240 회귀 / F 브랜드·접근성 /
  G 성능 실측(파싱 2.7~5.8s 지배) / H는 P1 실패로 소스 게이트 대체.

### P5 — 결함 수정 [완료]
- **결함 1건**: overview 문서에서 엑셀 부록 라벨 열=값 열 겹침(담보명 18행 덮임 — E 실측).
  → 라벨(col_b0~col_asum-1 병합)/값(col_asum) 분리 수정 + 회귀 테스트
  `test_export_form_248.py`(2건) → 재검증 5건 차이 0. **잔존 결함 0.**
- 사양 결정 필요 4건은 QA 리포트 말미에 분리(수정 금지 원칙 준수).

### P6 — 디벨롭 옵션 카탈로그 [완료 — tasks/BOHUMFIT-248-improvement-catalog.md]
- 파싱 커버리지 4·UX 4·산출물 품질 4·운영/QA 자동화 4·성능 2 = 18항목(전부 QA 증거 기반)
  + 다음 태스크 묶음 권장안(합성 픽스처 CI화 → 가입제안서 트랙 → Human 병행 결정).

## 최종 검증 체크리스트 (1차 — 전체)
- [x] backend pytest — **707 passed, 8 skipped**(705 + 신규 2 — 갱신 9파일 근거 주석)
- [x] tsc app/node · lint · npm test **89** · build:verify(로컬 정직 FAIL 확인 — 게이트 동작 검증.
      정상 판정은 Codex 프로덕션 대체 검증)
- [x] ★3계층 교차 대조 5건 차이 0 / 총액 대사(시나리오 12조합+overview) 0 / 전=후 동일성(표준+overview)
- [x] QA 리포트 전 항목 판정 완료 — [결함] 잔존 0(1건 수정 완료·[사양 결정] 4건 분리)
- [x] PII grep 0 · pipeline diff 0 · diff 범위 = 선언 파일 + harness만(lockfile은 롤백으로 diff 0)

## 최종 검증 체크리스트 (2차 — Codex · 2026-07-27)
- [x] backend **707/8** · tsc app/node · lint · frontend **89**.
- [x] 로컬 build 343,225 B 참고 실행 후 `build:verify`가 크기/문자열 3종으로 exit 1 — 의도된 정직 FAIL.
- [x] 실 PDF 5건 payload→openpyxl 엑셀→PDF-HTML 재대조: 40행·계약 셀·단계/Y/N·월납/부값·estimated·전후 총액 차이 0. B 15계약, E overview 부록 18행/경고 포함.
- [x] B/E 3계층 행 단위 차이 0. 시각 렌더는 Application Control의 `skia.node` 차단으로 패킷 허용 openpyxl 구조/값 검증으로 대체, 익명 임시물 삭제.
- [x] package-lock·pipeline·supabase·src diff 0, PII/브랜드 계약 0, 실 PDF·엑셀·백업 tracked 0, diff check 통과.
