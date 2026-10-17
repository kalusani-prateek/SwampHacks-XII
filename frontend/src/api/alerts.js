// Alert service - stop-work and warning alerts raised by the backend's
// condition monitors (lightning, flood, heat, ...).
import { apiRequest, apiUrl, mockResponse, USE_MOCKS } from './client.js';
import { ENDPOINTS } from './endpoints.js';
import { mockStore } from '../mocks/store.js';

/**
 * Alerts, optionally filtered to active ones and/or one site.
 * REST API PLACEHOLDER: GET /api/alerts?active=true&siteId=  -> { alerts: Alert[] }
 */
export async function getAlerts({ activeOnly = false, siteId } = {}) {
  if (USE_MOCKS) {
    const alerts = mockStore.alerts.filter(
      (a) => (!activeOnly || a.active) && (!siteId || a.siteId === siteId),
    );
    return mockResponse({ alerts });
  }
  // e.g. /api/alerts?active=true&siteId=turkey-point (empty filters omitted)
  return apiRequest(ENDPOINTS.alerts.list, { query: { active: activeOnly, siteId } });
}

/**
 * Crew member confirms they've seen an alert.
 * REST API PLACEHOLDER: POST /api/alerts/:id/ack  -> { alert }
 */
export async function acknowledgeAlert(alertId) {
  if (USE_MOCKS) {
    const alert = mockStore.alerts.find((a) => a.id === alertId);
    if (alert) alert.acknowledged = true;
    return mockResponse({ alert });
  }
  return apiRequest(ENDPOINTS.alerts.acknowledge(alertId), { method: 'POST' });
}

/**
 * Subscribe to real-time alerts pushed by the server.
 * REST API PLACEHOLDER: GET /api/alerts/stream  (Server-Sent Events, PLANNED)
 * Until the stream exists, the UI polls getAlerts() (see hooks/usePolling.js).
 * @returns {() => void} unsubscribe function
 */
export function subscribeToAlerts(onAlert) {
  if (USE_MOCKS || typeof EventSource === 'undefined') return () => {};
  const source = new EventSource(apiUrl(ENDPOINTS.alerts.stream), { withCredentials: true });
  source.onmessage = (event) => onAlert(JSON.parse(event.data));
  return () => source.close();
}
