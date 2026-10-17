// Outbox service - emails and texts the backend sent (or only recorded, when
// SMTP/Twilio aren't configured). Supervisors see it in Manage › Briefings.
import { apiRequest, mockResponse, USE_MOCKS } from './client.js';
import { ENDPOINTS } from './endpoints.js';

/**
 * REST API PLACEHOLDER: GET /api/notifications?limit=  -> { notifications: [{ id, createdAt, channel, recipient, subject, body, status }] }
 */
export async function getNotifications(limit = 20) {
  if (USE_MOCKS) return mockResponse({ notifications: [] });
  return apiRequest(ENDPOINTS.notifications, { query: { limit } });
}
