// Job-site management (supervisors only): add sites (e.g. from EIA-860M), pause
// monitoring, delete. The platform requires at least 50 real power plant locations.
// Search lives in the URL: /manage/sites?q=entergy
import { useState } from 'react';
import { Link } from 'react-router-dom';
import HazardBadge from '../../../components/common/HazardBadge.jsx';
import { ErrorState, LoadingState } from '../../../components/common/Status.jsx';
import { useApi } from '../../../hooks/useApi.js';
import { useQueryParam } from '../../../hooks/useQueryParam.js';
import { urls } from '../../../routes.js';
import { createSite, deleteSite, getAllSites, updateSite } from '../../../api/sites.js';

const MIN_SITES = 50;
const TIMEZONES = ['America/New_York', 'America/Chicago', 'America/Denver', 'America/Phoenix', 'America/Los_Angeles'];
const EMPTY_FORM = { name: '', state: '', lat: '', lng: '', plantType: '', utility: '', waterway: '', timezone: TIMEZONES[0] };

export default function SitesTab() {
  // REST API PLACEHOLDER: GET /api/sites?includeInactive=true
  const { data, loading, error, reload } = useApi(() => getAllSites());
  const [form, setForm] = useState(EMPTY_FORM);
  const [showForm, setShowForm] = useState(false);
  const [query, setQuery] = useQueryParam('q');

  async function handleCreate(e) {
    e.preventDefault();
    // REST API PLACEHOLDER: POST /api/sites
    await createSite({ ...form, lat: Number(form.lat), lng: Number(form.lng), waterway: form.waterway || null });
    setForm(EMPTY_FORM);
    setShowForm(false);
    reload({ silent: true });
  }

  async function toggleActive(site) {
    await updateSite(site.id, { active: !site.active }); // REST API PLACEHOLDER: PUT /api/sites/:id
    reload({ silent: true });
  }

  async function handleDelete(site) {
    if (!window.confirm(`Remove ${site.name} from monitoring permanently?`)) return;
    await deleteSite(site.id); // REST API PLACEHOLDER: DELETE /api/sites/:id
    reload({ silent: true });
  }

  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  const activeCount = data.sites.filter((s) => s.active).length;
  const q = query.trim().toLowerCase();
  const sites = data.sites.filter((s) => !q || `${s.name} ${s.state} ${s.utility}`.toLowerCase().includes(q));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <p className={`text-sm font-medium ${activeCount >= MIN_SITES ? 'text-emerald-700' : 'text-red-600'}`}>
          {activeCount} active sites {activeCount >= MIN_SITES ? '✓' : `(minimum ${MIN_SITES})`}
        </p>
        <input className="input ml-auto w-56" placeholder="Search…" value={query} onChange={(e) => setQuery(e.target.value)} />
        <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? 'Cancel' : '+ Add site'}
        </button>
      </div>

      {/* Add site form */}
      {showForm && (
        <form onSubmit={handleCreate} className="card grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ['name', 'Plant name', true],
            ['state', 'State (e.g. FL)', true],
            ['lat', 'Latitude', true],
            ['lng', 'Longitude', true],
            ['plantType', 'Plant type', false],
            ['utility', 'Utility / operator', false],
            ['waterway', 'Nearby river / water body', false],
          ].map(([field, label, required]) => (
            <div key={field}>
              <label className="label" htmlFor={`site-${field}`}>
                {label}
              </label>
              <input
                id={`site-${field}`}
                className="input"
                type={field === 'lat' || field === 'lng' ? 'number' : 'text'}
                step="any"
                required={required}
                value={form[field]}
                onChange={(e) => setForm({ ...form, [field]: e.target.value })}
              />
            </div>
          ))}
          <div>
            <label className="label" htmlFor="site-tz">
              Time zone (for 6 PM briefing)
            </label>
            <select id="site-tz" className="input" value={form.timezone} onChange={(e) => setForm({ ...form, timezone: e.target.value })}>
              {TIMEZONES.map((tz) => (
                <option key={tz}>{tz}</option>
              ))}
            </select>
          </div>
          <div className="sm:col-span-2 lg:col-span-4">
            <button className="btn-primary">Save site</button>
          </div>
        </form>
      )}

      {/* Site table */}
      <div className="card overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-slate-500 uppercase">
            <tr>
              <th className="px-2 py-2">Site</th>
              <th className="hidden px-2 py-2 md:table-cell">Utility</th>
              <th className="hidden px-2 py-2 lg:table-cell">Coordinates</th>
              <th className="px-2 py-2">Hazard</th>
              <th className="px-2 py-2">Monitoring</th>
              <th className="px-2 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sites.map((site) => (
              <tr key={site.id} className={site.active ? '' : 'opacity-50'}>
                <td className="px-2 py-2">
                  <Link to={urls.site(site.id)} className="font-medium hover:text-brand">
                    {site.name}
                  </Link>{' '}
                  <span className="text-xs text-slate-400">{site.state}</span>
                  <p className="text-xs text-slate-400">/sites/{site.id}</p>
                </td>
                <td className="hidden px-2 py-2 text-slate-600 md:table-cell">{site.utility}</td>
                <td className="hidden px-2 py-2 text-xs text-slate-500 tabular-nums lg:table-cell">
                  {site.lat.toFixed(4)}, {site.lng.toFixed(4)}
                </td>
                <td className="px-2 py-2">
                  <HazardBadge score={site.hazardIndex} />
                </td>
                <td className="px-2 py-2">
                  <button
                    onClick={() => toggleActive(site)}
                    className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                      site.active ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-600'
                    }`}
                  >
                    {site.active ? 'Active' : 'Paused'}
                  </button>
                </td>
                <td className="px-2 py-2 text-right">
                  <button className="text-sm font-medium text-red-600 hover:underline" onClick={() => handleDelete(site)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
