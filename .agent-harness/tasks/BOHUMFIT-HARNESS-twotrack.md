# BOHUMFIT-HARNESS-twotrack 운영 방식: 단일 운영 → Cowork→Codex 투트랙

## Owner
Cowork(샌드박스 구현) → Codex(Windows 검증·커밋·푸시).

## 목표
운영 문서를 기존 단일 운영 하네스에서 "Cowork→Codex 투트랙"으로 교체한다.
코드 무변경(문서만). ENV-MOUNT-NOTES·태스크ID 규칙·검증 게이트(verify.md/Standard Verification)는 **보존**.

## 투트랙 정의
- Cowork(샌드박스/마운트): 기획·코드리딩·구현·리팩터·/tmp 검증(tsc/단위, Windows 원본 무결성 기준)·handoff·잠금 관리. **마운트 git 금지** — 커밋·푸시는 Codex.
- Codex(Windows 권위): 권위 검증(tsc·lint·test·build·backend pytest·브라우저 스모크)·태스크 범위 stage·commit·push.
- User: 우선순위·제품 방향·운영 승인·리스크 결정.

## A~D 교체 블록 (적용 대상)

### A. AGENTS.md — 서두 (단일 운영 → 투트랙)
- 서두를 `Cowork implements in the sandbox; Codex verifies on Windows and publishes` 의미의 투트랙 문구로 교체.
- active workflow 문구를 two-track Cowork→Codex flow로 교체.

### B. AGENTS.md — Agent Roles (Cowork 역할 신설 + 소유권 재정의)
- 단일 역할/소유권 문단을 Cowork+Codex 투트랙으로 교체(아래 본문 참조).

### C. AGENTS.md — Required Workflow / Standard Verification (git·검증 주체 명시)
- L6(git status) → Codex가 Windows에서 수행, Cowork는 마운트 git 미실행(ENV-MOUNT-NOTES).
- Standard Verification에 Cowork(/tmp)·Codex(Windows 권위) 분담 1줄 추가. 검증 명령 자체는 불변.

### D. CLAUDE.md + PROGRESS.md (단일 운영 → 투트랙 표기)
- CLAUDE.md L3 기존 단일 운영 하네스 표현 → `Cowork→Codex 투트랙 하네스 방식`.
- CLAUDE.md 필수순서 L4/L8 `Codex 잠금` → `본인(Cowork/Codex) 잠금`.
- CLAUDE.md 절대규칙 L22 기존 단일 운영 기준 해석 → `Cowork→Codex 투트랙 기준으로 해석(Cowork 구현·Codex 발행)`.
- PROGRESS.md 운영 방식 문구 → `운영 방식: Cowork→Codex 투트랙 하네스`.

## 보존(변경 금지)
- ENV-MOUNT-NOTES.md 및 그 참조 문구, 태스크ID 규칙(BOHUMFIT-{n}-{slug}/HARNESS/BUG/VERIFY), Standard Verification 명령(npm lint/test/build, backend pytest), verify.md.

## 검증
- 코드 무변경 → tsc/test/build 불필요. `git diff --check`는 마운트 git 금지로 Cowork 미실행 → Codex(Windows)가 수행. 사유 handoff 기록.

## 산출
- handoff: 교체 블록 적용 결과·보존 항목·git 미실행 사유. Next: Codex(commit·push).
