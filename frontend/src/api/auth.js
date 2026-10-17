// Auth service - wraps the existing Flask-Login endpoints in backend/app/routes.py.
import { apiRequest, mockResponse, ApiError, USE_MOCKS } from './client.js';
import { ENDPOINTS } from './endpoints.js';
import { mockStore } from '../mocks/store.js';

/**
 * Sign in with username + password.
 * REST API PLACEHOLDER: POST /api/auth/login  { username, password }
 * NOTE: the existing route returns only { message }. Planned change: also
 * return { user } so the UI knows the user's role without a second request.
 */
export async function login(username, password) {
  if (USE_MOCKS) {
    const user = mockStore.users.find((u) => u.username === username);
    // Mock mode accepts any password for the seeded demo users.
    if (!user || !password) throw new ApiError('Invalid username or password', 401);
    return mockResponse({ message: 'Logged in successfully', user });
  }
  return apiRequest(ENDPOINTS.auth.login, { method: 'POST', body: { username, password } });
}

/**
 * End the session.
 * REST API PLACEHOLDER: POST /api/auth/logout
 */
export async function logout() {
  if (USE_MOCKS) return mockResponse({ message: 'Logged out successfully' });
  return apiRequest(ENDPOINTS.auth.logout, { method: 'POST' });
}

/**
 * Return the signed-in user for the current session cookie (used on page load).
 * REST API PLACEHOLDER: GET /api/auth/me  -> { user }   (PLANNED)
 */
export async function getCurrentUser() {
  if (USE_MOCKS) {
    // Mock mode remembers the demo user in sessionStorage (see AuthContext).
    return mockResponse({ user: null });
  }
  return apiRequest(ENDPOINTS.auth.me);
}
