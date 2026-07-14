import { describe, expect, it } from "vitest";
import vercelConfigRaw from "../vercel.json?raw";

type Header = { key: string; value: string };
type HeaderRule = { source: string; headers: Header[] };

const config = JSON.parse(vercelConfigRaw) as { headers: HeaderRule[] };
const globalHeaders = config.headers.find((rule) => rule.source === "/(.*)")?.headers ?? [];
const csp = globalHeaders.find((header) => header.key === "Content-Security-Policy")?.value ?? "";

function directive(name: string): string[] {
  const value = csp
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${name} `));
  return value?.split(/\s+/).slice(1) ?? [];
}

describe("Vercel Content-Security-Policy", () => {
  it("preserves existing services and permits only the required hCaptcha origins", () => {
    expect(directive("script-src")).toEqual(expect.arrayContaining([
      "'self'",
      "https://js.tosspayments.com",
      "https://js.hcaptcha.com",
      "https://*.hcaptcha.com",
    ]));
    expect(directive("connect-src")).toEqual(expect.arrayContaining([
      "'self'",
      "https://*.supabase.co",
      "https://bohumfit.up.railway.app",
      "https://*.hcaptcha.com",
    ]));
    expect(directive("frame-src")).toEqual(expect.arrayContaining([
      "https://tosspayments.com",
      "https://*.tosspayments.com",
      "https://newassets.hcaptcha.com",
      "https://*.hcaptcha.com",
    ]));
    expect(directive("style-src")).toEqual(expect.arrayContaining([
      "'self'",
      "'unsafe-inline'",
      "https://cdn.jsdelivr.net",
    ]));
  });
});
