# BOHUMFIT-061 프런트·배포 보안 헤더 — CSP 강화·CORS·HSTS·security.txt

## Owner
- Cowork (구현+정적 검증) → Codex (Windows build·tsc·실 헤더·로그인 플로우·Report-Only 위반 확인·커밋·푸시) → Human (security.txt 연락처·HSTS preload 등록·CSP enforce 전환 승인)

## 근거
- 레드팀 보안 보고서(2026-06-18) bohumfit 프런트/배포 이슈. 대상=Vercel 정적 호스팅 헤더(vercel.json). 백엔드(060) 무관·파일 무접촉.

## STEP 0 진단 (구현 전)
- 보안 헤더는 **vercel.json `headers`** 한 곳(`public/_headers` 없음, vite.config.ts는 헤더 미설정).
- CSP(기존): `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; font-src 'self' https://cdn.jsdelivr.net; img-src 'self' data: blob:; connect-src 'self' https://*.supabase.co https://surit-react-production.up.railway.app; frame-ancestors 'none'`.
- HSTS(기존): `max-age=31536000; includeSubDomains`(1년).
- **와일드카드 CORS 없음**: repo·vercel.json에 `Access-Control-Allow-Origin: *` 부재(grep 0). Vercel 정적은 기본 ACAO 미부여 → STEP2 제거 대상 없음(no-op).
- security.txt 없음(`public/.well-known/` 부재).
- index.html: 인라인 스크립트 없음(외부 module `/src/main.tsx`만). vite.config.ts: react+tailwind plain(legacy 플러그인 없음).

## 구현
- **STEP1 BF-04 (CSP script-src — Report-Only 단계 적용)**: enforced CSP는 **그대로 유지**(`script-src 'self' 'unsafe-inline'` → 앱 동작 보존). 신규 **`Content-Security-Policy-Report-Only`** 추가 — `script-src 'self'`(unsafe-inline 제거), 나머지 동일. **이유**: 빌드 산출물의 인라인 스크립트(예: Vite modulepreload polyfill) 유무를 sandbox에서 브라우저로 확정 불가 + vite.config.ts는 본 태스크 변경 허용 범위 밖(polyfill 비활성 불가). 보고서/태스크 권장대로 **Report-Only로 위반 먼저 수집 후 enforce**(앱 깨짐 0 최우선). style-src 'unsafe-inline'(React 인라인 style 필요)·jsdelivr(Pretendard 폰트)·connect-src(supabase·railway)는 유지.
- **STEP2 BF-07 (와일드카드 CORS)**: 제거 대상 없음(진단상 부재) — 변경 없음. 백엔드 CORS는 명시적 화이트리스트(060/기존)·061 범위 밖.
- **STEP3 CM-01 (HSTS)**: `max-age=63072000; includeSubDomains; preload`(2년+preload, fithere 통일).
- **STEP4 CM-02 (security.txt)**: `public/.well-known/security.txt` 신규(RFC 9116) — Contact(플레이스홀더 `security@bohumfit.ai`)·Expires `2027-01-01T00:00:00Z`·Preferred-Languages `ko, en`·Canonical. Vite가 public/→dist 루트 복사, Vercel은 정적 파일을 SPA rewrite보다 먼저 서빙 → `/.well-known/security.txt` 정상 서빙.

## 검증
- vercel.json **유효 JSON**(구조 검증), HSTS·enforced CSP·Report-Only 값 확인(실파일 Read). security.txt 생성·내용 확인.
- 백엔드 파일 **무접촉**(vercel.json·security.txt·harness만) → 백엔드 무변경(pytest no-op).
- ⚠ **sandbox 한계**: `npm run build`(rolldown 네이티브 바인딩 비호환)·브라우저 로그인 플로우·실 응답 헤더·Report-Only 위반 콘솔은 **Codex/Windows 권위**. 마운트 bash-view는 vercel.json stale/절단 → 실파일 Read로 검증.

## 자체 점검
- ☑ script-src 'unsafe-inline' 강화(Report-Only로 단계 적용 — enforced는 무깨짐 유지) ☑ enforced CSP 불변으로 앱·로그인 정상(깨짐 0) ☑ 와일드카드 CORS 없음(no-op) ☑ HSTS 63072000·includeSubDomains·preload ☑ security.txt 추가(연락처 플레이스홀더) ☑ 백엔드 무변경 ☐ npm build·브라우저(Codex).

## Notes — Human/Codex 확인
- **security.txt 연락처**: `security@bohumfit.ai`는 **플레이스홀더** → Human이 실제 보안 연락처로 교체.
- **HSTS preload**: `preload` 토큰 추가됨. 실제 hstspreload.org **등록은 Human 판단**(등록 후 철회 어려움 — 전 서브도메인 HTTPS 강제 확신 필요).
- **CSP enforce 전환**: Report-Only 위반 로그를 Codex(빌드+브라우저)/운영에서 확인 → 위반 0이면 enforced `script-src`를 `'self'`로 승격. Vite modulepreload polyfill 인라인 위반만 있으면, 후속 태스크로 vite.config `build.modulePreload.polyfill=false`(061 범위 밖) 후 enforce. **enforce 전환은 Human/Codex 승인 게이트**.

## Next
- **Codex(Windows)**: `npm run build`·tsc·로컬 로그인 플로우(Google/Kakao/Email) 깨짐 0·실 응답 헤더(CSP/HSTS/security.txt 200)·Report-Only 콘솔 위반 확인 → 범위 파일 stage→commit→push. 커밋: `BOHUMFIT-061: 프런트 보안 헤더 — CSP script-src Report-Only 강화·HSTS preload·security.txt`.
- **Human**: security.txt 연락처 교체, HSTS preload 등록 판단, Report-Only 위반 검토 후 CSP enforce 전환 승인.
