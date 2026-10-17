// User service - supervisors manage crew and supervisor accounts.
// REST resources: /api/users (list, create) and /api/users/:id (read, update, delete).
// There is no admin role: the backend allows these calls for supervisors.
import { apiRequest, mockNotFound, mockResponse, ApiError, USE_MOCKS } from './client.js';
import { ENDPOINTS } from './endpoints.js';
import { mockStore } from '../mocks/store.js';

/**
 * All user accounts (supervisor only).
 * REST API PLACEHOLDER: GET /api/users  -> { users: User[] }   [PLANNED]
 */
export async function getUsers() {
  if (USE_MOCKS) return mockResponse({ users: mockStore.users });
  return apiRequest(ENDPOINTS.users.list);
}

/**
 * Add an account with a role (supervisor only).
 * REST API PLACEHOLDER: POST /api/users  { username, email, password, role }  -> { user }   [PLANNED]
 */
export async function createUser(data) {
  if (USE_MOCKS) {
    if (mockStore.users.some((u) => u.username === data.username)) {
      throw new ApiError('Username already exists', 409);
    }
    const { password: _password, ...fields } = data; // the mock never stores passwords
    const user = { id: Math.max(0, ...mockStore.users.map((u) => u.id)) + 1, ...fields };
    mockStore.users.push(user);
    return mockResponse({ user });
  }
  return apiRequest(ENDPOINTS.users.create, { method: 'POST', body: data });
}

/**
 * Update an account. Users may edit themselves; only supervisors may change `role`.
 * REST API PLACEHOLDER: PUT /api/users/:id  { username?, email?, password?, role? }   [EXISTS - add `role`]
 */
export async function updateUser(userId, data) {
  if (USE_MOCKS) {
    const user = mockStore.users.find((u) => u.id === userId);
    if (!user) return mockNotFound('User not found');
    Object.assign(user, data);
    return mockResponse({ message: 'User updated successfully' });
  }
  return apiRequest(ENDPOINTS.users.detail(userId), { method: 'PUT', body: data });
}

/**
 * Delete an account (self or supervisor).
 * REST API PLACEHOLDER: DELETE /api/users/:id   [EXISTS]
 */
export async function deleteUser(userId) {
  if (USE_MOCKS) {
    mockStore.users = mockStore.users.filter((u) => u.id !== userId);
    return mockResponse({ message: 'User deleted successfully' });
  }
  return apiRequest(ENDPOINTS.users.detail(userId), { method: 'DELETE' });
}
