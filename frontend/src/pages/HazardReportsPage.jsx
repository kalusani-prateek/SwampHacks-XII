// Hazard reports from every crew: /reports?type=wildlife&days=7&mine=true
// Reports at your designated site come first (highlighted), newest first.
// Everyone can browse and search and can edit or delete the reports they made.
// Supervisors (who hold the admin privileges) can edit, re-status or delete
// any report. Filters live in the URL, so a filtered view can be shared and
// survives a reload.
import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import PageHeader from '../components/common/PageHeader.jsx';
import ReportEditor from '../components/reports/ReportEditor.jsx';
import ReportList from '../components/reports/ReportList.jsx';
import { ErrorState, LoadingState } from '../components/common/Status.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useApi } from '../hooks/useApi.js';
import { usePolling } from '../hooks/usePolling.js';
import { useQueryParam } from '../hooks/useQueryParam.js';
import { deleteReport, getReports, updateReport } from '../api/reports.js';
import { getSites } from '../api/sites.js';
import { DEFAULT_REPORT_WINDOW, REPORT_STATUSES, REPORT_WINDOWS, urls } from '../routes.js';
import { REPORT_TYPES } from '../utils/hazard.js';
import { mySiteFirst } from '../utils/mySite.js';
import { ROLES } from '../utils/roles.js';

const MAX_SHOWN = 500; // the server returns at most this many

