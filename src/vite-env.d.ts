/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SENTRY_DSN?: string;
  readonly VITE_API_URL: string;
  readonly VITE_SUPABASE_URL: string;
  readonly VITE_SUPABASE_ANON_KEY: string;
  // BOHUMFIT-103: 카카오 로그아웃(브라우저 세션 만료)용. REST API 키 + 로그아웃 redirect URI.
  readonly VITE_KAKAO_REST_API_KEY?: string;
  readonly VITE_KAKAO_LOGOUT_REDIRECT_URI?: string;
  readonly VITE_HCAPTCHA_SITEKEY?: string;
  readonly VITE_ENABLE_SMS_PASSWORD_RESET?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare const __APP_RELEASE__: string;
