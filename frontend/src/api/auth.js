// Auth service - wraps the Flask-Login endpoints in backend/app/api/auth.py.
import { apiRequest, mockResponse, ApiError, USE_MOCKS } from './client.js';
import { ENDPOINTS } from './endpoints.js';
import { mockStore } from '../mocks/store.js';

/**
 * Sign in with username + password.
 * REST API: POST /api/auth/login  { username, password }  -> { message, user }
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
 * Create a crew account at the site the person works at; the backend signs it
 * in straight away. (Supervisor accounts are added in Manage › Users or the CLI.)
 * REST API: POST /api/auth/register  { username, email, password, siteId }  -> 201 { message, user }
 */
export async function register({ username, email, password, siteId }) {
  if (USE_MOCKS) {
    // Mock mode keeps the account in memory until the page reloads; any password signs in.
    if (mockStore.users.some((u) => u.username === username)) throw new ApiError('Username already exists', 409);
    if (mockStore.users.some((u) => u.email === email.toLowerCase())) throw new ApiError('Email already exists', 409);
    const site = mockStore.sites.find((s) => s.id === siteId && s.active);
    if (!site) throw new ApiError('Choose the site you work at.', 400);
    const user = {
      id: Math.max(0, ...mockStore.users.map((u) => u.id)) + 1,
      username,
      email: email.toLowerCase(),
      role: 'crew',
      siteId: site.id,
      siteName: site.name,
    };
    mockStore.users.push(user);
    return mockResponse({ message: 'Account created', user });
  }
  return apiRequest(ENDPOINTS.auth.register, { method: 'POST', body: { username, email, password, siteId } });
}

/**
 * Mock mode only: demo data lives in memory, so after a page reload put the
 * signed-in account (remembered in sessionStorage) back into the mock store.
 */
export function restoreMockAccount(user) {
  if (USE_MOCKS && user && !mockStore.users.some((u) => u.id === user.id)) mockStore.users.push(user);
}

/**
 * End the session.
 * REST API: POST /api/auth/logout
 */
export async function logout() {
  if (USE_MOCKS) return mockResponse({ message: 'Logged out successfully' });
  return apiRequest(ENDPOINTS.auth.logout, { method: 'POST' });
}

/**
 * Return the signed-in user for the current session cookie (used on page load).
 * REST API: GET /api/auth/me  -> { user }
 */
export async function getCurrentUser() {
  if (USE_MOCKS) {
    // Mock mode remembers the demo user in sessionStorage (see AuthContext).
    return mockResponse({ user: null });
  }
  return apiRequest(ENDPOINTS.auth.me);
}
