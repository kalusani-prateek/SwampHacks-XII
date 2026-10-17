// =============================================================================
// MOCK CHATBOT - keyword-matching stand-in for the AI assistant so the chat UI
// works without a backend. It answers from the mock store (sites, alerts,
// rules, reports). It is NOT an AI: the real assistant is POST /api/chat, where
// the backend calls Claude with live site data (docs/API_PLAN.md § AI assistant).
// Replies are plain text with "•" bullets, the same format the real model is
// asked to use.
// =============================================================================
import { mockStore } from './store.js';
import { buildBriefing } from './generators.js';
import { getHazardLevel, HAZARD_TYPES, rankByRisk } from '../utils/hazard.js';
import { formatCountdown } from '../utils/time.js';

/** Lowercase, punctuation-free text for loose matching ("St. Lucie" -> "st lucie"). */
const normalize = (text) => ` ${text.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()} `;

const activeSites = () => mockStore.sites.filter((s) => s.active);

/** The site a question is about: a site named in the text wins over the page's site. */
function findSite(text, siteId) {
  const named = activeSites()
    .filter((s) => text.includes(normalize(s.name)))
    .sort((a, b) => b.name.length - a.name.length)[0]; // longest name wins ("Big Cajun II" over "Big")
  return named ?? activeSites().find((s) => s.id === siteId) ?? null;
}

/** Milliseconds left on a site's lightning all-clear countdown (0 = clear). */
function lightningRemainingMs(site) {
  const strike = mockStore.lightning[site.id];
  if (!strike?.lastStrikeAt) return 0;
  const end = new Date(strike.lastStrikeAt).getTime() + mockStore.alertRules.lightningAllClearMinutes * 60000;
  return Math.max(0, end - Date.now());
}

function lightningStatus(site) {
  const { lightningRadiusMiles: radius, lightningAllClearMinutes: minutes } = mockStore.alertRules;
  const remaining = lightningRemainingMs(site);
  if (remaining > 0) {
    const miles = mockStore.lightning[site.id].distanceMiles;
    return `⚡ STOP WORK at ${site.name}: strike ${miles} mi away. All-clear in ${formatCountdown(remaining)} if no new strike lands within ${radius} mi.`;
  }
  return `No lightning within ${radius} mi of ${site.name} in the last ${minutes} min.`;
}

function siteSummary(site) {
  const level = getHazardLevel(site.hazardIndex);
  return [
    `${site.name} (${site.state}): hazard index ${site.hazardIndex.toFixed(1)}/10, ${level.label.toLowerCase()} risk, call is ${level.decision}.`,
    ...site.drivers.map((d) => `• ${d}`),
    lightningStatus(site),
  ].join('\n');
}

function topSites(count = 5) {
  const ranked = rankByRisk(activeSites()).slice(0, count);
  return [
    `Top ${count} sites by hazard index right now:`,
    ...ranked.map(
      (s, i) => `${i + 1}. ${s.name} (${s.state}): ${s.hazardIndex.toFixed(1)}, ${getHazardLevel(s.hazardIndex).decision}. ${s.drivers[0] ?? ''}`,
    ),
    'Open the PlanIt Dashboard to see them on the map.',
  ].join('\n');
}

function lightningAnswer(site) {
  const { lightningRadiusMiles: radius, lightningAllClearMinutes: minutes } = mockStore.alertRules;
  const rule = `Lightning rule: any strike within ${radius} miles means stop work and get to shelter. Work resumes only after ${minutes} minutes with no new strike; every new strike restarts the countdown.`;
  if (site) return `${rule}\n${lightningStatus(site)}`;
  const stopped = activeSites().filter((s) => lightningRemainingMs(s) > 0);
  return stopped.length
    ? `${rule}\nStop-work is in effect at ${stopped.length} site(s): ${stopped.map((s) => s.name).join(', ')}.`
    : `${rule}\nNo site is under a lightning stop-work right now.`;
}

function heatAnswer(site) {
  const limit = mockStore.alertRules.heatIndexF;
  return [
    site
      ? `Heat index at ${site.name}: ${site.conditions.heatIndexF}°F (advisory at ${limit}°F).`
      : `Heat advisories start at a ${limit}°F heat index.`,
    '• Drink about 1 cup of water every 15 to 20 minutes, even if you are not thirsty.',
    '• Take rest breaks in the shade, and more often as the heat index climbs.',
    '• Watch for dizziness, headache, nausea, confusion, or hot and dry skin.',
    '• Suspected heat stroke is an emergency: call 911 and start cooling the person right away.',
  ].join('\n');
}

function floodAnswer(site) {
  const rain = mockStore.alertRules.floodRainInches;
  const lines = [`River sites get a flood-risk warning after ${rain}" or more of overnight rain.`];
  if (site?.waterway) {
    lines.push(`${site.name} is on the ${site.waterway}: ${site.conditions.precip24hIn}" of rain in 24 h, river stage ${site.conditions.riverStageFt} ft.`);
  } else if (site) {
    lines.push(`${site.name} isn't on a river, so river-flood warnings don't apply. Soil moisture is ${site.conditions.soilMoisturePct}%, so expect soft ground.`);
  } else {
    const warned = mockStore.alerts.filter((a) => a.active && a.type === 'flooding');
    lines.push(warned.length ? `Active flood warnings: ${warned.map((a) => a.siteName).join(', ')}.` : 'No active flood warnings.');
  }
  lines.push('• Never drive or walk through floodwater. Turn around instead.');
  return lines.join('\n');
}

