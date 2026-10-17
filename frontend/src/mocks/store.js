// =============================================================================
// MOCK STORE - in-memory "database" used while VITE_USE_MOCKS=true.
// Supervisor edits (Manage panel) change this object, so they last until the page reloads.
// Delete this folder once every service in src/api/ uses the real REST API.
// =============================================================================
import { PLANTS } from './plants.js';
import { buildSiteHazards } from './generators.js';

const minutesAgo = (m) => new Date(Date.now() - m * 60000).toISOString();

// Sites = real plant locations + generated hazard picture.
const sites = PLANTS.map((plant) => ({ ...plant, active: true, ...buildSiteHazards(plant) }));

// Most recent lightning strike within 10 mi for high-lightning sites.
const lightning = {};
sites
  .filter((s) => s.hazards.lightning >= 7)
  .forEach((s, i) => {
    lightning[s.id] = { lastStrikeAt: minutesAgo(3 + i * 4), distanceMiles: 2 + (i % 7) };
  });

// Alerts the backend monitors would raise from the conditions above.
const alerts = [];
for (const site of sites) {
  if (lightning[site.id]) {
    alerts.push({
      id: `a-lightning-${site.id}`,
      siteId: site.id,
      siteName: site.name,
      type: 'lightning',
      severity: 'stop-work',
      title: 'STOP WORK: lightning within 10 miles',
      message: `Strike detected ${lightning[site.id].distanceMiles} mi away. 30-minute all-clear countdown resets with each new strike.`,
      createdAt: lightning[site.id].lastStrikeAt,
      active: true,
      acknowledged: false,
    });
  }
  if (site.waterway && site.hazards.flooding >= 7) {
    alerts.push({
      id: `a-flood-${site.id}`,
      siteId: site.id,
      siteName: site.name,
      type: 'flooding',
      severity: 'warning',
      title: 'Flood-risk warning',
      message: `${site.conditions.precip24hIn}" of rain overnight; ${site.waterway} at ${site.conditions.riverStageFt} ft and rising.`,
      createdAt: minutesAgo(90),
      active: true,
      acknowledged: false,
    });
  }
  if (site.conditions.heatIndexF >= 105) {
    alerts.push({
      id: `a-heat-${site.id}`,
      siteId: site.id,
      siteName: site.name,
      type: 'heat',
      severity: 'warning',
      title: 'Extreme heat advisory',
      message: `Heat index forecast to reach ${site.conditions.heatIndexF}°F. Enforce water-rest-shade.`,
      createdAt: minutesAgo(180),
      active: true,
      acknowledged: false,
    });
  }
}
alerts.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

export const mockStore = {
  sites,
  lightning,
  alerts,

  // Demo accounts. Mock login accepts any non-empty password. Only two roles:
  // supervisors hold all management privileges (there is no admin account).
  users: [
    { id: 1, username: 'supervisor', email: 'supervisor@planit.dev', role: 'supervisor' },
    { id: 2, username: 'crew', email: 'crew@planit.dev', role: 'crew' },
  ],

  // Crew hazard reports (the gator sighting from the brief included).
  reports: [
    { id: 'r-1', siteId: 'turkey-point', type: 'wildlife', description: 'Alligator (~8 ft) in the canal next to the temporary road entrance.', lat: 25.4381, lng: -80.3352, photoUrl: null, reportedBy: 'crew', createdAt: minutesAgo(60 * 20), status: 'verified' },
    { id: 'r-2', siteId: 'turkey-point', type: 'soil', description: 'Track loader sunk to the axles at mat section 4. Ground is muck.', lat: 25.4342, lng: -80.3291, photoUrl: null, reportedBy: 'crew', createdAt: minutesAgo(60 * 3), status: 'open' },
    { id: 'r-3', siteId: 'grand-gulf', type: 'flooding', description: 'Standing water over the laydown yard access road.', lat: 32.0091, lng: -91.0502, photoUrl: null, reportedBy: 'supervisor', createdAt: minutesAgo(45), status: 'open' },
    { id: 'r-4', siteId: 'palo-verde', type: 'heat', description: 'Two crew members showing heat exhaustion symptoms; moved to cooling trailer.', lat: 33.3895, lng: -112.8601, photoUrl: null, reportedBy: 'crew', createdAt: minutesAgo(60 * 26), status: 'resolved' },
    { id: 'r-5', siteId: 'diablo-canyon', type: 'debris', description: 'Fallen eucalyptus limb blocking north access road.', lat: 35.2131, lng: -120.8531, photoUrl: null, reportedBy: 'crew', createdAt: minutesAgo(60 * 6), status: 'open' },
  ],

  // Thresholds used by the backend alert monitors (supervisors edit them in Manage › Alert rules).
  alertRules: {
    lightningRadiusMiles: 10,
    lightningAllClearMinutes: 30,
    floodRainInches: 2,
    heatIndexF: 105,
    windMph: 35,
    hazardIndexAlert: 7.5,
  },

  // 6 PM next-day briefing configuration.
  briefingSettings: {
    enabled: true,
    localTime: '18:00',
    channels: { email: true, sms: true, push: true },
    recipients: ['crew', 'supervisor'],
  },
};