export default function HazardReportsPage() {
  const { user } = useAuth();
  const isSupervisor = user.role === ROLES.SUPERVISOR;
  const [, setParams] = useSearchParams();
  const [q, setQ] = useQueryParam('q');
  const [site, setSite] = useQueryParam('site');
  const [type, setType] = useQueryParam('type', { allowed: Object.keys(REPORT_TYPES) });
  const [status, setStatus] = useQueryParam('status', { defaultValue: 'all', allowed: REPORT_STATUSES });
  const [days, setDays] = useQueryParam('days', { defaultValue: DEFAULT_REPORT_WINDOW, allowed: REPORT_WINDOWS.map((w) => w.value) });
  const [mine, setMine] = useQueryParam('mine', { allowed: ['true'] });
  const [search, setSearch] = useState(q); // what's typed; searched after a short pause
  const [editingId, setEditingId] = useState(null);
  const [actionError, setActionError] = useState('');

  // Search once typing pauses, not on every keystroke.
  useEffect(() => {
    if (search.trim() === q) return undefined;
    const timer = setTimeout(() => setQ(search.trim()), 300);
    return () => clearTimeout(timer);
  }, [search, q, setQ]);

  // REST API PLACEHOLDER: GET /api/sites (names + the site filter)
  const sitesApi = useApi(() => getSites());
  // REST API PLACEHOLDER: GET /api/reports?siteId=&type=&status=&days=&q=&mine=true
  const { data, loading, error, reload } = useApi(
    () =>
      getReports(
        {
          siteId: site || undefined,
          type: type || undefined,
          status: status === 'all' ? undefined : status,
          days: days === 'all' ? undefined : days,
          q: q || undefined,
          mine: mine === 'true',
        },
        user,
      ),
    [site, type, status, days, q, mine, user],
  );
  // New reports show up without a refresh (paused while editing).
  usePolling(() => reload({ silent: true }), editingId ? null : 30_000);

  const sites = sitesApi.data?.sites ?? [];
  const siteById = Object.fromEntries(sites.map((s) => [s.id, s]));
  const siteNames = Object.fromEntries(sites.map((s) => [s.id, s.name]));
  const filtered = Boolean(q || site || type || mine) || status !== 'all' || days !== DEFAULT_REPORT_WINDOW;

  function clearFilters() {
    setSearch('');
    setParams({}, { replace: true }); // one URL update; separate setters would overwrite each other
  }

  async function save(report, changes) {
    await updateReport(report.id, changes); // REST API PLACEHOLDER: PATCH /api/reports/:id (errors show in the form)
    setEditingId(null);
    reload({ silent: true });
  }

  async function remove(report) {
    const label = REPORT_TYPES[report.type]?.label.toLowerCase() ?? 'hazard';
    if (!window.confirm(`Delete this ${label} report? This can't be undone.`)) return;
    setActionError('');
    try {
      await deleteReport(report.id); // REST API PLACEHOLDER: DELETE /api/reports/:id
      reload({ silent: true });
    } catch (err) {
      setActionError(err.message);
    }
  }

  return (
    <>
      <PageHeader
        title="Hazard reports"
        subtitle={
          isSupervisor
            ? 'Hazards reported by crews at every site. As a supervisor you can edit, re-status or delete any report.'
            : 'Hazards reported by crews at every site. You can edit or delete the reports you made.'
        }
        actions={
          <Link to={urls.newReport({ site: site || undefined })} className="btn-primary">
            + Report a hazard
          </Link>
        }
      />

      {/* Filters */}
      <div className="card mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <div className="sm:col-span-2 lg:col-span-1">
          <label className="label" htmlFor="report-search">
            Search
          </label>
          <input
            id="report-search"
            type="search"
            className="input"
            placeholder="gator, road, crew name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div>
          <label className="label" htmlFor="report-site">
            Site
          </label>
          <select id="report-site" className="input" value={site} onChange={(e) => setSite(e.target.value)}>
            <option value="">All sites</option>
            {sites.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.state})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="report-type">
            Hazard type
          </label>
          <select id="report-type" className="input" value={type} onChange={(e) => setType(e.target.value)}>
            <option value="">All types</option>
            {Object.entries(REPORT_TYPES).map(([key, t]) => (
              <option key={key} value={key}>
                {t.icon} {t.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="report-status">
            Status
          </label>
          <select id="report-status" className="input capitalize" value={status} onChange={(e) => setStatus(e.target.value)}>
            {REPORT_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s === 'all' ? 'All statuses' : s}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="report-days">
            Reported
          </label>
          <select id="report-days" className="input" value={days} onChange={(e) => setDays(e.target.value)}>
            {REPORT_WINDOWS.map((w) => (
              <option key={w.value} value={w.value}>
                {w.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-wrap items-center gap-4 sm:col-span-2 lg:col-span-5">
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={mine === 'true'} onChange={(e) => setMine(e.target.checked ? 'true' : '')} />
            Only my reports
          </label>
          {filtered && (
            <button type="button" className="text-sm font-medium text-brand hover:underline" onClick={clearFilters}>
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Results */}
      <div className="card">
        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState error={error} onRetry={reload} />
        ) : (
          <>
            <p className="mb-1 text-sm text-slate-500" aria-live="polite">
              {data.reports.length === MAX_SHOWN ? `Newest ${MAX_SHOWN} reports` : `${data.reports.length} report${data.reports.length === 1 ? '' : 's'}`}
            </p>
            {actionError && (
              <p role="alert" className="mb-2 text-sm text-red-600">
                {actionError}
              </p>
            )}
            <ReportList
              reports={mySiteFirst(data.reports, user.siteId)}
              siteNames={siteNames}
              highlightSiteId={user.siteId}
              emptyMessage={filtered ? 'No hazard reports match these filters.' : 'No hazard reports in the last 30 days.'}
              actions={(report) =>
                report.canEdit &&
                (editingId === report.id ? (
                  <ReportEditor
                    report={report}
                    site={siteById[report.siteId]}
                    canChangeStatus={isSupervisor}
                    onSave={(changes) => save(report, changes)}
                    onCancel={() => setEditingId(null)}
                  />
                ) : (
                  <>
                    <button className="btn-secondary px-2 py-1 text-xs" onClick={() => setEditingId(report.id)}>
                      Edit
                    </button>
                    <button className="btn-secondary px-2 py-1 text-xs text-red-600" onClick={() => remove(report)}>
                      Delete
                    </button>
                  </>
                ))
              }
            />
          </>
        )}
      </div>
    </>
  );
}
