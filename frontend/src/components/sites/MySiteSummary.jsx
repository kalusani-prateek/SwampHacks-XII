// Dashboard card for the signed-in person's designated site: its hazard index and
// reasons, top hazards, active alerts and hazard reports from the last 7 days.
import { Link } from 'react-router-dom';
import { urls } from '../../routes.js';
import { REPORT_TYPES } from '../../utils/hazard.js';
import { MY_SITE_HIGHLIGHT } from '../../utils/mySite.js';
import { timeAgo } from '../../utils/time.js';
import HazardBadge from '../common/HazardBadge.jsx';
import HazardBreakdown from './HazardBreakdown.jsx';

const SEVERITY_DOT = { 'stop-work': 'bg-red-600', warning: 'bg-orange-500', info: 'bg-sky-500' };
const SHOWN = 3; // hazards, alerts and reports listed in each column

const Column = ({ title, children }) => (
  <section className="min-w-0">
    <h3 className="mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">{title}</h3>
    {children}
  </section>
);

/**
 * @param {object|null} site   the designated site (null if none chosen or not monitored)
 * @param {string|null} siteName   its name from the user's account, for the "not monitored" message
 * @param {object[]} alerts    active alerts at the site
 * @param {object[]} reports   hazard reports at the site, newest first
 */
export default function MySiteSummary({ site, siteName, alerts, reports }) {
  if (!site) {
    return (
      <div className="card mb-6 flex flex-wrap items-center justify-between gap-3 border-dashed">
        <p className="text-sm text-slate-600">
          {siteName
            ? `Your site (${siteName}) isn't being monitored right now.`
            : 'Choose the site you work at to see its hazards and reports here.'}
        </p>
        <Link to={urls.account()} className="btn-secondary px-3 py-1.5 text-sm">
          {siteName ? 'Change your site' : 'Choose your site'}
        </Link>
      </div>
    );
  }

  const topHazards = Object.fromEntries(Object.entries(site.hazards ?? {}).sort((a, b) => b[1] - a[1]).slice(0, SHOWN));
  const stopWork = alerts.some((a) => a.severity === 'stop-work');

  return (
    <section aria-label="Your site" className={`card mb-6 ${MY_SITE_HIGHLIGHT}`}>
      {/* Site, index and reasons */}
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold tracking-wide text-orange-700 uppercase">📍 Your site</p>
          <h2 className="text-lg font-bold text-navy-800">
            {site.name} <span className="text-sm font-normal text-slate-500">· {site.state}</span>
          </h2>
          {stopWork && <p className="mt-1 text-sm font-bold text-red-700">⚡ Stop work in effect</p>}
          {site.drivers?.length > 0 && (
            <ul className="mt-1 space-y-0.5 text-sm text-slate-600">
              {site.drivers.slice(0, SHOWN).map((d) => (
                <li key={d}>• {d}</li>
              ))}
            </ul>
          )}
        </div>
        <div className="flex flex-col items-end gap-2">
          <HazardBadge score={site.hazardIndex} showDecision size="lg" />
          <Link to={urls.site(site.id)} className="text-sm font-medium text-brand hover:underline">
            Open site page →
          </Link>
        </div>
      </div>

      <div className="mt-3 grid gap-5 md:grid-cols-3">
        <Column title="Top hazards">
          <HazardBreakdown hazards={topHazards} />
        </Column>

        <Column title={`Active alerts (${alerts.length})`}>
          {alerts.length === 0 ? (
            <p className="text-sm text-slate-500">No active alerts.</p>
          ) : (
            <ul className="space-y-2">
              {alerts.slice(0, SHOWN).map((a) => (
                <li key={a.id} className="flex gap-2 text-sm">
                  <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${SEVERITY_DOT[a.severity] ?? SEVERITY_DOT.info}`} />
                  <span className="min-w-0">
                    <span className="font-medium text-slate-800">{a.title}</span>
                    <span className="block text-xs text-slate-500">{timeAgo(a.createdAt)}</span>
                  </span>
                </li>
              ))}
              {alerts.length > SHOWN && (
                <li>
                  <Link to={urls.alerts()} className="text-sm font-medium text-brand hover:underline">
                    All alerts →
                  </Link>
                </li>
              )}
            </ul>
          )}
        </Column>

        <Column title={`Reports, last 7 days (${reports.length})`}>
          {reports.length === 0 ? (
            <p className="text-sm text-slate-500">No hazards reported this week.</p>
          ) : (
            <ul className="space-y-2">
              {reports.slice(0, SHOWN).map((r) => (
                <li key={r.id} className="text-sm">
                  <span className="font-medium text-slate-800">
                    {REPORT_TYPES[r.type]?.icon ?? '⚠️'} {REPORT_TYPES[r.type]?.label ?? r.type}
                  </span>
                  <span className="block truncate text-slate-600">{r.description}</span>
                  <span className="block text-xs text-slate-500">
                    {r.reportedBy} · {timeAgo(r.createdAt)} · {r.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm font-medium">
            {reports.length > 0 && (
              <Link to={urls.reports({ site: site.id, days: '7' })} className="text-brand hover:underline">
                All reports →
              </Link>
            )}
            <Link to={urls.newReport({ site: site.id })} className="text-brand hover:underline">
              + Report a hazard here
            </Link>
          </div>
        </Column>
      </div>
    </section>
  );
}
