// BOHUMFIT-047: 상단 가로 네비 셸 (Mercury 문법) — 기능·산식·라우팅 변경 0.
// 046 좌측 사이드바를 폐기하고 상단 sticky 바로 전환. 설계사 대면 운용 기준(빠른 전환·시연).
// - 데스크탑/태블릿: 가로 한 줄. '알릴의무 필터'는 고객용/설계사용 드롭다운.
// - 모바일: 햄버거 → 드롭다운 패널(aria-expanded·role=menu, ESC·외부클릭 닫기, motion-safe).
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { ChevronDown, Menu, X } from "lucide-react";
import { useAuth } from "../lib/auth-context";
import Footer from "./Footer";
import Logo from "./Logo";

type SimpleItem = { kind: "link"; to: string; label: string };
type MenuItem =
  | SimpleItem
  | {
      kind: "dropdown";
      label: string;
      /** 활성 판정 기준 경로 (startsWith) */
      match: string;
      items: ReadonlyArray<{ to: string; label: string; caption: string }>;
    };

// BOHUMFIT-077/079: 설계사 업무 흐름 기준 메뉴 재구성.
//   자료 받기 | 고지의무 분석 | 보장 비교분석 | 실손 계산 | 요금제
//   ("왜 중요한가" 제거→메인 통합, "알릴의무 필터"→"고지의무 분석", "보장분석"→"보장 비교분석"=/coverage-compare)
const NAV: ReadonlyArray<MenuItem> = [
  { kind: "link", to: "/download-guide", label: "자료 받기" },
  {
    kind: "dropdown",
    label: "고지의무 분석",
    match: "/disclosure",
    items: [
      { to: "/disclosure?mode=agent", label: "설계사용", caption: "청약 전 고지의무 분석" },
      { to: "/disclosure?mode=customer", label: "고객용", caption: "기존 보험 고지 점검" },
    ],
  },
  { kind: "link", to: "/coverage-compare", label: "보장 비교분석" },
  { kind: "link", to: "/insurance", label: "실손 계산" },
  // BOHUMFIT-093: 보험사 전산·약관·팩스 링크모음(공개)
  { kind: "link", to: "/insurance-links", label: "보험사 링크" },
  { kind: "link", to: "/subscription", label: "요금제" },
];

const LINK_BASE =
  "relative px-1 py-1.5 text-sm transition-colors after:absolute after:inset-x-0 after:-bottom-[14px] after:h-0.5 after:rounded-full";
const LINK_ACTIVE = "font-semibold text-accent-700 after:bg-accent-600";
const LINK_IDLE = "font-medium text-ink-soft hover:text-ink-900 after:bg-transparent";

function BrandLogo({ onClick }: { onClick?: () => void }) {
  return (
    <Link to="/" onClick={onClick} className="shrink-0" aria-label="보험핏 홈">
      <Logo size={20} variant="light" />
    </Link>
  );
}

