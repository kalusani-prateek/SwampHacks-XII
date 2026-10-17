// Crew hazard report service - "Waze for job sites": photo + map pin, shared
// with the team and saved to a long-lived location-hazard database.
import { apiRequest, mockResponse, USE_MOCKS } from './client.js';
import { ENDPOINTS } from './endpoints.js';
import { mockStore } from '../mocks/store.js';

/**
 * Hazard reports, optionally for one site.
 * REST API PLACEHOLDER: GET /api/reports?siteId=  -> { reports: Report[] }
 */
export async function getReports({ siteId } = {}) {
  if (USE_MOCKS) {
    const reports = mockStore.reports.filter((r) => !siteId || r.siteId === siteId);
    return mockResponse({ reports });
  }
  return apiRequest(ENDPOINTS.reports.list, { query: { siteId } });
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
