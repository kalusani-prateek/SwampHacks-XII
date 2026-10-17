// Manage › Overview: platform-wide numbers + the 10 riskiest sites.
import StatCard from '../../../components/common/StatCard.jsx';
import SiteRiskTable from '../../../components/sites/SiteRiskTable.jsx';
import { ErrorState, LoadingState } from '../../../components/common/Status.jsx';
import { useApi } from '../../../hooks/useApi.js';
import { getStats } from '../../../api/stats.js';
import { getSites } from '../../../api/sites.js';

export default function OverviewTab() {
  // REST API PLACEHOLDERS: GET /api/stats + GET /api/sites
  const { data, loading, error, reload } = useApi(async () => {
    const [{ stats }, { sites }] = await Promise.all([getStats(), getSites()]);
    return { stats, sites };
  });

  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const { stats, sites } = data;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <StatCard label="Monitored sites" value={stats.sites} />
        <StatCard label="No-go sites" value={stats.noGoSites} tone="danger" />
        <StatCard label="Active alerts" value={stats.activeAlerts} tone="warning" />
        <StatCard label="Open reports" value={stats.openReports} tone="warning" />
        <StatCard label="Users" value={stats.users} />
      </div>
      <div className="card">
        <h2 className="mb-2 font-semibold text-navy-800">Top 10 sites by risk</h2>
        <SiteRiskTable sites={sites} limit={10} />
      </div>
    </div>
  );
}
