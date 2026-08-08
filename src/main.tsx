import * as Sentry from "@sentry/react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import InstallPrompt from "./components/InstallPrompt";
import UpdatePrompt from "./components/mobile/UpdatePrompt";
import { AuthProvider } from "./lib/AuthContext";
import { registerServiceWorker } from "./lib/pwa";

import { scrubPii } from "./lib/errorMessages";

const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN;

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: import.meta.env.MODE,
    release: __APP_RELEASE__,
    tracesSampleRate: 0.1,
    replaysSessionSampleRate: 0.0,   // 세션 리플레이 비활성(PII 보호)
    replaysOnErrorSampleRate: 0.0,
    beforeSend(event) {
      // 폼 입력값 등 PII 제거
      if (event.request?.data) delete event.request.data;
      if (event.request?.cookies) delete event.request.cookies;
      // BOHUMFIT-277(B-F5): request 밖에도 PII가 실린다 — 275 실측상 **console breadcrumb**과
      //   **exception 문자열**이 미처리였다. 전송 직전 문자열을 한 번 더 훑는다.
      //   ★서버 `pii.py`와 같은 규칙(파일명 → `서류`)이라 두 쪽 로그가 같은 모양이 된다.
      if (event.message) event.message = scrubPii(event.message);
      for (const crumb of event.breadcrumbs ?? []) {
        if (crumb.message) crumb.message = scrubPii(crumb.message);
        if (crumb.data) {
          for (const key of Object.keys(crumb.data)) {
            const value = crumb.data[key];
            if (typeof value === "string") crumb.data[key] = scrubPii(value);
          }
        }
      }
      for (const entry of event.exception?.values ?? []) {
        if (entry.value) entry.value = scrubPii(entry.value);
      }
      return event;
    },
  });
}

// BOHUMFIT-264: PWA 앱 셸 — 프로덕션 빌드에서만 서비스워커를 등록한다(실패해도 앱은 그대로).
registerServiceWorker();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <App />
      {/* 264: 설치 안내 배너 — 설치됨·최근 닫음이면 스스로 렌더하지 않는다(기존 화면 무간섭). */}
      <InstallPrompt />
      {/* 265: 새 버전 안내 — 대기 중인 서비스워커가 없으면 렌더하지 않는다(기존 화면 무간섭·fixed 배치).
          ★자동 새로고침 금지: 사용자가 "새로고침"을 눌러야 SKIP_WAITING을 보내고, 제어권이 넘어온 뒤 1회만 리로드한다.
          264가 install 단계의 자동 skipWaiting()을 제거했기 때문에 이 배선이 없으면
          새 버전이 "모든 탭을 닫기 전까지" 적용되지 않는다(Human 승인으로 265에 포함). */}
      <UpdatePrompt />
    </AuthProvider>
  </StrictMode>,
);
