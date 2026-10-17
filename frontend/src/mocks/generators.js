// =============================================================================
// MOCK DATA GENERATORS
// Stand-ins for backend logic so the UI can be built before the API exists:
//   buildSiteHazards -> backend data ingestion + ML hazard index (GET /api/sites)
//   buildForecast    -> ML 7-day forecast              (GET /api/sites/:id/forecast)
//   buildBriefing    -> 6 PM next-day briefing job     (GET /api/briefings)
// A seeded random generator keeps the numbers the same between reloads.
// =============================================================================
import { getHazardLevel, HAZARD_TYPES } from '../utils/hazard.js';

/** Deterministic PRNG (mulberry32) seeded from a string. */
function seededRandom(seedText) {
  let seed = [...seedText].reduce((acc, ch) => (acc * 31 + ch.charCodeAt(0)) >>> 0, 7);
  return () => {
    seed = (seed + 0x6d2b79f5) >>> 0;
    let t = seed;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const round1 = (n) => Math.round(n * 10) / 10;
const clamp = (n, min = 0, max = 10) => Math.min(max, Math.max(min, n));

// Baseline hazard score (0-10) per regional profile; noise is added per site.
const PROFILE_BASELINES = {
  florida: { heat: 8, lightning: 7, flooding: 5, wildfire: 2, soil: 7, wildlife: 7, wind: 4 },
  gulf: { heat: 7.5, lightning: 6, flooding: 7, wildfire: 2, soil: 6, wildlife: 5, wind: 5 },
  river: { heat: 5, lightning: 4, flooding: 7.5, wildfire: 1, soil: 6.5, wildlife: 2, wind: 3 },
  southwest: { heat: 8.5, lightning: 3, flooding: 1.5, wildfire: 6, soil: 1, wildlife: 2, wind: 4 },
  west: { heat: 4, lightning: 2, flooding: 1.5, wildfire: 7, soil: 2, wildlife: 2.5, wind: 5 },
  southeast: { heat: 6, lightning: 5.5, flooding: 3.5, wildfire: 2.5, soil: 4.5, wildlife: 2.5, wind: 3 },
  midwest: { heat: 4, lightning: 4.5, flooding: 4, wildfire: 1.5, soil: 4, wildlife: 1, wind: 6 },
  northeast: { heat: 3, lightning: 3, flooding: 3, wildfire: 1, soil: 3.5, wildlife: 1, wind: 4.5 },
};

/**
 * Combine per-hazard scores into one 0-10 index. Weighted toward the worst
 * hazard: one extreme hazard should dominate the go/no-go call.
 * (Placeholder for the ML model's output.)
 */
export function combineHazards(hazards) {
  const scores = Object.values(hazards).sort((a, b) => b - a);
  const mean = scores.reduce((sum, s) => sum + s, 0) / scores.length;
  return round1(clamp(0.6 * scores[0] + 0.25 * scores[1] + 0.15 * mean));
}

/** Per-hazard scores, live conditions and plain-language risk drivers for a plant. */
export function buildSiteHazards(plant) {
  const rand = seededRandom(plant.id);
  const base = PROFILE_BASELINES[plant.profile];

  const hazards = {};
  for (const key of Object.keys(HAZARD_TYPES)) {
    hazards[key] = round1(clamp(base[key] + (rand() - 0.5) * 4));
  }
  // Only sites on a waterway can flood from river rise.
  if (!plant.waterway) hazards.flooding = round1(Math.min(hazards.flooding, 3));

  // Live conditions roughly consistent with the scores.
  const conditions = {
    tempF: Math.round(70 + hazards.heat * 2.6),
    heatIndexF: Math.round(72 + hazards.heat * 4.2),
    humidityPct: Math.round(40 + hazards.soil * 5),
    windMph: Math.round(4 + hazards.wind * 3.5),
    precip24hIn: round1(hazards.flooding * 0.35 + rand() * 0.5),
    soilMoisturePct: Math.round(15 + hazards.soil * 7),
    lightningStrikes1h: hazards.lightning > 6 ? Math.round(rand() * 40 + 5) : 0,
    riverStageFt: plant.waterway ? round1(8 + hazards.flooding * 2.2) : null,
    fireWeatherIndex: round1(hazards.wildfire * 9),
  };

  return {
    hazards,
    hazardIndex: combineHazards(hazards),
    conditions,
    drivers: describeDrivers(hazards, conditions, plant),
    updatedAt: new Date().toISOString(),
  };
}

/** Plain-language reasons behind the top hazards. */
function describeDrivers(hazards, c, plant) {
  const text = {
    heat: `Heat index ${c.heatIndexF}°F by midday`,
    lightning: c.lightningStrikes1h ? `${c.lightningStrikes1h} lightning strikes in the last hour nearby` : 'Afternoon thunderstorms possible',
    flooding: plant.waterway ? `${plant.waterway} stage ${c.riverStageFt} ft after ${c.precip24hIn}" of rain` : `${c.precip24hIn}" of rain in 24 h`,
    wildfire: `Fire weather index ${c.fireWeatherIndex} (dry fuels, low humidity)`,
    soil: `Soil moisture ${c.soilMoisturePct}%: soft ground, vehicles may get stuck`,
    wildlife: plant.profile === 'florida' ? 'Alligator activity reported near water edges' : 'Wildlife sightings reported near site',
    wind: `Sustained wind ${c.windMph} mph: crane / aerial lift limits`,
  };
  return Object.entries(hazards)
    .filter(([, score]) => score >= 5)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([key]) => text[key]);
}

/**
 * Calendar date (YYYY-MM-DD) `offsetDays` from today in the site's own time
 * zone. Using UTC instead would make "tomorrow" skip a day every US evening.
 */
function siteLocalDate(timeZone, offsetDays) {
  const today = new Intl.DateTimeFormat('en-CA', { timeZone }).format(new Date()); // en-CA formats as YYYY-MM-DD
  const date = new Date(`${today}T12:00:00Z`); // noon UTC keeps day math clear of DST edges
  date.setUTCDate(date.getUTCDate() + offsetDays);
  return date.toISOString().slice(0, 10);
}

/** 7-day hazard forecast starting tomorrow (site-local dates). */
export function buildForecast(site) {
  const rand = seededRandom(`${site.id}-forecast`);
  const topHazard = Object.entries(site.hazards).sort((a, b) => b[1] - a[1])[0][0];
  return Array.from({ length: 7 }, (_, i) => {
    return {
      date: siteLocalDate(site.timezone, i + 1),
      hazardIndex: round1(clamp(site.hazardIndex + (rand() - 0.5) * 3)),
      topHazard,
    };
  });
}

// Recommended controls for each hazard, used in briefings.
const CONTROLS = {
  heat: 'Water-rest-shade: 15 min rest every hour in shade; start heavy work at first light.',
  lightning: 'Stop work for any strike within 10 mi; resume only after a 30-minute all-clear.',
  flooding: 'Keep off low ground and levee toes; check river stage before mobilizing equipment.',
  wildfire: 'No hot work; stage extinguishers; plan two evacuation routes.',
  soil: 'Use mats / temporary road; no heavy equipment on saturated ground.',
  wildlife: 'Spotter on water edges; keep 30 ft from alligators and snakes; report sightings in app.',
  wind: 'Ground cranes and aerial lifts above manufacturer wind limits.',
};

/** Next-day safety briefing as the 6 PM job would produce it. */
export function buildBriefing(site) {
  const [tomorrow] = buildForecast(site);
  const level = getHazardLevel(tomorrow.hazardIndex);
  const topHazards = Object.entries(site.hazards)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([key, score]) => ({ key, score, control: CONTROLS[key] }));

  return {
    siteId: site.id,
    siteName: site.name,
    state: site.state,
    timezone: site.timezone,
    forDate: tomorrow.date,
    hazardIndex: tomorrow.hazardIndex,
    decision: level.decision,
    summary: `${level.label} risk expected tomorrow at ${site.name}. Primary concern: ${HAZARD_TYPES[topHazards[0].key].label.toLowerCase()}.`,
    topHazards,
  };
}
