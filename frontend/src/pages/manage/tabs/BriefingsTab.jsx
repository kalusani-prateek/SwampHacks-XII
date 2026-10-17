// Daily next-day briefing settings: send time (site-local), delivery
// channels, recipients, plus a "send now" button for testing.
import { useEffect, useState } from 'react';
import { ErrorState, LoadingState } from '../../../components/common/Status.jsx';
import { useApi } from '../../../hooks/useApi.js';
import { getBriefingSettings, updateBriefingSettings } from '../../../api/settings.js';
import { sendBriefingsNow } from '../../../api/briefings.js';
import { ROLES } from '../../../utils/roles.js';

export default function BriefingsTab() {
  // REST API PLACEHOLDER: GET /api/settings/briefings
  const { data, loading, error, reload } = useApi(() => getBriefingSettings());
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
  );
}
