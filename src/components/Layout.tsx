// BOHUMFIT-045: Mercury 라이트 네비 — 기능·라우팅 불변(시각 계층만).
// 밝은 캔버스 헤더 + 잉크 로고 + 활성 메뉴는 포인트색 텍스트(언더라인 없음).
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth-context";
import Footer from "./Footer";

const NAV_ITEMS = [
  { to: "/why", label: "왜 중요한가" },
  { to: "/check", label: "고객 점검" },
  { to: "/disclosure", label: "설계사 필터" },
  { to: "/insurance", label: "실손 계산" },
  { to: "/coverage", label: "보장분석" },
];

export default function Layout() {
  const { user, signOut } = useAuth();

  return (
    <div className="min-h-screen bg-canvas">
      <header className="sticky top-0 z-30 border-b border-line bg-canvas/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3.5">
          <Link
            to="/"
            className="shrink-0 text-lg font-extrabold tracking-tight text-ink-900 transition-colors hover:text-ink-700"
          >
            BOHUMFIT<span className="text-accent-600">.</span>
          </Link>

          <nav
            aria-label="주요 메뉴"
            className="flex min-w-0 items-center gap-1 overflow-x-auto text-sm font-medium"
          >
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `whitespace-nowrap rounded-btn px-3 py-1.5 transition-colors ${
                    isActive
                      ? "font-semibold text-accent-700"
                      : "text-ink-soft hover:bg-ink-50 hover:text-ink-900"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="flex shrink-0 items-center gap-3">
            {user ? (
              <>
                <span className="hidden text-caption text-ink-soft sm:inline">{user.email}</span>
                <button
                  onClick={signOut}
                  className="rounded-btn border border-line-strong bg-white px-3.5 py-1.5 text-caption font-semibold text-ink-800 transition-colors hover:bg-ink-50"
                >
                  로그아웃
                </button>
              </>
            ) : (
              <NavLink
                to="/login"
                className="rounded-btn bg-ink-900 px-4 py-1.5 text-caption font-semibold text-white transition-colors hover:bg-ink-700"
              >
                로그인
              </NavLink>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-8">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
