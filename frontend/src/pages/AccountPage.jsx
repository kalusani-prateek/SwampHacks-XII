// Your account (/account): change your username, email, designated site and
// password. The designated site is listed first and highlighted on the Sites,
// Alerts, Hazard Reports and Briefings pages. Changing your username, email or
// password needs your current password (the server checks it too).
import { useState } from 'react';
import { Link } from 'react-router-dom';
import PageHeader from '../components/common/PageHeader.jsx';
import { ErrorState, LoadingState } from '../components/common/Status.jsx';
import { useAuth } from '../context/AuthContext.jsx';
import { useApi } from '../hooks/useApi.js';
import { getSites } from '../api/sites.js';
import { urls } from '../routes.js';

// The backend's rules (backend/app/api/validation.py), checked here first for instant feedback.
const USERNAME = /^[A-Za-z0-9_.-]{3,64}$/;
const EMAIL = /^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$/;
const MIN_PASSWORD = 8;

const formFor = (user) => ({
  username: user.username,
  email: user.email,
  siteId: user.siteId ?? '',
  newPassword: '',
  confirm: '',
  currentPassword: '',
});

export default function AccountPage() {
  const { user, updateAccount } = useAuth();
  // REST API PLACEHOLDER: GET /api/sites (the sites you can choose)
  const { data, loading, error, reload } = useApi(() => getSites());
  const [form, setForm] = useState(() => formFor(user));
  const [message, setMessage] = useState({ error: '', saved: '' });
  const [saving, setSaving] = useState(false);

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value });
  const changes = {};
  if (form.username.trim() !== user.username) changes.username = form.username.trim();
  if (form.email.trim().toLowerCase() !== user.email) changes.email = form.email.trim();
  if (form.siteId !== (user.siteId ?? '')) changes.siteId = form.siteId;
  if (form.newPassword) changes.password = form.newPassword;
  const needsCurrentPassword = Boolean(changes.username || changes.email || changes.password);

  function problem() {
    if (!USERNAME.test(form.username.trim())) return 'Username must be 3-64 letters, digits, dots, dashes or underscores.';
    if (form.email.trim().length > 120 || !EMAIL.test(form.email.trim())) return 'Enter a valid email address.';
    if (!form.siteId) return 'Choose the site you work at.';
    if (form.newPassword && form.newPassword.length < MIN_PASSWORD) return `New password must be at least ${MIN_PASSWORD} characters.`;
    if (form.newPassword !== form.confirm) return "The new passwords don't match.";
    if (needsCurrentPassword && !form.currentPassword) return 'Enter your current password to change your username, email or password.';
    return null;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const issue = problem();
    if (issue) return setMessage({ error: issue, saved: '' });
    if (Object.keys(changes).length === 0) return setMessage({ error: '', saved: 'Nothing to change.' });
    setSaving(true);
    try {
      // REST API PLACEHOLDER: PUT /api/users/:id
      const updated = await updateAccount(needsCurrentPassword ? { ...changes, currentPassword: form.currentPassword } : changes);
      setForm(formFor(updated));
      setMessage({ error: '', saved: changes.password ? 'Saved. Use your new password next time you sign in.' : 'Saved.' });
    } catch (err) {
      setMessage({ error: err.message, saved: '' });
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const siteKnown = data.sites.some((s) => s.id === user.siteId);

  return (
    <>
      <PageHeader title="My account" subtitle={`Signed in as ${user.username} (${user.role})`} />

      <form onSubmit={handleSubmit} className="card max-w-xl space-y-5" noValidate>
        <section className="space-y-3">
          <h2 className="font-semibold text-navy-800">Profile</h2>
          <div>
            <label className="label" htmlFor="account-username">
              Username
            </label>
            <input id="account-username" className="input" autoComplete="username" value={form.username} onChange={update('username')} />
          </div>
          <div>
            <label className="label" htmlFor="account-email">
              Email
            </label>
            <input id="account-email" type="email" className="input" autoComplete="email" value={form.email} onChange={update('email')} />
          </div>
          <div>
            <label className="label" htmlFor="account-site">
              Your site
            </label>
            <select id="account-site" className="input" value={form.siteId} onChange={update('siteId')} aria-describedby="account-site-hint">
              <option value="">Choose the site you work at</option>
              {data.sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.state})
                </option>
              ))}
            </select>
            <p id="account-site-hint" className="mt-1 text-xs text-slate-500">
              {siteKnown ? (
                <>
                  Shown first and highlighted on the Sites, Alerts, Hazard Reports and Briefings pages.{' '}
                  <Link to={urls.site(user.siteId)} className="font-medium text-brand hover:underline">
                    Open {user.siteName}
                  </Link>
                </>
              ) : (
                "You don't have a site yet. Choose the one you work at."
              )}
            </p>
          </div>
        </section>

        <section className="space-y-3 border-t border-slate-100 pt-4">
          <h2 className="font-semibold text-navy-800">Change password</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="account-new-password">
                New password
              </label>
              <input
                id="account-new-password"
                type="password"
                className="input"
                autoComplete="new-password"
                value={form.newPassword}
                onChange={update('newPassword')}
                placeholder={`At least ${MIN_PASSWORD} characters`}
              />
            </div>
            <div>
              <label className="label" htmlFor="account-confirm">
                Confirm new password
              </label>
              <input
                id="account-confirm"
                type="password"
                className="input"
                autoComplete="new-password"
                value={form.confirm}
                onChange={update('confirm')}
              />
            </div>
          </div>
        </section>

        <section className="space-y-2 border-t border-slate-100 pt-4">
          <label className="label" htmlFor="account-current-password">
            Current password{needsCurrentPassword ? '' : ' (only to change your username, email or password)'}
          </label>
          <input
            id="account-current-password"
            type="password"
            className={`input ${needsCurrentPassword && !form.currentPassword ? 'border-brand' : ''}`}
            autoComplete="current-password"
            value={form.currentPassword}
            onChange={update('currentPassword')}
          />
        </section>

        {message.error && (
          <p role="alert" className="text-sm text-red-600">
            {message.error}
          </p>
        )}
        {message.saved && (
          <p role="status" className="text-sm text-emerald-700">
            {message.saved}
          </p>
        )}
        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? 'Saving…' : 'Save changes'}
        </button>
      </form>
    </>
  );
}
