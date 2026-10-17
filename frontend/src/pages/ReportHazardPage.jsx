// Crew hazard reporting: choose a site, tap the map to pin the hazard, add a
// photo + description and submit. The report goes to the team and into the
// long-term location-hazard database.
// URL: /reports/new?site=turkey-point  (the selected site stays in the URL)
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryParam } from '../hooks/useQueryParam.js';
import { urls } from '../routes.js';
import PageHeader from '../components/common/PageHeader.jsx';
import LocationPicker from '../components/map/LocationPicker.jsx';
import { ErrorState, LoadingState } from '../components/common/Status.jsx';
import { useApi } from '../hooks/useApi.js';
import { useAuth } from '../context/AuthContext.jsx';
import { getSites } from '../api/sites.js';
import { createReport } from '../api/reports.js';
import { REPORT_TYPES } from '../utils/hazard.js';

export default function ReportHazardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  // REST API PLACEHOLDER: GET /api/sites (to choose the site)
  const { data, loading, error, reload } = useApi(() => getSites());

  const [siteId, setSiteId] = useQueryParam('site');
  const [type, setType] = useState('wildlife');
  const [description, setDescription] = useState('');
  const [pin, setPin] = useState(null); // { lat, lng }
  const [photo, setPhoto] = useState(null);
  const [preview, setPreview] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  const site = data?.sites.find((s) => s.id === siteId);

  // Validate ?site= against real sites; missing or unknown -> your designated site (or the first site).
  useEffect(() => {
    if (!data?.sites.length || data.sites.some((s) => s.id === siteId)) return;
    setSiteId(data.sites.some((s) => s.id === user.siteId) ? user.siteId : data.sites[0].id);
  }, [data, siteId, setSiteId, user.siteId]);
  // Clear the pin when the site changes.
  useEffect(() => setPin(null), [siteId]);

  // Photo preview (object URL is freed when replaced or on unmount).
  useEffect(() => {
    if (!photo) return setPreview(null);
    const url = URL.createObjectURL(photo);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!pin) return setSubmitError('Tap the map to pin where the hazard is.');
    setSubmitting(true);
    setSubmitError('');
    try {
      // REST API PLACEHOLDER: POST /api/reports (multipart/form-data with photo)
      await createReport({ siteId, type, description, lat: pin.lat, lng: pin.lng, photo, reporter: user.username });
      navigate(urls.site(siteId));
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  return (
    <>
      <PageHeader title="Report a hazard" subtitle="Shared instantly with your crew and saved for future project owners." />

      <form onSubmit={handleSubmit} className="grid gap-6 lg:grid-cols-2">
        {/* Map: tap to pin */}
        <div className="card flex flex-col p-0">
          <p className="px-4 pt-3 text-sm text-slate-600">
            {pin ? `📍 Pinned at ${pin.lat.toFixed(5)}, ${pin.lng.toFixed(5)}` : 'Tap the map where the hazard is.'}
          </p>
          <div className="h-[420px] p-3">{site && <LocationPicker site={site} value={pin} onChange={setPin} />}</div>
        </div>

        {/* Details */}
        <div className="card space-y-4">
          <div>
            <label className="label" htmlFor="site">
              Site
            </label>
            <select id="site" className="input" value={siteId} onChange={(e) => setSiteId(e.target.value)}>
              {data.sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.state})
                </option>
              ))}
            </select>
          </div>

          <div>
            <span className="label">Hazard type</span>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {Object.entries(REPORT_TYPES).map(([key, t]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setType(key)}
                  className={`rounded-lg border px-2 py-2 text-left text-sm ${
                    type === key ? 'border-brand bg-orange-50 font-semibold' : 'border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  {t.icon} {t.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="label" htmlFor="desc">
              What did you see?
            </label>
            <textarea
              id="desc"
              className="input min-h-24"
              placeholder="e.g. 8 ft gator in the canal by the east gate"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="label" htmlFor="photo">
              Photo
            </label>
            {/* `capture` opens the rear camera directly on phones */}
            <input
              id="photo"
              type="file"
              accept="image/*"
              capture="environment"
              className="block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-navy-800 file:px-3 file:py-2 file:text-white"
              onChange={(e) => setPhoto(e.target.files?.[0] ?? null)}
            />
            {preview && <img src={preview} alt="Hazard preview" className="mt-3 max-h-48 rounded-lg object-cover" />}
          </div>

          {submitError && <p className="text-sm text-red-600">{submitError}</p>}
          <button type="submit" className="btn-primary w-full" disabled={submitting}>
            {submitting ? 'Sending…' : 'Send report'}
          </button>
        </div>
      </form>
    </>
  );
}
