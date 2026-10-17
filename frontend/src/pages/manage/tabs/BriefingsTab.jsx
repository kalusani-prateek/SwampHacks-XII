// Daily next-day briefing settings: send time (site-local), delivery
// channels, recipients, a "send now" button, and the outbox of recent
// emails/texts (recorded only, when SMTP/Twilio aren't configured).
import { useEffect, useState } from 'react';
import { EmptyState, ErrorState, LoadingState } from '../../../components/common/Status.jsx';
import { useApi } from '../../../hooks/useApi.js';
import { getBriefingSettings, updateBriefingSettings } from '../../../api/settings.js';
import { sendBriefingsNow } from '../../../api/briefings.js';
import { getNotifications } from '../../../api/notifications.js';
import { ROLES } from '../../../utils/roles.js';
import { timeAgo } from '../../../utils/time.js';

const STATUS_STYLES = {
  sent: 'bg-emerald-100 text-emerald-800',
  logged: 'bg-slate-200 text-slate-700',
  failed: 'bg-red-100 text-red-800',
};

/** Recent outbound emails and texts. */
function Outbox({ notifications }) {
  return (
    <div className="card max-w-2xl">
      <h2 className="font-semibold text-navy-800">Recent notifications</h2>
      <p className="mb-2 text-xs text-slate-500">
        "logged" means the message was recorded but not sent, because email (SMTP) or SMS (Twilio) isn't configured on the server.
      </p>
      {notifications.length === 0 ? (
        <EmptyState>No notifications yet.</EmptyState>
      ) : (
        <ul className="divide-y divide-slate-100">
          {notifications.map((n) => (
            <li key={n.id} className="py-2 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_STYLES[n.status]}`}>{n.status}</span>
                <span className="font-medium uppercase text-slate-500">{n.channel}</span>
                <span className="text-slate-700">{n.recipient}</span>
                <span className="ml-auto text-xs text-slate-400">{timeAgo(n.createdAt)}</span>
              </div>
              <p className="mt-1 truncate text-slate-600">{n.subject || n.body}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function BriefingsTab() {
  // REST API PLACEHOLDER: GET /api/settings/briefings
  const { data, loading, error, reload } = useApi(() => getBriefingSettings());
  // REST API PLACEHOLDER: GET /api/notifications
  const outbox = useApi(() => getNotifications(10));
  const [settings, setSettings] = useState(null);
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (data) setSettings(data.settings);
  }, [data]);

  function flash(text) {
    setMessage(text);
    setTimeout(() => setMessage(''), 3000);
  }

  async function handleSave(e) {
    e.preventDefault();
    await updateBriefingSettings(settings); // REST API PLACEHOLDER: PUT /api/settings/briefings
    flash('✓ Settings saved');
  }

  async function handleSendNow() {
    const { sent } = await sendBriefingsNow(); // REST API PLACEHOLDER: POST /api/briefings
    flash(`✓ Briefings sent for ${sent} sites`);
    outbox.reload({ silent: true });
  }

  function toggleRecipient(role) {
    const recipients = settings.recipients.includes(role)
      ? settings.recipients.filter((r) => r !== role)
      : [...settings.recipients, role];
    setSettings({ ...settings, recipients });
  }

  if (loading || (!settings && !error)) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  return (
    <div className="space-y-6">
      <form onSubmit={handleSave} className="card max-w-2xl space-y-5">
        <label className="flex items-center gap-3">
          <input
            type="checkbox"
            className="h-4 w-4 accent-brand"
            checked={settings.enabled}
            onChange={(e) => setSettings({ ...settings, enabled: e.target.checked })}
          />
          <span className="text-sm font-semibold text-navy-800">Send daily next-day safety briefing</span>
        </label>
  
        <div>
          <label className="label" htmlFor="send-time">
            Send time (each site's local time)
          </label>
          <input
            id="send-time"
            type="time"
            className="input w-40"
            value={settings.localTime}
            onChange={(e) => setSettings({ ...settings, localTime: e.target.value })}
          />
          <p className="mt-1 text-xs text-slate-500">Brief requirement: 6:00 PM local.</p>
        </div>
  
        <div>
          <span className="label">Channels</span>
          <div className="flex flex-wrap gap-4">
            {Object.keys(settings.channels).map((channel) => (
              <label key={channel} className="flex items-center gap-2 text-sm capitalize">
                <input
                  type="checkbox"
                  className="accent-brand"
                  checked={settings.channels[channel]}
                  onChange={(e) => setSettings({ ...settings, channels: { ...settings.channels, [channel]: e.target.checked } })}
                />
                {channel}
              </label>
            ))}
          </div>
        </div>
  
        <div>
          <span className="label">Recipients</span>
          <div className="flex flex-wrap gap-4">
            {Object.values(ROLES).map((role) => (
              <label key={role} className="flex items-center gap-2 text-sm capitalize">
                <input
                  type="checkbox"
                  className="accent-brand"
                  checked={settings.recipients.includes(role)}
                  onChange={() => toggleRecipient(role)}
                />
                {role}
              </label>
            ))}
          </div>
        </div>
  
        <div className="flex flex-wrap items-center gap-3">
          <button className="btn-primary">Save settings</button>
          <button type="button" className="btn-secondary" onClick={handleSendNow}>
            Send briefings now
          </button>
          {message && <span className="text-sm text-emerald-700">{message}</span>}
        </div>
      </form>
      <Outbox notifications={outbox.data?.notifications ?? []} />
    </div>
  );
}
