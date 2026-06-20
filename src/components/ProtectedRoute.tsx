import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { usePhoneGateStatus } from "../lib/usePhoneGate";

// BOHUMFIT-075/085/086: 로그인 보호 + 휴대폰 본인인증 게이트(소셜·이메일 공통, DB 기준 일원화).
//   086: 판정 로직을 공용 훅(usePhoneGateStatus)으로 일원화. 행 없음=미인증, internal 우회,
//   스키마 부재/일시 오류만 deploy-safe 통과. 같은 훅을 공개 랜딩(PhoneGate)에서도 사용.
export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const location = useLocation();
  const status = usePhoneGateStatus();

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-gray-400">로딩 중...</div>
    );
  }

  if (status === "anonymous") return <Navigate to="/login" replace />;

  // /phone-verify 자체는 게이트 제외(무한 리다이렉트 방지).
  if (status === "unverified" && location.pathname !== "/phone-verify") {
    // 086: 인증 후 원래 가려던 경로로 복귀할 수 있도록 from 전달.
    return <Navigate to="/phone-verify" replace state={{ from: location.pathname + location.search }} />;
  }

  return <>{children}</>;
}
