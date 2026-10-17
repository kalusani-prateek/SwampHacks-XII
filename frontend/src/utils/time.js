// Date/time helpers. Sites span several US time zones, so anything shown as
// "local" is formatted in the site's own IANA time zone.

/** e.g. "3:42 PM CDT" in the given time zone. */
export function formatLocalTime(date, timeZone) {
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
    timeZone,
  }).format(new Date(date));
}

/** e.g. "Oct 16, 3:42 PM" in the viewer's time zone. */
export function formatDateTime(date) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(date));
}

/** "5 min ago", "2 h ago", ... */
export function timeAgo(date) {
  const minutes = Math.round((Date.now() - new Date(date).getTime()) / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  return `${Math.round(hours / 24)} d ago`;
}

/** mm:ss for countdown timers. */
export function formatCountdown(ms) {
  const totalSeconds = Math.max(0, Math.ceil(ms / 1000));
  const m = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
  const s = String(totalSeconds % 60).padStart(2, '0');
  return `${m}:${s}`;
}

/** Short weekday label ("Mon") for forecast charts. */
export function weekdayLabel(date) {
  return new Intl.DateTimeFormat('en-US', { weekday: 'short' }).format(new Date(date));
}
