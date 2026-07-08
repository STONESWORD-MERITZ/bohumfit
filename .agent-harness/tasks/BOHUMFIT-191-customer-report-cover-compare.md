# BOHUMFIT-191 고객용 리포트 표지 + 전 VS 후 비교

## Owner
Codex (Windows 원본 직접 구현·검증·커밋·push)

## Source
- `.agent-harness/tasks/BOHUMFIT-188-before-after-compare.md`
- BOHUMFIT-189 구현 커밋 `c0ab2bf`
- BOHUMFIT-190 구현 커밋 `1f78ff9`

## Goal
고객용 PDF 리포트에 FIT v1.1 오리지널 표지를 추가하고, 컨설팅 전/후를 보험료·총납입·보장금액 확대 관점에서 읽기 쉽게 보여준다.

## Scope
- `backend/coverage/export_pdf.py`: 표지, 마스킹, GA 로고 슬롯, 전후 비교 3축, 대분류별 보장 변화.
- `backend/coverage/export_excel.py`: 전후 비교 시트 상단 전/후/증감 보험료와 대분류별 보장 변화 요약.
- `backend/coverage/schema.py`: 표지 입력 필드 계약 dataclass.
- `src/pages/CoverageRemodel.tsx`: 표지 수기 입력 UI, 고객용 표지 미리보기, export payload `report_cover`.
- `backend/tests/test_coverage_report_191.py`: 표지·마스킹·비교 3축·Excel 비교 시트 회귀.

## Non-Goals
- `backend/pipeline/` 무접촉.
- 타사 표지 디자인 복제 금지. 필드 구조만 반영하고 FIT v1.1 색상/심볼을 사용한다.
- 프로필 자동연동, GA 목록 드롭다운, 실제 로고 업로드/삽입은 BOHUMFIT-192 이후 별도 태스크.
- `[전]`/189/190/187/188 코어 회귀 금지.
- 실 PDF·엑셀·PII 파일 저장/커밋 금지.

## Acceptance
- 표지에는 고객명(마스킹), 보험나이, 상령일, 소속(GA), 설계사명, 작성일자가 수기 입력값으로 표시된다. 미입력 값은 생략된다.
- GA 로고 슬롯은 빈 상태로 허용된다.
- PDF는 월납입보험료, 총납입보험료, 대분류별 보장금액 변화를 나란히 보여주고 개선 요약을 포함한다.
- Excel 전후 비교 시트도 전/후/증감 보험료와 대분류별 보장 변화 요약을 포함한다.
- FIT v1.1 에메랄드 `#084734`와 ㅍ 심볼, 기존 면책 문구를 유지한다.

## Verification
- `npx tsc -p tsconfig.app.json --noEmit`
- `npx tsc -p tsconfig.node.json --noEmit`
- `npm run build`
- `cd backend && python -m pytest -q`
- `cd backend && python -m pytest tests/test_coverage_report_191.py -vv`
- 문건주 실 PDF smoke는 메모리에서만 수행하고 산출물을 저장하지 않는다.
