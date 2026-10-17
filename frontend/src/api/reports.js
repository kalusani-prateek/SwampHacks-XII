// Crew hazard report service - "Waze for job sites": photo + map pin, shared
// with the team and saved to a long-lived location-hazard database.
import { apiRequest, mockNotFound, mockResponse, USE_MOCKS } from './client.js';
import { ENDPOINTS } from './endpoints.js';
import { mockStore } from '../mocks/store.js';

/**
 * Hazard reports, newest first. Every filter is optional: siteId, type, status,
 * days (reported in the last N days), q (words in the description, reporter or
 * site name) and mine (only your own). Each report says whether you may edit it (canEdit).
 * `viewer` ({ username, role }) is only needed in mock mode, for `mine` and `canEdit`.
 * REST API PLACEHOLDER: GET /api/reports?siteId=&type=&status=&days=&q=&mine=true  -> { reports: Report[] }
 */
export async function getReports({ siteId, type, status, days, q, mine } = {}, viewer) {
  if (USE_MOCKS) {
    const since = days ? Date.now() - Number(days) * 86_400_000 : 0;
    const text = q?.trim().toLowerCase();
    const siteName = (id) => mockStore.sites.find((s) => s.id === id)?.name ?? '';
    const reports = mockStore.reports
      .filter((r) => (!siteId || r.siteId === siteId) && (!type || r.type === type) && (!status || r.status === status))
      .filter((r) => (!mine || r.reportedBy === viewer?.username) && new Date(r.createdAt).getTime() >= since)
      .filter((r) => !text || [r.description, r.reportedBy, siteName(r.siteId)].some((v) => v.toLowerCase().includes(text)))
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
      .map((r) => ({ ...r, canEdit: viewer?.role === 'supervisor' || r.reportedBy === viewer?.username }));
    return mockResponse({ reports });
  }
  return apiRequest(ENDPOINTS.reports.list, { query: { siteId, type, status, days, q, mine } });
}

/**
 * Submit a new hazard report with an optional photo.
 * REST API PLACEHOLDER: POST /api/reports  (multipart/form-data)
 *   fields: siteId, type, description, lat, lng, photo (file)
 *   -> { report }
 * The backend should broadcast the new report to the site's crew (alerts stream).
 */
export async function createReport({ siteId, type, description, lat, lng, photo, reporter }) {
  if (USE_MOCKS) {
    const report = {
      id: `r-${Date.now()}`,
      siteId,
      type,
      description,
      lat,
      lng,
      // In mock mode the photo is shown from an in-memory object URL.
      photoUrl: photo ? URL.createObjectURL(photo) : null,
      reportedBy: reporter,
      createdAt: new Date().toISOString(),
      status: 'open',
    };
    mockStore.reports.unshift(report);
    return mockResponse({ report });
  }

  const form = new FormData();
  form.append('siteId', siteId);
  form.append('type', type);
  form.append('description', description);
  form.append('lat', lat);
  form.append('lng', lng);
  if (photo) form.append('photo', photo);
  return apiRequest(ENDPOINTS.reports.create, { method: 'POST', body: form });
}

/**
 * Edit a report: any of { type, description, lat, lng, removePhoto }. Allowed for
 * the person who reported it and for supervisors (the server checks).
 * REST API PLACEHOLDER: PATCH /api/reports/:id  -> { report }
 */
export async function updateReport(reportId, changes) {
  if (USE_MOCKS) {
    const report = mockStore.reports.find((r) => r.id === reportId);
    if (!report) return mockNotFound('Report not found');
    const { removePhoto, ...fields } = changes;
    Object.assign(report, fields, removePhoto ? { photoUrl: null } : {});
    return mockResponse({ report });
  }
  return apiRequest(ENDPOINTS.reports.detail(reportId), { method: 'PATCH', body: changes });
}

/**
 * Delete a report (the person who reported it, or a supervisor).
 * REST API PLACEHOLDER: DELETE /api/reports/:id  -> { message }
 */
export async function deleteReport(reportId) {
  if (USE_MOCKS) {
    const index = mockStore.reports.findIndex((r) => r.id === reportId);
    if (index === -1) return mockNotFound('Report not found');
    mockStore.reports.splice(index, 1);
    return mockResponse({ message: 'Report deleted' });
  }
  return apiRequest(ENDPOINTS.reports.detail(reportId), { method: 'DELETE' });
}

/**
 * Supervisor moderation: verify, resolve or dismiss a report.
 * REST API PLACEHOLDER: PATCH /api/reports/:id  { status }  -> { report }
 */
export async function updateReportStatus(reportId, status) {
  if (USE_MOCKS) {
    const report = mockStore.reports.find((r) => r.id === reportId);
    if (report) report.status = status;
    return mockResponse({ report });
  }
  return apiRequest(ENDPOINTS.reports.detail(reportId), { method: 'PATCH', body: { status } });
}
