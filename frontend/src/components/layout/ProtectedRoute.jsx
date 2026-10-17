// Route guard. Signed out -> /login?next=<current url> (or a clean /login
// right after an explicit sign-out). Wrong role -> the home page.
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import { hasRole } from '../../utils/roles.js';
import { urls } from '../../routes.js';
import { LoadingState } from '../common/Status.jsx';

export default function ProtectedRoute({ roles }) {
  const { user, loading, signedOut } = useAuth();
  const location = useLocation();

  if (loading) return <LoadingState label="Checking session…" />;
  if (!user) {
    // Keep the requested page in a readable `next` param so it survives reloads,
    // except after signing out: the next person should start fresh.
    const next = `${location.pathname}${location.search}`;
    const keepNext = !signedOut && next !== urls.home();
    return <Navigate to={urls.login({ next: keepNext ? next : undefined })} replace />;
  }
  if (!hasRole(user, roles)) return <Navigate to={urls.home()} replace />;

  return <Outlet />;
}
