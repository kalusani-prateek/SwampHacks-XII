// =============================================================================
// MOCK DATA - 58 real U.S. power plant locations used as job sites.
// Coordinates are approximate, taken from public plant records. In production
// this list comes from the backend, which imports EIA-860M
// (REST API PLACEHOLDER: GET /api/sites).
//
// `profile` picks which hazards the mock generator weights most heavily:
//   florida   - heat, lightning, wildlife (alligators), soil saturation
//   gulf      - heat, flooding, lightning, wind
//   river     - flooding + soil saturation (Mississippi / Ohio / Missouri / Tennessee)
//   southwest - extreme heat, wildfire
//   west      - wildfire, wind
//   southeast - heat, lightning
//   midwest   - wind / severe storms, flooding
//   northeast - wind, mild heat
// =============================================================================

const ET = 'America/New_York';
const CT = 'America/Chicago';
const MT = 'America/Denver';
const AZ = 'America/Phoenix';
const PT = 'America/Los_Angeles';

export const PLANTS = [
  // ---- Florida -------------------------------------------------------------
  { id: 'turkey-point', name: 'Turkey Point', state: 'FL', lat: 25.4356, lng: -80.3308, plantType: 'Nuclear / Gas', utility: 'Florida Power & Light', timezone: ET, profile: 'florida', waterway: 'Biscayne Bay' },
  { id: 'st-lucie', name: 'St. Lucie', state: 'FL', lat: 27.3487, lng: -80.2464, plantType: 'Nuclear', utility: 'Florida Power & Light', timezone: ET, profile: 'florida', waterway: 'Atlantic Ocean' },
  { id: 'martin', name: 'Martin', state: 'FL', lat: 27.0536, lng: -80.5639, plantType: 'Natural Gas / Solar', utility: 'Florida Power & Light', timezone: ET, profile: 'florida', waterway: null },
  { id: 'manatee', name: 'Manatee', state: 'FL', lat: 27.6061, lng: -82.3453, plantType: 'Natural Gas', utility: 'Florida Power & Light', timezone: ET, profile: 'florida', waterway: null },
  { id: 'west-county', name: 'West County Energy Center', state: 'FL', lat: 26.6983, lng: -80.3747, plantType: 'Natural Gas', utility: 'Florida Power & Light', timezone: ET, profile: 'florida', waterway: null },
  { id: 'fort-myers', name: 'Fort Myers', state: 'FL', lat: 26.6967, lng: -81.7828, plantType: 'Natural Gas', utility: 'Florida Power & Light', timezone: ET, profile: 'florida', waterway: 'Caloosahatchee River' },
  { id: 'riviera-beach', name: 'Riviera Beach', state: 'FL', lat: 26.7653, lng: -80.0525, plantType: 'Natural Gas', utility: 'Florida Power & Light', timezone: ET, profile: 'florida', waterway: 'Lake Worth Lagoon' },
  { id: 'port-everglades', name: 'Port Everglades', state: 'FL', lat: 26.0856, lng: -80.1253, plantType: 'Natural Gas', utility: 'Florida Power & Light', timezone: ET, profile: 'florida', waterway: 'Port Everglades' },
  { id: 'lauderdale', name: 'Lauderdale', state: 'FL', lat: 26.0686, lng: -80.1983, plantType: 'Natural Gas', utility: 'Florida Power & Light', timezone: ET, profile: 'florida', waterway: null },
  { id: 'cape-canaveral', name: 'Cape Canaveral Energy Center', state: 'FL', lat: 28.4697, lng: -80.7647, plantType: 'Natural Gas', utility: 'Florida Power & Light', timezone: ET, profile: 'florida', waterway: 'Indian River' },
  { id: 'sanford', name: 'Sanford', state: 'FL', lat: 28.8417, lng: -81.325, plantType: 'Natural Gas', utility: 'Florida Power & Light', timezone: ET, profile: 'florida', waterway: 'St. Johns River' },
  { id: 'crystal-river', name: 'Crystal River', state: 'FL', lat: 28.9573, lng: -82.6993, plantType: 'Coal / Gas', utility: 'Duke Energy Florida', timezone: ET, profile: 'florida', waterway: 'Gulf of Mexico' },
  { id: 'big-bend', name: 'Big Bend', state: 'FL', lat: 27.7944, lng: -82.4036, plantType: 'Natural Gas / Coal', utility: 'Tampa Electric', timezone: ET, profile: 'florida', waterway: 'Tampa Bay' },
  { id: 'deerhaven', name: 'Deerhaven', state: 'FL', lat: 29.7583, lng: -82.3886, plantType: 'Natural Gas / Coal', utility: 'Gainesville Regional Utilities', timezone: ET, profile: 'florida', waterway: null },

  // ---- Lower Mississippi / Gulf Coast --------------------------------------
  { id: 'grand-gulf', name: 'Grand Gulf', state: 'MS', lat: 32.0072, lng: -91.0481, plantType: 'Nuclear', utility: 'Entergy', timezone: CT, profile: 'river', waterway: 'Mississippi River' },
  { id: 'waterford', name: 'Waterford 3', state: 'LA', lat: 29.9953, lng: -90.4711, plantType: 'Nuclear', utility: 'Entergy', timezone: CT, profile: 'gulf', waterway: 'Mississippi River' },
  { id: 'river-bend', name: 'River Bend', state: 'LA', lat: 30.757, lng: -91.333, plantType: 'Nuclear', utility: 'Entergy', timezone: CT, profile: 'gulf', waterway: 'Mississippi River' },
  { id: 'big-cajun-2', name: 'Big Cajun II', state: 'LA', lat: 30.7264, lng: -91.3667, plantType: 'Coal', utility: 'Cleco', timezone: CT, profile: 'gulf', waterway: 'Mississippi River' },
  { id: 'wa-parish', name: 'W.A. Parish', state: 'TX', lat: 29.4828, lng: -95.6311, plantType: 'Coal / Gas', utility: 'NRG Energy', timezone: CT, profile: 'gulf', waterway: 'Brazos River' },
  { id: 'south-texas', name: 'South Texas Project', state: 'TX', lat: 28.795, lng: -96.0481, plantType: 'Nuclear', utility: 'STP Nuclear Operating Co.', timezone: CT, profile: 'gulf', waterway: 'Colorado River (TX)' },

  // ---- Upper Mississippi / Ohio / Missouri rivers --------------------------
  { id: 'rush-island', name: 'Rush Island', state: 'MO', lat: 38.1306, lng: -90.2625, plantType: 'Coal', utility: 'Ameren Missouri', timezone: CT, profile: 'river', waterway: 'Mississippi River' },
  { id: 'labadie', name: 'Labadie', state: 'MO', lat: 38.5622, lng: -90.8375, plantType: 'Coal', utility: 'Ameren Missouri', timezone: CT, profile: 'river', waterway: 'Missouri River' },
  { id: 'sioux', name: 'Sioux', state: 'MO', lat: 38.915, lng: -90.29, plantType: 'Coal', utility: 'Ameren Missouri', timezone: CT, profile: 'river', waterway: 'Mississippi River' },
  { id: 'baldwin', name: 'Baldwin', state: 'IL', lat: 38.205, lng: -89.855, plantType: 'Coal', utility: 'Vistra', timezone: CT, profile: 'river', waterway: 'Kaskaskia River' },
  { id: 'quad-cities', name: 'Quad Cities', state: 'IL', lat: 41.7261, lng: -90.31, plantType: 'Nuclear', utility: 'Constellation', timezone: CT, profile: 'river', waterway: 'Mississippi River' },
  { id: 'prairie-island', name: 'Prairie Island', state: 'MN', lat: 44.6219, lng: -92.6331, plantType: 'Nuclear', utility: 'Xcel Energy', timezone: CT, profile: 'river', waterway: 'Mississippi River' },
  { id: 'gibson', name: 'Gibson', state: 'IN', lat: 38.3722, lng: -87.7656, plantType: 'Coal', utility: 'Duke Energy Indiana', timezone: CT, profile: 'river', waterway: 'Wabash River' },
  { id: 'browns-ferry', name: 'Browns Ferry', state: 'AL', lat: 34.7042, lng: -87.1186, plantType: 'Nuclear', utility: 'Tennessee Valley Authority', timezone: CT, profile: 'river', waterway: 'Tennessee River' },
  { id: 'cumberland', name: 'Cumberland', state: 'TN', lat: 36.3903, lng: -87.6539, plantType: 'Coal', utility: 'Tennessee Valley Authority', timezone: CT, profile: 'river', waterway: 'Cumberland River' },
  { id: 'watts-bar', name: 'Watts Bar', state: 'TN', lat: 35.6022, lng: -84.7894, plantType: 'Nuclear', utility: 'Tennessee Valley Authority', timezone: ET, profile: 'river', waterway: 'Tennessee River' },

  // ---- Southeast -----------------------------------------------------------
  { id: 'vogtle', name: 'Vogtle', state: 'GA', lat: 33.1417, lng: -81.7625, plantType: 'Nuclear', utility: 'Georgia Power', timezone: ET, profile: 'southeast', waterway: 'Savannah River' },
  { id: 'scherer', name: 'Scherer', state: 'GA', lat: 33.0614, lng: -83.8072, plantType: 'Coal', utility: 'Georgia Power', timezone: ET, profile: 'southeast', waterway: null },
  { id: 'bowen', name: 'Bowen', state: 'GA', lat: 34.1256, lng: -84.9192, plantType: 'Coal', utility: 'Georgia Power', timezone: ET, profile: 'southeast', waterway: 'Etowah River' },
  { id: 'oconee', name: 'Oconee', state: 'SC', lat: 34.7939, lng: -82.8986, plantType: 'Nuclear', utility: 'Duke Energy', timezone: ET, profile: 'southeast', waterway: 'Lake Keowee' },
  { id: 'catawba', name: 'Catawba', state: 'SC', lat: 35.0514, lng: -81.0697, plantType: 'Nuclear', utility: 'Duke Energy', timezone: ET, profile: 'southeast', waterway: 'Lake Wylie' },
  { id: 'mcguire', name: 'McGuire', state: 'NC', lat: 35.4325, lng: -80.9483, plantType: 'Nuclear', utility: 'Duke Energy', timezone: ET, profile: 'southeast', waterway: 'Lake Norman' },
  { id: 'north-anna', name: 'North Anna', state: 'VA', lat: 38.0606, lng: -77.7897, plantType: 'Nuclear', utility: 'Dominion Energy', timezone: ET, profile: 'southeast', waterway: 'Lake Anna' },

  // ---- Mid-Atlantic / Northeast / Great Lakes ------------------------------
  { id: 'calvert-cliffs', name: 'Calvert Cliffs', state: 'MD', lat: 38.4347, lng: -76.4417, plantType: 'Nuclear', utility: 'Constellation', timezone: ET, profile: 'northeast', waterway: 'Chesapeake Bay' },
  { id: 'peach-bottom', name: 'Peach Bottom', state: 'PA', lat: 39.7589, lng: -76.2689, plantType: 'Nuclear', utility: 'Constellation', timezone: ET, profile: 'northeast', waterway: 'Susquehanna River' },
  { id: 'limerick', name: 'Limerick', state: 'PA', lat: 40.2242, lng: -75.5872, plantType: 'Nuclear', utility: 'Constellation', timezone: ET, profile: 'northeast', waterway: 'Schuylkill River' },
  { id: 'susquehanna', name: 'Susquehanna', state: 'PA', lat: 41.0889, lng: -76.1467, plantType: 'Nuclear', utility: 'Talen Energy', timezone: ET, profile: 'northeast', waterway: 'Susquehanna River' },
  { id: 'millstone', name: 'Millstone', state: 'CT', lat: 41.3089, lng: -72.1681, plantType: 'Nuclear', utility: 'Dominion Energy', timezone: ET, profile: 'northeast', waterway: 'Long Island Sound' },
  { id: 'seabrook', name: 'Seabrook', state: 'NH', lat: 42.8989, lng: -70.8508, plantType: 'Nuclear', utility: 'NextEra Energy', timezone: ET, profile: 'northeast', waterway: 'Atlantic Ocean' },
  { id: 'nine-mile-point', name: 'Nine Mile Point', state: 'NY', lat: 43.5222, lng: -76.41, plantType: 'Nuclear', utility: 'Constellation', timezone: ET, profile: 'northeast', waterway: 'Lake Ontario' },
  { id: 'niagara', name: 'Robert Moses Niagara', state: 'NY', lat: 43.1428, lng: -79.0397, plantType: 'Hydro', utility: 'New York Power Authority', timezone: ET, profile: 'northeast', waterway: 'Niagara River' },
  { id: 'fermi-2', name: 'Fermi 2', state: 'MI', lat: 41.9631, lng: -83.2578, plantType: 'Nuclear', utility: 'DTE Energy', timezone: ET, profile: 'midwest', waterway: 'Lake Erie' },

  // ---- Midwest / Plains ----------------------------------------------------
  { id: 'byron', name: 'Byron', state: 'IL', lat: 42.075, lng: -89.2819, plantType: 'Nuclear', utility: 'Constellation', timezone: CT, profile: 'midwest', waterway: 'Rock River' },
  { id: 'braidwood', name: 'Braidwood', state: 'IL', lat: 41.2433, lng: -88.2292, plantType: 'Nuclear', utility: 'Constellation', timezone: CT, profile: 'midwest', waterway: 'Kankakee River' },
  { id: 'wolf-creek', name: 'Wolf Creek', state: 'KS', lat: 38.2389, lng: -95.6889, plantType: 'Nuclear', utility: 'Evergy', timezone: CT, profile: 'midwest', waterway: null },
  { id: 'comanche-peak', name: 'Comanche Peak', state: 'TX', lat: 32.2983, lng: -97.7853, plantType: 'Nuclear', utility: 'Vistra', timezone: CT, profile: 'midwest', waterway: 'Squaw Creek Reservoir' },

  // ---- Mountain West / Southwest / Pacific ---------------------------------
  { id: 'palo-verde', name: 'Palo Verde', state: 'AZ', lat: 33.3881, lng: -112.8617, plantType: 'Nuclear', utility: 'Arizona Public Service', timezone: AZ, profile: 'southwest', waterway: null },
  { id: 'four-corners', name: 'Four Corners', state: 'NM', lat: 36.69, lng: -108.4811, plantType: 'Coal', utility: 'Arizona Public Service', timezone: MT, profile: 'southwest', waterway: 'Morgan Lake' },
  { id: 'hoover-dam', name: 'Hoover Dam', state: 'NV', lat: 36.0156, lng: -114.7378, plantType: 'Hydro', utility: 'U.S. Bureau of Reclamation', timezone: PT, profile: 'southwest', waterway: 'Colorado River' },
  { id: 'intermountain', name: 'Intermountain', state: 'UT', lat: 39.5097, lng: -112.5806, plantType: 'Coal / Gas', utility: 'Intermountain Power Agency', timezone: MT, profile: 'west', waterway: null },
  { id: 'colstrip', name: 'Colstrip', state: 'MT', lat: 45.8836, lng: -106.6139, plantType: 'Coal', utility: 'Talen Energy', timezone: MT, profile: 'west', waterway: null },
  { id: 'diablo-canyon', name: 'Diablo Canyon', state: 'CA', lat: 35.2114, lng: -120.8544, plantType: 'Nuclear', utility: 'Pacific Gas & Electric', timezone: PT, profile: 'west', waterway: 'Pacific Ocean' },
  { id: 'grand-coulee', name: 'Grand Coulee', state: 'WA', lat: 47.9567, lng: -118.9817, plantType: 'Hydro', utility: 'U.S. Bureau of Reclamation', timezone: PT, profile: 'west', waterway: 'Columbia River' },
  { id: 'columbia', name: 'Columbia Generating Station', state: 'WA', lat: 46.4711, lng: -119.3339, plantType: 'Nuclear', utility: 'Energy Northwest', timezone: PT, profile: 'west', waterway: 'Columbia River' },
];
