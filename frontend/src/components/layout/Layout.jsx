// App shell for signed-in pages: navbar, offline and stop-work banners, page
// content and the floating AI assistant. New alerts also raise browser
// notifications (once the user allows them in the navbar).
import { useEffect } from 'react';
import { Link, Outlet } from 'react-router-dom';
import { urls } from '../../routes.js';
import Navbar from './Navbar.jsx';
import ChatWidget from '../chat/ChatWidget.jsx';
import { useApi } from '../../hooks/useApi.js';
import { usePolling } from '../../hooks/usePolling.js';
import { useAlertNotifications } from '../../hooks/useAlertNotifications.js';
import { useOnlineStatus } from '../../hooks/useOnlineStatus.js';
import { getAlerts, subscribeToAlerts } from '../../api/alerts.js';

const ALERT_POLL_MS = 30_000;

export default function Layout() {
  // REST API PLACEHOLDER: GET /api/alerts?active=true (polled every 30 s)
  const { data, reload } = useApi(() => getAlerts({ activeOnly: true }));
  usePolling(() => reload({ silent: true }), ALERT_POLL_MS);

  // REST API PLACEHOLDER: GET /api/alerts/stream (SSE). Refresh as soon as the server pushes an alert.
  useEffect(() => subscribeToAlerts(() => reload({ silent: true })), [reload]);

  useAlertNotifications(data?.alerts);
  const online = useOnlineStatus();

  const alerts = data?.alerts ?? [];
  const stopWork = alerts.filter((a) => a.severity === 'stop-work');

  return (
    <div className="min-h-screen bg-slate-100">
      <Navbar activeAlertCount={alerts.length} />

      {/* Offline: pages show the last data saved on this device (see public/sw.js) */}
      {!online && (
        <div className="bg-amber-500 text-amber-950">
          <p className="mx-auto max-w-7xl px-4 py-2 text-sm font-semibold">
            You're offline. Showing the last data saved on this device; reports and changes need a connection.
          </p>
        </div>
      )}

      {/* Stop-work banner: shown on every page while any site has an active stop-work alert */}
      {stopWork.length > 0 && (
        <div className="bg-red-600 text-white">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2 text-sm">
            <span className="font-bold">⚡ STOP WORK in effect at {stopWork.length} site(s):</span>
            <span className="truncate">{stopWork.map((a) => a.siteName).join(', ')}</span>
            <Link to={urls.alerts()} className="ml-auto font-semibold underline">
              View alerts
            </Link>
          </div>
        </div>
      )}

      {/* Bottom padding keeps page content clear of the floating chat button */}
      <main className="mx-auto max-w-7xl px-4 pt-6 pb-24">
        <Outlet />
      </main>

      <ChatWidget />
    </div>
  );
}
