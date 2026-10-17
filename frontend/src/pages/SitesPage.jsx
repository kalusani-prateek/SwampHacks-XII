// Searchable list of all job sites with their current hazard index. Your
// designated site comes first and is highlighted; the rest are ranked by risk.
// Search lives in the URL: /sites?q=florida
import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQueryParam } from '../hooks/useQueryParam.js';
import { urls } from '../routes.js';
import PageHeader from '../components/common/PageHeader.jsx';
import HazardBadge from '../components/common/HazardBadge.jsx';
import MySiteBadge from '../components/common/MySiteBadge.jsx';
import { EmptyState, ErrorState, LoadingState } from '../components/common/Status.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useApi } from '../hooks/useApi.js';
import { getSites } from '../api/sites.js';
import { rankByRisk } from '../utils/hazard.js';
import { MY_SITE_HIGHLIGHT, mySiteFirst } from '../utils/mySite.js';

export default function SitesPage() {
  const { user } = useAuth();
  // REST API PLACEHOLDER: GET /api/sites
  const { data, loading, error, reload } = useApi(() => getSites());
  const [query, setQuery] = useQueryParam('q');

  const sites = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = data?.sites ?? [];
    const matches = q
      ? list.filter((s) => `${s.name} ${s.state} ${s.utility} ${s.plantType}`.toLowerCase().includes(q))
      : list;
    return mySiteFirst(rankByRisk(matches), user.siteId, (s) => s.id);
  }, [data, query, user.siteId]);

  return (
    <>
      <PageHeader
        title="Job sites"
        subtitle="Combined risk picture for every monitored site"
        actions={
          <input
            className="input w-64"
            placeholder="Search name, state, utility…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        }
      />

      {loading && <LoadingState />}
      {error && <ErrorState error={error} onRetry={reload} />}
      {data && sites.length === 0 && <EmptyState>No sites match "{query}".</EmptyState>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sites.map((site) => (
          <Link
            key={site.id}
            to={urls.site(site.id)}
            className={`card transition hover:border-brand hover:shadow-md ${site.id === user.siteId ? MY_SITE_HIGHLIGHT : ''}`}
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="font-semibold text-navy-800">{site.name}</p>
                <p className="text-xs text-slate-500">
                  {site.state} · {site.plantType}
                </p>
                {site.id === user.siteId && (
                  <div className="mt-1">
                    <MySiteBadge />
                  </div>
                )}
              </div>
              <HazardBadge score={site.hazardIndex} showDecision />
            </div>
            <ul className="mt-3 space-y-0.5 text-xs text-slate-600">
              {site.drivers.map((d) => (
                <li key={d}>• {d}</li>
              ))}
            </ul>
          </Link>
        ))}
      </div>
    </>
  );
}
