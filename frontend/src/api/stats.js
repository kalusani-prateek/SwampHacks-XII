// Stats service - headline numbers for the Manage › Overview tab.
import { apiRequest, mockResponse, USE_MOCKS } from './client.js';
import { ENDPOINTS } from './endpoints.js';
import { mockStore } from '../mocks/store.js';

/**
 * Platform-wide counts (supervisor only).
 * REST API PLACEHOLDER: GET /api/stats  -> { stats: { sites, noGoSites, activeAlerts, openReports, users } }   [PLANNED]
 */
export async function getStats() {
  if (USE_MOCKS) {
    const active = mockStore.sites.filter((s) => s.active);
    return mockResponse({
      stats: {
        sites: active.length,
        noGoSites: active.filter((s) => s.hazardIndex > 7.5).length,
        activeAlerts: mockStore.alerts.filter((a) => a.active).length,
        openReports: mockStore.reports.filter((r) => r.status === 'open').length,
        users: mockStore.users.length,
      },
    });
  }
  return apiRequest(ENDPOINTS.stats);
}
