// Sign-in page (/login?next=/manage/users). After signing in, the user returns
// to `next` if it is a safe in-app path, otherwise to their role's home page.
// When demo accounts exist (mock mode, or a development server), they are
// offered as one-click buttons.
import { useState } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { BACKEND_HINT, isMockFallback, USE_MOCKS } from '../api/client.js';
import { useMeta } from '../hooks/useMeta.js';
import { usePageTitle } from '../hooks/usePageTitle.js';
import { PATHS, urls } from '../routes.js';
import { isSafeInternalPath } from '../utils/url.js';

export default function LoginPage() {
  usePageTitle('Sign in');
  const { user, login } = useAuth();
  // Two roles only (supervisor and crew); the server says whether demo accounts exist.
  const demoAccounts = useMeta()?.demoAccounts;
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Validate `next` so /login?next=https://evil.example can't redirect off-site.
  const nextParam = params.get('next');
  const next =
    isSafeInternalPath(nextParam) && ![PATHS.login, PATHS.register].some((path) => nextParam.startsWith(path)) ? nextParam : null;

  if (user) return <Navigate to={next ?? urls.home()} replace />;

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      // REST API PLACEHOLDER: POST /api/auth/login
      await login(form.username, form.password);
      // "/" redirects each role to its home page (see HomeRedirect in App.jsx).
      navigate(next ?? urls.home(), { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-navy-800 px-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-center text-4xl font-extrabold text-white">
          PlanIT <span className="text-brand">Control</span>
        </h1>
        <p className="mb-8 text-center text-sm text-slate-400">Job-site hazard monitoring for utility field crews</p>

        <form onSubmit={handleSubmit} className="card space-y-4">
          {isMockFallback() && (
            <p role="status" className="rounded-md bg-yellow-50 px-3 py-2 text-xs text-yellow-800">
              {BACKEND_HINT}
            </p>
          )}
          <div>
            <label className="label" htmlFor="username">
              Username
            </label>
            <input
              id="username"
              className="input"
              autoComplete="username"
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="input"
              autoComplete="current-password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="submit" className="btn-primary w-full" disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
          <p className="text-center text-sm text-slate-500">
            New to PlanIT?{' '}
            <Link to={urls.register({ next })} className="font-medium text-brand hover:underline">
              Create an account
            </Link>
          </p>

          {demoAccounts && (
            <div className="border-t border-slate-100 pt-3 text-xs text-slate-500">
              <p className="mb-2">
                {USE_MOCKS ? 'Demo data: pick a demo account (any password works).' : 'Demo server: pick a demo account.'}
              </p>
              <div className="flex gap-2">
                {demoAccounts.usernames.map((name) => (
                  <button
                    key={name}
                    type="button"
                    className="btn-secondary flex-1 px-2 py-1 text-xs"
                    onClick={() => setForm({ username: name, password: demoAccounts.password })}
                  >
                    {name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
