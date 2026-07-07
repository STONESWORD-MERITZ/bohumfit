# BOHUMFIT-180 — 보장분석 리모델링표 프런트 + 기존 보장분석 통합

Owner flow: Claude Chat -> Claude Cowork -> Codex
Current owner: Cowork(구현 완료) -> Codex(Windows tsc/build/스모크·파일정리 판단·커밋·푸시)

## 배경 (Human 확정)
179/179b 백엔드(/coverage/analyze)가 KB 신정원 보장분석 제안서 PDF→[전]/[최종] 생성. 이 태스크는
그 데이터를 리모델링표로 렌더 + 라우트 통합. C방식: /coverage-compare를 KB 보장분석으로 재편, /coverage(고아) 제거. 내보내기는 181.

## Step 0 — 기존 라우트 실사 결과 (★중요)
- `/coverage`(CoverageAnalysis): **NAV 미연결 = 라우트 고아 맞음**. 단 코드는 실동작 — 엑셀(.xlsx) 원천자료 SheetJS 파싱 → 담보 매핑(2단계 수동배정) → 전 비분표 + 후 비분표/최종비교(043/044) + 내보내기. 전용 파일: `pages/CoverageAnalysis.tsx`·`lib/coverageMapping(.test)`·`lib/coverageParse(.test)`·`lib/coverageExport`·`components/coverage/CoverageAfterSection·CoverageTableView`. → **살릴 기능 있음(테스트 2개 포함) → 파일 삭제는 Human 확인**.
- `/coverage-compare`(CoverageCompare): NAV "보장 비교분석" 연결. 114 백엔드 `/coverage/parse` 기반 PDF 비교(현재보험↔제안서 3단계) **실동작**. → 재편 시 이 기능 접근 불가.
- 179 응답 스키마 확인: `{before:{customer,premium{monthly_total,paid_total},companies[월납desc],coverages[…summary,by_company]}, final:{premium,coverages[value,recommended,gap,status],rollup_by_group12}, warnings}`.

## Step 1~3 — KB 보장분석 화면 (완료)
- 신규 `src/pages/CoverageRemodel.tsx` — ConsentGate(고객동의) + KB PDF 업로드 → `POST /coverage/analyze`(Bearer) → [최종]/[전] 렌더.
- [최종](상단·크게): 월납합계·총납입·부족/미가입 요약 카드 + 13대분류 그룹핑 담보별 권장/가입/과부족/준비상태. 과부족 색: 충분=에메랄드(accent), 부족=앰버, 미가입=회색(ink). status 배지.
- [전](하단·펼침, 기본 접힘): 회사(월납 내림차순 열)×담보 매트릭스 + 좌측 합산/대표 요약열 + 계약 비고(계피 등 remark).
- PII: 업로드·응답 화면 세션 내만, 저장 없음.

## Step 4 — 라우트 정리 (완료, 보수적)
- `src/App.tsx`: `/coverage-compare` → `<ProtectedRoute><CoverageRemodel/></ProtectedRoute>`(재편). `/coverage` 라우트 + CoverageAnalysis import 제거. CoverageCompare import → CoverageRemodel.
- NAV(Layout.tsx) "보장 비교분석"→/coverage-compare 이미 연결(무편집, 이제 KB 화면 표시).
- ★파일 미삭제(Cowork): CoverageAnalysis.tsx·CoverageCompare.tsx·lib/coverage*·components/coverage/* 보존 — 실동작+테스트 영향이라 Human 확인 후 Codex가 git rm 판단.

## 수정 금지 (준수)
- backend 전체 / Disclosure·타 페이지 / 179 API 응답 구조 / 내보내기(181).

## 검증 체크리스트
- [x] Step 0 실사 결과 handoff 기록(살릴 기능 유무 명시)
- [x] [최종] 과부족 색상 + [전] 회사별 세부 렌더 (CoverageRemodel)
- [x] 흰 바탕 라임/그린티 텍스트 0 / raw gray 0 (grep)
- [x] /coverage 죽은링크 0 (grep) · CoverageAnalysis 참조 App.tsx 외 0
- [x] PII 미저장(업로드·응답 세션 내·ConsentGate)
- [ ] tsc/build/npm test는 Codex 권위(기준선 514/8·npm 53, 백엔드 무변경). ⚠App.tsx 마운트 truncation → Codex Windows tsc 확인 필수.

## Stage 예정 (Codex)
- src/pages/CoverageRemodel.tsx(신규)·src/App.tsx(라우트)
- (파일 삭제 보류: CoverageAnalysis.tsx·CoverageCompare.tsx·lib/coverage*·components/coverage/* — Human 확인 후)
- .agent-harness/tasks/BOHUMFIT-180-coverage-remodel-ui.md, handoff.md, locks.md

## ★Human 확인 필요
- C방식으로 **실동작 기능 2종이 접근 불가**가 됨: ① 114 PDF 비교(현재보험↔제안서) ② 엑셀 전/후 비분표+내보내기. 의도한 대체가 맞는지, 파일/테스트까지 삭제할지 확인.

## 커밋 메시지 (Codex)
feat(BOHUMFIT-180): 보장분석 리모델링표 프런트 + 보장분석 라우트 통합
