/* eslint-disable react-refresh/only-export-components */
import { useEffect } from "react";
import type { ReactNode } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import * as Sentry from "@sentry/react";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import ScrollToTop from "./components/ScrollToTop";
import { PhoneGate } from "./lib/usePhoneGate";
import { useAuth } from "./lib/auth-context";
import Home from "./pages/Home";
import DisclosureHub from "./pages/DisclosureHub";
import InsuranceCalculator from "./pages/InsuranceCalculator";
import CoverageAnalysis from "./pages/CoverageAnalysis";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import PrivacyPolicy from "./pages/PrivacyPolicy";
import TermsOfService from "./pages/TermsOfService";
import WhyDisclosure from "./pages/WhyDisclosure";
import Subscription from "./pages/Subscription";
import PhoneVerify from "./pages/PhoneVerify";
import DownloadGuide from "./pages/DownloadGuide";
import CoverageGuide from "./pages/CoverageGuide";
import CoverageCompare from "./pages/CoverageCompare";
import InsuranceLinks from "./pages/InsuranceLinks";
import ReportSample from "./pages/ReportSample";
import NotFound from "./pages/NotFound"; // BOHUMFIT-165
import { ToastProvider } from "./components/ToastContext"; // BOHUMFIT-131

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function FallbackUI() {
  return (
    <div className="min-h-screen flex items-center justify-center px-6 text-center">
      <div className="max-w-md">
        <p className="text-2xl font-extrabold text-gray-900">잠시 문제가 생겼어요</p>
        <p className="mt-2 text-sm text-gray-600">
          페이지를 새로고침하거나, 잠시 후 다시 시도해 주세요.
        </p>
        <button
          onClick={() => location.reload()}
          className="mt-5 rounded-xl bg-accent-600 px-5 py-2.5 text-sm font-bold text-white"
        >
          새로고침
        </button>
      </div>
    </div>
  );
}

// BOHUMFIT-097: 이미 로그인한 사용자가 /login·/signup 에 오면 가입화면으로 튕기지 않고
//   분석 화면으로 보낸다(버그2: 로그인 상태 "무료로 시작하기" → 회원가입 이동 방지).
//   이메일 미확인 계정은 세션이 없어(user=null) 가드에 걸리지 않으므로 로그인 시도가 가능하다(버그3 무충돌).
function RedirectIfAuthed({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-gray-400">로딩 중...</div>
    );
  }
  if (user) return <Navigate to="/disclosure?mode=agent" replace />;
  return <>{children}</>;
}

function App() {
  useEffect(() => {
    void fetch(`${API_BASE}/api/health`, {
      method: "GET",
      signal: AbortSignal.timeout(5000),
    }).catch(() => {
      // Warm-up call should never block initial render.
    });
  }, []);

  return (
    <ToastProvider>
    <BrowserRouter>
      <ScrollToTop />
      <Routes>
        <Route path="/login" element={<RedirectIfAuthed><Login /></RedirectIfAuthed>} />
        <Route path="/signup" element={<RedirectIfAuthed><Signup /></RedirectIfAuthed>} />
        {/* BOHUMFIT-075: 소셜/이메일 공통 휴대폰 본인인증 게이트(로그인 필요·전체화면) */}
        <Route path="/phone-verify" element={<ProtectedRoute><PhoneVerify /></ProtectedRoute>} />
        <Route element={<Layout />}>
          {/* BOHUMFIT-086: 소셜/이메일 로그인 후 도착하는 랜딩(/)도 게이트를 거치게 함.
              비로그인은 공개로 노출, 로그인했지만 미인증이면 /phone-verify로 이동. */}
          <Route index element={<PhoneGate><Home /></PhoneGate>} />
          {/* BOHUMFIT-046: 고객용/설계사용 통합 허브 — 모드는 ?mode= 파라미터 */}
          <Route
            path="disclosure"
            element={<ProtectedRoute><DisclosureHub /></ProtectedRoute>}
          />
          {/* 구 고객용 경로 — 북마크·기존 링크 보존용 redirect */}
          <Route path="check" element={<Navigate to="/disclosure?mode=customer" replace />} />
          {/* BOHUMFIT-112: 고지의무 리포트 샘플 미리보기(공개·비로그인 구독 유도) */}
          <Route path="disclosure/sample" element={<ReportSample />} />
          {/* BOHUMFIT-077: 심평원 자료 다운로드 가이드(공개) */}
          <Route path="download-guide" element={<DownloadGuide />} />
          <Route path="coverage-guide" element={<CoverageGuide />} />
          {/* BOHUMFIT-092: 보험사 전산·약관·팩스 링크모음(공개) */}
          <Route path="insurance-links" element={<InsuranceLinks />} />
          {/* BOHUMFIT-114: 비로그인도 Step1 열람 가능, 분석 실행은 페이지 내부에서 로그인 유도 */}
          <Route path="coverage-compare" element={<CoverageCompare />} />
          <Route
            path="insurance"
            element={<ProtectedRoute><InsuranceCalculator /></ProtectedRoute>}
          />
          <Route
            path="coverage"
            element={<ProtectedRoute><CoverageAnalysis /></ProtectedRoute>}
          />
          {/* BOHUMFIT-071: 구독 관리. BOHUMFIT-111: 비로그인도 요금제 열람 가능(결제 버튼만 로그인 유도) */}
          <Route path="subscription" element={<Subscription />} />
          <Route path="why" element={<WhyDisclosure />} />
          <Route path="privacy-policy" element={<PrivacyPolicy />} />
          <Route path="terms-of-service" element={<TermsOfService />} />
          {/* BOHUMFIT-165: 구 별칭 경로는 정본으로 영구 리다이렉트(외부 북마크 호환) */}
          <Route path="privacy" element={<Navigate to="/privacy-policy" replace />} />
          <Route path="terms" element={<Navigate to="/terms-of-service" replace />} />
          {/* BOHUMFIT-165: 정의되지 않은 모든 경로 → 404 */}
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
    </ToastProvider>
  );
}

export default Sentry.withErrorBoundary(App, { fallback: <FallbackUI /> });
