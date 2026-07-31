import * as Sentry from "@sentry/react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import InstallPrompt from "./components/InstallPrompt";
import { AuthProvider } from "./lib/AuthContext";
import { registerServiceWorker } from "./lib/pwa";

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
    </AuthProvider>
  </StrictMode>,
);
