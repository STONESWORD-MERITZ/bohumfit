// BOHUMFIT-044: 금융 대시보드 톤 상단 네비 — 기능·라우팅 불변(시각 계층만).
// 브랜드 바(네이비→골드)는 PDF 리포트 아이덴티티를 화면으로 확장한 것.
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
      <header className="sticky top-0 z-30 border-b border-line bg-white/95 backdrop-blur">
        {/* 브랜드 바 — PDF 리포트 헤더와 동일한 네이비→골드 */}
        <div aria-hidden className="h-1 bg-gradient-to-r from-navy-800 via-navy-800 via-70% to-gold-400" />
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
          <Link
            to="/"
            className="shrink-0 text-lg font-extrabold tracking-tight text-navy-900 transition-colors hover:text-navy-700"
          >
            BOHUMFIT<span className="text-gold-400">.</span>
          </Link>

          <nav
            aria-label="주요 메뉴"
            className="flex min-w-0 items-center gap-1 overflow-x-auto text-sm font-semibold"
          >
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `whitespace-nowrap border-b-2 px-2.5 py-1.5 transition-colors ${
                    isActive
                      ? "border-gold-400 text-navy-900"
                      : "border-transparent text-ink-soft hover:text-navy-800"
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
                  className="rounded-lg border border-navy-200 bg-white px-3.5 py-1.5 text-caption font-bold text-navy-800 transition-colors hover:bg-navy-50"
                >
                  로그아웃
                </button>
              </>
            ) : (
              <NavLink
                to="/login"
                className="rounded-lg bg-navy-800 px-4 py-1.5 text-caption font-bold text-white transition-colors hover:bg-navy-700"
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
