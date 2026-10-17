// Helpers for presenting the 0-10 hazard index consistently across the app.

/** Hazard categories the platform tracks per site (matches the brief). */
export const HAZARD_TYPES = {
  heat: { label: 'Extreme heat', icon: '🌡️' },
  lightning: { label: 'Lightning', icon: '⚡' },
  flooding: { label: 'Flooding', icon: '🌊' },
  wildfire: { label: 'Wildfire', icon: '🔥' },
  soil: { label: 'Soil saturation', icon: '🟫' },
  wildlife: { label: 'Wildlife', icon: '🐊' },
  wind: { label: 'Wind / storms', icon: '🌪️' },
};

/** Types a crew member can choose when filing a hazard report. */
export const REPORT_TYPES = {
  ...HAZARD_TYPES,
  debris: { label: 'Debris / obstruction', icon: '🚧' },
  equipment: { label: 'Equipment stuck / damaged', icon: '🚜' },
  other: { label: 'Other', icon: '⚠️' },
};

// Score bands. `max` is inclusive of the upper bound of the band.
const LEVELS = [
  { max: 2.5, label: 'Low', decision: 'GO', badge: 'bg-emerald-100 text-emerald-800', hex: '#10b981' },
  { max: 5, label: 'Moderate', decision: 'GO', badge: 'bg-yellow-100 text-yellow-800', hex: '#eab308' },
  { max: 7.5, label: 'High', decision: 'CAUTION', badge: 'bg-orange-100 text-orange-800', hex: '#f97316' },
  { max: 10, label: 'Extreme', decision: 'NO-GO', badge: 'bg-red-100 text-red-800', hex: '#dc2626' },
];

/** Map a 0-10 score to its band (label, go/no-go decision, colors). */
export function getHazardLevel(score) {
  return LEVELS.find((level) => score <= level.max) ?? LEVELS[LEVELS.length - 1];
}

/** Sort sites so the riskiest is first (used by dashboard + Manage overview). */
export function rankByRisk(sites) {
  return [...sites].sort((a, b) => b.hazardIndex - a.hazardIndex);
}
