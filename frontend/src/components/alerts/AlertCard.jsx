// One alert (stop-work / warning) with an acknowledge button. `mine` highlights
// alerts at your designated site.
import { Link } from 'react-router-dom';
import { urls } from '../../routes.js';
import { HAZARD_TYPES } from '../../utils/hazard.js';
import { MY_SITE_HIGHLIGHT } from '../../utils/mySite.js';
import { timeAgo } from '../../utils/time.js';
import MySiteBadge from '../common/MySiteBadge.jsx';

const SEVERITY_STYLES = {
  'stop-work': 'border-l-red-600 bg-red-50',
  warning: 'border-l-orange-500 bg-orange-50',
  info: 'border-l-sky-500 bg-sky-50',
};

export default function AlertCard({ alert, onAcknowledge, mine = false }) {
  return (
    <article className={`card border-l-4 ${SEVERITY_STYLES[alert.severity] ?? SEVERITY_STYLES.info} ${mine ? MY_SITE_HIGHLIGHT : ''}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-bold text-navy-800">
            {HAZARD_TYPES[alert.type]?.icon} {alert.title}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <Link to={urls.site(alert.siteId)} className="text-sm font-medium text-brand hover:underline">
              {alert.siteName}
            </Link>
            {mine && <MySiteBadge />}
          </div>
        </div>
        <span className="text-xs text-slate-500">{timeAgo(alert.createdAt)}</span>
      </div>
      <p className="mt-2 text-sm text-slate-700">{alert.message}</p>
      <div className="mt-3">
        {alert.acknowledged ? (
          <span className="text-xs font-semibold text-emerald-700">✓ Acknowledged</span>
        ) : (
          <button className="btn-secondary text-xs" onClick={() => onAcknowledge(alert.id)}>
            Acknowledge
          </button>
        )}
      </div>
    </article>
  );
}
