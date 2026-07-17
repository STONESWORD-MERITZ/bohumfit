# BOHUMFIT

보험 가입 전 고지 리스크를 점검하는 AI 보조 플랫폼입니다.

- 운영 도메인: `bohumfit.ai`
- 외부 브랜드: `BOHUMFIT` / `보험핏`
- 내부 태스크 prefix: 기존 이력 보존을 위해 `BOHUMFIT-*` 유지

## 현재 운영 방식

이 저장소는 **Claude Chat → Claude Cowork → Codex 3역할 하네스 방식**으로 진행합니다.

- 최상위 규칙: `AGENTS.md`
- 프로젝트 세부 관례: `CLAUDE.md`
- 새 채팅 업무 계약: `.agent-harness/WORKFLOW.md`
- 태스크: `.agent-harness/tasks/`
- 최신 작업 기록: `.agent-harness/handoff.md`
- 잠금 관리: `.agent-harness/locks.md`
- 검증 명령: `.agent-harness/verify.md`

역할은 아래처럼 나눕니다.

- Claude Chat: 사용자의 요구를 취지 중심 작업 패킷으로 정리합니다.
- Claude Cowork: 샌드박스에서 구현, 테스트 추가, 1차 검증, handoff 기록을 담당합니다.
- Codex: Windows 원본에서 권위 검증, 좁은 보정, scoped commit/push, 배포 확인을 담당합니다.
- Human: 사업 판단, 법무·개인정보·결제·대시보드 설정처럼 코드 밖 결정을 담당합니다.

과거 handoff/task에 남아 있는 예전 운영 표기는 역사 기록입니다. 새 작업은 `.agent-harness/WORKFLOW.md`의 New Chat Packet 형식으로 이어받습니다.

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

## Windows 신규 환경 셋업

저장소의 `.python-version`에 맞는 Python 3.12.10과 Microsoft Visual C++ 2015-2022 Redistributable (x64)를 먼저 설치합니다. VC++ 재배포 패키지는 백엔드 Python 의존성이 사용하는 Windows 네이티브 런타임에 필요합니다.

백엔드 운영 의존성, 개발·테스트 의존성, Playwright Chromium을 순서대로 설치합니다.

```powershell
cd backend
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
```

`requirements-dev.txt`는 로컬 검증 도구의 재현성을 위해 현재 Windows 설치본 버전을 고정합니다.

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
2. 최신 `handoff.md`, 관련 task, `.agent-harness/locks.md`를 확인한다.
3. Cowork는 마운트 git 금지 원칙을 지키고, Codex는 Windows에서 `git status --short -uall`을 확인한다.
4. 태스크 범위 안에서만 수정하되, 사용자의 취지 기준으로 필요한 회귀 테스트와 안전장치는 보강한다.
5. 검증 결과와 남은 이슈를 `handoff.md` 상단에 남긴다.
6. 사용자가 publish를 요청했거나 태스크 완료 조건에 push가 있으면 Codex가 태스크 범위 파일만 커밋·푸시한다.
