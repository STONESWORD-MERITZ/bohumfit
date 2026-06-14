# BOHUMFIT-050 보라 하드코딩 잔재 → 그린 치환 (049 토큰 위에서)

## Owner
Cowork(Claude) — 구현. 검증·커밋은 Codex(Windows). 색 외 변경 절대 금지(기능·카피·구조·로직 불변).

## 전제
- 049에서 토큰(accent 램프·primary)만 그린 전환됨(머지 8355f86). 이번엔 토큰을 안 거친 하드코딩 보라 잔재 치환.
- ★가능한 곳은 토큰 참조(accent-600/700 클래스)로 → 단일소스화. 어색한 곳(체크박스 accent-color·그림자 rgba)만 그린 hex/rgba 직접.

## 그린 값(049 동일)
- `#7C3AED` → `accent-600`(= #15663D), `#6D28D9` → `accent-700`(= #0F4E2F)
- 체크박스 `accent-[#7C3AED]` → `accent-[#15663D]`(직접 hex)
- `rgba(124,58,237,α)` → `rgba(21,102,61,α)`
- backend brand-bar `#7C3AED` → `#15663D`(직접 hex, CSS)

## 대상 (049 스캔 C/F)
(C) 프런트 하드코딩 hex/rgba(className arbitrary·accent-color·shadow):
  - `Disclosure.tsx`·`InsuranceCalculator.tsx`·`Signup.tsx`·`BeforeAfter.tsx`·`ConsentGate.tsx`
  - ※ accent-* className(049 자동 전환분)·로직·카피 무수정. 하드코딩 hex/rgba만.
(F) backend `report_disclosure.html`·`report_insurance.html` brand-bar 포인트색만 그린(047 톤·구조·면책 불변).

## 제외
- 로고 `bohumfit_logo.svg`/`_white.svg` `#5955DE` — 미변경(재제작 예정), handoff 유지 기록.
- index.css(049 완료)·accent-* className — 재변경 금지.

## ENV
- Windows 원본 무결성 기준(마운트 절단 대비). backend 템플릿 NUL/UTF-8 확인. 마운트 git 금지, 검증 /tmp.

## 자체검증
- /tmp tsc(앱 영향 확인) + src 잔존 보라 grep(`#7C3AED`/`#6D28D9`/`rgba(124,58,237` = 0, 로고 #5955DE만) + backend `#7C3AED`=0 + 그린 대비 4.5:1·포레스트 톤.

## 산출
- handoff: 치환 파일·토큰화 여부·잔존 보라 0(로고 제외)·backend 처리. Next: Codex 검증·커밋·푸시 → Human 육안.
