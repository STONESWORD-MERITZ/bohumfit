/// <reference types="node" />

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it } from "vitest";

import {
  isInstallDismissed,
  rememberInstallDismiss,
  shouldShowInstallHint,
} from "./pwa";

/**
 * BOHUMFIT-264 — PWA 셸 회귀.
 * ★핵심 계약: 서비스워커가 **분석 결과·파일 응답·API를 캐시하지 않는다**(PII 보호).
 *   SW는 브라우저 전용 스크립트라 소스를 읽어 정책 함수를 격리 실행해 검증한다.
 */

const SW_SOURCE = readFileSync(resolve(process.cwd(), "public/sw.js"), "utf8");

/** sw.js의 캐시 판정 로직만 떼어내 Node에서 실행할 수 있게 감싼다. */
function loadSwPolicy() {
  const origin = "https://bohumfit.ai";
  const body = SW_SOURCE
    // self/이벤트 등록부는 필요 없다 — 판정 함수만 평가한다.
    .replace(/self\.addEventListener[\s\S]*$/, "")
    .replace(/self\.location\.origin/g, JSON.stringify(origin));
  const factory = new Function(
    `${body}
    return {
      CACHE_VERSION,
      OFFLINE_URL,
      PRECACHE_URLS,
      isCacheableRequest,
      isCacheableResponse,
      isStaticAsset,
    };`,
  );
  return { origin, ...(factory() as Record<string, never>) } as {
    origin: string;
    CACHE_VERSION: string;
    OFFLINE_URL: string;
    PRECACHE_URLS: string[];
    isCacheableRequest: (req: { method: string; url: string; mode?: string }) => boolean;
    isCacheableResponse: (res: { status: number; type: string } | null) => boolean;
    isStaticAsset: (url: URL) => boolean;
  };
}

const sw = loadSwPolicy();
const req = (url: string, init: { method?: string; mode?: string } = {}) => ({
  method: init.method ?? "GET",
  mode: init.mode ?? "no-cors",
  url: url.startsWith("http") ? url : `${sw.origin}${url}`,
});

describe("BOHUMFIT-264 service worker cache policy", () => {
  it("caches the app shell navigation and static assets", () => {
    expect(sw.isCacheableRequest(req("/", { mode: "navigate" }))).toBe(true);
    expect(sw.isCacheableRequest(req("/disclosure", { mode: "navigate" }))).toBe(true);
    expect(sw.isCacheableRequest(req("/assets/index-abc123.js"))).toBe(true);
    expect(sw.isCacheableRequest(req("/assets/index-abc123.css"))).toBe(true);
    expect(sw.isCacheableRequest(req("/icon-192.png"))).toBe(true);
  });

  it("★never caches analysis results, file downloads or API calls (PII)", () => {
    // 분석·보장분석 API(동일 출처 프록시 형태 포함)
    expect(sw.isCacheableRequest(req("/api/coverage/analyze"))).toBe(false);
    expect(sw.isCacheableRequest(req("/coverage/export/excel"))).toBe(false);
    expect(sw.isCacheableRequest(req("/api/analyze"))).toBe(false);
    expect(sw.isCacheableRequest(req("/auth/v1/token"))).toBe(false);
    expect(sw.isCacheableRequest(req("/rest/v1/profiles"))).toBe(false);
    // 산출물 파일
    expect(sw.isCacheableRequest(req("/downloads/report.xlsx"))).toBe(false);
    expect(sw.isCacheableRequest(req("/downloads/report.pdf"))).toBe(false);
    // 업로드·변경 요청
    expect(sw.isCacheableRequest(req("/", { method: "POST", mode: "navigate" }))).toBe(false);
    // 교차 출처(백엔드 API 도메인 등)
    expect(sw.isCacheableRequest(req("https://api.example.com/coverage/analyze"))).toBe(false);
    expect(sw.isCacheableRequest(req("https://api.example.com/assets/app.js"))).toBe(false);
  });

  it("only stores successful same-origin responses", () => {
    expect(sw.isCacheableResponse({ status: 200, type: "basic" })).toBe(true);
    expect(sw.isCacheableResponse({ status: 404, type: "basic" })).toBe(false);
    expect(sw.isCacheableResponse({ status: 200, type: "opaque" })).toBe(false);
    expect(sw.isCacheableResponse(null)).toBe(false);
  });

  it("declares a versioned cache and an offline fallback", () => {
    expect(sw.CACHE_VERSION).toMatch(/^bohumfit-shell-v\d+$/); // 버전 올리면 구 캐시 삭제
    expect(sw.OFFLINE_URL).toBe("/offline.html");
    expect(sw.PRECACHE_URLS).toContain("/offline.html");
  });

  it("keeps the 265 hook without caching analysis payloads yet", () => {
    // 264 범위: 셸만 캐시. 분석 결과 캐시는 265(A안 24h·로그아웃 삭제)에서 이 함수만 넓힌다.
    expect(SW_SOURCE).toContain("isCacheableRequest");
    expect(sw.isCacheableRequest(req("/coverage/analyze", { mode: "navigate" }))).toBe(false);
  });
});

describe("BOHUMFIT-264 install prompt gating", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("hides when already installed or recently dismissed", () => {
    expect(shouldShowInstallHint({ standalone: true, dismissed: false, hasPrompt: true, ios: false })).toBe(false);
    expect(shouldShowInstallHint({ standalone: false, dismissed: true, hasPrompt: true, ios: false })).toBe(false);
  });

  it("shows when a browser prompt is available, or on iOS as guidance", () => {
    expect(shouldShowInstallHint({ standalone: false, dismissed: false, hasPrompt: true, ios: false })).toBe(true);
    expect(shouldShowInstallHint({ standalone: false, dismissed: false, hasPrompt: false, ios: true })).toBe(true);
    // 프롬프트도 없고 iOS도 아니면 띄우지 않는다(빈 배너 방지).
    expect(shouldShowInstallHint({ standalone: false, dismissed: false, hasPrompt: false, ios: false })).toBe(false);
  });

  it("remembers dismissal for 30 days", () => {
    const now = Date.UTC(2026, 6, 31);
    expect(isInstallDismissed(now)).toBe(false);
    rememberInstallDismiss(now);
    expect(isInstallDismissed(now + 29 * 24 * 60 * 60 * 1000)).toBe(true);
    expect(isInstallDismissed(now + 31 * 24 * 60 * 60 * 1000)).toBe(false);
  });
});

describe("BOHUMFIT-264 manifest", () => {
  const manifest = JSON.parse(readFileSync(resolve(process.cwd(), "public/site.webmanifest"), "utf8"));

  it("declares installability fields with brand colors", () => {
    expect(manifest.name).toContain("보험핏");
    expect(manifest.short_name).toBe("보험핏");
    expect(manifest.start_url).toBe("/");
    expect(manifest.scope).toBe("/");
    expect(manifest.display).toBe("standalone");
    expect(manifest.theme_color).toBe("#084734"); // 브랜드 에메랄드
    expect(manifest.background_color).toBe("#084734");
  });

  it("ships 192/512 icons for both any and maskable purposes", () => {
    const sizes = (purpose: string) =>
      manifest.icons.filter((i: { purpose: string }) => i.purpose === purpose).map((i: { sizes: string }) => i.sizes);
    expect(sizes("any")).toEqual(expect.arrayContaining(["192x192", "512x512"]));
    expect(sizes("maskable")).toEqual(expect.arrayContaining(["192x192", "512x512"]));
  });
});
