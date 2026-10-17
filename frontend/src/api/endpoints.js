// =============================================================================
// REST API endpoint map - single source of truth for every backend route the
// frontend uses. Paths are relative to API_BASE_URL ("/api").
// Full request/response contracts: docs/API_PLAN.md
//   [EXISTS]       = already implemented in backend/app/routes.py
//   [PLANNED]      = to be implemented
//   (supervisor)   = requires the supervisor role; everything else needs any signed-in user
//
// Conventions (so the future backend stays predictable):
//   - plural resource nouns, lowercase kebab-case:  /sites, /settings/alert-rules
//   - ids are path segments, always URL-encoded:    /sites/turkey-point
//   - filters are query params, not paths:          /alerts?active=true&siteId=turkey-point
//     (pass them via apiRequest(path, { query }) so empty values are dropped)
//   - one path, different verbs:                    GET /sites (list) · POST /sites (create)
//   - actions on one resource are sub-paths:        POST /alerts/:id/ack
//   - permissions come from the user's role, never from the URL (no /admin prefix)
// =============================================================================
import { segment } from '../utils/url.js';

export const ENDPOINTS = {
  auth: {
    login: '/auth/login', //       POST  [EXISTS]
    logout: '/auth/logout', //     POST  [EXISTS]
    register: '/auth/register', // POST  [EXISTS] new accounts are crew
    me: '/auth/me', //             GET   [PLANNED] current session user
  },

  users: {
    list: '/users', //                                       GET    [PLANNED] (supervisor)
    create: '/users', //                                     POST   [PLANNED] (supervisor)
    detail: (id) => `/users/${segment(id)}`, //              GET / PUT / DELETE [EXISTS] self or supervisor; `role` changes supervisor-only
  },

  sites: {
    list: '/sites', //                                       GET    [PLANNED] ?includeInactive=true (supervisor)
    create: '/sites', //                                     POST   [PLANNED] (supervisor)
    detail: (id) => `/sites/${segment(id)}`, //              GET    [PLANNED] · PUT / DELETE (supervisor)
    forecast: (id) => `/sites/${segment(id)}/forecast`, //   GET    [PLANNED] 7-day ML hazard forecast
    lightning: (id) => `/sites/${segment(id)}/lightning`, // GET    [PLANNED] last strike within 10 mi
  },

  alerts: {
    list: '/alerts', //                                      GET    [PLANNED] ?active=true&siteId=
    acknowledge: (id) => `/alerts/${segment(id)}/ack`, //    POST   [PLANNED]
    stream: '/alerts/stream', //                             GET    [PLANNED] Server-Sent Events push channel
  },

  reports: {
    list: '/reports', //                                     GET    [PLANNED] ?siteId=&status=
    create: '/reports', //                                   POST   [PLANNED] multipart (photo)
    detail: (id) => `/reports/${segment(id)}`, //            PATCH  [PLANNED] (supervisor) moderation
  },

  briefings: {
    list: '/briefings', //                                   GET    [PLANNED] ?date=YYYY-MM-DD
    create: '/briefings', //                                 POST   [PLANNED] (supervisor) send briefings now
    detail: (siteId) => `/briefings/${segment(siteId)}`, //  GET    [PLANNED] next-day briefing for a site
  },

  settings: {
    alertRules: '/settings/alert-rules', //                  GET / PUT [PLANNED] (supervisor for PUT)
    briefings: '/settings/briefings', //                     GET / PUT [PLANNED] (supervisor)
  },

  stats: '/stats', //                                        GET    [PLANNED] (supervisor) Manage › Overview numbers
  chat: '/chat', //                                          POST   [PLANNED] AI assistant reply (backend calls Claude)
};
