// Site service - job sites, their combined risk picture and hazard forecast.
import { apiRequest, mockNotFound, mockResponse, USE_MOCKS } from './client.js';
import { ENDPOINTS } from './endpoints.js';
import { mockStore } from '../mocks/store.js';
import { buildForecast } from '../mocks/generators.js';
import { slugify } from '../utils/url.js';

/** Mock lookup; unknown or paused sites 404 like the real API. */
const findMockSite = (siteId) => mockStore.sites.find((s) => s.id === siteId && s.active);

/**
 * All monitored job sites with their current hazard index (0-10).
 * REST API PLACEHOLDER: GET /api/sites  -> { sites: Site[] }
 */
export async function getSites() {
  if (USE_MOCKS) return mockResponse({ sites: mockStore.sites.filter((s) => s.active) });
  return apiRequest(ENDPOINTS.sites.list);
}

/**
 * Active site names for choosing "the site you work at" (works signed out, for the sign-up form).
 * REST API PLACEHOLDER: GET /api/sites/options  -> { sites: [{ id, name, state }] }
 */
export async function getSiteOptions() {
  if (USE_MOCKS) {
    const sites = mockStore.sites.filter((s) => s.active).map(({ id, name, state }) => ({ id, name, state }));
    return mockResponse({ sites: sites.sort((a, b) => a.name.localeCompare(b.name)) });
  }
  return apiRequest(ENDPOINTS.sites.options);
}

/**
 * One site's combined risk picture: per-hazard scores, live conditions and
 * the reasons behind the hazard index.
 * REST API PLACEHOLDER: GET /api/sites/:id  -> { site: Site }  |  404 if unknown
 */
export async function getSite(siteId) {
  if (USE_MOCKS) {
    const site = findMockSite(siteId);
    return site ? mockResponse({ site }) : mockNotFound('Site not found');
  }
  return apiRequest(ENDPOINTS.sites.detail(siteId));
}

/**
 * 7-day hazard index forecast, scored from the daily weather forecast.
 * REST API PLACEHOLDER: GET /api/sites/:id/forecast  -> { forecast: [{ date, hazardIndex, topHazard }] }
 */
export async function getSiteForecast(siteId) {
  if (USE_MOCKS) {
    const site = findMockSite(siteId);
    return site ? mockResponse({ forecast: buildForecast(site) }) : mockNotFound('Site not found');
  }
  return apiRequest(ENDPOINTS.sites.forecast(siteId));
}

/**
 * Most recent lightning strike within 10 miles of the site. Drives the
 * 30-minute all-clear countdown (it restarts whenever a newer strike arrives).
 * REST API PLACEHOLDER: GET /api/sites/:id/lightning  -> { lastStrikeAt, distanceMiles } | { lastStrikeAt: null }
 */
export async function getLightningStatus(siteId) {
  if (USE_MOCKS) {
    return mockResponse(mockStore.lightning[siteId] ?? { lastStrikeAt: null, distanceMiles: null }, 100);
  }
  return apiRequest(ENDPOINTS.sites.lightning(siteId));
}

// ------------------------------------------------- Supervisor management ----

/**
 * All sites including paused ones (supervisor only; the default list hides them).
 * REST API PLACEHOLDER: GET /api/sites?includeInactive=true  -> { sites: Site[] }   [PLANNED]
 */
export async function getAllSites() {
  if (USE_MOCKS) return mockResponse({ sites: mockStore.sites });
  return apiRequest(ENDPOINTS.sites.list, { query: { includeInactive: true } });
}

/**
 * Add a job site, e.g. one imported from EIA-860M (supervisor only).
 * REST API PLACEHOLDER: POST /api/sites  { name, lat, lng, state, timezone, plantType, utility, waterway }  -> { site }   [PLANNED]
 */
export async function createSite(data) {
  if (USE_MOCKS) {
    // The backend should generate the same kind of readable id: "Big Cajun II" -> "big-cajun-ii".
    const base = slugify(data.name) || 'site';
    let id = base;
    for (let n = 2; mockStore.sites.some((s) => s.id === id); n++) id = `${base}-${n}`;
    const site = {
      id,
      active: true,
      hazardIndex: 0,
      hazards: { heat: 0, lightning: 0, flooding: 0, wildfire: 0, soil: 0, wildlife: 0, wind: 0 },
      conditions: {},
      drivers: ['Awaiting first data pull'],
      ...data,
    };
    mockStore.sites.push(site);
    return mockResponse({ site });
  }
  return apiRequest(ENDPOINTS.sites.create, { method: 'POST', body: data });
}

/**
 * Edit a site or pause/resume monitoring (supervisor only).
 * REST API PLACEHOLDER: PUT /api/sites/:id  { ...fields, active }   [PLANNED]
 */
export async function updateSite(siteId, data) {
  if (USE_MOCKS) {
    const site = mockStore.sites.find((s) => s.id === siteId);
    if (!site) return mockNotFound('Site not found');
    Object.assign(site, data);
    return mockResponse({ message: 'Site updated' });
  }
  return apiRequest(ENDPOINTS.sites.detail(siteId), { method: 'PUT', body: data });
}

/**
 * Remove a site permanently (supervisor only).
 * REST API PLACEHOLDER: DELETE /api/sites/:id   [PLANNED]
 */
export async function deleteSite(siteId) {
  if (USE_MOCKS) {
    mockStore.sites = mockStore.sites.filter((s) => s.id !== siteId);
    return mockResponse({ message: 'Site deleted' });
  }
  return apiRequest(ENDPOINTS.sites.detail(siteId), { method: 'DELETE' });
}

// ----------------------------------------------------------- Demo helper ----

/**
 * Demo helper: record a strike "now" so the 30-minute countdown visibly
 * restarts. Real strikes come from NOAA's GOES lightning satellites; this is
 * for demos only (supervisors, and only when the server has DEMO_TOOLS on).
 * REST API PLACEHOLDER: POST /api/sites/:id/lightning/simulate  -> { lastStrikeAt, distanceMiles }
 */
export async function simulateLightningStrike(siteId) {
  if (USE_MOCKS) {
    mockStore.lightning[siteId] = {
      lastStrikeAt: new Date().toISOString(),
      distanceMiles: Math.round(Math.random() * 9 + 1),
    };
    return mockResponse(mockStore.lightning[siteId], 0);
  }
  return apiRequest(ENDPOINTS.sites.simulateStrike(siteId), { method: 'POST' });
}
