// =============================================================================
// Page URL map - single source of truth for every URL in the browser bar.
//   PATHS -> route patterns used by <Route path> in App.jsx
//   urls  -> builders used by <Link>, <NavLink> and navigate()
// Builders always return ABSOLUTE paths, so links work from any page.
// (Relative links inside nested/splat routes resolve against the current URL
// in React Router 7, which is what broke the panel tabs before.)
//
// Page URLs mirror the REST API resources they read from, e.g.
//   /sites/turkey-point  <->  GET /api/sites/turkey-point
// The full page -> API mapping is in docs/API.md ("Frontend routes").
// =============================================================================
import { segment, withQuery } from './utils/url.js';

export const PATHS = {
  home: '/',
  login: '/login',
  register: '/register',
  account: '/account', //        your profile: username, email, password, designated site
  dashboard: '/dashboard',
  sites: '/sites',
  siteDetail: '/sites/:siteId',
  alerts: '/alerts',
  reports: '/reports',
  newReport: '/reports/new',
  briefings: '/briefings',
  manage: '/manage', //          supervisor-only management panel
  manageTab: '/manage/:tab',
};

/** Manage panel tabs, in display order. `slug` is the URL segment: /manage/<slug>. */
export const MANAGE_TABS = [
  { slug: 'overview', label: 'Overview' },
  { slug: 'users', label: 'Users' },
  { slug: 'sites', label: 'Sites' },
  { slug: 'alert-rules', label: 'Alert rules' },
  { slug: 'reports', label: 'Hazard reports' },
  { slug: 'briefings', label: 'Briefings' },
];
export const DEFAULT_MANAGE_TAB = 'overview';
export const isManageTab = (slug) => MANAGE_TABS.some((tab) => tab.slug === slug);

/** Allowed values for URL query filters (anything else is ignored and removed). */
export const DASHBOARD_DECISIONS = ['all', 'no-go', 'caution', 'go'];
export const REPORT_STATUSES = ['all', 'open', 'verified', 'resolved', 'dismissed'];
/** Time windows on the Hazard Reports page (?days=7); "all" means no limit. */
export const REPORT_WINDOWS = [
  { value: '1', label: 'Last 24 hours' },
  { value: '7', label: 'Last 7 days' },
  { value: '30', label: 'Last 30 days' },
  { value: 'all', label: 'All time' },
];
export const DEFAULT_REPORT_WINDOW = '30';

// Each builder documents the readable URL it produces.
export const urls = {
  home: () => PATHS.home, //                                         /
  login: ({ next } = {}) => withQuery(PATHS.login, { next }), //     /login?next=/manage/users
  register: ({ next } = {}) => withQuery(PATHS.register, { next }), // /register?next=/alerts
  account: () => PATHS.account, //                                   /account
  dashboard: ({ decision } = {}) => withQuery(PATHS.dashboard, { decision }), // /dashboard?decision=no-go
  sites: ({ q } = {}) => withQuery(PATHS.sites, { q }), //           /sites?q=florida
  site: (siteId) => `${PATHS.sites}/${segment(siteId)}`, //          /sites/turkey-point
  alerts: ({ type } = {}) => withQuery(PATHS.alerts, { type }), //   /alerts?type=lightning
  reports: ({ q, site, type, status, days, mine } = {}) => withQuery(PATHS.reports, { q, site, type, status, days, mine }), // /reports?type=wildlife&days=7
  newReport: ({ site } = {}) => withQuery(PATHS.newReport, { site }), // /reports/new?site=turkey-point
  briefings: ({ q } = {}) => withQuery(PATHS.briefings, { q }), //   /briefings?q=texas
  manage: (tab = DEFAULT_MANAGE_TAB, query) => withQuery(`${PATHS.manage}/${segment(tab)}`, query), // /manage/reports?status=open
};
