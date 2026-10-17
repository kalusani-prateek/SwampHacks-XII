// User management (supervisors only): list, create, change role, delete.
// REST resources: /api/users and /api/users/:id (see src/api/users.js).
import { useState } from 'react';
import { ErrorState, LoadingState } from '../../../components/common/Status.jsx';
import { useApi } from '../../../hooks/useApi.js';
import { useAuth } from '../../../context/AuthContext.jsx';
import { createUser, deleteUser, getUsers, updateUser } from '../../../api/users.js';
import { ROLES } from '../../../utils/roles.js';

const EMPTY_FORM = { username: '', email: '', password: '', role: ROLES.CREW };

export default function UsersTab() {
  const { user: me } = useAuth();
  // REST API PLACEHOLDER: GET /api/users
  const { data, loading, error, reload } = useApi(() => getUsers());
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState('');

  async function handleCreate(e) {
    e.preventDefault();
    setFormError('');
    try {
      await createUser(form); // REST API PLACEHOLDER: POST /api/users
      setForm(EMPTY_FORM);
      reload({ silent: true });
    } catch (err) {
      setFormError(err.message);
    }
  }

  async function handleRoleChange(id, role) {
    await updateUser(id, { role }); // REST API PLACEHOLDER: PUT /api/users/:id
    reload({ silent: true });
  }

  async function handleDelete(u) {
    if (!window.confirm(`Delete user "${u.username}"?`)) return;
    await deleteUser(u.id); // REST API PLACEHOLDER: DELETE /api/users/:id
    reload({ silent: true });
  }

  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      {/* User table */}
      <div className="card overflow-x-auto lg:col-span-2">
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-slate-500 uppercase">
            <tr>
              <th className="px-2 py-2">Username</th>
              <th className="px-2 py-2">Email</th>
              <th className="px-2 py-2">Role</th>
              <th className="px-2 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.users.map((u) => (
              <tr key={u.id}>
                <td className="px-2 py-2 font-medium">{u.username}</td>
                <td className="px-2 py-2 text-slate-600">{u.email}</td>
                <td className="px-2 py-2">
                  <select
                    className="input py-1"
                    value={u.role}
                    disabled={u.id === me.id} // can't demote yourself, so there is always a supervisor
                    onChange={(e) => handleRoleChange(u.id, e.target.value)}
                  >
                    {Object.values(ROLES).map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-2 py-2 text-right">
                  {u.id !== me.id && (
                    <button className="text-sm font-medium text-red-600 hover:underline" onClick={() => handleDelete(u)}>
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Create user form */}
      <form onSubmit={handleCreate} className="card space-y-3">
        <h2 className="font-semibold text-navy-800">Add user</h2>
        {['username', 'email', 'password'].map((field) => (
          <div key={field}>
            <label className="label" htmlFor={`new-${field}`}>
              {field}
            </label>
            <input
              id={`new-${field}`}
              type={field === 'password' ? 'password' : field === 'email' ? 'email' : 'text'}
              className="input"
              value={form[field]}
              onChange={(e) => setForm({ ...form, [field]: e.target.value })}
              required
              minLength={field === 'password' ? 8 : 3} // matches the server's rules
            />
          </div>
        ))}
        <div>
          <label className="label" htmlFor="new-role">
            Role
          </label>
          <select id="new-role" className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            {Object.values(ROLES).map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>
        {formError && <p className="text-sm text-red-600">{formError}</p>}
        <button className="btn-primary w-full">Create user</button>
      </form>
    </div>
  );
}
