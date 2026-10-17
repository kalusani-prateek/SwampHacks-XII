// Top navigation. Links are filtered by the signed-in user's role, and the
// alerts link shows a live count of active alerts. Everything stays on one
// line: account actions (your site, My account, sign out) sit in a menu under
// your initials, "Report hazard" is a button, and below 1024 px the links fold
// into a menu.
import { useEffect, useRef, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { hasRole, ROLES } from '../../utils/roles.js';
import { BACKEND_HINT, isMockFallback, USE_MOCKS } from '../../api/client.js';
import { PATHS, urls } from '../../routes.js';
import { notificationsSupported } from '../../hooks/useAlertNotifications.js';

// `roles` = who can see the link (undefined = everyone signed in).
// Links use base paths (not /manage/overview) so NavLink highlights the
// section for every page inside it, e.g. "Manage" on /manage/users.
// `end` = highlight only on that exact path (/reports, not /reports/new).
const LINKS = [
  { to: PATHS.dashboard, label: 'Dashboard' },
  { to: PATHS.sites, label: 'Sites' },
  { to: PATHS.alerts, label: 'Alerts', showAlertCount: true },
  { to: PATHS.reports, label: 'Reports', end: true },
  { to: PATHS.briefings, label: 'Briefings' },
  { to: PATHS.manage, label: 'Manage', roles: [ROLES.SUPERVISOR] },
];

// Small inline icons (no icon library needed).
const icon = (paths) =>
  function Icon({ className = 'h-5 w-5' }) {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
        {paths}
      </svg>
    );
  };
const BellIcon = icon(
  <>
    <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
    <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
  </>,
);
const PlusIcon = icon(<path d="M12 5v14M5 12h14" />);
const MenuIcon = icon(<path d="M4 6h16M4 12h16M4 18h16" />);
const CloseIcon = icon(<path d="M18 6 6 18M6 6l12 12" />);
const ChevronIcon = icon(<path d="m6 9 6 6 6-6" />);

/** "crew.lead" -> "CL", "supervisor" -> "SU". */
function initials(name) {
  const parts = name.split(/[^A-Za-z0-9]+/).filter(Boolean);
  return (parts.length > 1 ? parts[0][0] + parts[1][0] : name.slice(0, 2)).toUpperCase();
}

function Avatar({ user }) {
  return (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand text-xs font-bold text-white">
      {initials(user.username)}
    </span>
  );
}

/** Browser-notification permission, plus a way to ask for it (browsers require a click). */
function useNotificationPermission() {
  const [permission, setPermission] = useState(() => (notificationsSupported() ? Notification.permission : 'unsupported'));
  return [permission, async () => setPermission(await Notification.requestPermission())];
}

const mockBadge = (
  <span
    className="cursor-help rounded bg-yellow-400/20 px-2 py-0.5 text-xs font-semibold whitespace-nowrap text-yellow-300"
    title={isMockFallback() ? BACKEND_HINT : 'Demo data (VITE_USE_MOCKS=true)'}
  >
    MOCK DATA
  </span>
);

