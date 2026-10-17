// Route table. All paths come from src/routes.js. There are two roles:
//   crew        -> sites, alerts, hazard reporting, briefings, AI assistant
//   supervisor  -> everything crew can do, plus the PlanIt Dashboard and the
//                  Manage panel (/manage/<tab>). Supervisors hold all
//                  management privileges; there is no separate admin.
import { Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/layout/Layout.jsx';
import ProtectedRoute from './components/layout/ProtectedRoute.jsx';
import LoginPage from './pages/LoginPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';
import SitesPage from './pages/SitesPage.jsx';
import SiteDetailPage from './pages/SiteDetailPage.jsx';
import AlertsPage from './pages/AlertsPage.jsx';
import ReportHazardPage from './pages/ReportHazardPage.jsx';
import BriefingsPage from './pages/BriefingsPage.jsx';
import NotFoundPage from './pages/NotFoundPage.jsx';
import ManagePage from './pages/manage/ManagePage.jsx';
import { useAuth } from './context/AuthContext.jsx';
import { PATHS, urls } from './routes.js';
import { ROLES } from './utils/roles.js';

/** "/" sends each role to its natural home page. */
function HomeRedirect() {
  const { user } = useAuth();
  return <Navigate to={user.role === ROLES.SUPERVISOR ? urls.dashboard() : urls.sites()} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path={PATHS.login} element={<LoginPage />} />

      {/* Everything below requires a signed-in user */}
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path={PATHS.home} element={<HomeRedirect />} />
          <Route path={PATHS.sites} element={<SitesPage />} />
          <Route path={PATHS.siteDetail} element={<SiteDetailPage />} />
          <Route path={PATHS.alerts} element={<AlertsPage />} />
          <Route path={PATHS.newReport} element={<ReportHazardPage />} />
          <Route path={PATHS.briefings} element={<BriefingsPage />} />

          {/* Supervisor only: PlanIt Dashboard + Manage panel (/manage -> /manage/overview) */}
          <Route element={<ProtectedRoute roles={[ROLES.SUPERVISOR]} />}>
            <Route path={PATHS.dashboard} element={<DashboardPage />} />
            <Route path={PATHS.manage} element={<Navigate to={urls.manage()} replace />} />
            <Route path={PATHS.manageTab} element={<ManagePage />} />
          </Route>

          {/* Unknown URL: show a real 404 instead of silently redirecting */}
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
