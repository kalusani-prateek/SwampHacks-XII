// Browser notifications for new stop-work and warning alerts, so crews hear
// about them even when the app is in a background tab.
import { useEffect, useRef } from 'react';

export const notificationsSupported = () => typeof window !== 'undefined' && 'Notification' in window;

/** Show a system notification (phones need the service-worker route). */
async function showNotification(title, options) {
  try {
    new Notification(title, options);
  } catch {
    const registration = await navigator.serviceWorker?.getRegistration?.();
    registration?.showNotification(title, options);
  }
}

/** Notify about alerts that weren't in the previous list (nothing on first load). */
export function useAlertNotifications(alerts) {
  const seen = useRef(null);
  useEffect(() => {
    if (!alerts) return;
    const ids = new Set(alerts.map((a) => a.id));
    if (seen.current && notificationsSupported() && Notification.permission === 'granted') {
      alerts
        .filter((a) => !seen.current.has(a.id) && a.severity !== 'info')
        .forEach((a) => showNotification(a.title, { body: `${a.siteName}: ${a.message}`, tag: `alert-${a.id}` }));
    }
    seen.current = ids;
  }, [alerts]);
}
