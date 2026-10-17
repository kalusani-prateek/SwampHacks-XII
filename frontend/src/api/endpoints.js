// =============================================================================
// REST API endpoint map - single source of truth for every backend route the
// frontend uses. Paths are relative to API_BASE_URL ("/api").
// Full request/response contracts: docs/API.md (implemented in backend/app/api/)
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
    login: '/auth/login', //       POST
    logout: '/auth/logout', //     POST
    register: '/auth/register', // POST  new accounts are crew
    me: '/auth/me', //             GET   current session user
  },

  users: {
    list: '/users', //                                       GET    (supervisor)
    create: '/users', //                                     POST   (supervisor)
    detail: (id) => `/users/${segment(id)}`, //              GET / PUT / DELETE self or supervisor; `role` changes supervisor-only
  },

  sites: {
    list: '/sites', //                                       GET    ?includeInactive=true (supervisor)
    options: '/sites/options', //                            GET    public: { id, name, state } for the sign-up form
    create: '/sites', //                                     POST   (supervisor)
    detail: (id) => `/sites/${segment(id)}`, //              GET    · PUT / DELETE (supervisor)
    forecast: (id) => `/sites/${segment(id)}/forecast`, //   GET    7-day hazard forecast
    lightning: (id) => `/sites/${segment(id)}/lightning`, // GET    last strike within 10 mi
    simulateStrike: (id) => `/sites/${segment(id)}/lightning/simulate`, // POST (supervisor, demo tools only)
  },

  alerts: {
    list: '/alerts', //                                      GET    ?active=true&siteId=
    acknowledge: (id) => `/alerts/${segment(id)}/ack`, //    POST
    stream: '/alerts/stream', //                             GET    Server-Sent Events push channel
  },

  reports: {
    list: '/reports', //                                     GET    ?siteId=&type=&status=&days=&q=&mine=true
    create: '/reports', //                                   POST   multipart (photo)
    detail: (id) => `/reports/${segment(id)}`, //            PATCH / DELETE  reporter or supervisor (status: supervisor)
  },

  briefings: {
    list: '/briefings', //                                   GET    ?date=YYYY-MM-DD
    create: '/briefings', //                                 POST   (supervisor) send briefings now
    detail: (siteId) => `/briefings/${segment(siteId)}`, //  GET    next-day briefing for a site
  },

  settings: {
    alertRules: '/settings/alert-rules', //                  GET / PUT (supervisor for PUT)
    briefings: '/settings/briefings', //                     GET / PUT (supervisor)
  },

  stats: '/stats', //                                        GET    (supervisor) Manage › Overview numbers
  notifications: '/notifications', //                        GET    (supervisor) recent emails/texts (outbox)
  chat: '/chat', //                                          POST   AI assistant reply (backend calls Gemini or Claude)
  meta: '/meta', //                                          GET    public server info and feature flags
};