/** 데스크탑 드롭다운 (호버/클릭/포커스 열림, ESC·외부클릭 닫기) */
function NavDropdown({
  label,
  active,
  items,
}: {
  label: string;
  active: boolean;
  items: ReadonlyArray<{ to: string; label: string; caption: string }>;
}) {
  const [open, setOpen] = useState(false);
  const [pinned, setPinned] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const visible = open || pinned;
  const close = useCallback(() => {
    setOpen(false);
    setPinned(false);
  }, []);

  useEffect(() => {
    if (!visible) return;
    const onDocClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) close();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("mousedown", onDocClick);
    window.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      window.removeEventListener("keydown", onKey);
    };
  }, [close, visible]);

  return (
    <div
      ref={ref}
      className="relative"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={visible}
        onClick={() => {
          setOpen(true);
          setPinned((v) => !v);
        }}
        className={`${LINK_BASE} inline-flex items-center gap-1 ${active ? LINK_ACTIVE : LINK_IDLE}`}
      >
        {label}
        <ChevronDown size={14} strokeWidth={2} aria-hidden className={`transition-transform ${visible ? "rotate-180" : ""}`} />
      </button>
      {visible && (
        <div
          role="menu"
          className="absolute left-0 top-[calc(100%+12px)] z-50 w-56 overflow-hidden rounded-card border border-line bg-white py-1 shadow-overlay"
        >
          {items.map((it) => (
            <Link
              key={it.to}
              to={it.to}
              role="menuitem"
              onClick={close}
              className="block px-4 py-2.5 transition-colors hover:bg-accent-50"
            >
              <span className="block text-sm font-semibold text-ink-900">{it.label}</span>
              <span className="block text-caption text-ink-soft">{it.caption}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function UserArea({ stacked = false }: { stacked?: boolean }) {
  const { user, signOut } = useAuth();
  if (!user) {
    return (
      <NavLink
        to="/login"
        className="rounded-btn bg-ink-900 px-4 py-1.5 text-caption font-semibold text-white transition-colors hover:bg-ink-700"
      >
        로그인
      </NavLink>
    );
  }
  return (
    <div className={stacked ? "space-y-2" : "flex items-center gap-3"}>
      <span className={`truncate text-caption text-ink-soft ${stacked ? "block" : "hidden md:inline"}`} title={user.email ?? undefined}>
        {user.email}
      </span>
      {/* BOHUMFIT-163: 대시보드 진입점(로그인 시) — 구독 왼쪽 */}
      <NavLink
        to="/dashboard"
        className={({ isActive }) =>
          `rounded-btn px-3.5 py-1.5 text-caption font-semibold transition-colors ${stacked ? "block w-full text-center " : ""}${
            isActive ? "bg-accent-50 text-accent-700" : "text-ink-800 hover:bg-ink-50"
          }`
        }
      >
        대시보드
      </NavLink>
      {/* BOHUMFIT-075: 구독 메뉴(로그인 시) — 로그아웃 왼쪽 */}
      <NavLink
        to="/subscription"
        className={({ isActive }) =>
          `rounded-btn px-3.5 py-1.5 text-caption font-semibold transition-colors ${stacked ? "block w-full text-center " : ""}${
            isActive ? "bg-accent-50 text-accent-700" : "text-ink-800 hover:bg-ink-50"
          }`
        }
      >
        구독
      </NavLink>
      <button
        onClick={signOut}
        className={`rounded-btn border border-line-strong bg-white px-3.5 py-1.5 text-caption font-semibold text-ink-800 transition-colors hover:bg-ink-50 ${stacked ? "w-full" : ""}`}
      >
        로그아웃
      </button>
    </div>
  );
}

export default function Layout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const panelRef = useRef<HTMLDivElement>(null);

  // 라우트(쿼리 포함) 변경 시 모바일 메뉴 닫기
  useEffect(() => {
    const timer = window.setTimeout(() => setMenuOpen(false), 0);
    return () => window.clearTimeout(timer);
  }, [location.pathname, location.search]);

  // 모바일 메뉴 열림: ESC·외부클릭 닫기 (드롭다운 패널이라 스크롤 잠금은 생략)
  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    const onDocClick = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    window.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onDocClick);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onDocClick);
    };
  }, [menuOpen]);

  const disclosureActive = location.pathname.startsWith("/disclosure");

  return (
    // BOHUMFIT-173: 100vh→100dvh — 모바일 주소창 수축 반영(짧은 페이지 footer 가림 방지). min-height라 긴 페이지 무영향.
    <div className="min-h-dvh bg-canvas">
      <header className="sticky top-0 z-40 border-b border-line bg-canvas/90 backdrop-blur">
        <div ref={panelRef} className="mx-auto max-w-6xl px-5">
          <div className="flex h-14 items-center justify-between gap-4">
            <BrandLogo />

            {/* 데스크탑·태블릿 가로 메뉴 */}
            <nav aria-label="주요 메뉴" className="hidden items-center gap-8 md:flex">
              {NAV.map((item) =>
                item.kind === "link" ? (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) => `${LINK_BASE} ${isActive ? LINK_ACTIVE : LINK_IDLE}`}
                  >
                    {item.label}
                  </NavLink>
                ) : (
                  <NavDropdown key={item.label} label={item.label} active={disclosureActive} items={item.items} />
                ),
              )}
            </nav>

            <div className="hidden md:block">
              <UserArea />
            </div>

            {/* 모바일 햄버거 */}
            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              aria-label={menuOpen ? "메뉴 닫기" : "메뉴 열기"}
              aria-expanded={menuOpen}
              aria-controls="bf-top-menu"
              className="rounded-btn p-2 text-ink-700 transition-colors hover:bg-ink-50 md:hidden"
            >
              {menuOpen ? <X size={20} aria-hidden /> : <Menu size={20} aria-hidden />}
            </button>
          </div>

          {/* 모바일 드롭다운 패널 */}
          {menuOpen && (
            <div
              id="bf-top-menu"
              role="menu"
              className="border-t border-line py-2 md:hidden"
            >
              {NAV.map((item) =>
                item.kind === "link" ? (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    role="menuitem"
                    onClick={() => setMenuOpen(false)}
                    className={({ isActive }) =>
                      `block rounded-btn px-3 py-2.5 text-sm transition-colors ${
                        isActive ? "bg-accent-50 font-semibold text-accent-700" : "font-medium text-ink-soft hover:bg-ink-50"
                      }`
                    }
                  >
                    {item.label}
                  </NavLink>
                ) : (
                  <div key={item.label} className="px-3 py-1.5">
                    <p className="px-0 py-1 text-caption font-semibold text-ink-400">{item.label}</p>
                    {item.items.map((sub) => (
                      <Link
                        key={sub.to}
                        to={sub.to}
                        role="menuitem"
                        onClick={() => setMenuOpen(false)}
                        className="block rounded-btn px-3 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-ink-50 hover:text-ink-900"
                      >
                        {sub.label}
                        <span className="ml-1.5 text-caption font-normal text-ink-400">{sub.caption}</span>
                      </Link>
                    ))}
                  </div>
                ),
              )}
              <div className="mt-2 border-t border-line px-3 pt-3">
                <UserArea stacked />
              </div>
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-5 py-8">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
