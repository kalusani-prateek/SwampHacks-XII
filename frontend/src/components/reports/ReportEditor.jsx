// Edit form for a hazard report: type, description, map pin and photo removal,
// plus the status (open / verified / resolved / dismissed) for supervisors.
// Shown to the person who reported it and to supervisors (report.canEdit).
import { useState } from 'react';
import LocationPicker from '../map/LocationPicker.jsx';
import { REPORT_TYPES } from '../../utils/hazard.js';

const MAX_DESCRIPTION = 1000; // same limit as the backend
const STATUSES = ['open', 'verified', 'resolved', 'dismissed'];

/**
 * @param {object} props.report    the report being edited
 * @param {object} [props.site]    its site ({ id, name, lat, lng }), for moving the map pin
 * @param {boolean} [props.canChangeStatus]  supervisors only (the server checks too)
 * @param {(changes) => Promise} props.onSave  receives only the changed fields; throws on failure
 * @param {() => void} props.onCancel
 */
export default function ReportEditor({ report, site, canChangeStatus = false, onSave, onCancel }) {
  const [status, setStatus] = useState(report.status);
  const [type, setType] = useState(report.type);
  const [description, setDescription] = useState(report.description);
  const [pin, setPin] = useState({ lat: report.lat, lng: report.lng });
  const [showMap, setShowMap] = useState(false);
  const [removePhoto, setRemovePhoto] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    const text = description.trim();
    if (!text) return setError('Describe the hazard.');
    const changes = {};
    if (canChangeStatus && status !== report.status) changes.status = status;
    if (type !== report.type) changes.type = type;
    if (text !== report.description) changes.description = text;
    if (pin.lat !== report.lat || pin.lng !== report.lng) Object.assign(changes, pin);
    if (removePhoto) changes.removePhoto = true;
    if (Object.keys(changes).length === 0) return onCancel(); // nothing changed
    setSaving(true);
    setError('');
    try {
      await onSave(changes);
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
      {canChangeStatus && (
        <div className="sm:w-1/2 sm:pr-1.5">
          <label className="label" htmlFor={`status-${report.id}`}>
            Status
          </label>
          <select id={`status-${report.id}`} className="input capitalize" value={status} onChange={(e) => setStatus(e.target.value)}>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <label className="label" htmlFor={`type-${report.id}`}>
            Hazard type
          </label>
          <select id={`type-${report.id}`} className="input" value={type} onChange={(e) => setType(e.target.value)}>
            {Object.entries(REPORT_TYPES).map(([key, t]) => (
              <option key={key} value={key}>
                {t.icon} {t.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <span className="label">Location</span>
          <p className="py-2 text-sm text-slate-600">
            📍 {pin.lat.toFixed(5)}, {pin.lng.toFixed(5)}{' '}
            {site && (
              <button type="button" className="font-medium text-brand hover:underline" onClick={() => setShowMap(!showMap)}>
                {showMap ? 'Done' : 'Move pin'}
              </button>
            )}
          </p>
        </div>
      </div>

      {showMap && site && (
        <div>
          <p className="mb-1 text-xs text-slate-500">Tap the map where the hazard is.</p>
          <div className="h-64">
            <LocationPicker site={site} value={pin} onChange={setPin} />
          </div>
        </div>
      )}

      <div>
        <label className="label" htmlFor={`desc-${report.id}`}>
          Description
        </label>
        <textarea
          id={`desc-${report.id}`}
          className="input min-h-20"
          value={description}
          maxLength={MAX_DESCRIPTION}
          onChange={(e) => setDescription(e.target.value)}
          required
        />
      </div>

      {report.photoUrl && (
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input type="checkbox" checked={removePhoto} onChange={(e) => setRemovePhoto(e.target.checked)} />
          Remove the photo
        </label>
      )}

      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <button type="submit" className="btn-primary px-3 py-1.5 text-sm" disabled={saving}>
          {saving ? 'Saving…' : 'Save changes'}
        </button>
        <button type="button" className="btn-secondary px-3 py-1.5 text-sm" onClick={onCancel} disabled={saving}>
          Cancel
        </button>
      </div>
    </form>
  );
}
