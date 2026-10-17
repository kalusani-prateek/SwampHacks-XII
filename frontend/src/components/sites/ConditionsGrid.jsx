// Live environmental readings for a site (weather, soil, river, lightning).

// Label and unit for each reading. Readings a site doesn't have are hidden.
// Sources: Open-Meteo (weather, soil), NOAA GOES (lightning), USGS (river),
// NASA FIRMS (fires), iNaturalist (wildlife), National Weather Service (alerts).
const READINGS = [
  { key: 'tempF', label: 'Temperature', unit: '°F' },
  { key: 'heatIndexF', label: 'Heat index', unit: '°F' },
  { key: 'humidityPct', label: 'Humidity', unit: '%' },
  { key: 'windMph', label: 'Wind', unit: ' mph' },
  { key: 'windGustMph', label: 'Gusts', unit: ' mph' },
  { key: 'precip24hIn', label: 'Rain (24 h)', unit: '"' },
  { key: 'soilMoisturePct', label: 'Soil moisture', unit: '%' },
  { key: 'lightningStrikes1h', label: 'Strikes (1 h, 10 mi)', unit: '' },
  { key: 'riverStageFt', label: 'River stage', unit: ' ft' },
  { key: 'riverChange24hFt', label: 'River change (24 h)', unit: ' ft', signed: true },
  { key: 'nearestFireMiles', label: 'Nearest fire', unit: ' mi' },
  { key: 'wildlifeSightings30d', label: 'Wildlife sightings (30 d)', unit: '' },
  { key: 'nwsAlerts', label: 'NWS alerts in effect', unit: '' },
  { key: 'fireWeatherIndex', label: 'Fire weather idx', unit: '' },
  { key: 'modelRiskPct', label: 'ML model risk today', unit: '%' },
];

export default function ConditionsGrid({ conditions }) {
  return (
    <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {READINGS.filter((r) => conditions[r.key] != null).map((r) => (
        <div key={r.key} className="rounded-lg bg-slate-50 p-3">
          <dt className="text-xs text-slate-500">{r.label}</dt>
          <dd className="text-lg font-semibold tabular-nums text-navy-800">
            {r.signed && conditions[r.key] > 0 ? '+' : ''}
            {conditions[r.key]}
            {r.unit}
          </dd>
        </div>
      ))}
    </dl>
  );
}
