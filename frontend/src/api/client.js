// =============================================================================
// REST API client
// =============================================================================
// Every network call in the app goes through `apiRequest`. Each service module
// in src/api/ checks `USE_MOCKS` first: when no backend answers at startup, it
// returns data from src/mocks instead. VITE_USE_MOCKS in .env forces one mode
// for the whole app in one place.
// =============================================================================

import { withQuery } from '../utils/url.js';

/**
 * Base URL of the Flask REST API (see docs/API.md). Trailing slashes are
 * stripped so "/api/" + "/sites" never becomes "/api//sites". Can be relative
 * ("/api", via the Vite proxy) or absolute ("https://api.example.com/api").
 */
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/+$/, '');

/**
 * When true, services return mock data instead of calling the backend.
 * VITE_USE_MOCKS: "true" = always mock, "false" = always the real API,
 * "auto" (default) = use the backend if it answers at startup (see detectBackend).
 * Declared with `let` so every module sees the value detectBackend() sets.
 */
const MOCK_SETTING = (import.meta.env.VITE_USE_MOCKS ?? 'auto').toLowerCase();
export let USE_MOCKS = MOCK_SETTING === 'true';

/** Decide mock vs. real API once, before the app renders (called from main.jsx). */
export async function detectBackend() {
  if (MOCK_SETTING !== 'auto') return USE_MOCKS;
  try {
    const response = await fetch(`${API_BASE_URL}/meta`, { signal: AbortSignal.timeout(2500) });
    const data = await response.json();
    USE_MOCKS = !(response.ok && data.api === 'planit-control');
  } catch {
    USE_MOCKS = true; // no backend running: fall back to demo data
  }
  return USE_MOCKS;
}

/** True when demo data is showing only because the backend didn't answer (not forced by VITE_USE_MOCKS=true). */
export function isMockFallback() {
  return USE_MOCKS && MOCK_SETTING === 'auto';
}

/** Explains the demo-data fallback in the UI (navbar badge, sign-in page). */
export const BACKEND_HINT =
  "The backend isn't running, so this is demo data. Start it (in backend: .venv\\Scripts\\python run.py) and " +
  (import.meta.hot ? 'this page switches to live data by itself.' : 'refresh the page.');

/** Error thrown for non-2xx responses; carries the HTTP status. */
export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

/**
 * Perform a request against the REST API.
 * @param {string} path               Endpoint path from endpoints.js, e.g. "/sites" or "/sites/turkey-point"
 * @param {object} [options]
 * @param {string} [options.method]   HTTP verb (default GET)
 * @param {object} [options.query]    Query params, e.g. { siteId, active: true }; empty values are omitted
 * @param {object|FormData} [options.body] JSON-serialisable object or FormData (file uploads)
 * @returns {Promise<any>} Parsed JSON body
 */
export async function apiRequest(path, { method = 'GET', query, body } = {}) {
  if (!path.startsWith('/')) throw new Error(`API path must start with "/": ${path}`);
  const isFormData = body instanceof FormData;

  const response = await fetch(apiUrl(path, query), {
    method,
    // Flask-Login uses a session cookie, so it must be sent with every request.
    credentials: 'include',
    // Let the browser set the multipart boundary for FormData uploads.
    headers: isFormData ? undefined : { 'Content-Type': 'application/json' },
    body: isFormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.message || response.statusText, response.status);
  }
  return data;
}

/** Full URL for an endpoint (also used for EventSource streams). */
export function apiUrl(path, query) {
  return withQuery(`${API_BASE_URL}${path}`, query);
}

/**
 * Reject like the REST API would for a missing resource (HTTP 404), so pages
 * handle "not found" the same way in mock and real mode.
 */
export function mockNotFound(message = 'Not found') {
  return new Promise((_, reject) => setTimeout(() => reject(new ApiError(message, 404)), 150));
}

/**
 * Resolve mock data after a short delay so loading states behave like the
 * real API. Data is deep-cloned so callers can't mutate the mock store.
 */
export function mockResponse(data, delayMs = 250) {
  return new Promise((resolve) => setTimeout(() => resolve(structuredClone(data)), delayMs));
}