/** Your initials; opens a menu with your role and site, My account and Sign out. */
function AccountMenu({ user, onSignOut }) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);
  const { pathname } = useLocation();

  useEffect(() => setOpen(false), [pathname]); // close after navigating

  // Close on a click outside or Escape.
  useEffect(() => {
    if (!open) return undefined;
    const onPointerDown = (e) => {
      if (!menuRef.current?.contains(e.target)) setOpen(false);
    };
    const onKeyDown = (e) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  return (
    <div ref={menuRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls="account-menu"
        aria-label={`Account menu for ${user.username}`}
        className="flex items-center gap-2 rounded-full py-1 pr-2 pl-1 text-left transition hover:bg-white/10"
      >
        <Avatar user={user} />
        {/* Name and role beside the initials on wide screens */}
        <span className="hidden leading-tight xl:block">
          <span className="block max-w-32 truncate text-sm font-medium text-white">{user.username}</span>
          <span className="block text-xs text-slate-400 capitalize">{user.role}</span>
        </span>
        <ChevronIcon className={`h-4 w-4 text-slate-400 transition ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div
          id="account-menu"
          role="menu"
          className="absolute right-0 mt-2 w-64 overflow-hidden rounded-xl bg-white text-slate-700 shadow-lg ring-1 ring-black/5"
        >
          <div className="border-b border-slate-100 px-4 py-3">
            <p className="truncate font-semibold text-navy-800">{user.username}</p>
            <p className="text-xs text-slate-500 capitalize">{user.role}</p>
            <p className="mt-1 truncate text-xs text-slate-600">{user.siteName ? `📍 ${user.siteName}` : 'No site chosen yet'}</p>
          </div>
          <NavLink to={urls.account()} role="menuitem" className="block px-4 py-2.5 text-sm hover:bg-slate-50">
            My account
          </NavLink>
          <button type="button" role="menuitem" onClick={onSignOut} className="block w-full px-4 py-2.5 text-left text-sm hover:bg-slate-50">
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}

export default function Navbar({ activeAlertCount = 0 }) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false); // the menu below 1024 px
  const [permission, askPermission] = useNotificationPermission();
  const { pathname } = useLocation();

  useEffect(() => setOpen(false), [pathname]); // close after navigating

  // ProtectedRoute handles the redirect: a clean /login, so the next user starts fresh.
  const handleLogout = () => logout();

  // Active link: lighter background plus an orange marker (underneath on desktop, at the left in the menu).
  const linkClass =
    (stacked) =>
    ({ isActive }) =>
      `flex items-center rounded-md px-3 py-2 text-sm font-medium whitespace-nowrap transition ${
        isActive
          ? `bg-white/10 text-white ${stacked ? 'shadow-[inset_3px_0_0_0_var(--color-brand)]' : 'shadow-[inset_0_-2px_0_0_var(--color-brand)]'}`
          : 'text-slate-300 hover:bg-white/5 hover:text-white'
      }`;

  const links = (stacked) =>
    LINKS.filter((link) => hasRole(user, link.roles)).map((link) => (
      <NavLink key={link.to} to={link.to} end={link.end} className={linkClass(stacked)}>
        {link.label}
        {link.showAlertCount && activeAlertCount > 0 && (
          <span className="ml-1.5 min-w-5 rounded-full bg-red-600 px-1.5 text-center text-[11px] leading-5 font-bold text-white">
            {activeAlertCount}
          </span>
        )}
      </NavLink>
    ));

  return (
    <header className="relative z-40 bg-navy-800 text-white shadow">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4">
        {/* Logo */}
        <NavLink to={urls.home()} className="mr-2 shrink-0 text-lg font-extrabold tracking-tight whitespace-nowrap">
          PlanIT <span className="text-brand">Control</span>
        </NavLink>

        {/* Links (1024 px and wider) */}
        <nav aria-label="Main" className="hidden items-center gap-0.5 lg:flex">
          {links(false)}
        </nav>

        <div className="ml-auto flex items-center gap-1.5">
          {USE_MOCKS && <span className="hidden xl:inline">{mockBadge}</span>}
          {permission === 'default' && (
            <button
              type="button"
              onClick={askPermission}
              title="Turn on alert notifications"
              aria-label="Turn on alert notifications"
              className="hidden rounded-md p-2 text-slate-300 transition hover:bg-white/10 hover:text-white lg:inline-flex"
            >
              <BellIcon />
            </button>
          )}
          <NavLink to={urls.newReport()} className="btn-primary px-3 py-1.5 whitespace-nowrap" aria-label="Report a hazard" title="Report a hazard">
            <PlusIcon className="h-4 w-4" />
            <span className="hidden sm:inline">Report hazard</span>
          </NavLink>
          <div className="hidden lg:block">
            <AccountMenu user={user} onSignOut={handleLogout} />
          </div>
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label={open ? 'Close menu' : 'Open menu'}
            className="rounded-md p-2 text-slate-200 transition hover:bg-white/10 lg:hidden"
          >
            {open ? <CloseIcon /> : <MenuIcon />}
          </button>
        </div>
      </div>

      {/* Menu below 1024 px: you, the links, then account actions */}
      {open && (
        <div id="mobile-menu" className="border-t border-white/10 lg:hidden">
          <div className="mx-auto max-w-7xl px-4 py-3">
            <div className="mb-2 flex items-center gap-3 px-3 pb-2">
              <Avatar user={user} />
              <div className="min-w-0 leading-tight">
                <p className="truncate text-sm font-semibold">{user.username}</p>
                <p className="truncate text-xs text-slate-400">
                  <span className="capitalize">{user.role}</span>
                  {user.siteName && ` · 📍 ${user.siteName}`}
                </p>
              </div>
              {USE_MOCKS && <span className="ml-auto">{mockBadge}</span>}
            </div>
            <nav aria-label="Main" className="space-y-1">
              {links(true)}
            </nav>
            <div className="mt-2 space-y-1 border-t border-white/10 pt-2">
              <NavLink to={urls.account()} className={linkClass(true)}>
                My account
              </NavLink>
              {permission === 'default' && (
                <button
                  type="button"
                  onClick={askPermission}
                  className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-medium text-slate-300 hover:bg-white/5 hover:text-white"
                >
                  <BellIcon className="h-4 w-4" /> Turn on alert notifications
                </button>
              )}
              <button
                type="button"
                onClick={handleLogout}
                className="block w-full rounded-md px-3 py-2 text-left text-sm font-medium text-slate-300 hover:bg-white/5 hover:text-white"
              >
                Sign out
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
