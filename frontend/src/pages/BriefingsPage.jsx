// Next-day safety briefings. The backend generates and sends these every
// evening at 6 PM site-local time; this page shows the latest one per site.
// Your designated site's briefing comes first (highlighted), then by risk.
// Search lives in the URL: /briefings?q=texas
import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQueryParam } from '../hooks/useQueryParam.js';
import { urls } from '../routes.js';
import PageHeader from '../components/common/PageHeader.jsx';
import HazardBadge from '../components/common/HazardBadge.jsx';
import MySiteBadge from '../components/common/MySiteBadge.jsx';
import { ErrorState, LoadingState } from '../components/common/Status.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useApi } from '../hooks/useApi.js';
import { getBriefings } from '../api/briefings.js';
import { HAZARD_TYPES } from '../utils/hazard.js';
import { MY_SITE_HIGHLIGHT, mySiteFirst } from '../utils/mySite.js';
import { formatLocalTime } from '../utils/time.js';

export default function BriefingsPage() {
  const { user } = useAuth();
  // REST API PLACEHOLDER: GET /api/briefings
  const { data, loading, error, reload } = useApi(() => getBriefings());
  const [query, setQuery] = useQueryParam('q');

  const briefings = useMemo(() => {
    const q = query.trim().toLowerCase();
    const ranked = (data?.briefings ?? [])
      .filter((b) => !q || `${b.siteName} ${b.state}`.toLowerCase().includes(q))
      .sort((a, b) => b.hazardIndex - a.hazardIndex);
    return mySiteFirst(ranked, user.siteId);
  }, [data, query, user.siteId]);

  if (loading) return <LoadingState label="Loading briefings…" />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  return (
    <>
      <PageHeader
        title="Next-day safety briefings"
        subtitle="Sent automatically every evening at 6:00 PM local site time."
        actions={
          <input className="input w-56" placeholder="Filter sites…" value={query} onChange={(e) => setQuery(e.target.value)} />
        }
      />

      <div className="grid gap-4 md:grid-cols-2">
        {briefings.map((b) => (
          <article key={b.siteId} className={`card ${b.siteId === user.siteId ? MY_SITE_HIGHLIGHT : ''}`}>
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <Link to={urls.site(b.siteId)} className="font-semibold text-navy-800 hover:text-brand">
                    {b.siteName}
                  </Link>
                  {b.siteId === user.siteId && <MySiteBadge />}
                </div>
                <p className="text-xs text-slate-500">
                  For {b.forDate} · local time now {formatLocalTime(new Date(), b.timezone)}
                </p>
              </div>
              <HazardBadge score={b.hazardIndex} showDecision />
            </div>
            <p className="mt-2 text-sm text-slate-700">{b.summary}</p>
            <ul className="mt-3 space-y-2">
              {b.topHazards.map((h) => (
                <li key={h.key} className="rounded-lg bg-slate-50 p-2 text-sm">
                  <span className="font-semibold">
                    {HAZARD_TYPES[h.key].icon} {HAZARD_TYPES[h.key].label} ({h.score.toFixed(1)})
                  </span>
                  <p className="text-slate-600">{h.control}</p>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </>
  );
}
