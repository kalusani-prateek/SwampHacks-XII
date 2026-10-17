// Moderation queue for crew hazard reports. Verified reports become part of
// the long-term location-hazard database for future project owners.
// Status filter lives in the URL: /manage/reports?status=verified
import ReportList from '../../../components/reports/ReportList.jsx';
import { ErrorState, LoadingState } from '../../../components/common/Status.jsx';
import { useApi } from '../../../hooks/useApi.js';
import { useQueryParam } from '../../../hooks/useQueryParam.js';
import { getReports, updateReportStatus } from '../../../api/reports.js';
import { getAllSites } from '../../../api/sites.js';
import { REPORT_STATUSES } from '../../../routes.js';

export default function ReportsTab() {
  // REST API PLACEHOLDERS: GET /api/reports + GET /api/sites (for site names)
  const { data, loading, error, reload } = useApi(async () => {
    const [{ reports }, { sites }] = await Promise.all([getReports(), getAllSites()]);
    return { reports, siteNames: Object.fromEntries(sites.map((s) => [s.id, s.name])) };
  });
  const [status, setStatus] = useQueryParam('status', { defaultValue: 'open', allowed: REPORT_STATUSES });

  async function setReportStatus(id, next) {
    await updateReportStatus(id, next); // REST API PLACEHOLDER: PATCH /api/reports/:id
    reload({ silent: true });
  }

  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  const reports = data.reports.filter((r) => status === 'all' || r.status === status);

  return (
    <div className="card">
      <div className="mb-2 flex flex-wrap gap-2">
        {REPORT_STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setStatus(s)}
            className={`rounded-full px-3 py-1 text-xs font-semibold capitalize ${
              status === s ? 'bg-navy-800 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {s}
          </button>
        ))}
      </div>
      <ReportList
        reports={reports}
        siteNames={data.siteNames}
        actions={(report) => (
          <>
            {report.status !== 'verified' && (
              <button className="btn-secondary px-2 py-1 text-xs" onClick={() => setReportStatus(report.id, 'verified')}>
                Verify
              </button>
            )}
            {report.status !== 'resolved' && (
              <button className="btn-secondary px-2 py-1 text-xs" onClick={() => setReportStatus(report.id, 'resolved')}>
                Mark resolved
              </button>
            )}
            {report.status !== 'dismissed' && (
              <button className="btn-secondary px-2 py-1 text-xs text-red-600" onClick={() => setReportStatus(report.id, 'dismissed')}>
                Dismiss
              </button>
            )}
          </>
        )}
      />
    </div>
  );
}
