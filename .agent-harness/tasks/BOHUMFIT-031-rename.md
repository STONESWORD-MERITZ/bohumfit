# BOHUMFIT-031 BOHUMFIT→BOHUMFIT 전면 리네임 (통제 리네임)

## Owner
Codex(Windows) — 구현·검증·커밋·푸시 단독. (브랜드/문서/태스크ID 기계적 치환 + git)

## 목적
사명 변경(BOHUMFIT→BOHUMFIT)에 따라 코드베이스·문서·태스크ID의 BOHUMFIT 참조를 정리한다.
단, 배포·외부연동을 깨뜨릴 수 있는 식별자는 자동 치환하지 않고 분류·보고한다.

## 분류 (핵심 — 무지성 일괄치환 금지)
### A. 치환 (BOHUMFIT→BOHUMFIT)
- 문서 본문: PROGRESS.md, handoff.md, AGENTS.md, CLAUDE.md, README, 감사보고서 등 제품명
- 주석 · 사용자 노출 문구 · 로그 메시지
- 태스크ID 접두사: tasks/BOHUMFIT-* → BOHUMFIT-* (파일명 + 내부 참조 + AGENTS.md "Task prefix")
- 순수 표시용 상수/라벨/리포트 문자열

### B. 검토 후 개별 판단 (깨질 위험 — 함부로 바꾸지 말 것)
- 배포 프로젝트명(Vercel/Railway), git remote, 로컬 경로(...\bohumfit-react), package.json "name"
- 외부 서비스 식별자: Supabase 프로젝트 ref, Sentry release/project 태그
- 환경변수 NAME(예: BOHUMFIT_*), 클라이언트 의존 API 경로/계약 문자열
→ 각 항목을 handoff에 "보존/이관 사유"와 함께 표로 기록. 코드에서만 바꾸고 대시보드를 안 바꾸면 배포가 깨지므로 보존하거나 운영 체크리스트로 이관.

### C. 제외 (이 태스크 아님)
- 실제 배포 대시보드/폴더/원격 저장소 리네임 = 운영 작업(별도 체크리스트)
- 산식·룰 로직 변경 0 (이름만, 동작 불변)

## 병렬 조율 (BOHUMFIT-030과 동시 진행)
- locks.md에서 030이 잠근 파일은 **제외하고** 본 태스크 잠금 추가
- 030 잠금 파일(main.py·requirements.txt 등)의 BOHUMFIT는 **030 머지 후 reconciliation 단계**에서 처리
  (030 신규 산출물 문자열은 030이 이미 BOHUMFIT으로 생성 → 잔여는 기존 문자열뿐)
- Codex가 git 단일 권위 → 커밋·푸시 직렬화, 각 푸시 전 검증 게이트 통과 필수

## 검증
- 인벤토리: 전체 `grep -ri "bohumfit"` → A/B/C 분류표 handoff 기록
- 치환 후: npx tsc(app/node) · npm run lint · npm test · npm run build · cd backend && pytest -q 전부 통과
- 앱 구동 smoke: 로그인/분석/배포 식별자(B) 미손상 확인
- 최종 게이트 grep: 남은 BOHUMFIT = B(보존목록)와 정확히 일치, 그 외 0건
- 030 머지 후 reconciliation grep으로 잔여 0건 재확인

## 산출
- handoff에 A 치환 목록 / B 보존·이관 표 / C 운영 체크리스트 기록
- AGENTS.md Task prefix를 BOHUMFIT로 갱신
