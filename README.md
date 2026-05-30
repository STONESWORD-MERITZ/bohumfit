# BOHUMFIT

보험 가입 전 고지 리스크를 점검하는 AI 보조 플랫폼입니다.

- 운영 도메인: `bohumfit.ai`
- 외부 브랜드: `BOHUMFIT` / `보험핏`
- 내부 태스크 prefix: 기존 이력 보존을 위해 `SURIT-*` 유지

## 현재 운영 방식

이 저장소는 **Codex 단독 하네스 방식**으로 진행합니다.

- 최상위 규칙: `AGENTS.md`
- 프로젝트 세부 관례: `CLAUDE.md` (파일명은 유지, 내용은 Codex 기준)
- 태스크: `.agent-harness/tasks/`
- 최신 작업 기록: `.agent-harness/handoff.md`
- 잠금 관리: `.agent-harness/locks.md`
- 검증 명령: `.agent-harness/verify.md`

과거 handoff/task에 남아 있는 Claude 또는 Cowork 표기는 역사 기록입니다. 새 작업의 구현, 검증, 커밋, 푸시는 Codex가 단독으로 담당합니다.

## 오픈 전 리스크 원칙

- BOHUMFIT은 보험 가입·인수·보험금 지급을 보장하지 않습니다.
- 결과는 청약서 문항·약관·보험회사 심사 기준과 대조해야 하는 참고용 보조자료입니다.
- 건강정보는 민감정보이므로 분석 시작 전 별도 동의가 필요합니다.
- 설계사가 고객 자료를 업로드하는 경우 정보주체 동의 확보가 필요합니다.
- 오픈 체크리스트는 `BOHUMFIT_OPEN_RISK_CHECKLIST.md`를 기준으로 합니다.

## 기술 스택

- Frontend: React 19, TypeScript, Vite, Tailwind CSS
- Backend: FastAPI, Python, pdfplumber, pandas, google-genai
- Deploy: Vercel(frontend), Railway(backend)

## 기본 검증

```powershell
npm run lint
npm test
npm run build
```

백엔드 변경 시:

```powershell
cd backend
python -m pytest -q
```

프런트 변경 시:

```powershell
npx tsc -p tsconfig.app.json --noEmit
npx tsc -p tsconfig.node.json --noEmit
```

## 작업 원칙

1. `AGENTS.md`를 먼저 읽고 하네스 절차를 따른다.
2. 작업 전 `git status --short -uall`과 `.agent-harness/locks.md`를 확인한다.
3. 태스크 범위 안에서만 수정한다.
4. 검증 결과와 남은 이슈를 `handoff.md` 상단에 남긴다.
5. 사용자가 publish를 요청했거나 태스크 완료 조건에 push가 있으면 Codex가 직접 커밋·푸시한다.
