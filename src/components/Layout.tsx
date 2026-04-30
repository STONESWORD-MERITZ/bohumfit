import { NavLink, Outlet } from "react-router-dom";

export default function Layout() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-5 h-14 flex items-center text-sm font-semibold border-b-[3px] transition-colors whitespace-nowrap ${
      isActive
        ? "text-blue-500 border-blue-500 font-bold"
        : "text-gray-500 border-transparent hover:text-gray-900"
    }`;

  return (
    <div className="min-h-screen bg-[#0a1628]">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-6xl mx-auto flex items-center gap-1 px-4">
          <NavLink to="/" className="px-4 h-14 flex items-center text-base font-black text-gray-900 hover:text-blue-500 tracking-tight">
            SURIT
          </NavLink>
          <NavLink to="/disclosure" className={linkClass}>
            알릴의무 필터
          </NavLink>
          <NavLink to="/before-after" className={linkClass}>
            보장분석 비포&에프터
          </NavLink>
        </div>
      </nav>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-6 pb-10">
        <Outlet />
      </main>
    </div>
  );
}