function wildlifeAnswer(site) {
  const sightings = mockStore.reports.filter((r) => r.type === 'wildlife' && (!site || r.siteId === site.id)).slice(0, 3);
  return [
    ...(sightings.length ? ['Recent wildlife reports:', ...sightings.map((r) => `• ${r.description}`)] : []),
    '• Keep at least 30 ft from alligators and snakes. Never approach or feed them.',
    '• Use a spotter near water edges and tall grass.',
    '• Report every sighting with Report Hazard so the next crew knows.',
  ].join('\n');
}

function briefingAnswer(site) {
  if (!site) return 'Next-day briefings go out every evening at 6:00 PM local time for each site. Ask about a specific site, for example "tomorrow at Grand Gulf".';
  const b = buildBriefing(site);
  return [
    `Tomorrow (${b.forDate}) at ${site.name}: ${b.hazardIndex.toFixed(1)}/10, ${b.decision}.`,
    b.summary,
    ...b.topHazards.map((h) => `• ${HAZARD_TYPES[h.key].label}: ${h.control}`),
  ].join('\n');
}

function alertsAnswer(site) {
  const active = mockStore.alerts.filter((a) => a.active && (!site || a.siteId === site.id));
  if (active.length === 0) return site ? `No active alerts at ${site.name}.` : 'No active alerts anywhere.';
  return [
    `${active.length} active alert(s)${site ? ` at ${site.name}` : ''}:`,
    ...active.slice(0, 5).map((a) => `• ${a.title}: ${a.siteName}`),
    ...(active.length > 5 ? [`…and ${active.length - 5} more on the Alerts page.`] : []),
  ].join('\n');
}

const HOW_TO_REPORT = [
  'To report a hazard:',
  '1. Open Report Hazard (or "+ Report hazard" on a site page).',
  '2. Tap the map where the hazard is.',
  '3. Pick the type, describe it and add a photo.',
  '4. Send. Your crew sees it right away, and it is saved for future projects at that spot.',
].join('\n');

const HELP = [
  'I can help with:',
  '• Site risk: "Is it safe to work at Turkey Point?"',
  '• Priorities: "Which sites are riskiest today?"',
  '• Lightning, heat, flooding and wildlife rules',
  '• Active alerts and tomorrow\'s briefing for a site',
  '• How to report a hazard',
].join('\n');

const EMERGENCY = 'If someone is hurt or in danger, call 911 now. Then tell your supervisor and stop work in the area. Don\'t wait on the app.';

// Checked in order; the first pattern that matches answers. Emergencies come first.
const INTENTS = [
  { pattern: /\b(911|emergency|injur\w*|hurt|bleeding|unconscious|collapsed|heat stroke|bitten)\b/, answer: () => EMERGENCY },
  { pattern: /\b(lightning|thunder\w*|strikes?)\b/, answer: lightningAnswer },
  { pattern: /\b(riskiest|worst|highest|most dangerous|focus|priorit\w*|rank\w*|which sites)\b/, answer: () => topSites() },
  { pattern: /\b(report|photo|pin)\b/, answer: () => HOW_TO_REPORT },
  { pattern: /\b(heat|hot|temperature|hydrat\w*|dehydrat\w*)\b/, answer: heatAnswer },
  { pattern: /\b(flood\w*|rain\w*|river|levee)\b/, answer: floodAnswer },
  { pattern: /\b(gators?|alligators?|snakes?|wildlife|animals?)\b/, answer: wildlifeAnswer },
  { pattern: /\b(briefing|tomorrow|forecast)\b/, answer: briefingAnswer },
  { pattern: /\b(alerts?|warnings?)\b/, answer: alertsAnswer },
  { pattern: /\b(safe|status|go|no go|conditions|work today)\b/, answer: (site) => (site ? siteSummary(site) : 'Which site? Open a site page, or name it, for example "Is it safe at Grand Gulf?"') },
  { pattern: /\b(thanks?|thank you)\b/, answer: () => 'Anytime. Stay safe out there.' },
  { pattern: /\b(hi|hello|hey|help|what can you do)\b/, answer: () => `Hi! I'm the PlanIT assistant.\n${HELP}` },
];

/**
 * Reply to the last user message.
 * @param {{ role: string, content: string }[]} messages  conversation, oldest first
 * @param {string|null} siteId                             site the user is viewing
 */
export function mockChatReply(messages, siteId) {
  const text = normalize(messages[messages.length - 1]?.content ?? '');
  const site = findSite(text, siteId);
  const intent = INTENTS.find((i) => i.pattern.test(text));
  if (intent) return intent.answer(site);
  if (site) return siteSummary(site); // just a site name, e.g. "turkey point"
  return `In demo mode I only understand a few topics, so I didn't catch that.\n${HELP}`;
}
