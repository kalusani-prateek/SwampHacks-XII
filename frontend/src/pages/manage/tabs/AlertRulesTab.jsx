// Alert thresholds used by the backend condition monitors.
// Defaults follow the brief: lightning within 10 mi -> 30-min all-clear.
import { useEffect, useState } from 'react';
import { ErrorState, LoadingState } from '../../../components/common/Status.jsx';
import { useApi } from '../../../hooks/useApi.js';
import { getAlertRules, updateAlertRules } from '../../../api/settings.js';

// Field definitions: key in the rules object, label, unit, help text.
const FIELDS = [
  { key: 'lightningRadiusMiles', label: 'Lightning stop-work radius', unit: 'miles', help: 'Any strike inside this radius triggers a stop-work alert.' },
  { key: 'lightningAllClearMinutes', label: 'Lightning all-clear countdown', unit: 'minutes', help: 'Restarts with each new strike inside the radius.' },
  { key: 'floodRainInches', label: 'Overnight rain for flood warning', unit: 'inches', help: 'Applies to sites on rivers (e.g. the Mississippi).' },
  { key: 'heatIndexF', label: 'Extreme heat advisory', unit: '°F heat index', help: 'Triggers water-rest-shade guidance.' },
  { key: 'windMph', label: 'High-wind alert', unit: 'mph', help: 'Crane / aerial lift operating limit.' },
  { key: 'hazardIndexAlert', label: 'Hazard index alert level', unit: '0-10', help: 'Alert supervisors when a site\'s hazard index crosses this.' },
];

export default function AlertRulesTab() {
  // REST API PLACEHOLDER: GET /api/settings/alert-rules
  const { data, loading, error, reload } = useApi(() => getAlertRules());
  const [rules, setRules] = useState(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data) setRules(data.rules);
  }, [data]);

  async function handleSave(e) {
    e.preventDefault();
    await updateAlertRules(rules); // REST API PLACEHOLDER: PUT /api/settings/alert-rules
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  }

  if (loading || (!rules && !error)) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  return (
    <form onSubmit={handleSave} className="card max-w-3xl space-y-5">
      {FIELDS.map((f) => (
        <div key={f.key} className="grid items-center gap-2 sm:grid-cols-3">
          <div className="sm:col-span-2">
            <label htmlFor={f.key} className="text-sm font-semibold text-navy-800">
              {f.label}
            </label>
            <p className="text-xs text-slate-500">{f.help}</p>
          </div>
          <div className="flex items-center gap-2">
            <input
              id={f.key}
              type="number"
              step="any"
              min="0"
              className="input"
              value={rules[f.key]}
              onChange={(e) => setRules({ ...rules, [f.key]: Number(e.target.value) })}
            />
            <span className="text-xs whitespace-nowrap text-slate-500">{f.unit}</span>
          </div>
        </div>
      ))}
      <div className="flex items-center gap-3">
        <button className="btn-primary">Save rules</button>
        {saved && <span className="text-sm text-emerald-700">✓ Saved</span>}
      </div>
    </form>
  );
}
