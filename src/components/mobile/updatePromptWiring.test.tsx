// BOHUMFIT-265 마무리 — UpdatePrompt 배선 회귀 + 개인정보처리방침 고지 정합.
//   ★핵심 계약: 배선해도 **기존 화면 DOM이 한 노드도 늘지 않는다**(대기 중인 새 버전이 없을 때 null 렌더).
//   ★자동 새로고침 금지: 배선부(main.tsx)에 리로드 코드가 없고, 사용자가 누를 때만 SKIP_WAITING이 나간다.
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import UpdatePrompt from "./UpdatePrompt";

// 방침 페이지는 Supabase를 직접 쓰지 않지만, 공용 헤더가 인증 컨텍스트를 참조할 수 있어 최소 모킹만 둔다.
vi.mock("../../lib/supabase", () => ({
  supabase: {
    auth: {
      getSession: vi.fn(async () => ({ data: { session: null, user: null }, error: null })),
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
      signOut: vi.fn(async () => ({ error: null })),
    },
  },
}));

// 보호 화면(고지·리모델링)은 인증 컨텍스트만 있으면 초기 화면이 렌더된다.
vi.mock("../../lib/auth-context", () => ({
  useAuth: () => ({ session: { access_token: "test-access-token" }, loading: false }),
}));

import PrivacyPolicy from "../../pages/PrivacyPolicy";
import Disclosure from "../../pages/Disclosure";
import CoverageRemodel from "../../pages/CoverageRemodel";

const ROOT = process.cwd();
const MAIN = readFileSync(join(ROOT, "src/main.tsx"), "utf8");
const POLICY = readFileSync(join(ROOT, "src/pages/PrivacyPolicy.tsx"), "utf8");
/** 주석을 제거한 실행 코드만 검사한다(설명 문구가 가드를 오탐시키지 않도록). */
const codeOf = (src: string) =>
  src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "").replace(/\{\/\*[\s\S]*?\*\/\}/g, "");
const MAIN_CODE = codeOf(MAIN);

// jsdom에는 scrollIntoView가 없다(고지 화면이 포커스 이동에 사용) — 앱 결함이 아니라 환경 공백이라 채운다.
if (!Element.prototype.scrollIntoView) Element.prototype.scrollIntoView = vi.fn();

afterEach(() => cleanup());

describe("UpdatePrompt 배선(main.tsx)", () => {
  it("★<App/> 형제로 배선된다 — 화면 컴포넌트 내부가 아니라 최상위에 얹는다", () => {
    expect(MAIN_CODE).toContain('import UpdatePrompt from "./components/mobile/UpdatePrompt"');
    // AuthProvider 안(로그인 상태 접근 가능) · App 뒤(형제) 순서를 고정한다.
    const provider = MAIN_CODE.indexOf("<AuthProvider>");
    const app = MAIN_CODE.indexOf("<App />");
    const prompt = MAIN_CODE.indexOf("<UpdatePrompt />");
    const providerEnd = MAIN_CODE.indexOf("</AuthProvider>");
    expect(provider).toBeGreaterThan(-1);
    expect(app).toBeGreaterThan(provider);
    expect(prompt).toBeGreaterThan(app);
    expect(prompt).toBeLessThan(providerEnd);
  });

  it("★배선부에 자동 새로고침 코드가 없다(사용자 확인 후에만 갱신)", () => {
    expect(MAIN_CODE).not.toMatch(/location\.reload|skipWaiting|SKIP_WAITING/);
  });

  it("264 설치 배너 배선은 그대로 남아 있다(회귀 0)", () => {
    expect(MAIN_CODE).toContain("<InstallPrompt />");
    expect(MAIN_CODE).toContain("registerServiceWorker()");
  });
});

