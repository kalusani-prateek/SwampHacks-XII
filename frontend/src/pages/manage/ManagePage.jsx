// Manage panel - supervisor-only management tools. Supervisors hold every
// management privilege (there is no separate admin role). Each tab has its
// own readable URL: /manage/overview, /manage/users, /manage/sites,
// /manage/alert-rules, /manage/reports, /manage/briefings
// (tab slugs live in src/routes.js; access is enforced in App.jsx).
import { NavLink, Navigate, useParams } from 'react-router-dom';
import PageHeader from '../../components/common/PageHeader.jsx';
import OverviewTab from './tabs/OverviewTab.jsx';
import UsersTab from './tabs/UsersTab.jsx';
import SitesTab from './tabs/SitesTab.jsx';
import AlertRulesTab from './tabs/AlertRulesTab.jsx';
import ReportsTab from './tabs/ReportsTab.jsx';
import BriefingsTab from './tabs/BriefingsTab.jsx';
import { MANAGE_TABS, isManageTab, urls } from '../../routes.js';

// URL slug -> tab component.
const TAB_COMPONENTS = {
  overview: OverviewTab,
  users: UsersTab,
  sites: SitesTab,
  'alert-rules': AlertRulesTab,
  reports: ReportsTab,
  briefings: BriefingsTab,
};

export default function ManagePage() {
  const { tab } = useParams();

  // Unknown tab (e.g. /manage/settings): fall back to the overview.
  if (!isManageTab(tab)) return <Navigate to={urls.manage()} replace />;

  const ActiveTab = TAB_COMPONENTS[tab];
  const activeLabel = MANAGE_TABS.find((t) => t.slug === tab).label;

  return (
    <>
      <PageHeader
        title="Manage"
        documentTitle={`Manage · ${activeLabel}`}
        subtitle="Supervisor tools: users, job sites, alert rules, crew reports and briefings."
      />

      {/* overflow-y-hidden: the tabs' -1px underline overlap must not add a vertical scrollbar */}
      <nav className="mb-6 flex gap-1 overflow-x-auto overflow-y-hidden border-b border-slate-200" aria-label="Manage sections">
        {MANAGE_TABS.map((t) => (
          <NavLink
            key={t.slug}
            to={urls.manage(t.slug)} // absolute: /manage/<slug>
            className={({ isActive }) =>
              `-mb-px border-b-2 px-4 py-2 text-sm font-medium whitespace-nowrap ${
                isActive ? 'border-brand text-brand' : 'border-transparent text-slate-500 hover:text-navy-800'
              }`
            }
          >
            {t.label}
          </NavLink>
        ))}
      </nav>

      {/* `key` resets tab state when switching tabs */}
      <ActiveTab key={tab} />
    </>
  );
}
