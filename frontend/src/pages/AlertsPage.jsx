// Live alert feed across every site. Alerts at your designated site come first
// (highlighted), then the rest; stop-work alerts lead within each group.
// Filter lives in the URL: /alerts?type=lightning
import { useMemo } from 'react';
import { useQueryParam } from '../hooks/useQueryParam.js';
import PageHeader from '../components/common/PageHeader.jsx';
import AlertCard from '../components/alerts/AlertCard.jsx';
import { EmptyState, ErrorState, LoadingState } from '../components/common/Status.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useApi } from '../hooks/useApi.js';
import { usePolling } from '../hooks/usePolling.js';
import { acknowledgeAlert, getAlerts } from '../api/alerts.js';
import { HAZARD_TYPES } from '../utils/hazard.js';
import { mySiteFirst } from '../utils/mySite.js';

const POLL_MS = 15_000;
const SEVERITY_ORDER = { 'stop-work': 0, warning: 1, info: 2 };
const ALERT_TYPES = ['all', ...Object.keys(HAZARD_TYPES)];

export default function AlertsPage() {
  const { user } = useAuth();
  // REST API PLACEHOLDER: GET /api/alerts?active=true (polled; SSE stream planned)
  const { data, loading, error, reload } = useApi(() => getAlerts({ activeOnly: true }));
  usePolling(() => reload({ silent: true }), POLL_MS);
  const [type, setType] = useQueryParam('type', { defaultValue: 'all', allowed: ALERT_TYPES });

  const alerts = useMemo(
    () =>
      mySiteFirst(
        (data?.alerts ?? [])
          .filter((a) => type === 'all' || a.type === type)
          .sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]),
        user.siteId,
      ),
    [data, type, user.siteId],
  );

  async function handleAcknowledge(alertId) {
    await acknowledgeAlert(alertId); // REST API PLACEHOLDER: POST /api/alerts/:id/ack
    reload({ silent: true });
  }

  return (
    <>
      <PageHeader
        title="Alerts"
        subtitle="Raised automatically when conditions turn dangerous. Refreshes every 15 s."
        actions={
          <select className="input w-auto" value={type} onChange={(e) => setType(e.target.value)}>
            <option value="all">All hazard types</option>
            {Object.entries(HAZARD_TYPES).map(([key, t]) => (
              <option key={key} value={key}>
                {t.label}
              </option>
            ))}
          </select>
        }
      />
      {loading && <LoadingState />}
      {error && <ErrorState error={error} onRetry={reload} />}
      {data && alerts.length === 0 && <EmptyState>No active alerts. All sites are clear.</EmptyState>}
      <div className="grid gap-4 md:grid-cols-2">
        {alerts.map((alert) => (
          <AlertCard key={alert.id} alert={alert} mine={alert.siteId === user.siteId} onAcknowledge={handleAcknowledge} />
        ))}
      </div>
    </>
  );
}
