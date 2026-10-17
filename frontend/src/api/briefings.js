// Briefing service - next-day safety briefings generated every evening at
// 6 PM *site-local* time by a backend scheduler.
import { apiRequest, mockNotFound, mockResponse, USE_MOCKS } from './client.js';
import { ENDPOINTS } from './endpoints.js';
import { mockStore } from '../mocks/store.js';
import { buildBriefing } from '../mocks/generators.js';

/**
 * Latest next-day briefing for every site.
 * REST API PLACEHOLDER: GET /api/briefings?date=YYYY-MM-DD  -> { briefings: Briefing[] }
 */
export async function getBriefings() {
  if (USE_MOCKS) {
    return mockResponse({ briefings: mockStore.sites.filter((s) => s.active).map(buildBriefing) });
  }
  return apiRequest(ENDPOINTS.briefings.list);
}

/**
 * Latest next-day briefing for one site.
 * REST API PLACEHOLDER: GET /api/briefings/:siteId  -> { briefing }  |  404 if unknown
 */
export async function getBriefing(siteId) {
  if (USE_MOCKS) {
    const site = mockStore.sites.find((s) => s.id === siteId && s.active);
    return site ? mockResponse({ briefing: buildBriefing(site) }) : mockNotFound('Site not found');
  }
  return apiRequest(ENDPOINTS.briefings.detail(siteId));
}

/**
 * Generate and send next-day briefings now instead of waiting for 6 PM
 * (supervisor only). POST to the collection = create new briefings; omit
 * `siteIds` to send for every active site.
 * REST API PLACEHOLDER: POST /api/briefings  { siteIds?: string[] }  -> { sent: number }   [PLANNED]
 */
export async function sendBriefingsNow(siteIds) {
  if (USE_MOCKS) {
    return mockResponse({ sent: siteIds?.length ?? mockStore.sites.filter((s) => s.active).length }, 600);
  }
  return apiRequest(ENDPOINTS.briefings.create, { method: 'POST', body: { siteIds } });
}
