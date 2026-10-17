// Server info: which optional features are on (demo tools, demo accounts, AI assistant).
import { apiRequest, mockResponse, USE_MOCKS } from './client.js';
import { ENDPOINTS } from './endpoints.js';

let cached = null;

/**
 * Fetched once per page load and shared.
 * REST API PLACEHOLDER: GET /api/meta  -> { demoTools, demoAccounts, assistant, lightningSource, scoring }
 */
export function getMeta() {
  if (!cached) {
    cached = USE_MOCKS
      ? mockResponse({
          demoTools: true,
          demoAccounts: { usernames: ['supervisor', 'crew'], password: 'demo' },
          assistant: false,
          lightningSource: 'mock',
          scoring: { method: 'mock', label: 'Demo data (no backend connected)' },
        }, 0)
      : apiRequest(ENDPOINTS.meta).catch(() => ({}));
  }
  return cached;
}
