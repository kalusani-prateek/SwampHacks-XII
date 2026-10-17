// Live environmental readings for a site (weather, soil, river, lightning).

// label, unit and formatter for each reading the backend returns.
const READINGS = [
  { key: 'tempF', label: 'Temperature', unit: '°F' },
  { key: 'heatIndexF', label: 'Heat index', unit: '°F' },
  { key: 'humidityPct', label: 'Humidity', unit: '%' },
  { key: 'windMph', label: 'Wind', unit: ' mph' },
  { key: 'precip24hIn', label: 'Rain (24 h)', unit: '"' },
  { key: 'soilMoisturePct', label: 'Soil moisture', unit: '%' },
  { key: 'lightningStrikes1h', label: 'Strikes (1 h, 10 mi)', unit: '' },
  { key: 'riverStageFt', label: 'River stage', unit: ' ft' },
  { key: 'fireWeatherIndex', label: 'Fire weather idx', unit: '' },
];

export default function ConditionsGrid({ conditions }) {
  return (
    <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {READINGS.filter((r) => conditions[r.key] != null).map((r) => (
        <div key={r.key} className="rounded-lg bg-slate-50 p-3">
          <dt className="text-xs text-slate-500">{r.label}</dt>
          <dd className="text-lg font-semibold tabular-nums text-navy-800">
            {conditions[r.key]}
            {r.unit}
          </dd>
        </div>
      ))}
    </dl>
  );
}