describe("★기존 화면 렌더 회귀 0", () => {
  it("대기 중인 새 버전이 없으면 DOM에 아무것도 추가하지 않는다", () => {
    const { container } = render(<UpdatePrompt />);
    expect(container.innerHTML).toBe("");
    expect(screen.queryByTestId("sw-update-prompt")).toBeNull();
  });

  it("페이지와 함께 렌더해도 기존 화면 DOM이 동일하다(노드 수·마크업 불변)", () => {
    const withoutPrompt = render(
      <MemoryRouter>
        <PrivacyPolicy />
      </MemoryRouter>
    );
    const baselineHtml = withoutPrompt.container.innerHTML;
    const baselineNodes = withoutPrompt.container.querySelectorAll("*").length;
    cleanup();

    // main.tsx와 같은 형제 배치를 재현한다.
    const withPrompt = render(
      <MemoryRouter>
        <PrivacyPolicy />
        <UpdatePrompt />
      </MemoryRouter>
    );
    expect(withPrompt.container.innerHTML).toBe(baselineHtml);
    expect(withPrompt.container.querySelectorAll("*").length).toBe(baselineNodes);
  });

  // ★패킷 지정 화면 — 표가 크고 fixed 요소가 겹치기 쉬운 두 화면에서 직접 확인한다.
  it.each([
    ["Disclosure(고지 분석)", Disclosure],
    ["CoverageRemodel(보장 리모델링)", CoverageRemodel],
  ])("%s 렌더가 UpdatePrompt 배선 전후로 동일하다", (_label, Page) => {
    const before = render(
      <MemoryRouter>
        <Page />
      </MemoryRouter>
    );
    const baselineHtml = before.container.innerHTML;
    const baselineNodes = before.container.querySelectorAll("*").length;
    expect(baselineNodes).toBeGreaterThan(0); // 화면이 실제로 렌더됐는지 먼저 확인
    cleanup();

    const after = render(
      <MemoryRouter>
        <Page />
        <UpdatePrompt />
      </MemoryRouter>
    );
    expect(after.container.innerHTML).toBe(baselineHtml);
    expect(after.container.querySelectorAll("*").length).toBe(baselineNodes);
  });
});

describe("★개인정보처리방침 — 오프라인 캐시 고지(1문장 추가)", () => {
  it("보유·파기 조항에 기기 내 임시 보관 문장이 추가된다", () => {
    render(
      <MemoryRouter>
        <PrivacyPolicy />
      </MemoryRouter>
    );
    const added = screen.getByText(/오프라인 열람용 기기 내 임시 보관/);
    expect(added.textContent).toContain("최근 분석 5건");
    expect(added.textContent).toContain("24시간");
    expect(added.textContent).toContain("로그아웃 시 즉시 삭제");
    // ★서버 전송 0 — A안의 핵심 사실이 고지에 포함돼야 한다.
    expect(added.textContent).toContain("서비스 서버로 전송되지 않습니다");
  });

  it("★기존 조항 문구가 그대로 보존된다(삭제·치환 0)", () => {
    for (const kept of [
      "업로드 원본 PDF와 분석 중 생성된 건강정보는 분석 직후 서버에서 폐기하는 것을 원칙으로 하며, 서비스 데이터베이스에 저장하지 않습니다.",
      "회원 계정 정보는 회원 탈퇴 시까지 보유하며, 탈퇴 후에는 지체 없이 파기합니다.",
      "업로드 PDF와 건강정보 분석 원천자료는 분석 처리 완료 후 즉시 삭제하는 것을 원칙으로 합니다.",
      "최근 분석 자동 기록(분석 결과 요약): 분석 실행 시 최근 10건 범위에서 자동 기록되며, 7일이 지나면 자동 파기합니다.",
      "접속 로그 등 서비스 운영 기록은 보안, 장애 대응, 부정 이용 방지를 위하여 필요한 기간 동안 보관 후 파기합니다.",
    ]) {
      expect(POLICY).toContain(kept);
    }
    // 조항 번호 체계 무변경
    for (const title of [
      "3. 민감정보(건강정보)의 처리",
      "4. 개인정보의 보유 및 이용기간",
      "5. 개인정보의 파기 절차 및 방법",
    ]) {
      expect(POLICY).toContain(title);
    }
  });
});
