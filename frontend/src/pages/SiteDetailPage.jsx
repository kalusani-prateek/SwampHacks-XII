// One site's full risk picture: hazard index, per-hazard breakdown, live
// conditions, lightning countdown, 7-day forecast, alerts and crew reports.
import { Link, useParams } from 'react-router-dom';
import PageHeader from '../components/common/PageHeader.jsx';
import HazardBadge from '../components/common/HazardBadge.jsx';
import { ErrorState, LoadingState } from '../components/common/Status.jsx';
import HazardBreakdown from '../components/sites/HazardBreakdown.jsx';
import ConditionsGrid from '../components/sites/ConditionsGrid.jsx';
import ForecastChart from '../components/sites/ForecastChart.jsx';
import LightningCountdown from '../components/alerts/LightningCountdown.jsx';
import AlertCard from '../components/alerts/AlertCard.jsx';
import ReportList from '../components/reports/ReportList.jsx';
import SiteMap from '../components/map/SiteMap.jsx';
import { useApi } from '../hooks/useApi.js';
import { getSite, getSiteForecast } from '../api/sites.js';
import { acknowledgeAlert, getAlerts } from '../api/alerts.js';
import { getReports } from '../api/reports.js';
import { formatLocalTime, timeAgo } from '../utils/time.js';
import { isValidSlug } from '../utils/url.js';
import { ApiError } from '../api/client.js';
import { urls } from '../routes.js';
import NotFoundPage from './NotFoundPage.jsx';

export default function SiteDetailPage() {
  // URL: /sites/:siteId  (e.g. /sites/turkey-point)
  const { siteId } = useParams();

  // REST API PLACEHOLDERS (fetched in parallel):
  //   GET /api/sites/:siteId
  //   GET /api/sites/:siteId/forecast
  //   GET /api/alerts?active=true&siteId=:siteId
  //   GET /api/reports?siteId=:siteId
  const { data, loading, error, reload } = useApi(async () => {
    // Malformed ids (e.g. /sites/Turkey%20Point) never reach the API.
    if (!isValidSlug(siteId)) throw new ApiError('Site not found', 404);
    const [{ site }, { forecast }, { alerts }, { reports }] = await Promise.all([
      getSite(siteId),
      getSiteForecast(siteId),
      getAlerts({ activeOnly: true, siteId }),
      getReports({ siteId }),
    ]);
    return { site, forecast, alerts, reports };
  }, [siteId]);

  if (loading) return <LoadingState label="Loading site…" />;
  // REST convention: unknown resource -> HTTP 404 -> not-found page.
  if (error?.status === 404) {
    return <NotFoundPage title="Site not found" message={`There is no monitored site at /sites/${siteId}.`} />;
  }
  if (error) return <ErrorState error={error} onRetry={reload} />;

  const { site, forecast, alerts, reports } = data;

  async function handleAcknowledge(alertId) {
    await acknowledgeAlert(alertId); // REST API PLACEHOLDER: POST /api/alerts/:id/ack
    reload({ silent: true });
  }

  return (
    <>
      <PageHeader
        title={site.name}
        subtitle={`${site.state} · ${site.plantType} · ${site.utility}${site.waterway ? ` · ${site.waterway}` : ''} · Local time ${formatLocalTime(new Date(), site.timezone)}`}
        actions={
          <Link to={urls.newReport({ site: site.id })} className="btn-primary">
            + Report hazard
          </Link>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left column: score + lightning + breakdown */}
        <div className="space-y-6">
          <div className="card">
            <p className="label">ML hazard index</p>
            <HazardBadge score={site.hazardIndex} showDecision size="lg" />
            <ul className="mt-3 space-y-1 text-sm text-slate-700">
              {site.drivers.map((d) => (
                <li key={d}>• {d}</li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-slate-400">Updated {timeAgo(site.updatedAt)}</p>
          </div>

          <LightningCountdown siteId={site.id} />

          <div className="card">
            <h2 className="mb-3 font-semibold text-navy-800">Combined risk picture</h2>
            <HazardBreakdown hazards={site.hazards} />
          </div>
        </div>

        {/* Right two columns: conditions, forecast, map, alerts, reports */}
        <div className="space-y-6 lg:col-span-2">
          <div className="card">
            <h2 className="mb-3 font-semibold text-navy-800">Current conditions</h2>
            <ConditionsGrid conditions={site.conditions} />
          </div>

          <div className="card">
            <h2 className="mb-3 font-semibold text-navy-800">7-day hazard forecast</h2>
            <ForecastChart forecast={forecast} />
          </div>

          {alerts.length > 0 && (
            <div className="space-y-3">
              <h2 className="font-semibold text-navy-800">Active alerts</h2>
              {alerts.map((a) => (
                <AlertCard key={a.id} alert={a} onAcknowledge={handleAcknowledge} />
              ))}
            </div>
          )}

          <div className="card h-72 p-0">
            <SiteMap sites={[site]} reports={reports} center={[site.lat, site.lng]} zoom={14} />
          </div>

          <div className="card">
            <h2 className="mb-1 font-semibold text-navy-800">Crew hazard reports</h2>
            <ReportList reports={reports} />
          </div>
        </div>
      </div>
    </>
  );
}
