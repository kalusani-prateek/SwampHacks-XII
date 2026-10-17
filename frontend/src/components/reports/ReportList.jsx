// List of crew hazard reports. `actions(report)` lets a page add buttons (or an
// edit form) under a report without duplicating the list markup;
// `highlightSiteId` marks reports at your designated site.
import { Link } from 'react-router-dom';
import { urls } from '../../routes.js';
import { REPORT_TYPES } from '../../utils/hazard.js';
import { timeAgo } from '../../utils/time.js';
import MySiteBadge from '../common/MySiteBadge.jsx';
import { EmptyState } from '../common/Status.jsx';

const STATUS_STYLES = {
  open: 'bg-orange-100 text-orange-800',
  verified: 'bg-sky-100 text-sky-800',
  resolved: 'bg-emerald-100 text-emerald-800',
  dismissed: 'bg-slate-200 text-slate-600',
};

export default function ReportList({ reports, siteNames = {}, actions, highlightSiteId, emptyMessage = 'No hazard reports yet.' }) {
  if (reports.length === 0) return <EmptyState>{emptyMessage}</EmptyState>;

  return (
    <ul className="divide-y divide-slate-100">
      {reports.map((report) => {
        const extra = actions?.(report);
        const mine = Boolean(highlightSiteId) && report.siteId === highlightSiteId;
        return (
          <li key={report.id} className={`flex gap-3 py-3 ${mine ? 'my-1 rounded-lg border-l-4 border-brand bg-orange-50 px-3' : ''}`}>
            {report.photoUrl ? (
              <a href={report.photoUrl} target="_blank" rel="noreferrer" className="shrink-0" title="Open the full photo">
                <img src={report.photoUrl} alt="Hazard photo" className="h-16 w-16 rounded-lg object-cover" />
              </a>
            ) : (
              <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-2xl">
                {REPORT_TYPES[report.type]?.icon ?? '⚠️'}
              </div>
            )}
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold text-navy-800">{REPORT_TYPES[report.type]?.label ?? report.type}</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_STYLES[report.status]}`}>
                  {report.status}
                </span>
                {siteNames[report.siteId] && (
                  <Link to={urls.site(report.siteId)} className="text-xs text-slate-500 hover:text-brand hover:underline">
                    {siteNames[report.siteId]}
                  </Link>
                )}
                {mine && <MySiteBadge />}
              </div>
              <p className="mt-0.5 break-words text-sm text-slate-700">{report.description}</p>
              <p className="mt-0.5 text-xs text-slate-400">
                {report.reportedBy} · {timeAgo(report.createdAt)} · {report.lat.toFixed(4)}, {report.lng.toFixed(4)}
              </p>
              {extra && <div className="mt-2 flex flex-wrap gap-2">{extra}</div>}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
