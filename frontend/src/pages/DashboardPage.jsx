// PlanIt Dashboard (crew and supervisors): a summary of your own site, then a
// map plus a ranked list showing which sites need attention and resources
// first. Filter lives in the URL: /dashboard?decision=no-go
import { useMemo, useState } from 'react';
import { useQueryParam } from '../hooks/useQueryParam.js';
import { DASHBOARD_DECISIONS } from '../routes.js';
import PageHeader from '../components/common/PageHeader.jsx';
import StatCard from '../components/common/StatCard.jsx';
import SiteMap from '../components/map/SiteMap.jsx';
import MySiteSummary from '../components/sites/MySiteSummary.jsx';
import SiteRiskTable from '../components/sites/SiteRiskTable.jsx';
import { ErrorState, LoadingState } from '../components/common/Status.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useApi } from '../hooks/useApi.js';
import { usePolling } from '../hooks/usePolling.js';
import { getSites } from '../api/sites.js';
import { getAlerts } from '../api/alerts.js';
import { getReports } from '../api/reports.js';
import { getHazardLevel } from '../utils/hazard.js';

const REFRESH_MS = 60_000;

export default function DashboardPage() {
  const { user } = useAuth();
  // REST API PLACEHOLDER: GET /api/sites + GET /api/alerts?active=true + GET /api/reports?siteId=&days=7
  // for your own site (refreshed every minute)
  const { data, loading, error, reload } = useApi(async () => {
    const [{ sites }, { alerts }, { reports }] = await Promise.all([
      getSites(),
      getAlerts({ activeOnly: true }),
      user.siteId ? getReports({ siteId: user.siteId, days: 7 }, user) : { reports: [] },
    ]);
    return { sites, alerts, mySiteReports: reports };
  }, [user.siteId]);
  usePolling(() => reload({ silent: true }), REFRESH_MS);

  const [selected, setSelected] = useState(null);
  // URL uses lowercase values (no-go | caution | go); decisions are uppercase.
  const [filter, setFilter] = useQueryParam('decision', { defaultValue: 'all', allowed: DASHBOARD_DECISIONS });

  const sites = useMemo(() => {
    const all = data?.sites ?? [];
    if (filter === 'all') return all;
    return all.filter((s) => getHazardLevel(s.hazardIndex).decision === filter.toUpperCase());
  }, [data, filter]);

  if (loading) return <LoadingState label="Loading sites…" />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  const all = data.sites;
  const count = (decision) => all.filter((s) => getHazardLevel(s.hazardIndex).decision === decision).length;

  return (
    <>
      <PageHeader
        title="PlanIt Dashboard"
        subtitle={`${all.length} monitored sites, ranked by hazard index (0-10)`}
        actions={
          <select className="input w-auto" value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="all">All sites</option>
            <option value="no-go">No-go only</option>
            <option value="caution">Caution only</option>
            <option value="go">Go only</option>
          </select>
        }
      />

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="No-go sites" value={count('NO-GO')} tone="danger" hint="Hazard index above 7.5" />
        <StatCard label="Caution sites" value={count('CAUTION')} tone="warning" hint="Hazard index 5 to 7.5" />
        <StatCard label="Go sites" value={count('GO')} tone="good" />
        <StatCard label="Active alerts" value={data.alerts.length} tone={data.alerts.length ? 'danger' : 'default'} />
      </div>

      <MySiteSummary
        site={all.find((s) => s.id === user.siteId) ?? null}
        siteName={user.siteName}
        alerts={data.alerts.filter((a) => a.siteId === user.siteId)}
        reports={data.mySiteReports}
      />

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="card h-[520px] p-0 lg:col-span-3">
          <SiteMap sites={sites} selectedId={selected?.id} onSelect={setSelected} />
        </div>
        <div className="card max-h-[520px] overflow-y-auto lg:col-span-2">
          <h2 className="mb-2 font-semibold text-navy-800">Focus here first</h2>
          <SiteRiskTable sites={sites} selectedId={selected?.id} onSelect={setSelected} />
        </div>
      </div>
    </>
  );
}
