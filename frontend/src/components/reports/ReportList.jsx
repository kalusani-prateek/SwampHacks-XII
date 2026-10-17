// List of crew hazard reports. `actions` lets the Manage panel add moderation
// buttons without duplicating the list markup.
import { REPORT_TYPES } from '../../utils/hazard.js';
import { timeAgo } from '../../utils/time.js';
import { EmptyState } from '../common/Status.jsx';

const STATUS_STYLES = {
  open: 'bg-orange-100 text-orange-800',
  verified: 'bg-sky-100 text-sky-800',
  resolved: 'bg-emerald-100 text-emerald-800',
  dismissed: 'bg-slate-200 text-slate-600',
};

export default function ReportList({ reports, siteNames = {}, actions }) {
  if (reports.length === 0) return <EmptyState>No hazard reports yet.</EmptyState>;

  return (
    <ul className="divide-y divide-slate-100">
      {reports.map((report) => (
        <li key={report.id} className="flex gap-3 py-3">
          {report.photoUrl ? (
            <img src={report.photoUrl} alt="" className="h-16 w-16 shrink-0 rounded-lg object-cover" />
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
              {siteNames[report.siteId] && <span className="text-xs text-slate-500">{siteNames[report.siteId]}</span>}
            </div>
            <p className="mt-0.5 text-sm text-slate-700">{report.description}</p>
            <p className="mt-0.5 text-xs text-slate-400">
              {report.reportedBy} · {timeAgo(report.createdAt)} · {report.lat.toFixed(4)}, {report.lng.toFixed(4)}
            </p>
            {actions && <div className="mt-2 flex flex-wrap gap-2">{actions(report)}</div>}
          </div>
        </li>
      ))}
    </ul>
  );
}
