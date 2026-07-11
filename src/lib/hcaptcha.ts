export function hCaptchaSiteKey(): string {
  return import.meta.env.VITE_HCAPTCHA_SITEKEY?.trim() || "";
}

export function isHCaptchaEnabled(): boolean {
  return Boolean(hCaptchaSiteKey());
}
