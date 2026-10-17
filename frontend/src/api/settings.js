// Settings service - supervisor-editable configuration the backend uses:
// alert thresholds and the 6 PM briefing schedule. Both are single
// ("singleton") REST resources under /api/settings.
import { apiRequest, mockResponse, USE_MOCKS } from './client.js';
import { ENDPOINTS } from './endpoints.js';
import { mockStore } from '../mocks/store.js';

/**
 * Thresholds the backend monitors use to raise alerts.
 * REST API PLACEHOLDER: GET /api/settings/alert-rules  -> { rules }   [PLANNED]
 */
export async function getAlertRules() {
  if (USE_MOCKS) return mockResponse({ rules: mockStore.alertRules });
  return apiRequest(ENDPOINTS.settings.alertRules);
}

/**
 * Save alert thresholds (supervisor only).
 * REST API PLACEHOLDER: PUT /api/settings/alert-rules  { rules }  -> { rules }   [PLANNED]
 */
export async function updateAlertRules(rules) {
  if (USE_MOCKS) {
    mockStore.alertRules = rules;
    return mockResponse({ rules });
  }
  return apiRequest(ENDPOINTS.settings.alertRules, { method: 'PUT', body: { rules } });
}

/**
 * Next-day briefing schedule, channels and recipients.
 * REST API PLACEHOLDER: GET /api/settings/briefings  -> { settings }   [PLANNED]
 */
export async function getBriefingSettings() {
  if (USE_MOCKS) return mockResponse({ settings: mockStore.briefingSettings });
  return apiRequest(ENDPOINTS.settings.briefings);
}

/**
 * Save briefing settings (supervisor only).
 * REST API PLACEHOLDER: PUT /api/settings/briefings  { settings }  -> { settings }   [PLANNED]
 */
export async function updateBriefingSettings(settings) {
  if (USE_MOCKS) {
    mockStore.briefingSettings = settings;
    return mockResponse({ settings });
  }
  return apiRequest(ENDPOINTS.settings.briefings, { method: 'PUT', body: { settings } });
}
