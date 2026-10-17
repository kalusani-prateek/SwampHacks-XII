// Sign-up page (/register?next=/alerts). Anyone can create a crew account here,
// choosing the site they work at (their designated site, shown first across
// the app), and the backend signs it in straight away. Supervisor accounts are
// created by an existing supervisor (Manage › Users) or the create-supervisor CLI.
import { useState } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { getSiteOptions } from '../api/sites.js';
import { useAuth } from '../context/AuthContext.jsx';
import { useApi } from '../hooks/useApi.js';
import { usePageTitle } from '../hooks/usePageTitle.js';
import { PATHS, urls } from '../routes.js';
import { isSafeInternalPath } from '../utils/url.js';

// The backend's rules (backend/app/api/validation.py), checked here first for instant feedback.
const USERNAME = /^[A-Za-z0-9_.-]{3,64}$/;
const EMAIL = /^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$/;
const MIN_PASSWORD = 8;

/** First problem with the form, or null when it can be sent. */
function problemWith({ username, email, siteId, password, confirm }) {
  if (!USERNAME.test(username.trim())) return 'Username must be 3-64 letters, digits, dots, dashes or underscores.';
  if (email.trim().length > 120 || !EMAIL.test(email.trim())) return 'Enter a valid email address.';
  if (!siteId) return 'Choose the site you work at.';
  if (password.length < MIN_PASSWORD) return `Password must be at least ${MIN_PASSWORD} characters.`;
  if (password !== confirm) return "The passwords don't match.";
  return null;
}

export default function RegisterPage() {
  usePageTitle('Create account');
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  // REST API PLACEHOLDER: GET /api/sites/options (public, so it works before signing in)
  const siteOptions = useApi(() => getSiteOptions());
  const [form, setForm] = useState({ username: '', email: '', siteId: '', password: '', confirm: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Same rule as the sign-in page: `next` must be a safe in-app path.
  const nextParam = params.get('next');
  const next =
    isSafeInternalPath(nextParam) && ![PATHS.login, PATHS.register].some((path) => nextParam.startsWith(path)) ? nextParam : null;

  if (user) return <Navigate to={next ?? urls.home()} replace />;

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  async function handleSubmit(e) {
    e.preventDefault();
    const problem = problemWith(form);
    setError(problem ?? '');
    if (problem) return;
    setSubmitting(true);
    try {
      // REST API: POST /api/auth/register (creates a crew account and signs it in)
      await register({ username: form.username.trim(), email: form.email.trim(), password: form.password, siteId: form.siteId });
      // "/" sends crew to the site list (see HomeRedirect in App.jsx).
      navigate(next ?? urls.home(), { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-navy-800 px-4 py-10">
      <div className="w-full max-w-sm">
        <h1 className="mb-1 text-center text-4xl font-extrabold text-white">
          PlanIT <span className="text-brand">Control</span>
        </h1>
        <p className="mb-8 text-center text-sm text-slate-400">Create a crew account</p>

        <form onSubmit={handleSubmit} className="card space-y-4">
          <div>
            <label className="label" htmlFor="username">
              Username
            </label>
            <input
              id="username"
              className="input"
              autoComplete="username"
              value={form.username}
              onChange={update('username')}
              aria-describedby="username-hint"
              required
            />
            <p id="username-hint" className="mt-1 text-xs text-slate-500">
              3-64 letters, digits, dots, dashes or underscores
            </p>
          </div>
          <div>
            <label className="label" htmlFor="email">
              Email
            </label>
            <input id="email" type="email" className="input" autoComplete="email" value={form.email} onChange={update('email')} required />
          </div>
          <div>
            <label className="label" htmlFor="site">
              Your site
            </label>
            <select
              id="site"
              className="input"
              value={form.siteId}
              onChange={update('siteId')}
              aria-describedby="site-hint"
              disabled={!siteOptions.data}
              required
            >
              <option value="">
                {siteOptions.loading ? 'Loading sites…' : siteOptions.error ? "Couldn't load the sites" : 'Choose the site you work at'}
              </option>
              {siteOptions.data?.sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.state})
                </option>
              ))}
            </select>
            <p id="site-hint" className="mt-1 text-xs text-slate-500">
              {siteOptions.error ? (
                <button type="button" className="font-medium text-brand hover:underline" onClick={() => siteOptions.reload()}>
                  Try again
                </button>
              ) : (
                'Shown first across the app. You can change it later in your account.'
              )}
            </p>
          </div>
          <div>
            <label className="label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              className="input"
              autoComplete="new-password"
              value={form.password}
              onChange={update('password')}
              aria-describedby="password-hint"
              required
            />
            <p id="password-hint" className="mt-1 text-xs text-slate-500">
              At least {MIN_PASSWORD} characters
            </p>
          </div>
          <div>
            <label className="label" htmlFor="confirm">
              Confirm password
            </label>
            <input
              id="confirm"
              type="password"
              className="input"
              autoComplete="new-password"
              value={form.confirm}
              onChange={update('confirm')}
              required
            />
          </div>
          {error && (
            <p role="alert" className="text-sm text-red-600">
              {error}
            </p>
          )}
          <button type="submit" className="btn-primary w-full" disabled={submitting}>
            {submitting ? 'Creating account…' : 'Create account'}
          </button>

          <div className="space-y-1 border-t border-slate-100 pt-3 text-center">
            <p className="text-sm text-slate-500">
              Already have an account?{' '}
              <Link to={urls.login({ next })} className="font-medium text-brand hover:underline">
                Sign in
              </Link>
            </p>
            <p className="text-xs text-slate-400">New accounts are crew accounts. A supervisor can change your role later.</p>
          </div>
        </form>
      </div>
    </div>
  );
}
