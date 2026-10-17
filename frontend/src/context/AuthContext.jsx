// Auth state shared across the app: the signed-in user plus login/logout.
import { createContext, useContext, useEffect, useState } from 'react';
import * as authApi from '../api/auth.js';
import { USE_MOCKS } from '../api/client.js';
import { clearOfflineData } from '../offline.js';

const AuthContext = createContext(null);
const MOCK_SESSION_KEY = 'planit-mock-user';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); // true until the session check finishes
  // True right after an explicit sign-out, so ProtectedRoute sends the user to
  // a clean /login instead of /login?next=<the page they signed out from>.
  const [signedOut, setSignedOut] = useState(false);

  // On page load, restore the existing session.
  useEffect(() => {
    if (USE_MOCKS) {
      // Mock mode: there is no session cookie, so remember the user in sessionStorage.
      try {
        const saved = sessionStorage.getItem(MOCK_SESSION_KEY);
        if (saved) setUser(JSON.parse(saved));
      } catch {
        /* storage unavailable: start signed out */
      }
      setLoading(false);
      return;
    }
    // REST API PLACEHOLDER: GET /api/auth/me
    authApi
      .getCurrentUser()
      .then(({ user }) => setUser(user))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  async function login(username, password) {
    const response = await authApi.login(username, password);
    // Until the backend returns `user` from /login, fall back to /auth/me.
    const signedIn = response.user ?? (await authApi.getCurrentUser()).user;
    setUser(signedIn);
    setSignedOut(false);
    if (USE_MOCKS) {
      try {
        sessionStorage.setItem(MOCK_SESSION_KEY, JSON.stringify(signedIn));
      } catch {
        /* storage unavailable: session lasts until reload */
      }
    }
    return signedIn;
  }

  async function logout() {
    await authApi.logout();
    clearOfflineData(); // the next person on a shared device shouldn't see this user's saved data
    // Both updates render together, so the redirect sees signedOut = true.
    setUser(null);
    setSignedOut(true);
    if (USE_MOCKS) {
      try {
        sessionStorage.removeItem(MOCK_SESSION_KEY);
      } catch {
        /* ignore */
      }
    }
  }

  return <AuthContext.Provider value={{ user, loading, signedOut, login, logout }}>{children}</AuthContext.Provider>;
}

/** Access the auth context from any component. */
export function useAuth() {
  return useContext(AuthContext);
}
