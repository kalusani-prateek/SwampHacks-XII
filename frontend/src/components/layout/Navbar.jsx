// Top navigation. Links are filtered by the signed-in user's role, and the
// alerts link shows a live count of active alerts.
import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { hasRole, ROLES } from '../../utils/roles.js';
import { BACKEND_HINT, isMockFallback, USE_MOCKS } from '../../api/client.js';
import { PATHS, urls } from '../../routes.js';
import { notificationsSupported } from '../../hooks/useAlertNotifications.js';

/** Asks once for permission to show browser notifications for new alerts. */
function NotificationButton({ className }) {
  const [permission, setPermission] = useState(() => (notificationsSupported() ? Notification.permission : 'unsupported'));
  if (permission !== 'default') return null; // already allowed, blocked, or unsupported
  return (
    <button className={className} onClick={async () => setPermission(await Notification.requestPermission())}>
      🔔 Enable alert notifications
    </button>
  );
}

// `roles` = who can see the link (undefined = everyone signed in).
// Links use base paths (not /manage/overview) so NavLink highlights the
// section for every page inside it, e.g. "Manage" on /manage/users.
const LINKS = [
  { to: PATHS.dashboard, label: 'PlanIt Dashboard', roles: [ROLES.SUPERVISOR] },
  { to: PATHS.sites, label: 'Sites' },
  { to: PATHS.alerts, label: 'Alerts', showAlertCount: true },
  { to: PATHS.newReport, label: 'Report Hazard' },
  { to: PATHS.briefings, label: 'Briefings' },
  { to: PATHS.manage, label: 'Manage', roles: [ROLES.SUPERVISOR] },
];

export default function Navbar({ activeAlertCount = 0 }) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false); // mobile menu

  // ProtectedRoute handles the redirect: a clean /login, so the next user starts fresh.
  const handleLogout = () => logout();

  const linkClass = ({ isActive }) =>
    `block rounded-md px-3 py-2 text-sm font-medium transition ${
      isActive ? 'bg-white/10 text-white' : 'text-slate-300 hover:bg-white/5 hover:text-white'
    }`;

  const links = LINKS.filter((link) => hasRole(user, link.roles)).map((link) => (
    <NavLink key={link.to} to={link.to} className={linkClass} onClick={() => setOpen(false)}>
      {link.label}
      {link.showAlertCount && activeAlertCount > 0 && (
        <span className="ml-2 rounded-full bg-red-600 px-1.5 py-0.5 text-xs font-bold text-white">
          {activeAlertCount}
        </span>
      )}
    </NavLink>
  ));

  return (
    <header className="bg-navy-800 text-white shadow">
      <div className="mx-auto flex max-w-7xl items-center gap-6 px-4 py-3">
        {/* Logo */}
        <NavLink to={urls.home()} className="text-lg font-extrabold tracking-tight">
          PlanIT <span className="text-brand">Control</span>
        </NavLink>

        {/* Desktop links */}
        <nav className="hidden flex-1 items-center gap-1 md:flex">{links}</nav>

        {/* User info + logout */}
        <div className="ml-auto hidden items-center gap-3 md:flex">
          {USE_MOCKS && (
            <span
              className="cursor-help rounded bg-yellow-400/20 px-2 py-0.5 text-xs font-semibold text-yellow-300"
              title={isMockFallback() ? BACKEND_HINT : 'Demo data (VITE_USE_MOCKS=true)'}
            >
              MOCK DATA
            </span>
          )}
          <NotificationButton className="rounded-md px-2 py-1 text-xs text-slate-300 hover:bg-white/10" />
          <span className="text-sm text-slate-300">
            {user.username} <span className="text-slate-500">({user.role})</span>
          </span>
          <button onClick={handleLogout} className="rounded-md px-3 py-1.5 text-sm text-slate-300 hover:bg-white/10">
            Sign out
          </button>
        </div>

        {/* Mobile menu toggle */}
        <button className="ml-auto rounded-md p-2 md:hidden" onClick={() => setOpen((o) => !o)} aria-label="Menu">
          ☰
        </button>
      </div>

      {/* Mobile links */}
      {open && (
        <nav className="space-y-1 border-t border-white/10 px-4 py-3 md:hidden">
          {links}
          <NotificationButton className="block w-full rounded-md px-3 py-2 text-left text-sm text-slate-300" />
          <button onClick={handleLogout} className="block w-full rounded-md px-3 py-2 text-left text-sm text-slate-300">
            Sign out ({user.username})
          </button>
        </nav>
      )}
    </header>
  );
}
